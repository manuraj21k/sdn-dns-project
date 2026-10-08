#!/usr/bin/env python3
"""
DNS-like UDP client (Person A).

Sends QUERY messages, retries on timeout, caches answers (TTL) and logs latency.

Usage:
    # single lookup
    python3 dns/client.py --id h1 --server 10.0.0.100 --port 5353 --name web.local

    # batch lookups (for experiments)
    python3 dns/client.py --id h1 --server 10.0.0.100 --port 5353 \
        --names-file tests/names.txt --repeat 50 --interval-ms 100 \
        --log tests/results/client_h1.csv

    # health probe
    python3 dns/client.py --server 10.0.0.11 --port 5353 --ping
"""

import argparse
import os
import socket
import sys
import time

DEFAULT_TTL = 30


class Cache:
    """In-memory cache: name -> (ip, expiry_time, server_id)."""

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.store = {}

    def get(self, name):
        if not self.enabled:
            return None
        entry = self.store.get(name)
        if entry is None:
            return None
        ip, expiry, server_id = entry
        if time.time() >= expiry:
            del self.store[name]          # expired
            return None
        return ip, server_id

    def put(self, name, ip, ttl, server_id):
        if self.enabled:
            self.store[name] = (ip, time.time() + ttl, server_id)


def send_and_wait(server, port, message, timeout, retries):
    """
    Send one message and wait for a reply. Tries 1 + `retries` times.
    Returns the reply text, or None if every attempt timed out.
    A fresh socket per attempt avoids picking up late replies from earlier attempts.
    """
    for _attempt in range(1 + retries):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        try:
            sock.sendto(message.encode("utf-8"), (server, port))
            data, _addr = sock.recvfrom(4096)
            return data.decode("utf-8", errors="replace").strip()
        except socket.timeout:
            continue
        except OSError:
            # e.g. network unreachable; treat like a lost attempt
            continue
        finally:
            sock.close()
    return None


def lookup(name, args, cache):
    """
    Resolve one name. Returns (result, ip, latency_ms, cache_hit, server_id)
    where result is OK, NXDOMAIN, TIMEOUT or ERROR.
    """
    name = name.lower()

    cached = cache.get(name)
    if cached is not None:
        ip, server_id = cached
        return "OK", ip, 0.0, "yes", server_id

    start = time.perf_counter()
    reply = send_and_wait(args.server, args.port, f"QUERY {name}", args.timeout, args.retries)
    latency_ms = (time.perf_counter() - start) * 1000.0

    if reply is None:
        return "TIMEOUT", "-", latency_ms, "no", "-"

    parts = reply.split()
    if parts and parts[0] == "ANSWER" and len(parts) >= 3:
        ip = parts[2]
        try:
            ttl = int(parts[3]) if len(parts) >= 4 else DEFAULT_TTL
        except ValueError:
            ttl = DEFAULT_TTL
        server_id = parts[4] if len(parts) >= 5 else "-"
        cache.put(name, ip, ttl, server_id)
        return "OK", ip, latency_ms, "no", server_id
    if parts and parts[0] == "NXDOMAIN":
        return "NXDOMAIN", "-", latency_ms, "no", "-"      # not cached
    return "ERROR", "-", latency_ms, "no", "-"


def open_log(path):
    """Open the CSV log for appending; write the header if the file is new."""
    if not path:
        return None
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    is_new = not os.path.exists(path) or os.path.getsize(path) == 0
    f = open(path, "a", encoding="utf-8")
    if is_new:
        f.write("timestamp,client,name,result,latency_ms,cache_hit,server\n")
    return f


def main():
    parser = argparse.ArgumentParser(description="DNS-like UDP client")
    parser.add_argument("--id", default="h1", help="client id for the log (default h1)")
    parser.add_argument("--server", default="10.0.0.100", help="server or virtual DNS IP")
    parser.add_argument("--port", type=int, default=5353)
    parser.add_argument("--name", help="single name to look up")
    parser.add_argument("--names-file", help="file with one name per line (batch mode)")
    parser.add_argument("--repeat", type=int, default=1, help="repeat the names list N times")
    parser.add_argument("--interval-ms", type=int, default=0, help="pause between queries")
    parser.add_argument("--timeout", type=float, default=1.0, help="seconds per attempt (default 1.0)")
    parser.add_argument("--retries", type=int, default=3, help="retries after the first attempt (default 3)")
    parser.add_argument("--no-cache", action="store_true", help="disable the cache")
    parser.add_argument("--log", help="CSV log path, e.g. tests/results/client_h1.csv")
    parser.add_argument("--ping", action="store_true", help="send PING and print the reply")
    args = parser.parse_args()

    # Health probe mode
    if args.ping:
        reply = send_and_wait(args.server, args.port, "PING", args.timeout, 0)
        if reply is None:
            print("NO REPLY")
            sys.exit(1)
        print(reply)
        sys.exit(0)

    # Build the list of names to look up
    names = []
    if args.name:
        names.append(args.name)
    if args.names_file:
        with open(args.names_file, "r", encoding="utf-8") as f:
            names.extend(line.strip() for line in f if line.strip())
    if not names:
        parser.error("give --name or --names-file (or use --ping)")

    batch_mode = bool(args.names_file)
    cache = Cache(enabled=not args.no_cache)
    log = open_log(args.log)

    ok = 0
    total = 0
    last_result = "OK"
    for _round in range(args.repeat):
        for name in names:
            result, ip, latency_ms, hit, server_id = lookup(name, args, cache)
            total += 1
            last_result = result
            if result == "OK":
                ok += 1

            line = f"{time.time():.3f},{args.id},{name.lower()},{result},{latency_ms:.3f},{hit},{server_id}"
            if log:
                log.write(line + "\n")
                log.flush()
            print(f"{name.lower():<15} {result:<9} {ip:<12} {latency_ms:8.3f} ms  cache_hit={hit}  server={server_id}")

            if args.interval_ms > 0:
                time.sleep(args.interval_ms / 1000.0)

    if log:
        log.close()
    if batch_mode or total > 1:
        print(f"\nSummary: {ok}/{total} lookups returned OK")
    # Single-query mode: non-zero exit on TIMEOUT or ERROR
    if not batch_mode and total == 1 and last_result in ("TIMEOUT", "ERROR"):
        sys.exit(1)


if __name__ == "__main__":
    main()
