# Deploy an HA Cluster

This tutorial walks you through deploying a highly-available Talos control plane with worker nodes using the role.

## What You Will Build

- 3 control-plane nodes for etcd and Kubernetes API redundancy
- 2 worker nodes for workloads
- A shared VIP that floats across control planes

## Step 1 — Create the Inventory

Create `inventory.yml`:

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

## Step 2 — Understand the VIP

With multiple control planes, the role calculates a shared VIP automatically:

- Gathers every node's global IPv4 addresses
- Determines the common subnet
- Applies the `talos_vip_rule` (`-1`, `+1`, or a fixed octet) to pick the VIP

Default is `"-1"` (lowest IP minus one in the subnet). You can override it:

```yaml
vars:
  talos_vip_rule: "100"
```

## Step 3 — Dry-Run

```bash
ansible-playbook -i inventory.yml site.yml
```

Review `.talos/generated/` and `.talos/reports/` before applying.

## Step 4 — Deploy

```bash
ansible-playbook -i inventory.yml site.yml \
  -e talos_apply_dry_run=false \
  -e talos_force_generate=true
```

The role bootstraps etcd on the first control plane, waits for all nodes to reboot into the running stage, and verifies every node reports `Ready`.

## Step 5 — Verify

```bash
export KUBECONFIG=.talos/kubeconfig
kubectl get nodes
kubectl get pods -n kube-system
```

You should see all five nodes and a healthy set of system pods.

## Next Steps

- [Customize a node](../how-to-guides/customize-a-node.md)
- [Troubleshoot VIP conflicts](../how-to-guides/troubleshoot-vip-conflicts.md)
