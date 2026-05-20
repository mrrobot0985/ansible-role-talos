# Role Variables

All variables can be set in `group_vars/`, `host_vars/`, or directly in the playbook.

## Core Settings

| Variable | Description | Type | Default |
| --- | --- | --- | --- |
| `cluster_name` | Name of the Talos cluster | str | `talos-cluster` |
| `cp_endpoint` | Kubernetes API endpoint used by `talosctl gen config` | str | `https://<first-cp-ip>:6443` |
| `talos_vip_rule` | VIP rule: `"-1"` (lowest-1), `"+1"` (highest+1), or fixed octet (e.g. `"100"`) | str | `"-1"` |
| `talosctl_version` | Talos version to install/download | str | `v1.11.5` |

## Cluster Services

| Variable | Description | Type | Default |
| --- | --- | --- | --- |
| `cluster_dns_servers` | List of upstream DNS servers | list | `[]` |
| `cluster_dns_domain` | DNS search domain | str | `cluster.local` |
| `cluster_ntp_servers` | List of NTP servers | list | `[]` |
| `talos_extensions` | List of official extensions (short names) | list | `[]` |
| `talos_kernel_args` | List of extra kernel arguments | list | `[]` |
| `control_plane_workloads` | Remove `NoSchedule` taint from control planes | bool | `false` |
| `enable_essentials` | Install metrics-server + local-path-provisioner | bool | `false` |

## Runtime Behavior

| Variable | Description | Type | Default |
| --- | --- | --- | --- |
| `talos_force_generate` | Force regeneration of secrets and base config | bool | `false` |
| `talos_apply_dry_run` | Apply configs in dry-run mode (safe default) | bool | `true` |
| `bootstrap_timeout` | Seconds to wait for nodes to become Ready | int | `1200` |
| `report_timeout` | Seconds to wait for pods/API during reporting | int | `300` |
| `yq_version` | Version of `yq` to install | str | `v4.48.2` |

## Vault Encryption (Optional)

| Variable | Description | Type | Default |
| --- | --- | --- | --- |
| `encrypt_talos_dir` | Encrypt `.talos/` with `ansible-vault` | bool | `false` |
| `vault_pass_file` | Path to vault password file | str | `.vault_pass` |
