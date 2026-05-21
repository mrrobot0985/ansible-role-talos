# Architecture

## Execution Pipeline

The role executes in six strictly ordered phases via `import_tasks`:

### 1. Setup (`setup.yml`)

- Creates `.talos/` subdirectories (`config/base`, `config/secrets`, `patches/nodes`, `generated`)
- Optionally encrypts `.talos/` with `ansible-vault`
- Ensures `/usr/local/bin` is in `PATH`
- Installs `talosctl`, `kubectl`, and `yq` (all pinned or latest stable with SHA256 verification)

### 2. Config (`generate-config.yml`)

- Generates cluster secrets (`talosctl gen secrets`) idempotently via `stat` checks
- Generates base `controlplane.yaml`, `worker.yaml`, and `talosconfig` via `talosctl gen config`
- Sets `0600` permissions on all sensitive files
- Respects `talos_force_generate` to override idempotency

### 3. Facts (`gather-facts.yml`)

- Detects maintenance mode via `machinestatus`
- Gathers resources via `talosctl get`:
  - `disks` — for smart disk selection
  - `machineconfig.v1alpha1` — current config state
  - `version` — Talos version
  - `links` — network interfaces
  - `addresses` — IP addresses
  - `timeservers` — NTP configuration
  - `kernelparamstatus` — non-default kernel params
- Processes raw facts through the `talos_fact_processor` filter to produce:
  - `usable_disks` — filtered by size, readonly, transport
  - `install_disk` — smallest usable disk
  - `global_addresses` — non-local IPs
  - `primary_interface` — interface matching inventory IP
  - `all_interfaces` — Ethernet interfaces with state and driver
  - `changed_kernel_params` — params diverging from defaults
  - `machinestatus_stage` / `machinestatus_ready`
- Calculates cluster VIP via the `talos_vip` filter:
  - Aggregates all global IPv4 addresses
  - Filters out KubeSpan overlay addresses (`10.244.*`, `10.42.*`, `fd*`, etc.)
  - Determines common subnet
  - Applies `talos_vip_rule` to compute VIP

### 4. Patch (`patch-config.yml`)

- Generates per-node RFC6902 JSON patch via the `talos_patch` filter:
  - Hostname
  - Install disk
  - DNS nameservers
  - NTP servers
  - VIP and network config (control plane only)
  - Extra kernel arguments
  - System extensions
  - Node labels / taints (single-node vs HA aware)
- Applies patch to base config with `talosctl machineconfig patch`
- Handles multi-document YAML (Talos v1.12+) by extracting the first document before patching

### 5. Apply (`apply-config.yml`)

- Applies final machineconfig with `talosctl apply-config --insecure`
- Respects `talos_apply_dry_run` (skips actual apply when `true`)
- Waits for nodes to reboot using `ansible.builtin.wait_for`

### 6. Bootstrap (`bootstrap-cluster.yml`)

- Skipped entirely in dry-run mode
- Sets `talosconfig` endpoint to the first control plane node
- Bootstraps etcd on the first control plane node (`talosctl bootstrap`)
- Fetches kubeconfig (`talosctl kubeconfig`)
- Rewrites kubeconfig to use the VIP when one is configured
- Waits for Kubernetes API to become reachable (VIP or bootstrap node)
- Waits for all control plane nodes to report `Ready`
- Waits for all worker nodes to report `Ready`

## Filter Plugins

Pure-computation logic lives in `filter_plugins/` and is called from Jinja2 expressions in tasks.

| Filter | Purpose |
| --- | --- |
| `talos_vip` | Calculates the cluster VIP from real node IPs. Aggregates all global IPv4 addresses, determines common subnet, applies `talos_vip_rule` (`-1`, `+1`, or fixed octet). Skips KubeSpan overlay addresses. |
| `talos_patch` | Builds a pure RFC6902 JSON patch from gathered facts + inventory variables. Handles hostname, disk selection, DNS, NTP, VIP, kernel args, system extensions, node labels, and taints. |
| `talos_node_type` | Determines node type (`controlplane`, `worker`, `standalone`) from inventory group membership. |
| `talos_parse_resource` | Parses NDJSON or single JSON output from `talosctl get` into Python dicts/lists. |

## Design Patterns

- **Immutable target**: Talos has no SSH or package manager. The role never logs into nodes; it uses `talosctl` exclusively.
- **localhost delegation**: All tasks that invoke `talosctl` or `kubectl` run on `localhost` (the Ansible control node) via `delegate_to: localhost`. Inventory hosts need only `ansible_host`; `ansible_connection: local` is not required.
- **Dry-run by default**: `talos_apply_dry_run: true` in defaults. Set to `false` for actual deployment.
- **Idempotency**: Uses `creates:`, `stat` checks, `changed_when`, and skip-when-exists logic so re-running the playbook is safe.
- **JSON Patch only**: The role never edits YAML directly. It produces RFC6902 JSON patches and uses `talosctl machineconfig patch` to build final configs.
- **Multi-document YAML safe**: Handles Talos v1.12+ multi-document output by extracting the first document before patching.
