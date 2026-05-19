#!/bin/bash
set -euo pipefail

echo "FLUSHING LIBVIRT..."

# Stop & destroy all domains
for dom in $(virsh list --all --name); do
  [[ -n "$dom" ]] && virsh destroy "$dom" 2>/dev/null || true
  virsh undefine "$dom" --remove-all-storage --wipe-storage --snapshots-metadata --checkpoints-metadata --nvram --tpm 2>/dev/null || true
done

# Kill QEMU as fallback
pkill -9 -f qemu || true

# Delete all volumes in non-default pools only
for pool in $(virsh pool-list --all --name); do
  [[ "$pool" != "default" && -n "$pool" ]] && {
    virsh pool-start "$pool" 2>/dev/null || true
    for vol in $(virsh vol-list --pool "$pool" --details | awk 'NR>2 {print $1}'); do
      [[ -n "$vol" ]] && virsh vol-delete "$vol" --pool "$pool" 2>/dev/null || true
    done
    virsh pool-destroy "$pool" 2>/dev/null || true
    virsh pool-delete "$pool" 2>/dev/null || true
    virsh pool-undefine "$pool" 2>/dev/null || true
  }
done

# Destroy non-default networks
for net in $(virsh net-list --all --name); do
  [[ "$net" != "default" && -n "$net" ]] && {
    virsh net-destroy "$net" 2>/dev/null || true
    virsh net-undefine "$net" 2>/dev/null || true
  }
done

# Recreate default network if missing
if ! virsh net-info default >/dev/null 2>&1; then
  virsh net-define /usr/share/libvirt/networks/default.xml 2>/dev/null || true
  virsh net-start default 2>/dev/null || true
  virsh net-autostart default 2>/dev/null || true
fi

# Recreate default pool if missing (use sudo for dir creation)
if ! virsh pool-info default >/dev/null 2>&1; then
  sudo mkdir -p /var/lib/libvirt/images
  sudo chown libvirt-qemu:kvm /var/lib/libvirt/images 2>/dev/null || true
  virsh pool-define-as default dir --target /var/lib/libvirt/images 2>/dev/null || true
  virsh pool-build default 2>/dev/null || true
  virsh pool-start default 2>/dev/null || true
  virsh pool-autostart default 2>/dev/null || true
fi

echo "LIBVIRT FLUSHED. DEFAULTS RESTORED."