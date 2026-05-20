# mrrobot0985.talos

[![CI](https://github.com/mrrobot0985/ansible-role-talos/actions/workflows/ci.yml/badge.svg)](https://github.com/mrrobot0985/ansible-role-talos/actions/workflows/ci.yml)
[![Ansible Galaxy](https://img.shields.io/badge/galaxy-mrrobot0985.talos-blue.svg)](https://galaxy.ansible.com/mrrobot0985/talos)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Ansible](https://img.shields.io/badge/ansible-%3E%3D2.14-black.svg)](https://docs.ansible.com/ansible/latest/index.html)

> Production-grade, zero-touch Ansible role for deploying **Talos Linux Kubernetes clusters** using only live node facts — no manual YAML editing required.

## What It Does

- **Live Node Discovery** — Queries disks, network interfaces, addresses, and version directly from each node via the Talos API.
- **Smart Disk Selection** — Automatically picks the smallest usable disk (>=4 GB, non-removable, writable).
- **Deterministic Static IP + Gateway** — Uses real node IPs and calculates the correct gateway from the discovered subnet.
- **Smart Shared VIP** — Calculates a conflict-free VIP with full CIDR; validates in both maintenance and running states.
- **Safe, Idempotent Apply** — JSON Patch-based configuration (RFC6902), works in maintenance or running mode.
- **Full Bootstrap Automation** — Generates secrets, applies patches, reboots, bootstraps etcd, rewrites kubeconfig to VIP, waits for nodes Ready.
- **Single-Node & HA Ready** — Correctly enables `allowSchedulingOnControlPlanes` for standalone clusters.

## Architecture Note: Localhost Delegation

This role delegates all `talosctl` and `kubectl` operations to `localhost`.
Talos is immutable with no SSH or package manager; the Ansible control node
generates configs and calls `talosctl` directly against node IPs. Inventory
hosts need only `ansible_host` (and optionally `talos_ip`); `ansible_connection:
local` is not required on hosts. This is an intentional design choice for Talos
automation, not a workaround.

## Limitations

- **Smart disk selection** is heuristic-based (smallest non-removable, writable disk ≥4 GB). It may fail on exotic hardware (RAID, multipath, or very small NVMe partitions). Review `.talos/reports/` when in doubt.
- **IPv6 VIP is not supported** — The VIP itself (used by keepalived/kube-vip) remains IPv4-only. IPv6 dual-stack addresses are detected, filtered, and reported in `talos_network_global.cluster_subnet_v6`, but the VIP is always IPv4.
- **IPv6-only networks are not supported** — At least one routable IPv4 address per node is required for VIP calculation and endpoint discovery.

## Requirements

- Nodes booted into Talos ISO (maintenance mode, port `50000` reachable)
- Ansible >= 2.14 and Python 3.9+ on the control node
- `talosctl`, `kubectl`, and `yq` are auto-installed by the role

## 30-Second Usage

Dry-run first (safe default — generates configs without touching nodes):

```bash
ansible-playbook -i inventory.yml site.yml
```

Review `.talos/generated/`, then deploy for real:

```bash
ansible-playbook -i inventory.yml site.yml \
  -e talos_apply_dry_run=false \
  -e talos_force_generate=true
```

## Documentation

| I want to... | Go to |
| --- | --- |
| Learn how to deploy a cluster from scratch | [Getting Started](docs/tutorials/getting-started.md) |
| Solve a specific problem | [How-To Guides](docs/how-to-guides/) |
| Look up a variable, tag, or module | [Reference](docs/reference/variables.md) |
| Understand why the role works this way | [Explanation](docs/explanation/why-zero-touch.md) |

See [`docs/index.md`](docs/index.md) for the full documentation index.

## License

[Apache 2.0](LICENSE)

---

**Another Intelligence** · *mrrobot0985* · 2026
