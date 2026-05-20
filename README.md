# mrrobot0985.talos

> Production-grade, zero-touch Ansible role for deploying **Talos Linux Kubernetes clusters** using only live node facts — no manual YAML editing required.

---

## Key Features

- **Live Node Discovery** — Queries disks, network interfaces, addresses, machine status, kernel parameters, and version directly via the Talos API (`talosctl get`)
- **Smart Disk Selection** — Automatically picks the smallest usable disk (>=4 GB, non-readonly, non-removable, non-USB)
- **Deterministic Static IP + Gateway** — Uses real node IPs and calculates the correct gateway from the discovered subnet
- **Smart Shared VIP** — Calculates a conflict-free VIP (`-1` default, `+1`, or fixed octet) with full CIDR; validates in both maintenance and running states
- **Per-Node Customization** — Kernel args, official system extensions, hostname via `host_vars/`
- **Cluster-Wide DNS & NTP** — Optional custom upstream servers injected into all nodes
- **Safe, Idempotent Apply** — JSON Patch-based configuration (RFC6902), works in maintenance or running mode
- **Full Bootstrap Automation** — Generates secrets/configs, applies patches, reboots, bootstraps etcd, rewrites kubeconfig to VIP, waits for nodes Ready
- **Rich Reporting** — Detailed per-node and cluster Markdown reports
- **Single-Node & HA Ready** — Correctly enables `allowSchedulingOnControlPlanes` for standalone clusters
- **Zero-Touch Tooling** — Automatically downloads and installs `talosctl`, `kubectl`, and `yq` on the Ansible control node

---

## Requirements

- Nodes booted into Talos ISO (maintenance mode) with port `50000` reachable
- Ansible >= 2.14
- Python 3.9+ on control node
- `talosctl` is auto-installed by the role (version controlled by `talosctl_version`)
- For local integration testing: Ubuntu 22.04+ with KVM/libvirt and Vagrant

---

## Role Variables

### Core Settings

| Variable | Description | Type | Default |
|----------|-------------|------|---------|
| `cluster_name` | Name of the Talos cluster | str | `talos-cluster` |
| `cp_endpoint` | Kubernetes API endpoint used by `talosctl gen config` | str | `https://<first-cp-ip>:6443` |
| `talos_vip_rule` | VIP rule: `"-1"` (lowest-1), `"+1"` (highest+1), or fixed octet (e.g. `"100"`) | str | `"-1"` |
| `talosctl_version` | Talos version to install/download | str | `v1.11.5` |

### Cluster Services

| Variable | Description | Type | Default |
|----------|-------------|------|---------|
| `cluster_dns_servers` | List of upstream DNS servers | list | `[]` |
| `cluster_dns_domain` | DNS search domain | str | `cluster.local` |
| `cluster_ntp_servers` | List of NTP servers | list | `[]` |
| `talos_extensions` | List of official extensions (short names) | list | `[]` |
| `talos_kernel_args` | List of extra kernel arguments | list | `[]` |
| `control_plane_workloads` | Remove `NoSchedule` taint from control planes | bool | `false` |
| `enable_essentials` | Install metrics-server + local-path-provisioner | bool | `false` |

### Runtime Behavior

| Variable | Description | Type | Default |
|----------|-------------|------|---------|
| `talos_force_generate` | Force regeneration of secrets and base config | bool | `false` |
| `talos_apply_dry_run` | Apply configs in dry-run mode (safe default) | bool | `true` |
| `bootstrap_timeout` | Seconds to wait for nodes to become Ready | int | `1200` |
| `report_timeout` | Seconds to wait for pods/API during reporting | int | `300` |
| `yq_version` | Version of `yq` to install | str | `v4.48.2` |

### Vault Encryption (Optional)

| Variable | Description | Type | Default |
|----------|-------------|------|---------|
| `encrypt_talos_dir` | Encrypt `.talos/` with `ansible-vault` | bool | `false` |
| `vault_pass_file` | Path to vault password file | str | `.vault_pass` |

All variables can be set in `group_vars/`, `host_vars/`, or directly in the playbook.

---

## Inventory Examples

### Single Control Plane (Standalone)

```yaml
---
all:
  children:
    talos_controlplane:
      hosts:
        cp-1:
          ansible_connection: local
          talos_ip: 192.168.121.82
          node_type: controlplane
  vars:
    cluster_name: mytalos
```

### HA Control Plane + Workers

```yaml
---
all:
  children:
    talos_controlplane:
      hosts:
        cp-1:
          ansible_connection: local
          talos_ip: 10.255.0.3
          node_type: controlplane
        cp-2:
          ansible_connection: local
          talos_ip: 10.255.0.4
          node_type: controlplane
        cp-3:
          ansible_connection: local
          talos_ip: 10.255.0.5
          node_type: controlplane
    talos_workers:
      hosts:
        worker-1:
          ansible_connection: local
          talos_ip: 10.255.0.6
          node_type: worker
        worker-2:
          ansible_connection: local
          talos_ip: 10.255.0.7
          node_type: worker
  vars:
    cluster_name: ha-cluster
    talos_vip_rule: "100"
```

### Important Inventory Notes

- Every node **must** have `ansible_connection: local` (all tasks delegate to localhost)
- Every node **must** have `talos_ip` set to the node's reachable IP in maintenance mode
- `node_type` is optional but recommended; the role auto-detects from group membership

---

## Per-Node Customization

Create `host_vars/<hostname>.yml` to customize individual nodes.

### Example: `host_vars/cp-1.yml`

```yaml
customization:
  extraKernelArgs:
    - kvm.ignore_msrs=1
    - intel_iommu=on
    - iommu=pt
  systemExtensions:
    officialExtensions:
      - siderolabs/intel-ucode
      - siderolabs/qemu-guest-agent
      - siderolabs/iscsi-tools
```

### Example: `host_vars/worker-1.yml`

```yaml
customization:
  extraKernelArgs:
    - console=ttyS0
  systemExtensions:
    officialExtensions:
      - siderolabs/qemu-guest-agent
```

---

## Usage

### Basic Playbook

```yaml
---
- name: Deploy Talos Cluster
  hosts: all
  roles:
    - name: mrrobot0985.talos
      vars:
        talos_apply_dry_run: false
        talos_force_generate: true
```

### Dry-Run First (Recommended)

```bash
ansible-playbook -i inventory.yml site.yml
```

By default `talos_apply_dry_run: true`, so the role generates configs and reports without applying them. Review `.talos/generated/` before switching to `false`.

### Real Deployment

```bash
ansible-playbook -i inventory.yml site.yml -e talos_apply_dry_run=false -e talos_force_generate=true
```

---

## Execution Pipeline (How It Works)

The role executes in six strictly ordered phases via `import_tasks`:

### 1. Setup (`00-setup.yml`)

- Creates `.talos/` subdirectories (`config/base`, `config/secrets`, `patches/nodes`, `generated`, `reports/`)
- Optionally encrypts `.talos/` with `ansible-vault`
- Ensures `/usr/local/bin` is in `PATH`
- Installs `talosctl` (pinned version, amd64/arm64 aware)
- Installs `kubectl` (latest stable, verified with SHA256 checksum)
- Installs `yq` (pinned version)

### 2. Config (`10-config.yml`)

- Generates cluster secrets (`talosctl gen secrets`) idempotently via `stat` checks
- Generates base `controlplane.yaml`, `worker.yaml`, and `talosconfig` via `talosctl gen config`
- Sets `0600` permissions on all sensitive files
- Respects `talos_force_generate` to override idempotency

### 3. Facts (`20-facts.yml`)

- Waits for Talos API port `50000` on each node
- Detects maintenance mode via `machinestatus`
- Gathers resources via `talosctl get`:
  - `disks` — for smart disk selection
  - `machineconfig.v1alpha1` — current config state
  - `version` — Talos version
  - `links` — network interfaces
  - `addresses` — IP addresses
  - `timeservers` — NTP configuration
  - `kernelparamstatus` — non-default kernel params
- Processes raw facts through `set_fact` tasks to produce:
  - `usable_disks` — filtered by size, readonly, transport
  - `install_disk` — smallest usable disk
  - `global_addresses` — non-local IPs
  - `primary_interface` — interface matching inventory IP
  - `all_interfaces` — Ethernet interfaces with state and driver
  - `changed_kernel_params` — params diverging from defaults
  - `machinestatus_stage` / `machinestatus_ready`
- Calculates cluster VIP via `talos_network_module`:
  - Aggregates all global IPv4 addresses
  - Filters out KubeSpan overlay addresses (`10.244.*`, `10.42.*`, `fd*`, etc.)
  - Determines common subnet
  - Applies `talos_vip_rule` to compute VIP

### 4. Patch (`30-patch.yml`)

- Generates per-node RFC6902 JSON patch via `talos_patch_module`:
  - Hostname
  - Install disk
  - DNS nameservers
  - NTP servers
  - VIP and network config (control plane only)
  - Extra kernel arguments
  - System extensions
  - Node labels / taints (single-node vs HA aware)
- Applies patch to base config with `talosctl machineconfig patch`
- Handles multi-document YAML (Talos v1.12+) by extracting the first document before patching

### 5. Apply (`40-apply.yml`)

- Applies final machineconfig with `talosctl apply-config --insecure`
- Respects `talos_apply_dry_run` (skips actual apply when `true`)
- Waits for control plane nodes to reboot:
  - Waits for API port `50000` to go down (node rebooting)
  - Waits for API port `50000` to come back up
- Waits for worker nodes to reboot:
  - Waits for API port `50000` to become reachable after reboot

### 6. Bootstrap (`50-bootstrap.yml`)

- Skipped entirely in dry-run mode
- Sets `talosconfig` endpoint to the first control plane node
- Bootstraps etcd on the first control plane node (`talosctl bootstrap`)
- Fetches kubeconfig (`talosctl kubeconfig`)
- Rewrites kubeconfig to use the VIP when one is configured
- Waits for Kubernetes API to become reachable (VIP or bootstrap node)
- Waits for all control plane nodes to report `Ready`
- Waits for all worker nodes to report `Ready`
- Generates cluster-wide Markdown report (node list, system pods, component statuses, CNI)

---

## Tags

Use Ansible tags to run specific phases:

| Tag | Purpose |
|-----|---------|
| `setup` | Install talosctl, kubectl, yq; create directories |
| `config` | Generate secrets and base configs |
| `facts` | Gather and process all node facts |
| `machinestatus` | Detect maintenance mode |
| `resources` | Query disks, links, addresses, version, etc. |
| `networking` | Calculate VIP and subnet |
| `node_report` | Generate per-node Markdown reports |
| `patch` | Generate per-node JSON patches and final machineconfigs |
| `apply-config` | Apply machineconfigs and wait for reboot |
| `wait` | Wait for nodes to come back after reboot |
| `bootstrap` | Bootstrap etcd, fetch kubeconfig, wait for Ready |
| `cluster_report` | Generate final cluster-wide Markdown report |
| `talosctl` | Install/update talosctl only |
| `kubectl` | Install/update kubectl only |
| `yq` | Install/update yq only |

Example:

```bash
ansible-playbook -i inventory.yml site.yml --tags facts
```

---

## Generated Output

```
.talos/
├── config/
│   ├── base/
│   │   ├── controlplane.yaml     # Base control plane config
│   │   ├── worker.yaml           # Base worker config
│   │   └── talosconfig           # Talos client config
│   └── secrets/
│       └── secrets.yaml          # Encrypted secrets bundle
├── patches/
│   └── nodes/
│       ├── cp-1.json             # Per-node RFC6902 JSON patch
│       ├── cp-2.json
│       └── worker-1.json
├── generated/
│   ├── cp-1.yaml                 # Final machineconfig (reviewable)
│   ├── cp-2.yaml
│   └── worker-1.yaml
├── reports/
│   └── <cluster_name>/
│       ├── node_cp-1.md          # Detailed per-node report
│       ├── node_cp-2.md
│       ├── node_worker-1.md
│       └── cluster_report.md    # Cluster-wide summary
└── kubeconfig                    # Final Kubernetes admin config
```

---

## Custom Python Modules

All modules live in `library/` and wrap `talosctl` or the Talos API.

| Module | Purpose |
|--------|---------|
| `talos_patch_module.py` | Builds a pure RFC6902 JSON patch from gathered facts + inventory variables. Handles hostname, disk selection, DNS, NTP, VIP, kernel args, system extensions, node labels, and taints. |
| `talos_network_module.py` | Calculates the cluster VIP from real node IPs. Aggregates all global IPv4 addresses, determines common subnet, applies `talos_vip_rule` (`-1`, `+1`, or fixed octet). Skips KubeSpan overlay addresses. |
| `talos_gen_config.py` | Thin wrapper around `talosctl gen config`. Produces base controlplane/worker configs + talosconfig. |
| `talos_gen_secrets.py` | Thin wrapper around `talosctl gen secrets`. Produces encrypted secrets bundle. |
| `talos_wait.py` | Waits for Talos API TCP ports (up or down) or for kubectl nodes to report Ready. Supports `api` and `nodes` modes. |
| `get_cluster_report.py` | Generates cluster-wide data: node list, system pods, component statuses, CNI detection, Talos version. |
| `talos_node_type.py` | Determines node type (`controlplane`, `worker`, `standalone`) from inventory group membership. |

---

## Local Integration Testing (Vagrant + libvirt)

A full Vagrant-based development environment is included. Requires Ubuntu 22.04+ with KVM/libvirt.

### Quick Start

```bash
# Install dependencies (libvirt, QEMU, vagrant-libvirt, remmina)
make install

# Boot VMs from Talos ISO (default: 1 CP, 0 workers)
make up

# Run the test playbook
make test

# Destroy VMs
make down

# Full cleanup (VMs + .talos/ + .vagrant/)
make clean

# Emergency reset (clean + full libvirt resource flush)
make flush
```

### Override Defaults

```bash
CP_COUNT=3 WORKER_COUNT=2 TALOS_VERSION=v1.10.0 make up
```

### Available Make Targets

| Target | Description |
|--------|-------------|
| `install` | Install system dependencies |
| `up` | `vagrant up` + generate inventory + wait for running |
| `down` | `vagrant destroy -f` |
| `inventory` | Regenerate `.vagrant/inventory.yml` |
| `vnc` | Generate and launch VNC viewers |
| `test` | Run `tests/test.yml` against live VMs |
| `clean` | Destroy VMs and wipe `.talos/` / `.vagrant/` |
| `flush` | Emergency reset (clean + libvirt flush) |

### Vagrant Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TALOS_CP` | `1` | Number of control plane nodes |
| `TALOS_WORKERS` | `0` | Number of worker nodes |
| `TALOS_VERSION` | `v1.11.3` | Talos ISO version to download |
| `TALOS_CP_MEMORY` | `3072` | Memory per CP node (MB) |
| `TALOS_WORKER_MEMORY` | `2048` | Memory per worker node (MB) |

---

## CI/CD

GitHub Actions workflow at `.github/workflows/ci.yml`:

1. **Lint** — Runs `yamllint` and `ansible-lint` on every push/PR
2. **Integration** — Runs on a self-hosted `linux, kvm` runner:
   - `make install`
   - `make flush`
   - `make up` (single-node)
   - `make test`
   - `make clean`
   - Uploads Talos logs on failure
3. **Publish** — Pushes the role to Ansible Galaxy on `v*` tags

---

## Design Patterns

- **Immutable target**: Talos has no SSH or package manager. The role never logs into nodes; it uses `talosctl` exclusively.
- **localhost delegation**: All tasks run on `localhost` (the Ansible control node). Inventory hosts use `ansible_connection: local` and `talos_ip` to identify nodes.
- **Dry-run by default**: `talos_apply_dry_run: true` in defaults. Set to `false` for actual deployment.
- **Idempotency**: Uses `creates:`, `stat` checks, `changed_when`, and skip-when-exists logic so re-running the playbook is safe.
- **JSON Patch only**: The role never edits YAML directly. It produces RFC6902 JSON patches and uses `talosctl machineconfig patch` to build final configs.
- **Multi-document YAML safe**: Handles Talos v1.12+ multi-document output by extracting the first document before patching.

---

## Best Practices

- Boot nodes with the official Talos ISO from Sidero Labs
- Ensure at least one disk >= 4 GB (non-removable, writable)
- Use a dedicated network segment for Talos traffic
- Set `cp_endpoint` to the future VIP or a DNS name pointing to it
- Run in dry-run mode first, review `.talos/generated/`, then deploy
- Re-run the playbook safely — it is fully idempotent
- Keep `.talos/` in `.gitignore` (the role does this automatically)
- Use `ansible-vault` for secrets in production (`encrypt_talos_dir: true`)

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| VIP conflict / unreachable | VIP overlaps with existing IP | Change `talos_vip_rule` to `"+1"` or a fixed octet |
| Node stuck installing | Bad disk selection or gateway | Check `.talos/reports/` for selected disk and subnet |
| Bootstrap fails | Firewall blocking port 6443/50000 | Ensure first CP node is reachable and not blocked |
| `apply-config` rejected | Multi-document YAML issue | The role handles this automatically via `yq` extraction |
| No usable disks found | All disks are removable/USB/CDROM | Attach a non-removable disk >= 4 GB |
| KubeSpan addresses in VIP calc | Overlay IPs leaking into aggregation | The role filters `10.244.*`, `10.42.*`, `fd*`, etc. automatically |
| Node not Ready after bootstrap | CNI not initialized | Wait longer (`bootstrap_timeout`) or check CNI logs |

---

## License

[Apache 2.0](LICENSE)

---

## Author

**Another Intelligence**  
*mrrobot0985*  
2026
