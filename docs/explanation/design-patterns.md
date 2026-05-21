# Design Patterns

## Immutable Target

Talos Linux has no SSH daemon, no package manager, and no writable root filesystem. The role never logs into nodes. All interaction happens through `talosctl`, which speaks to the Talos API over port `50000` (maintenance) or `6443` (Kubernetes API).

## localhost Delegation

Every task that invokes `talosctl` or `kubectl` runs on `localhost` (the Ansible control node) via `delegate_to: localhost`. Inventory hosts need only `ansible_host` (and optionally `talos_ip`); `ansible_connection: local` is not required. This is intentional because Talos is immutable and does not expose SSH.

## Dry-Run by Default

The role ships with `talos_apply_dry_run: true`. The first run generates configs and patches without applying anything. Review `.talos/generated/` (final machineconfigs) to confirm correctness, then flip to `false` for the real deployment.

## Idempotency

Re-running the playbook is safe:

- `creates:` and `stat` checks skip already-generated artifacts.
- `changed_when` suppresses false change reports.
- Skip-when-exists logic prevents re-applying identical configs.

## JSON Patch Only

The role never edits YAML directly. Instead, it constructs a pure RFC6902 JSON patch per node and applies it with `talosctl machineconfig patch`. This keeps the base config untouched and makes every change explicit and reversible.

## Multi-Document YAML Safety

Talos v1.12+ can emit multi-document YAML. The role extracts the first document with `yq` before patching, preventing parse errors.
