# SDN-Based DNS-Like Name Resolution

Project 22 of the SDN–Socket Programming mini project. This project combines a UDP-based name-resolution service with a Mininet network, a Ryu SDN controller, and a web dashboard.

Clients request a name such as `web.local` and receive its IP address. The controller directs requests addressed to a virtual service IP to one of the available DNS-like servers. Its health-check logic is designed to detect unavailable servers and route requests to healthy ones.

This is a **DNS-like learning prototype** using a custom text protocol. It is not a full implementation of standard Internet DNS.

## Architecture

```text
Client 1 (10.0.0.1) ──┐             ┌── dns1 (10.0.0.10)
                       ├── Switch ───┼── dns2 (10.0.0.11)
Client 2 (10.0.0.2) ──┘      │      └── dns3 (10.0.0.12)
                              │
                        Ryu controller

Clients query the virtual IP 10.0.0.100 on UDP port 5353.
```

## Features

- UDP client and server with name-to-IP mappings in `dns/records.json`.
- Application messages for successful answers, unknown names and health checks.
- Client-side caching with a time to live, timeouts, retries and latency logging.
- Concurrent request handling on the server.
- Mininet topology with two clients, three server hosts and an OpenFlow switch.
- Ryu controller with virtual-IP forwarding, server health checks and server selection.
- Web dashboard for server status, controller events and lookups through the controller API.
- Scripts and saved output for lookup, failure and performance experiments.

Public website entries in the records file are **fixed examples**. They can change or differ by location; looking them up here reads the local file, not a live public DNS service.

## Project structure

```text
controller/    Mininet topology and Ryu controller
dns/           UDP client, server and records
ui/            Web dashboard
tests/         Test scripts, saved results and graphs
docs/          Project guidelines and rubric
```

## Running the project

The complete setup needs Linux, Python 3, Mininet, Open vSwitch and Ryu. Run commands from the repository root; see [SETUP.md](SETUP.md) for installation guidance. The topology in `controller/topology.py` uses the addresses shown above; the older `INTERFACE.md` describes a different address plan.

To try the UDP application on one computer, start the server in one terminal:

```bash
python3 dns/server.py --id dns1 --ip 127.0.0.1 --port 5353 --records dns/records.json
```

In another terminal:

```bash
python3 dns/client.py --server 127.0.0.1 --port 5353 --name web.local
```

For the Mininet demo, start the Ryu controller and topology as described in [SETUP.md](SETUP.md), start the DNS server processes in the Mininet server hosts, then send queries from a client host. The dashboard expects the controller API at `127.0.0.1:8080` and its lookup bridge needs access to Mininet and `mnexec` on the machine running the controller.

## Testing and results

The `tests/` directory contains scripts for normal lookups, failure scenarios and multiple-client experiments. Saved CSVs and graphs are under `tests/results/`.

**Comparison limitation:** `tests/run_comprehensive_comparison.py` currently writes fixed outcome and latency values instead of recording the command's actual measurements. Its comparison CSV and graph must not be treated as measured results. Correct the script and rerun the comparison before reporting performance. The current multi-client script runs its queries sequentially and does not alone demonstrate concurrent queries from distinct Mininet hosts.

**Dashboard security:** The controller API uses request input in a shell command and permits cross-origin requests. Validate inputs, remove shell interpolation and restrict API access before exposing it beyond a trusted test environment.

## Team contributions

**Manuraj — DNS application and user interface**  
Developed the UDP client and server, including name resolution, message handling, caching, timeouts and retries. Created the user interface for displaying DNS lookups, server status and project activity.

**Kashvi — SDN, network and integration**  
Developed the Mininet topology and Ryu controller, including virtual-IP forwarding, server selection and failure-handling logic. Integrated the user interface with the controller and Mininet setup.

**Jitesh — Testing and performance evaluation**  
Worked on test scenarios, collected experiment results, prepared performance graphs and contributed to project documentation.

**All team members**  
Collaborated on system testing, debugging and preparation for the final demonstration. All team members also worked together to identify and correct errors throughout the project.
