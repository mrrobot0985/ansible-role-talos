# Troubleshoot VIP Conflicts

If the VIP overlaps with an existing IP, the cluster endpoint will be unreachable.

## Symptom

- Bootstrap hangs waiting for the Kubernetes API
- `kubectl` times out against the VIP

## Diagnosis

Check `.generated/nodes/*.md` for the calculated VIP and subnet.

## Fix

Change `talos_vip_rule` to a non-conflicting value:

```yaml
vars:
  talos_vip_rule: "+1"    # highest IP + one in the subnet
  # or
  talos_vip_rule: "100"   # fixed octet in the last position
```

Re-run the playbook. The role recalculates the VIP from live node facts.
