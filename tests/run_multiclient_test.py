#!/usr/bin/env python3
import subprocess
import os

LOG_FILE = "tests/results/multiclient_results.csv"
VIP = "10.0.0.100"
PORT = "5353"

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def main():
    os.makedirs("tests/results", exist_ok=True)
    with open(LOG_FILE, "w") as f:
        f.write("timestamp,client,name,result,latency_ms,cache_hit,server\n")

    print("==================================================================")
    print(" MULTI-CLIENT CONCURRENCY TEST                                    ")
    print("==================================================================\n")

    print("[1] Executing query from client1...")
    out1 = run_cmd(f"python3 dns/client.py --id client1 --server {VIP} --port {PORT} --name web.local --no-cache --log {LOG_FILE}")
    print(f"    client1 result: {out1}")

    print("[2] Executing query from client2...")
    out2 = run_cmd(f"python3 dns/client.py --id client2 --server {VIP} --port {PORT} --name mail.local --no-cache --log {LOG_FILE}")
    print(f"    client2 result: {out2}")

    print(f"\n[+] Multi-client results recorded in: {LOG_FILE}")

if __name__ == "__main__":
    main()