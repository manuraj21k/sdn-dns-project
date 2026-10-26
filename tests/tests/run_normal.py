#!/usr/bin/env python3
import subprocess
import time
import os

LOG_FILE = "tests/results/normal_results.csv"
SERVER_IP = "10.0.0.10"
PORT = "5353"

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def main():
    os.makedirs("tests/results", exist_ok=True)
    print("=== Running Test 1: Normal Lookups & Cache Hit vs Miss ===")
    
    # 1. First lookup (Cache Miss)
    print("\n[1] Executing Query: web.local (Expecting Cache Miss)")
    cmd1 = f"python3 dns/client.py --id client1 --server {SERVER_IP} --port {PORT} --name web.local --log {LOG_FILE}"
    out1 = run_cmd(cmd1)
    print(out1)
    
    time.sleep(1)
    
    # 2. Second lookup (Cache Hit)
    print("\n[2] Executing Repeated Query: web.local (Expecting Cache Hit)")
    cmd2 = f"python3 dns/client.py --id client1 --server {SERVER_IP} --port {PORT} --name web.local --log {LOG_FILE}"
    out2 = run_cmd(cmd2)
    print(out2)
    
    time.sleep(1)

    # 3. Batch Queries
    print("\n[3] Executing Multiple Domain Lookups")
    domains = ["mail.local", "files.local", "db.local", "app.local"]
    for domain in domains:
        cmd = f"python3 dns/client.py --id client1 --server {SERVER_IP} --port {PORT} --name {domain} --log {LOG_FILE}"
        out = run_cmd(cmd)
        print(out)
        time.sleep(0.5)

    print(f"\n[+] Results recorded in: {LOG_FILE}")

if __name__ == "__main__":
    main()