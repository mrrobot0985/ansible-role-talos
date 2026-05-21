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
| `patch` | Generate per-node JSON patches and final machineconfigs |
| `apply-config` | Apply machineconfigs and wait for reboot |
| `wait` | Wait for nodes to come back after reboot |
| `bootstrap` | Bootstrap etcd, fetch kubeconfig, wait for Ready |
| `talosctl` | Install/update talosctl only |
| `kubectl` | Install/update kubectl only |
| `yq` | Install/update yq only |

## Example

```bash
ansible-playbook -i inventory.yml site.yml --tags facts
```
