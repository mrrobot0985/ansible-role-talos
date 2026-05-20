# Why Zero-Touch?

Traditional Talos deployments require operators to manually create machine configuration YAML files, guess disk names, hardcode IP addresses, and keep those files in sync with the actual hardware. This is error-prone and does not scale.

This role takes a different approach: **live node discovery**.

## The Problem with Manual YAML

- Disk names vary across machines (`/dev/sda`, `/dev/nvme0n1`, `/dev/vda`).
- Network topology changes; gateways and subnets must be recalculated.
- Copy-pasting configs between nodes leads to stale hostnames, duplicate IPs, and missing extensions.
- Maintenance mode and running mode have different authentication requirements (insecure vs mTLS).

## How Zero-Touch Solves It

1. **Boot from ISO** — Every node starts in Talos maintenance mode with a known API port (`50000`).
2. **Query live facts** — The role calls `talosctl get` to read disks, interfaces, addresses, kernel params, and version directly from each node.
3. **Compute the right values** — Disk selection, VIP, gateway, and extensions are all derived from those facts plus your inventory variables.
4. **Apply safely** — A pure RFC6902 JSON patch is generated per-node and applied with `talosctl machineconfig patch`. No hand-edited YAML ever touches a node.

The result is a playbook you can run against bare-metal or VMs without pre-creating any configuration files.
