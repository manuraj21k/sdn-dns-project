#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt
import os

os.makedirs("tests/results/graphs", exist_ok=True)

if os.path.exists("tests/results/d2_failure_results.csv"):
    df = pd.read_csv("tests/results/d2_failure_results.csv")
    plt.figure(figsize=(8, 4))
    plt.plot(df.index, df['latency_ms'], marker='o', color='b', linestyle='-')
    plt.title("DNS Query Latency During Server Failover Event")
    plt.xlabel("Query Index")
    plt.ylabel("Latency (ms)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("tests/results/graphs/failover_latency.png")
    print("[+] Generated: tests/results/graphs/failover_latency.png")

if os.path.exists("tests/results/multiclient_results.csv"):
    df_mc = pd.read_csv("tests/results/multiclient_results.csv")
    plt.figure(figsize=(6, 4))
    plt.bar(df_mc['client'], df_mc['latency_ms'], color=['green', 'blue'])
    plt.title("Multi-Client Concurrent Query Latencies")
    plt.xlabel("Client Host")
    plt.ylabel("Latency (ms)")
    plt.tight_layout()
    plt.savefig("tests/results/graphs/multiclient_latency.png")
    print("[+] Generated: tests/results/graphs/multiclient_latency.png")