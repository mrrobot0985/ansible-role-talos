# Testing the Ansible Role with Vagrant and Libvirt

This document explains how to use the provided Vagrantfile, Makefile, and supporting scripts to set up a local Talos Kubernetes cluster for testing and developing the `mrrobot0985.talos` Ansible role. The setup creates virtual machines (VMs) using Libvirt, boots them with the Talos ISO, generates an Ansible inventory, and runs tests. It's designed for quick iteration on Ubuntu-based systems.

## Prerequisites
- **OS**: Ubuntu 22.04+ (tested on 24.04).
- **Hardware**: CPU with virtualization (VT-x/AMD-V) enabled in BIOS; at least 8GB RAM for a small cluster.
- **Tools**: `virsh`, `xmllint` (from `libxml2-utils`), `wget` (pre-installed on Ubuntu).
- **No root required**: Scripts use sudo where needed.
- **Optional**: VNC client like Remmina for console access.

Run `make install` first to set up Libvirt, QEMU, Vagrant plugin, and Remmina.

## Setup
1. Clone the repository and navigate to it.
2. Run `make install` to install dependencies (Libvirt, QEMU, Vagrant-libvirt, Remmina).
3. (Optional) Log out and back in after `make install` for group changes to take effect.

## Usage
Use the Makefile for all commands. Session environment variables override defaults (CP_COUNT=1, WORKER_COUNT=0, TALOS_VERSION=v1.11.5).

- `make help`: Show current config and targets.
- `make up`: Boot VMs, generate inventory, launch VNC.
  - Example: `CP_COUNT=3 WORKER_COUNT=2 TALOS_VERSION=v1.11.5 make up`.
- `make test`: Run `up` + `ansible-playbook -i .vagrant/inventory.yml tests/test.yml` (applies the role).
- `make inventory`: Regenerate `.vagrant/inventory.yml` with real IPs.
- `make vnc`: Regenerate + launch VNC consoles in `.vagrant/open-vnc.sh`.
- `make down`: Destroy VMs.
- `make clean`: Destroy VMs + wipe `.talos` and `.vagrant`.
- `make flush`: Emergency reset (clean + full Libvirt flush).

After `make up`, VMs boot into Talos maintenance mode (port 50000). Use `make test` to apply the role.

## File Explanations
- **Vagrantfile**: Defines VMs (cp-* and worker-*), downloads Talos ISO, configures Libvirt (nested virt, serial logs in `.vagrant/talos-logs`). No provisioning; relies on Ansible for config.
- **Makefile**: Central orchestrator with defaults and env overrides. Chains commands (e.g., `up` calls inventory + VNC).
- **scripts/install-deps.sh**: Installs packages/groups; loads KVM module.
- **scripts/generate-inventory.sh**: Scans running VMs via `virsh`, waits for IPs, generates `.vagrant/inventory.yml` with `talos_controlplane`/`talos_workers` groups and `cluster_name: vagrant`.
- **scripts/generate-vnc.sh**: Detects VNC clients, gets ports via `virsh dumpxml`, generates executable `.vagrant/open-vnc.sh` to launch consoles. Supports VNC_PASSWORD env.
- **scripts/flush-libvirt.sh**: Nukes all non-default Libvirt resources (domains, volumes, pools, networks); restores defaults.

## Troubleshooting
- **No IPs in inventory**: Run `make inventory` after VMs boot (DHCP takes ~10s).
- **VNC fails**: Install Remmina; check `.vagrant/open-vnc.sh` for commands.
- **Libvirt errors**: Run `make flush`; ensure groups applied (`newgrp libvirt kvm`).
- **Test fails**: Check Talos logs in `.vagrant/talos-logs`; ensure `talosctl` in PATH.
- **Custom ISO**: Override TALOS_VERSION env.

For role-specific tests, edit `tests/test.yml` or add custom playbooks. This setup ensures reproducible, isolated environments for idempotency checks and feature development.