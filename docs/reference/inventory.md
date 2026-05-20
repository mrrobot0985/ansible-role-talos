# Inventory

## Single Control Plane (Standalone)

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

## HA Control Plane + Workers

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

## Important Notes

- Every node **must** have `ansible_connection: local` (all tasks delegate to localhost)
- Every node **must** have `talos_ip` set to the node's reachable IP in maintenance mode
- `node_type` is optional but recommended; the role auto-detects from group membership
