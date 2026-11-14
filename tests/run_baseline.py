#!/usr/bin/env python3
import subprocess
import time
import os

LOG_FILE = "tests/results/baseline_results.csv"
SERVER_IP = "10.0.0.10"
PORT = "5353"

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def main():
    os.makedirs("tests/results", exist_ok=True)
    print("=== Running Test 2: Static Baseline Measurement ===")
    
    domains = ["web.local", "mail.local", "files.local", "db.local", "app.local"]
    
    # Execute repeated requests to measure latency baseline without caching
    print("\n[1] Measuring Static Latency Baseline across 10 trials (No Cache)...")
    for i in range(10):
        domain = domains[i % len(domains)]
        cmd = f"python3 dns/client.py --id client1 --server {SERVER_IP} --port {PORT} --name {domain} --no-cache --log {LOG_FILE}"
        out = run_cmd(cmd)
        print(f"Trial {i+1:2d}: {out}")
        time.sleep(0.2)
        
    print(f"\n[+] Static baseline results recorded in: {LOG_FILE}")

if __name__ == "__main__":
    main()