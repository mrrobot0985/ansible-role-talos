# Rotate Secrets

If you need to regenerate cluster secrets and base configs (for example, after rotating CA certificates), use `talos_force_generate`.

## Rotate

```bash
ansible-playbook -i inventory.yml site.yml \
  -e talos_force_generate=true \
  -e talos_apply_dry_run=false
```

This bypasses the idempotency checks and re-runs:

- `talosctl gen secrets`
- `talosctl gen config`

> Existing nodes will need the new config applied and may reboot.
