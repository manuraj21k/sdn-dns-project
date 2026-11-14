import json
import subprocess
import time

from webob import Response
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib import hub
from ryu.lib.packet import arp, ether_types, ethernet, ipv4, packet, udp
from ryu.ofproto import ofproto_v1_3

DNS_API_INSTANCE_NAME = 'dns_dashboard_api'

VIP_IP = '10.0.0.100'
VIP_MAC = '00:00:00:00:00:64'
DNS_PORT = 5353

SERVERS = [
    {'id': 'dns1', 'ip': '10.0.0.10'},
    {'id': 'dns2', 'ip': '10.0.0.11'},
    {'id': 'dns3', 'ip': '10.0.0.12'},
]

HEALTH_INTERVAL_SEC = 2.5


class DnsDashboardController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(DnsDashboardController, self).__init__(req, link, data, **config)
        self.dns_app = data[DNS_API_INSTANCE_NAME]

    def _cors_response(self, payload, status=200):
        res = Response(
            content_type='application/json; charset=utf-8',
            body=json.dumps(payload).encode('utf-8'),
            status=status,
        )
        res.headers['Access-Control-Allow-Origin'] = '*'
        res.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        res.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return res

    @route('dns', '/api/state', methods=['GET', 'OPTIONS'])
    def get_state(self, req, **kwargs):
        if req.method == 'OPTIONS':
            return self._cors_response({})
        return self._cors_response(self.dns_app.get_dashboard_state())

    @route('dns', '/api/lookup', methods=['POST', 'OPTIONS'])
    def run_lookup(self, req, **kwargs):
        if req.method == 'OPTIONS':
            return self._cors_response({})
        try:
            body = json.loads(req.body.decode('utf-8') or '{}')
            domain = body.get('domain', 'web.local')
            client_host = body.get('client', 'client1')
            result = self.dns_app.trigger_mininet_lookup(client_host, domain)
            return self._cors_response(result)
        except Exception as exc:
            return self._cors_response({'status': 'ERROR', 'message': str(exc)}, status=500)


class DnsLoadBalancerController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(DnsLoadBalancerController, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(DnsDashboardController, {DNS_API_INSTANCE_NAME: self})

        self.mac_to_port = {}
        self.ip_to_mac = {}  # Learned dynamically from network traffic
        self.datapaths = {}
        self.rr_index = 0

        self.event_log = []
        self.last_selected_server = None
        self.server_meta = {
            srv['ip']: {
                'id': srv['id'],
                'ip': srv['ip'],
                'status': 'UNKNOWN',
                'last_seen': 0.0,
            }
            for srv in SERVERS
        }

        self.log_event('INIT', 'SDN DNS Controller started; probing backend servers')
        self.health_thread = hub.spawn(self._health_monitor_loop)

    def log_event(self, event_type, message):
        entry = {
            'time': time.strftime('%H:%M:%S'),
            'type': event_type,
            'message': message,
        }
        self.event_log.insert(0, entry)
        self.event_log = self.event_log[:30]
        self.logger.info('[%s] %s', event_type, message)

    def get_dashboard_state(self):
        servers_list = [
            {
                'id': meta['id'],
                'ip': meta['ip'],
                'status': meta['status'],
                'last_seen': meta['last_seen'],
            }
            for meta in self.server_meta.values()
        ]
        return {
            'mode': 'DEMO MODE',
            'timestamp': time.time(),
            'stale_after_sec': 5.0,
            'selected_server': self.last_selected_server,
            'servers': servers_list,
            'events': self.event_log,
        }

    def trigger_mininet_lookup(self, client_host, domain):
        cmd = (
            f"pgrep -f 'mininet:{client_host}' | head -n 1 | "
            f"xargs -r -I {{}} sudo mnexec -a {{}} python3 dns/client.py "
            f"--id {client_host} --server {VIP_IP} --port {DNS_PORT} --name {domain} --no-cache"
        )
        t0 = time.time()
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=6)
        latency_ms = round((time.time() - t0) * 1000, 2)
        out = (proc.stdout or '').strip()

        parts = out.split()
        answer_ip = parts[2] if len(parts) > 2 and 'OK' in out else 'N/A'
        srv_ip = next((p.split('=')[1] for p in parts if p.startswith('server=') and p != 'server=-'), None)
        if not srv_ip and self.last_selected_server:
            srv_ip = self.last_selected_server
        srv_id = self.server_meta.get(srv_ip, {}).get('id', srv_ip or 'unknown')

        status = 'OK' if 'OK' in out else 'TIMEOUT'
        self.log_event('LOOKUP', f"{client_host} queried {domain} -> {answer_ip} via {srv_id} ({status})")
        return {
            'status': status,
            'domain': domain,
            'answer_ip': answer_ip,
            'server_id': srv_id,
            'server_ip': srv_ip or 'unknown',
            'latency_ms': latency_ms,
            'raw': out,
        }

    def _probe_server(self, ip):
        cmd = (
            f"pgrep -f 'mininet:client1' | head -n 1 | "
            f"xargs -r -I {{}} sudo mnexec -a {{}} python3 dns/client.py "
            f"--id probe --server {ip} --port {DNS_PORT} --name web.local --no-cache"
        )
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1.5)
            return 'OK' in (proc.stdout or '')
        except Exception:
            return False

    def _health_monitor_loop(self):
        hub.sleep(1.5)
        while True:
            for srv in SERVERS:
                ip = srv['ip']
                srv_id = srv['id']
                prev_status = self.server_meta[ip]['status']
                alive = self._probe_server(ip)

                if alive:
                    self.server_meta[ip]['status'] = 'UP'
                    self.server_meta[ip]['last_seen'] = time.time()
                    if prev_status == 'DOWN':
                        self.log_event('RECOVERY', f"{srv_id} ({ip}) is back UP and added to active pool")
                    elif prev_status == 'UNKNOWN':
                        self.log_event('UP', f"{srv_id} ({ip}) detected UP")
                else:
                    if prev_status != 'DOWN':
                        self.server_meta[ip]['status'] = 'DOWN'
                        backup = self._peek_next_healthy_server()
                        if backup:
                            self.last_selected_server = backup['ip']
                            self.log_event(
                                'FAILOVER',
                                f"{srv_id} ({ip}) went DOWN -> redirected traffic to {backup['id']} ({backup['ip']})"
                            )
                        else:
                            self.last_selected_server = None
                            self.log_event('DOWN', f"{srv_id} ({ip}) went DOWN (no healthy backups available)")

            hub.sleep(HEALTH_INTERVAL_SEC)

    def _get_healthy_servers(self):
        healthy = [s for s in SERVERS if self.server_meta[s['ip']]['status'] == 'UP']
        if not healthy:
            healthy = [s for s in SERVERS if self.server_meta[s['ip']]['status'] != 'DOWN']
        return healthy

    def _peek_next_healthy_server(self):
        healthy = self._get_healthy_servers()
        if not healthy:
            return None
        return healthy[self.rr_index % len(healthy)]

    def _select_next_server(self):
        healthy = self._get_healthy_servers()
        if not healthy:
            return None
        chosen = healthy[self.rr_index % len(healthy)]
        self.rr_index = (self.rr_index + 1) % len(healthy)
        self.last_selected_server = chosen['ip']
        return chosen

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.datapaths[datapath.id] = datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        to_ctrl = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]

        # Default table-miss to controller
        self.add_flow(datapath, 0, parser.OFPMatch(), to_ctrl)

        # Only intercept ARP requests specifically targeting the Virtual IP (10.0.0.100)
        self.add_flow(
            datapath, 150,
            parser.OFPMatch(eth_type=ether_types.ETH_TYPE_ARP, arp_op=arp.ARP_REQUEST, arp_tpa=VIP_IP),
            to_ctrl,
        )

        # Intercept VIP DNS requests (10.0.0.100:5353)
        self.add_flow(
            datapath, 200,
            parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=VIP_IP, ip_proto=17, udp_dst=DNS_PORT),
            to_ctrl,
        )

        # Intercept DNS server replies (src port 5353 from backend servers) for VIP SNAT
        for srv in SERVERS:
            self.add_flow(
                datapath, 200,
                parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=srv['ip'], ip_proto=17, udp_src=DNS_PORT),
                to_ctrl,
            )

    def add_flow(self, datapath, priority, match, actions, idle_timeout=0, hard_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst,
            idle_timeout=idle_timeout,
            hard_timeout=hard_timeout,
        )
        datapath.send_msg(mod)

    def _send_arp_reply(self, datapath, in_port, src_mac, src_ip, target_mac, target_ip):
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_ARP, dst=src_mac, src=target_mac))
        pkt.add_protocol(
            arp.arp(
                opcode=arp.ARP_REPLY,
                src_mac=target_mac,
                src_ip=target_ip,
                dst_mac=src_mac,
                dst_ip=src_ip,
            )
        )
        pkt.serialize()
        actions = [datapath.ofproto_parser.OFPActionOutput(in_port)]
        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=datapath.ofproto.OFP_NO_BUFFER,
            in_port=datapath.ofproto.OFPP_CONTROLLER,
            actions=actions,
            data=pkt.data,
        )
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = datapath.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if not eth or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        # Learn MAC -> port dynamically
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][eth.src] = in_port

        # Learn IP -> MAC dynamically from any ARP or IPv4 packet
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            self.ip_to_mac[arp_pkt.src_ip] = arp_pkt.src_mac
            if arp_pkt.opcode == arp.ARP_REQUEST and arp_pkt.dst_ip == VIP_IP:
                self._send_arp_reply(datapath, in_port, eth.src, arp_pkt.src_ip, VIP_MAC, VIP_IP)
                return

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt:
            self.ip_to_mac[ip_pkt.src] = eth.src

        udp_pkt = pkt.get_protocol(udp.udp)
        server_ips = {s['ip'] for s in SERVERS}

        # 1. Forward VIP DNS request: Client -> VIP (10.0.0.100) ==> Selected Server
        if ip_pkt and udp_pkt and ip_pkt.dst == VIP_IP and udp_pkt.dst_port == DNS_PORT:
            chosen = self._select_next_server()
            if not chosen:
                self.log_event('DROP', f"Dropped DNS query from {ip_pkt.src}: all servers DOWN")
                return

            srv_ip = chosen['ip']
            srv_mac = self.ip_to_mac.get(srv_ip, 'ff:ff:ff:ff:ff:ff')
            srv_out_port = self.mac_to_port[dpid].get(srv_mac, ofproto.OFPP_FLOOD)

            raw_tail = pkt.protocols[-1] if isinstance(pkt.protocols[-1], (bytes, bytearray)) else b''
            udp_payload_len = max(0, udp_pkt.total_length - 8)
            payload = bytes(raw_tail[:udp_payload_len])

            new_pkt = packet.Packet()
            new_pkt.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_IP, dst=srv_mac, src=eth.src))
            new_pkt.add_protocol(ipv4.ipv4(dst=srv_ip, src=ip_pkt.src, proto=17, ttl=ip_pkt.ttl))
            new_pkt.add_protocol(udp.udp(src_port=udp_pkt.src_port, dst_port=DNS_PORT))
            if payload:
                new_pkt.add_protocol(payload)
            new_pkt.serialize()

            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=in_port,
                actions=[parser.OFPActionOutput(srv_out_port)],
                data=new_pkt.data,
            )
            datapath.send_msg(out)
            self.log_event('ROUTE', f"{ip_pkt.src}:{udp_pkt.src_port} -> {chosen['id']} ({srv_ip})")
            return

        # 2. Reverse DNS reply: Server -> Client ==> Spoof VIP (10.0.0.100)
        if ip_pkt and udp_pkt and ip_pkt.src in server_ips and udp_pkt.src_port == DNS_PORT:
            client_mac = self.ip_to_mac.get(ip_pkt.dst, eth.dst)
            client_port = self.mac_to_port[dpid].get(client_mac, ofproto.OFPP_FLOOD)

            raw_tail = pkt.protocols[-1] if isinstance(pkt.protocols[-1], (bytes, bytearray)) else b''
            udp_payload_len = max(0, udp_pkt.total_length - 8)
            payload = bytes(raw_tail[:udp_payload_len])

            rep_pkt = packet.Packet()
            rep_pkt.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_IP, dst=client_mac, src=VIP_MAC))
            rep_pkt.add_protocol(ipv4.ipv4(dst=ip_pkt.dst, src=VIP_IP, proto=17, ttl=ip_pkt.ttl))
            rep_pkt.add_protocol(udp.udp(src_port=DNS_PORT, dst_port=udp_pkt.dst_port))
            if payload:
                rep_pkt.add_protocol(payload)
            rep_pkt.serialize()

            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=in_port,
                actions=[parser.OFPActionOutput(client_port)],
                data=rep_pkt.data,
            )
            datapath.send_msg(out)
            return

        # Standard L2 learning switch forwarding (handles normal ARP broadcasts & direct traffic)
        out_port = self.mac_to_port[dpid].get(eth.dst, ofproto.OFPP_FLOOD)
        actions = [parser.OFPActionOutput(out_port)]
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=eth.dst, eth_src=eth.src)
            self.add_flow(datapath, 10, match, actions, idle_timeout=30)

        data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        datapath.send_msg(out)