#!/usr/bin/env python3
"""
DNS-like UDP server (Person A).

Implements the protocol in INTERFACE.md:
    QUERY <name>   ->  ANSWER <name> <ip> <ttl> <server_id> | NXDOMAIN <name> | ERROR <reason>
    PING           ->  PONG <server_id>

Usage:
    python3 dns/server.py --id dns1 --ip 10.0.0.11 --port 5353 --records dns/records.json
    python3 dns/server.py --id dns1 --ip 127.0.0.1 --port 5353 --records dns/records.json   # local test
"""

import argparse
import json
import re
import socket
import sys
import threading
import time

MAX_DATAGRAM = 512        # bytes; larger datagrams are rejected
MAX_NAME_LEN = 64         # characters
DEFAULT_TTL = 30          # seconds the client may cache an answer
NAME_RE = re.compile(r"^[a-z0-9.\-]+$")   # names are lowercased before matching


def load_records(path):
    """Load the name -> IP table and lowercase all names."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {name.lower(): ip for name, ip in raw.items()}


def handle_request(sock, data, addr, server_id, records, delay_ms):
    """Process one datagram and send the reply. Runs in its own thread."""
    reply = None
    request_text = "<undecodable>"
    try:
        if len(data) > MAX_DATAGRAM:
            reply = "ERROR toolong"
        else:
            try:
                request_text = data.decode("utf-8").strip()
            except UnicodeDecodeError:
                reply = "ERROR malformed"

            if reply is None:
                parts = request_text.split()
                if len(parts) == 1 and parts[0] == "PING":
                    reply = f"PONG {server_id}"
                elif len(parts) == 2 and parts[0] == "QUERY":
                    # Optional artificial delay to simulate a slow server.
                    if delay_ms > 0:
                        time.sleep(delay_ms / 1000.0)
                    name = parts[1].lower()
                    if len(name) > MAX_NAME_LEN or not NAME_RE.match(name):
                        reply = "ERROR malformed"
                    elif name in records:
                        reply = f"ANSWER {name} {records[name]} {DEFAULT_TTL} {server_id}"
                    else:
                        reply = f"NXDOMAIN {name}"
                else:
                    reply = "ERROR malformed"
    except Exception as exc:  # never crash on bad input
        print(f"[{server_id}] internal error: {exc}", file=sys.stderr)
        reply = "ERROR internal"

    try:
        sock.sendto(reply.encode("utf-8"), addr)
    except OSError as exc:
        print(f"[{server_id}] send failed to {addr}: {exc}", file=sys.stderr)

    first_word = reply.split()[0]
    print(f"{time.time():.3f} {server_id} {addr[0]} {request_text!r} -> {first_word}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="DNS-like UDP server")
    parser.add_argument("--id", default="dns1", help="server id used in PONG/ANSWER (default dns1)")
    parser.add_argument("--ip", default="0.0.0.0", help="IP to bind (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5353, help="UDP port (default 5353)")
    parser.add_argument("--records", default="dns/records.json", help="path to records JSON")
    parser.add_argument("--delay-ms", type=int, default=0, help="artificial delay per QUERY, to simulate a slow server")
    args = parser.parse_args()

    records = load_records(args.records)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((args.ip, args.port))
    print(f"[{args.id}] listening on {args.ip}:{args.port}, {len(records)} records loaded", flush=True)

    try:
        while True:
            data, addr = sock.recvfrom(4096)
            # One thread per request so a slow request never blocks PING or other clients.
            threading.Thread(
                target=handle_request,
                args=(sock, data, addr, args.id, records, args.delay_ms),
                daemon=True,
            ).start()
    except KeyboardInterrupt:
        print(f"\n[{args.id}] shutting down")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
