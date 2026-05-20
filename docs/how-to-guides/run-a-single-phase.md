# Run a Single Phase

Use Ansible tags to run only the phases you need.

## Common Tags

| Tag | What it does |
| --- | --- |
| `setup` | Install talosctl, kubectl, yq; create directories |
| `config` | Generate secrets and base configs |
| `facts` | Gather and process all node facts |
| `patch` | Generate per-node JSON patches and final machineconfigs |
| `apply-config` | Apply machineconfigs and wait for reboot |
| `bootstrap` | Bootstrap etcd, fetch kubeconfig, wait for Ready |

## Example

Gather facts only:

```bash
ansible-playbook -i inventory.yml site.yml --tags facts
```

Setup and config only (safe, no nodes required):

```bash
ansible-playbook -i inventory.yml site.yml --tags setup,config
```
