# Customize a Node

Use `host_vars/<hostname>.yml` to apply per-node kernel arguments and system extensions.

## Example: Control Plane with Intel Microcode

Create `host_vars/cp-1.yml`:

```yaml
customization:
  extraKernelArgs:
    - kvm.ignore_msrs=1
    - intel_iommu=on
    - iommu=pt
  systemExtensions:
    officialExtensions:
      - siderolabs/intel-ucode
      - siderolabs/qemu-guest-agent
      - siderolabs/iscsi-tools
```

## Example: Worker with Serial Console

Create `host_vars/worker-1.yml`:

```yaml
customization:
  extraKernelArgs:
    - console=ttyS0
  systemExtensions:
    officialExtensions:
      - siderolabs/qemu-guest-agent
```

The role reads these during the patch phase and inserts them into the per-node JSON patch automatically.
