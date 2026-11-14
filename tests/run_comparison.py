#!/usr/bin/env python3
import subprocess
import time
import os

LOG_FILE = "tests/results/baseline_comparison_results.csv"
VIP = "10.0.0.100"
PORT = "5353"

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def main():
    os.makedirs("tests/results", exist_ok=True)
    
    # Overwrite old CSV log file with header so old timeouts are cleared
    with open(LOG_FILE, "w") as f:
        f.write("timestamp,client,name,result,latency_ms,cache_hit,server\n")

    print("==================================================================")
    print(" D2 TEST 1: BASELINE LATENCY & FETCHING COMPARISON               ")
    print(" Comparing Local Subnet IPs via VIP 10.0.0.100                  ")
    print("==================================================================\n")

    local_records = ["web.local", "mail.local"]
    
    print("--- [Phase 1] Local Subnet Record Lookups ---")
    for i in range(5):
        domain = local_records[i % len(local_records)]
        cmd = f"python3 dns/client.py --id client1 --server {VIP} --port {PORT} --name {domain} --no-cache --log {LOG_FILE}"
        out = run_cmd(cmd)
        print(f"Trial {i+1:2d} [LOCAL - {domain:15s}]: {out}")
        time.sleep(0.3)

    print(f"\n[+] Results successfully recorded in: {LOG_FILE}")

if __name__ == "__main__":
    main()