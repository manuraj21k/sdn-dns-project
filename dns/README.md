# dns/: DNS application (Person A)

Plain Python 3, standard library only. See `../INTERFACE.md` for the protocol.

## Server

```bash
python3 dns/server.py --id dns1 --ip 10.0.0.11 --port 5353 --records dns/records.json
python3 dns/server.py --id dns2 --ip 127.0.0.1 --port 5354 --records dns/records.json --delay-ms 300   # slow server
```

| Option | Meaning | Default |
|---|---|---|
| `--id` | server id, returned in `ANSWER` and `PONG` | `dns1` |
| `--ip` | IP to bind | `0.0.0.0` |
| `--port` | UDP port | `5353` |
| `--records` | name-to-IP JSON file | `dns/records.json` |
| `--delay-ms` | artificial delay per `QUERY` (simulates a slow server) | `0` |

Each request runs in its own thread, so a slow query never blocks `PING` or other clients. One log line per request is printed.

## Client

```bash
# single lookup
python3 dns/client.py --id h1 --server 10.0.0.100 --port 5353 --name web.local

# batch lookups, logged to CSV
python3 dns/client.py --id h1 --server 10.0.0.100 --port 5353 \
    --names-file tests/names.txt --repeat 50 --interval-ms 100 --log tests/results/client_h1.csv

# health probe
python3 dns/client.py --server 10.0.0.11 --port 5353 --ping
```

| Option | Meaning | Default |
|---|---|---|
| `--server`, `--port` | where to send queries | `10.0.0.100`, `5353` |
| `--name` / `--names-file` | one name, or a file with one name per line | |
| `--repeat`, `--interval-ms` | repeat the list N times, pause between queries | `1`, `0` |
| `--timeout`, `--retries` | seconds per attempt, retries after the first | `1.0`, `3` |
| `--no-cache` | disable the cache | cache on |
| `--log` | CSV log file | none |
| `--ping` | send `PING` and print the reply | |

Single-lookup mode exits with a non-zero status on `TIMEOUT` or `ERROR`.

## Behavior notes

- Names are case-insensitive (lowercased on both sides).
- Cache entries expire after the TTL in the `ANSWER` (30 s). `NXDOMAIN` is not cached.
- A cache hit is logged with latency `0.000` and `cache_hit=yes`.
- CSV columns: `timestamp,client,name,result,latency_ms,cache_hit,server`.
- Latency for a timed-out lookup includes all retries.

## Local test (no Mininet)

```bash
python3 dns/server.py --id dns1 --ip 127.0.0.1 --port 5353 --records dns/records.json &
python3 dns/client.py --server 127.0.0.1 --port 5353 --names-file tests/names.txt --repeat 2
```

## Known limitations (first version, may change)

- Tested on localhost only; not yet verified inside Mininet with the controller's virtual-IP rewrite.
- The client does not match replies to queries with a transaction ID (each attempt uses a fresh socket instead).
- The cache is per client process, so single-lookup runs never hit it; use batch mode (`--names-file`) for cache experiments.
- The server's receive loop has no top-level error handling and thread count is unbounded.
- No automated tests yet.
