# SDN + Socket Programming: DNS-Like Name Resolution (Project 22)

A simplified DNS built on **UDP sockets**, running in a **Mininet** network and managed by an **SDN controller (Ryu)**. Clients look up names such as `web.local` and get an IP back. The controller decides which real DNS server receives each query, and **redirects queries automatically when a server fails or slows down**.

Course: SDN-Socket Programming (Jackfruit Mini Project). Requirements and rubric are in [`docs/`](docs/).

## Team

| Role | Member | Folder |
|---|---|---|
| Person A: DNS application (UDP server, client, caching) | Manuraj | `dns/` |
| Person B: Mininet topology + Ryu controller | Kashvi | `controller/` |
| Person C: tests, metrics, documentation | Jitesh | `tests/`, `docs/` |

## How it works

```
 h1 ─┐                                   ┌─ dns1 (10.0.0.11)
 h2 ─┼── switch(es) ── OpenFlow ── Ryu ──┼─ dns2 (10.0.0.12)
 h3 ─┘                  controller       └─ dns3 (10.0.0.13)  (optional)

 Clients query the virtual IP 10.0.0.100:5353.
 The controller maps it to a healthy real DNS server.
```

- **Sockets:** UDP client and server, timeouts and retries, client-side cache with TTL, concurrent request handling.
- **SDN:** controller detects a failed or slow server and rewrites flow rules to redirect traffic.
- **Evaluation:** lookup latency, success rate and recovery time, compared against a static baseline (no redirection).

The full message format, IP plan and rules are in [`INTERFACE.md`](INTERFACE.md).

## Quick start

1. Set up your machine: see [`SETUP.md`](SETUP.md).
2. Try the DNS app alone (no Mininet needed):
   ```bash
   # terminal 1
   python3 dns/server.py --id dns1 --ip 127.0.0.1 --port 5353 --records dns/records.json
   # terminal 2
   python3 dns/client.py --server 127.0.0.1 --port 5353 --name web.local
   ```
3. Run the full system (once the controller and topology exist): see `SETUP.md` section 4, later `./run_all.sh`.

## Repo layout

```
.
├── README.md
├── SETUP.md            install steps
├── INTERFACE.md        shared contract (messages, ports, IPs, logs)
├── run_all.sh          start everything (to be written)
├── requirements.txt
├── dns/                Person A: server.py, client.py, records.json
├── controller/         Person B: dns_controller.py, topology.py
├── tests/              Person C: names.txt, experiment scripts, results/
└── docs/               project sheet, rubric, final report, diagrams
```

## Status

| Item | Owner | Status |
|---|---|---|
| UDP DNS server and client | A | first version done (localhost-tested) |
| Caching, timeouts, retries | A | first version done (localhost-tested) |
| Mininet topology | B | not started |
| Ryu controller (forwarding) | B | not started |
| Failure detection + redirection | B | not started |
| Static baseline | B + C | not started |
| Experiments and graphs | C | not started |
| Final report and demo | all | not started |

## Team workflow

- One branch per person (`dns-work`, `controller-work`, `tests-work`); merge to `main` through pull requests reviewed by another member.
- Only edit files in your own folder. Ask the owner for changes elsewhere.
- Changes to `INTERFACE.md` need a message to the other two first.
- Everyone must be able to run the whole system on their own machine, and be able to explain all three parts in the viva.
