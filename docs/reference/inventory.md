# Inventory

## Single Control Plane (Standalone)

```yaml
---
all:
  children:
    talos_controlplane:
      hosts:
        cp-1:
          ansible_host: 192.168.121.82
          node_type: controlplane
  vars:
    cluster_name: mytalos
```

## HA Control Plane + Workers

```yaml
---
all:
  children:
    talos_controlplane:
      hosts:
        cp-1:
          ansible_host: 10.255.0.3
          node_type: controlplane
        cp-2:
          ansible_host: 10.255.0.4
          node_type: controlplane
        cp-3:
          ansible_host: 10.255.0.5
          node_type: controlplane
    talos_workers:
      hosts:
        worker-1:
          ansible_host: 10.255.0.6
          node_type: worker
        worker-2:
          ansible_host: 10.255.0.7
          node_type: worker
  vars:
    cluster_name: ha-cluster
    talos_vip_rule: "100"
```

## Important Notes

- Inventory hosts need only `ansible_host` (the node's reachable IP in maintenance mode)
- `talos_ip` is optional and defaults to `ansible_host`; use it only when the target IP differs from the inventory host (e.g. NAT, proxy, or dual-homed nodes)
- `node_type` is optional; the role auto-detects from group membership (`talos_controlplane` vs `talos_workers`)
- `ansible_connection: local` is **not** required; the role uses `delegate_to: localhost` internally for all `talosctl` and `kubectl` operations
