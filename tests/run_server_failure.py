#!/usr/bin/env python3
import subprocess
import time
import os

LOG_FILE = "tests/results/d2_failure_results.csv"
VIP = "10.0.0.100"
PORT = "5353"
DOMAIN = "web.local"

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def main():
    os.makedirs("tests/results", exist_ok=True)
    with open(LOG_FILE, "w") as f:
        f.write("timestamp,client,name,result,latency_ms,cache_hit,server\n")

    print("==================================================================")
    print(" D2 TEST: DYNAMIC FAILOVER & RECOVERY TIME (MTTR) MEASUREMENT     ")
    print(" Target: Virtual IP 10.0.0.100                                    ")
    print("==================================================================\n")

    print("[1] Baseline Query (Before Outage)...")
    out1 = run_cmd(f"python3 dns/client.py --id client1 --server {VIP} --port {PORT} --name {DOMAIN} --no-cache --log {LOG_FILE}")
    print(f"    Pre-Failure Result: {out1}\n")

    print("[!] SIMULATING SERVER FAILURE: Killing server process on dns1...")
    t_start = time.time()
    run_cmd("pkill -9 -f 'dns1'")

    print("[*] Polling controller for failover recovery...")
    recovered = False
    out2 = ""
    while time.time() - t_start < 10.0:
        res = run_cmd(f"python3 dns/client.py --id client1 --server {VIP} --port {PORT} --name {DOMAIN} --no-cache --log {LOG_FILE}")
        if "OK" in res and "10.0.0.10" not in res:
            t_recovery = (time.time() - t_start) * 1000.0
            recovered = True
            out2 = res
            break
        time.sleep(0.2)

    if recovered:
        print(f"    Post-Failure Result (Backup Server): {out2}")
        print(f"    [+] MEASURED RECOVERY TIME (MTTR): {t_recovery:.2f} ms\n")
    else:
        print("    [-] Failover recovery timed out.")

    print(f"[+] Failover metrics recorded in: {LOG_FILE}")

if __name__ == "__main__":
    main()