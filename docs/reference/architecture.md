# Architecture

## Execution Pipeline

The role executes in six strictly ordered phases via `import_tasks`:

### 1. Setup (`00-setup.yml`)

- Creates `.talos/` subdirectories (`config/base`, `config/secrets`, `patches/nodes`, `generated`, `.generated/`)
- Optionally encrypts `.talos/` with `ansible-vault`
- Ensures `/usr/local/bin` is in `PATH`
- Installs `talosctl` (pinned version, amd64/arm64 aware)
- Installs `kubectl` (latest stable, verified with SHA256 checksum)
- Installs `yq` (pinned version)

### 2. Config (`10-config.yml`)

- Generates cluster secrets (`talosctl gen secrets`) idempotently via `stat` checks
- Generates base `controlplane.yaml`, `worker.yaml`, and `talosconfig` via `talosctl gen config`
- Sets `0600` permissions on all sensitive files
- Respects `talos_force_generate` to override idempotency

### 3. Facts (`20-facts.yml`)

- Waits for Talos API port `50000` on each node
- Detects maintenance mode via `machinestatus`
- Gathers resources via `talosctl get`:
  - `disks` — for smart disk selection
  - `machineconfig.v1alpha1` — current config state
  - `version` — Talos version
  - `links` — network interfaces
  - `addresses` — IP addresses
  - `timeservers` — NTP configuration
  - `kernelparamstatus` — non-default kernel params
- Processes raw facts through `set_fact` tasks to produce:
  - `usable_disks` — filtered by size, readonly, transport
  - `install_disk` — smallest usable disk
  - `global_addresses` — non-local IPs
  - `primary_interface` — interface matching inventory IP
  - `all_interfaces` — Ethernet interfaces with state and driver
  - `changed_kernel_params` — params diverging from defaults
  - `machinestatus_stage` / `machinestatus_ready`
- Calculates cluster VIP via `talos_network_module`:
  - Aggregates all global IPv4 addresses
  - Filters out KubeSpan overlay addresses (`10.244.*`, `10.42.*`, `fd*`, etc.)
  - Determines common subnet
  - Applies `talos_vip_rule` to compute VIP

### 4. Patch (`30-patch.yml`)

- Generates per-node RFC6902 JSON patch via `talos_patch_module`:
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

### 5. Apply (`40-apply.yml`)

- Applies final machineconfig with `talosctl apply-config --insecure`
- Respects `talos_apply_dry_run` (skips actual apply when `true`)
- Waits for control plane nodes to reboot:
  - Waits for API port `50000` to go down (node rebooting)
  - Waits for API port `50000` to come back up
- Waits for worker nodes to reboot:
  - Waits for API port `50000` to become reachable after reboot

### 6. Bootstrap (`50-bootstrap.yml`)

- Skipped entirely in dry-run mode
- Sets `talosconfig` endpoint to the first control plane node
- Bootstraps etcd on the first control plane node (`talosctl bootstrap`)
- Fetches kubeconfig (`talosctl kubeconfig`)
- Rewrites kubeconfig to use the VIP when one is configured
- Waits for Kubernetes API to become reachable (VIP or bootstrap node)
- Waits for all control plane nodes to report `Ready`
- Waits for all worker nodes to report `Ready`
- Generates cluster documentation (Markdown report, index, mkdocs.yml) including node list, system pods, component statuses, and CNI detection

## Custom Python Modules

All modules live in `library/` and wrap `talosctl` or the Talos API.

| Module | Purpose |
| --- | --- |
| `talos_patch_module.py` | Builds a pure RFC6902 JSON patch from gathered facts + inventory variables. Handles hostname, disk selection, DNS, NTP, VIP, kernel args, system extensions, node labels, and taints. |
| `talos_network_module.py` | Calculates the cluster VIP from real node IPs. Aggregates all global IPv4 addresses, determines common subnet, applies `talos_vip_rule` (`-1`, `+1`, or fixed octet). Skips KubeSpan overlay addresses. |
| `talos_gen_config.py` | Thin wrapper around `talosctl gen config`. Produces base controlplane/worker configs + talosconfig. |
| `talos_gen_secrets.py` | Thin wrapper around `talosctl gen secrets`. Produces encrypted secrets bundle. |
| `talos_wait.py` | Waits for Talos API TCP ports (up or down) or for kubectl nodes to report Ready. Supports `api` and `nodes` modes. |
| `get_cluster_report.py` | Generates cluster-wide data: node list, system pods, component statuses, CNI detection, Talos version. |
| `talos_node_type.py` | Determines node type (`controlplane`, `worker`, `standalone`) from inventory group membership. |

## Design Patterns

- **Immutable target**: Talos has no SSH or package manager. The role never logs into nodes; it uses `talosctl` exclusively.
- **localhost delegation**: All tasks run on `localhost` (the Ansible control node). Inventory hosts use `ansible_connection: local` and `talos_ip` to identify nodes.
- **Dry-run by default**: `talos_apply_dry_run: true` in defaults. Set to `false` for actual deployment.
- **Idempotency**: Uses `creates:`, `stat` checks, `changed_when`, and skip-when-exists logic so re-running the playbook is safe.
- **JSON Patch only**: The role never edits YAML directly. It produces RFC6902 JSON patches and uses `talosctl machineconfig patch` to build final configs.
- **Multi-document YAML safe**: Handles Talos v1.12+ multi-document output by extracting the first document before patching.
