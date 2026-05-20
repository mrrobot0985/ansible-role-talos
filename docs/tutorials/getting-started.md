# Getting Started

This tutorial walks you through deploying your first Talos Linux cluster on your local machine using Vagrant and libvirt.

## Prerequisites

- Ubuntu 22.04+ (tested on 24.04)
- CPU with virtualization enabled (VT-x/AMD-V)
- At least 8 GB RAM

## Step 1 — Install Dependencies

```bash
make install
```

This installs libvirt, QEMU, the vagrant-libvirt plugin, and Remmina.

> You may need to log out and back in for group changes to take effect.

## Step 2 — Boot the VMs

```bash
make up
```

This creates one control-plane VM, boots it from the Talos ISO, and generates `.vagrant/inventory.yml`.

## Step 3 — Dry-Run

```bash
ansible-playbook -i .vagrant/inventory.yml tests/test.yml
```

Because `talos_apply_dry_run` defaults to `true`, the role generates configs and reports but does **not** touch the nodes. Review the output in `.talos/generated/`.

## Step 4 — Deploy for Real

```bash
ansible-playbook -i .vagrant/inventory.yml tests/test.yml \
  -e talos_apply_dry_run=false \
  -e talos_force_generate=true
```

The role applies machineconfigs, waits for reboots, bootstraps etcd, fetches kubeconfig, and waits for the node to become Ready.

## Step 5 — Verify

```bash
export KUBECONFIG=.talos/kubeconfig
kubectl get nodes
```

You should see your single control-plane node in the `Ready` state.

## Cleanup

```bash
make down   # destroy VMs
make clean  # destroy VMs + wipe .talos/ and .vagrant/
```

Next: try the [HA cluster tutorial](deploy-ha-cluster.md).
