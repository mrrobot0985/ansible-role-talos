# Testing Locally with Vagrant

This guide covers the Vagrant + libvirt development environment included in the repository.

## Prerequisites

- Ubuntu 22.04+ (tested on 24.04)
- CPU with virtualization (VT-x/AMD-V) enabled in BIOS
- At least 8 GB RAM for a small cluster
- `virsh`, `xmllint` (from `libxml2-utils`), `wget`
- Optional: VNC client like Remmina

Run `make install` first to set up libvirt, QEMU, the vagrant-libvirt plugin, and Remmina. You may need to log out and back in for group changes.

## Makefile Targets

| Target | Description |
| --- | --- |
| `make help` | Show current config and targets |
| `make up` | Boot VMs, generate inventory, launch VNC |
| `make test` | Run `up` + apply the role with the test playbook |
| `make inventory` | Regenerate `.vagrant/inventory.yml` |
| `make vnc` | Regenerate and launch VNC consoles |
| `make down` | Destroy VMs |
| `make clean` | Destroy VMs + wipe `.talos/` and `.vagrant/` |
| `make flush` | Emergency reset (clean + full libvirt flush) |

Override defaults with environment variables:

```bash
CP_COUNT=3 WORKER_COUNT=2 TALOS_VERSION=v1.11.5 make up
```

### Vagrant Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `TALOS_CP` | `1` | Number of control plane nodes |
| `TALOS_WORKERS` | `0` | Number of worker nodes |
| `TALOS_VERSION` | `v1.11.3` | Talos ISO version to download |
| `TALOS_CP_MEMORY` | `3072` | Memory per CP node (MB) |
| `TALOS_WORKER_MEMORY` | `2048` | Memory per worker node (MB) |

## File Explanations

- **Vagrantfile** — Defines VMs, downloads Talos ISO, configures libvirt (nested virt, serial logs in `.vagrant/talos-logs`).
- **scripts/install-deps.sh** — Installs packages and loads the KVM module.
- **scripts/generate-inventory.sh** — Scans running VMs via `virsh`, waits for IPs, generates `.vagrant/inventory.yml`.
- **scripts/generate-vnc.sh** — Detects VNC clients and ports, generates `.vagrant/open-vnc.sh`.
- **scripts/flush-libvirt.sh** — Nukes all non-default libvirt resources and restores defaults.

## Troubleshooting

- **No IPs in inventory**: Run `make inventory` after VMs boot (DHCP takes ~10s).
- **VNC fails**: Install Remmina; check `.vagrant/open-vnc.sh` for commands.
- **Libvirt errors**: Run `make flush`; ensure groups applied (`newgrp libvirt kvm`).
- **Test fails**: Check Talos logs in `.vagrant/talos-logs`; ensure `talosctl` is in PATH.
- **Custom ISO**: Override `TALOS_VERSION`.
