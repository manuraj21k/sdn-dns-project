# INTERFACE.md

Shared contract for **Project 22: Distributed DNS-Like Name Resolution System (UDP) with SDN**.

All three team members code against this file. **Do not change it without telling the other two first.** Any change must be committed with a clear message, and the people affected must acknowledge it.

| Role | Owner | Folder |
|---|---|---|
| Person A: DNS application (sockets) | _name_ | `dns/` |
| Person B: Mininet topology + SDN controller | _name_ | `controller/` |
| Person C: Tests, metrics, documentation | _name_ | `tests/`, `docs/` |

---

## 1. Overview

Clients send name-lookup queries over UDP to a **virtual DNS IP**. The SDN controller decides which real DNS server actually receives each query, and redirects traffic to a healthy server if one fails or becomes slow. Clients never need to know which real server answered.

```
 h1 ─┐                                   ┌─ dns1 (10.0.0.11)
 h2 ─┼── switch(es) ── OpenFlow ── Ryu ──┼─ dns2 (10.0.0.12)
 h3 ─┘                  controller       └─ dns3 (10.0.0.13)   (optional)

 Clients query the virtual IP 10.0.0.100;
 the controller maps it to a healthy real server.
```

---

## 2. Transport

| Item | Value |
|---|---|
| Protocol | UDP |
| DNS port | **5353** (not 53, so no root is needed for the DNS app itself) |
| Encoding | UTF-8 plain text |
| Datagram | One message per datagram, no trailing newline required |
| Max datagram size | 512 bytes (longer messages are dropped and answered with `ERROR`) |

---

## 3. Message format

All fields are separated by a **single space**. Message keywords are **uppercase**. Names are case-insensitive and are compared in lowercase.

### 3.1 Lookup

| Direction | Message | Example |
|---|---|---|
| Client → Server | `QUERY <name>` | `QUERY web.local` |
| Server → Client (found) | `ANSWER <name> <ip> <ttl> <server_id>` | `ANSWER web.local 10.0.0.20 30 dns1` |
| Server → Client (not found) | `NXDOMAIN <name>` | `NXDOMAIN foo.local` |
| Server → Client (bad request) | `ERROR <reason>` | `ERROR malformed` |

- `<ttl>` is the number of seconds the client may cache the answer.
- `<server_id>` is the id of the real server that answered (`dns1`, `dns2`, ...). It lets tests and the demo show **which server answered after a failover**, even though the client only talks to the virtual IP. Clients must also accept an `ANSWER` without the last two fields.
- `<name>`: letters, digits, `-`, `.`; max 64 characters.
- `<reason>` is one word: `malformed`, `toolong`, or `internal`.

### 3.2 Health check

| Direction | Message |
|---|---|
| Controller (or any host) → Server | `PING` |
| Server → sender | `PONG <server_id>` (for example `PONG dns1`) |

The server must answer `PING` promptly even while handling lookups.

---

## 4. Network plan

### 4.1 IP addresses

| Host | Role | IP |
|---|---|---|
| h1 | Client | 10.0.0.1 |
| h2 | Client | 10.0.0.2 |
| h3 | Client | 10.0.0.3 |
| dns1 | Real DNS server (primary) | 10.0.0.11 |
| dns2 | Real DNS server (backup) | 10.0.0.12 |
| dns3 | Real DNS server (optional) | 10.0.0.13 |
| (virtual) | **Virtual DNS IP** | **10.0.0.100** |

Netmask: `/24` (10.0.0.0/24). Hosts get these addresses from the Mininet script, not DHCP.

### 4.2 Virtual DNS IP (key design point)

- **Clients always send queries to 10.0.0.100:5353.** They never hard-code a real server.
- No host actually owns 10.0.0.100. The controller installs flow rules that rewrite the destination IP/MAC to the chosen real server on the way in, and rewrite the source back to 10.0.0.100 on the way out, so replies look like they came from the virtual IP.
- The controller may therefore also answer ARP requests for 10.0.0.100.

### 4.3 What each person delivers for this

| Person | Provides |
|---|---|
| A | Servers answer on 5353 and respond to `PING`. Clients accept replies from the virtual IP. |
| B | Topology with the hosts above; controller handling the virtual IP, ARP for it, and failover. |
| C | Tests that kill and restore servers by name (`dns1`, `dns2`, `dns3`). |

---

## 5. Records

The name → IP table is stored in `dns/records.json`. All real servers load the same file (unless a test says otherwise).

```json
{
  "web.local":   "10.0.0.20",
  "mail.local":  "10.0.0.21",
  "files.local": "10.0.0.22",
  "db.local":    "10.0.0.23",
  "app.local":   "10.0.0.24"
}
```

These target IPs do not need to belong to running hosts; the project is about name resolution.

---

## 6. Behavior rules

### 6.1 Server (Person A)

- Binds `0.0.0.0:<port>` and handles multiple clients concurrently.
- Looks up the lowercased name in the table; replies `ANSWER` or `NXDOMAIN`.
- Replies `ERROR malformed` for anything it cannot parse; never crashes on bad input.
- Answers `PING` with `PONG <server_id>`.
- Logs one line per request (see section 7).
- Optional artificial delay flag (`--delay-ms`) so tests can simulate a slow server.

### 6.2 Client (Person A)

| Setting | Default |
|---|---|
| Timeout per attempt | 1.0 second |
| Retries after first attempt | 3 (so up to 4 attempts total) |
| Cache TTL | the `<ttl>` from the answer (default 30 s if absent) |
| Cache | in memory, per client process; `--no-cache` disables it |

- A cache hit answers locally with no network traffic.
- `NXDOMAIN` results are **not** cached.
- After all retries fail, the client reports `TIMEOUT` and exits with a non-zero status (single-query mode).

### 6.3 Controller (Person B): requested behavior

_Person B should confirm or amend this section._

- Forward traffic to a healthy real server for queries sent to 10.0.0.100:5353.
- Detect a failed server (for example, `PING` probes with no `PONG`, or flow statistics) and redirect new queries to another healthy server.
- Restore a recovered server to the pool.
- Write controller events (failover, recovery) to a log with timestamps, so Person C can measure recovery time.

---

## 7. Logging

### 7.1 Client log (CSV, one line per lookup)

```
timestamp,client,name,result,latency_ms,cache_hit,server
```

| Field | Meaning | Example |
|---|---|---|
| timestamp | Unix time, seconds with decimals | `1760000000.123` |
| client | Client host id | `h1` |
| name | Name queried | `web.local` |
| result | `OK`, `NXDOMAIN`, `TIMEOUT`, or `ERROR` | `OK` |
| latency_ms | Time from first send to final reply, 3 decimals; `0.000` for cache hits is acceptable | `1.482` |
| cache_hit | `yes` or `no` | `no` |
| server | `server_id` from the `ANSWER`, else `-` | `dns1` |

Log file location: `tests/results/client_<host>.csv`. A header row is written when the file is created.

### 7.2 Server log (text, one line per request)

```
<timestamp> <server_id> <client_ip> <request> -> <response_keyword>
```

### 7.3 Controller log

```
<timestamp> <event> <details>
```

Events include `SERVER_DOWN`, `SERVER_UP`, `REDIRECT`. Details name the servers involved.

---

## 8. Launch commands

Person B uses these in the Mininet script; Person C uses them in tests. Run from the repo root.

**Server**
```
python3 dns/server.py --id dns1 --ip 10.0.0.11 --port 5353 --records dns/records.json [--delay-ms N]
```

**Client, single lookup**
```
python3 dns/client.py --id h1 --server 10.0.0.100 --port 5353 --name web.local [--no-cache]
```

**Client, batch mode**
```
python3 dns/client.py --id h1 --server 10.0.0.100 --port 5353 --names-file tests/names.txt --repeat 50 --interval-ms 100 --log tests/results/client_h1.csv
```

- `names.txt` holds one name per line.
- `--repeat N` sends the whole list N times; `--interval-ms` is the gap between queries.

**Health probe (manual check)**
```
python3 dns/client.py --server 10.0.0.11 --port 5353 --ping
```

---

## 9. Repo layout and ownership

```
sdn-dns-project/
├── README.md
├── SETUP.md
├── INTERFACE.md        # this file
├── run_all.sh
├── dns/                # Person A
│   ├── server.py
│   ├── client.py
│   └── records.json
├── controller/         # Person B
│   ├── dns_controller.py
│   └── topology.py
├── tests/              # Person C
│   ├── names.txt
│   ├── run_normal.py
│   ├── run_failure.py
│   ├── run_baseline.py
│   └── results/
└── docs/               # Person C
```

- Only edit files in your own folder. Ask the owner if you need a change elsewhere.
- Work on your own branch; merge to `main` through a pull request reviewed by another member.

---

## 10. Environment

- Ubuntu 22.04 (VM or native), Python 3, Mininet, Open vSwitch, Ryu (in a virtualenv).
- Exact install steps live in `SETUP.md`.
- Everyone must be able to run `./run_all.sh` on their own machine.

---

## 11. Baseline (for comparison experiments)

To show the benefit of SDN, Person C also runs a **static baseline**: the same topology and servers, but the controller only does plain forwarding and **no failover**, so the virtual IP always maps to dns1. Person B provides a flag (for example `--mode static|dynamic`) to switch between the two.

---

## 12. Open items (resolve before coding starts)

- [ ] Person B confirms the virtual-IP rewrite approach (section 4.2).
- [ ] Person B confirms the health-check method (`PING` probes vs flow stats).
- [ ] Person C confirms the CSV log format (section 7.1) works for their analysis.
- [ ] Team confirms timeout/retry/TTL defaults (section 6.2).
- [ ] Number of servers: 2 or 3?

---

## 13. Change log

| Date | Change | By |
|---|---|---|
| _yyyy-mm-dd_ | Initial version. `ANSWER` carries `<server_id>` as its last field. | _name_ |
