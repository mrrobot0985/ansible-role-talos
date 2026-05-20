# Tags

Use Ansible tags to run specific phases of the role pipeline.

| Tag | Purpose |
| --- | --- |
| `setup` | Install talosctl, kubectl, yq; create directories |
| `config` | Generate secrets and base configs |
| `facts` | Gather and process all node facts |
| `machinestatus` | Detect maintenance mode |
| `resources` | Query disks, links, addresses, version, etc. |
| `networking` | Calculate VIP and subnet |
| `node_report` | Generate per-node documentation (Markdown + YAML data) |
| `patch` | Generate per-node JSON patches and final machineconfigs |
| `apply-config` | Apply machineconfigs and wait for reboot |
| `wait` | Wait for nodes to come back after reboot |
| `bootstrap` | Bootstrap etcd, fetch kubeconfig, wait for Ready |
| `cluster_report` | Generate cluster documentation (Markdown + MkDocs config + YAML data) |
| `talosctl` | Install/update talosctl only |
| `kubectl` | Install/update kubectl only |
| `yq` | Install/update yq only |
| `mkdocs` | Install/update mkdocs-material only (docs opt-in) |

## Example

```bash
ansible-playbook -i inventory.yml site.yml --tags facts
```
