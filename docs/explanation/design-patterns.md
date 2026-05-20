# Design Patterns

## Immutable Target

Talos Linux has no SSH daemon, no package manager, and no writable root filesystem. The role never logs into nodes. All interaction happens through `talosctl`, which speaks to the Talos API over port `50000` (maintenance) or `6443` (Kubernetes API).

## localhost Delegation

Every task in the role runs on `localhost` (the Ansible control node). Inventory entries use `ansible_connection: local` plus `talos_ip` to tell the control node which node to reach. This is clunky but necessary because Talos does not expose SSH.

## Dry-Run by Default

The role ships with `talos_apply_dry_run: true`. The first run generates configs, patches, and reports without applying anything. Review `.talos/generated/` to confirm correctness, then flip to `false` for the real deployment.

## Idempotency

Re-running the playbook is safe:

- `creates:` and `stat` checks skip already-generated artifacts.
- `changed_when` suppresses false change reports.
- Skip-when-exists logic prevents re-applying identical configs.

## JSON Patch Only

The role never edits YAML directly. Instead, it constructs a pure RFC6902 JSON patch per node and applies it with `talosctl machineconfig patch`. This keeps the base config untouched and makes every change explicit and reversible.

## Multi-Document YAML Safety

Talos v1.12+ can emit multi-document YAML. The role extracts the first document with `yq` before patching, preventing parse errors.
