# DNS Observatory — dashboard preview

Open `index.html` in a browser. No installation, internet connection, Mininet or Ryu is needed.

This is a browser-only simulation. Lookups use sample records in the page; the server buttons simulate failure and recovery. The dashboard does not monitor servers, send UDP requests, change switch rules, or prove that failover works. Refreshing the page clears the demo state.

Server addresses reflect the topology in the previously shared ZIP. Confirm them with the team before connecting real data. The sample records are deliberately separate from the DNS server's JSON file.

## Connecting the real project later

The current client CSV has query status and latency but no returned IP or server-health data. The controller needs to expose current server health, active server, and timestamped events. A local backend running in an appropriate Mininet client namespace (or a verified route to it) can issue actual lookups and expose the results to the UI. Define the interface with the controller teammate, treat missing or stale status as unknown, and test in Mininet before removing the Demo Mode label. Do not interpret simulated events as real results.
