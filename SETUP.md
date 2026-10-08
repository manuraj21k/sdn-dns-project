# SETUP.md

How to set up your machine so you can run the whole project (Mininet + Ryu controller + DNS app). Everyone already has Ubuntu, so this only covers installing the tools. Finish it and pass the checks in section 5 **before** writing project code.

---

## 1. Install Mininet and tools

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv \
    mininet openvswitch-switch tcpdump net-tools
```

Make sure Open vSwitch is running:

```bash
sudo systemctl enable --now openvswitch-switch
sudo systemctl status openvswitch-switch    # should say "active"
```

---

## 2. Get the project code

```bash
git clone https://github.com/manuraj21k/sdn-dns-project.git sdn-dns-project
cd sdn-dns-project
git config user.name  "Your Name"
git config user.email "you@example.com"
git checkout -b <your-branch-name>      # e.g. dns-work, controller-work, tests-work
```

---

## 3. Install the Ryu controller (in a virtualenv)

Everyone needs this, because everyone should be able to run the full system, not just the controller owner.

```bash
cd ~/sdn-dns-project
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install "setuptools==67.6.1" "eventlet==0.30.2"
pip install ryu
ryu-manager --version
```

**Known issue:** Ryu is old and often breaks on newer Python versions with errors about `eventlet` (`cannot import name 'ALREADY_HANDLED'`) or `pkg_resources`. The pinned `setuptools` and `eventlet` versions above are the usual fix, and they must be installed **before** `pip install ryu`. If it still fails, tell the team and fix it once for everyone, then record the fix in this file.

---

## 4. How the pieces run

You normally use **two terminals**:

**Terminal 1: controller (no sudo, uses the venv)**
```bash
cd ~/sdn-dns-project
source venv/bin/activate
ryu-manager controller/dns_controller.py
```

**Terminal 2: topology (sudo, system Python)**
```bash
cd ~/sdn-dns-project
sudo python3 controller/topology.py
```

Notes:
- `sudo` does not use the virtualenv, which is fine: Mininet is installed system-wide and the DNS code only uses the Python standard library.
- Ryu listens for OpenFlow on port **6653**, and the topology connects to it at `127.0.0.1:6653`.
- `./run_all.sh` (written later by the team) will automate these steps.

---

## 5. Verify your setup (everyone must pass these)

**Check 1: Mininet works**
```bash
sudo mn --test pingall
```
Expected: `0% dropped`.

**Check 2: Ryu works with Mininet**

Terminal 1:
```bash
source venv/bin/activate
ryu-manager ryu.app.simple_switch_13
```
Terminal 2:
```bash
sudo mn --controller=remote,ip=127.0.0.1,port=6653 --topo single,3 --switch ovsk,protocols=OpenFlow13
mininet> pingall
mininet> exit
```
Expected: `0% dropped`.

**Check 3: Python runs inside a Mininet host**
```bash
sudo mn --topo single,2
mininet> h1 python3 -c "print('hello from h1')"
mininet> exit
```

If all three pass, your machine is ready.

---

## 6. Everyday commands

| Task | Command |
|---|---|
| Run a command on a Mininet host | `mininet> h1 <command>` |
| Clean up after a crashed run | `sudo mn -c` |
| Show switch flow rules | `sudo ovs-ofctl -O OpenFlow13 dump-flows s1` |
| Capture DNS packets on a host | `mininet> h1 tcpdump -i h1-eth0 -n udp port 5353` |
| Pull teammates' changes | `git pull origin main` |
| Stop a stuck controller | `pkill -f ryu-manager` |

---

## 7. Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| Leftover interfaces or `Error creating interface pair` | Run `sudo mn -c`, then retry. |
| `Unable to contact the remote controller at 127.0.0.1:6653` | Ryu is not running or crashed. Start Terminal 1 first. |
| `pingall` shows 100% drop with Ryu | The controller is not installing flows, or the switch is missing `protocols=OpenFlow13`. |
| `ovs-vsctl: ... database connection failed` | `sudo systemctl restart openvswitch-switch`. |
| `ModuleNotFoundError: No module named 'ryu'` | The venv is not active: `source venv/bin/activate`. |
| Ryu fails with `eventlet` or `setuptools` errors | See the known issue in section 3. |
| Port 6653 already in use | An old controller is still running: `pkill -f ryu-manager`. |

---

## 8. Checklist

- [ ] Packages from section 1 installed, Open vSwitch active
- [ ] Repo cloned, own branch created
- [ ] Ryu installed, `ryu-manager --version` works
- [ ] Checks 1 to 3 in section 5 pass
- [ ] Added any extra fix you needed to this file

---

## 9. Change log

| Date | Change | By |
|---|---|---|
| _yyyy-mm-dd_ | Initial version | _name_ |
