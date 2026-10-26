#!/usr/bin/env python3
import subprocess
import time
import os

LOG_FILE = "tests/results/failure_results.csv"
PRIMARY_SERVER = "10.0.0.10"
BACKUP_SERVER = "10.0.0.11"
PORT = "5353"

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def main():
    os.makedirs("tests/results", exist_ok=True)
    print("=== Running Test 3: Server Failure & Redirection Test ===")
    
    # 1. Normal query before failure
    print("\n[1] Testing Primary DNS Server (10.0.0.10)...")
    cmd1 = f"python3 dns/client.py --id client1 --server {PRIMARY_SERVER} --port {PORT} --name web.local --no-cache --log {LOG_FILE}"
    print(run_cmd(cmd1))

    # 2. Querying offline or unresponsive server
    print("\n[2] Simulating Primary DNS Server Timeout/Failure (Querying unreachable port/IP)...")
    cmd2 = f"python3 dns/client.py --id client1 --server 10.0.0.99 --port {PORT} --name web.local --timeout 1.0 --retries 1 --log {LOG_FILE}"
    start_time = time.time()
    out2 = run_cmd(cmd2)
    elapsed = time.time() - start_time
    print(f"Result: {out2 if out2 else 'TIMEOUT DETECTED'}")
    print(f"Recovery/Detection Delay: {elapsed:.3f} seconds")

    # 3. Failover query to backup server
    print("\n[3] Redirecting Query to Backup DNS Server (10.0.0.11)...")
    cmd3 = f"python3 dns/client.py --id client1 --server {BACKUP_SERVER} --port {PORT} --name web.local --no-cache --log {LOG_FILE}"
    print(run_cmd(cmd3))

    print(f"\n[+] Server failure test results recorded in: {LOG_FILE}")

if __name__ == "__main__":
    main()