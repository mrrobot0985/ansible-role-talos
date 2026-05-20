# Test with Vagrant

This tutorial walks you through running the role against local Talos VMs using the included Vagrant + libvirt environment. No bare metal or cloud instances required.

## What You Will Build

- 1 control-plane node booted from the Talos ISO
- 3 worker nodes booted from the Talos ISO
- A `.generated/` documentation site with live node facts

## Prerequisites

- Ubuntu 22.04+ with KVM/libvirt enabled
- `make`, `wget`, `xmllint` (`libxml2-utils`)
- 8 GB RAM minimum for the default VM sizes
- Run `make install` once to install Vagrant, QEMU, and the vagrant-libvirt plugin

## Step 1 -- Boot the VMs

```bash
make up
```

This downloads the Talos ISO, creates libvirt domains, and generates `.vagrant/inventory.yml`. Wait for the inventory to list IPs before proceeding.

## Step 2 -- Inspect the Inventory

```bash
cat .vagrant/inventory.yml
```

You should see `talos_controlplane` and `talos_workers` groups with an `ansible_host` per host.

## Step 3 -- Dry-Run Against the VMs

```bash
ansible-playbook -i .vagrant/inventory.yml tests/test.yml
```

The role gathers live facts from every VM, generates machineconfigs, and writes them to `.talos/generated/` for review. No changes are applied to the nodes.

## Step 4 -- Review Generated Documentation

The role writes browsable documentation to `.generated/`:

```bash
cd .generated
mkdocs serve
```

Open `http://127.0.0.1:8000` to view the Material-themed site with per-node pages, cluster overview, and structured YAML data.

## Step 5 -- Apply and Bootstrap

```bash
ansible-playbook -i .vagrant/inventory.yml tests/test.yml \
  -e talos_apply_dry_run=false \
  -e talos_force_generate=true
```

The role applies machineconfigs, waits for reboots, bootstraps etcd on the first control plane, fetches kubeconfig, and waits for all nodes to become Ready.

## Step 6 -- Verify

```bash
export KUBECONFIG=.talos/kubeconfig
kubectl get nodes
```

All VMs should report `Ready`.

## Cleanup

```bash
make down    # Destroy VMs
make clean   # Destroy VMs + wipe .talos/ and .vagrant/
make flush   # Emergency reset (clean + full libvirt flush)
```

## Next Steps

- [Deploy an HA cluster](deploy-ha-cluster.md) on real hardware
- [Customize a node](../how-to-guides/customize-a-node.md)
