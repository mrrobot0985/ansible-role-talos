# Getting Started

This tutorial walks you through deploying your first Talos Linux cluster using the role against real nodes.

## Prerequisites

- One or more servers booted from the Talos ISO in maintenance mode (port `50000` reachable)
- Ansible >= 2.14 and Python 3.9+ on your control node
- A network path from the control node to every Talos node on port `50000`

## Step 1 — Create the Inventory

Create `inventory.yml`:

```yaml
---
all:
  children:
    talos_controlplane:
      hosts:
        cp-1:
          ansible_host: 10.0.0.3
          node_type: controlplane
  vars:
    cluster_name: mytalos
```

Replace `ansible_host` with the actual maintenance-mode IP of each node.

## Step 2 — Create a Playbook

Create `site.yml`:

```yaml
---
- name: Deploy Talos Cluster
  hosts: all
  roles:
    - name: mrrobot0985.talos
```

## Step 3 — Dry-Run

```bash
ansible-playbook -i inventory.yml site.yml
```

The role generates configs and reports but does **not** touch the nodes. Review `.talos/generated/` before proceeding.

## Step 4 — Deploy

```bash
ansible-playbook -i inventory.yml site.yml \
  -e talos_apply_dry_run=false \
  -e talos_force_generate=true
```

The role applies machineconfigs, waits for reboots, bootstraps etcd, fetches kubeconfig, and waits for the node to become Ready.

## Step 5 — Verify

```bash
export KUBECONFIG=.talos/kubeconfig
kubectl get nodes
```

You should see your control-plane node in the `Ready` state.

## Testing Locally with Vagrant

If you want to test the role before deploying to real hardware, a Vagrant + libvirt development environment is included in the repository. See the [Vagrant tutorial](test-with-vagrant.md) for a step-by-step walkthrough, or the [Testing Locally](../how-to-guides/testing-locally.md) reference for full environment details.

Next: try the [HA cluster tutorial](deploy-ha-cluster.md).
