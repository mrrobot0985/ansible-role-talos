#!/usr/bin/env bash
# generate-inventory.sh — generate .vagrant/inventory.yml for Talos Vagrant cluster
# Only cp-* and worker-* nodes, no cp_endpoint, no legacy node/omni detection

set -euo pipefail

INVENTORY_DIR=".vagrant"
INVENTORY="${INVENTORY_DIR}/inventory.yml"
PROJECT_PREFIX="$(basename "$(pwd)")_"
CLUSTER_NAME="vagrant"

mkdir -p "$INVENTORY_DIR"
: > "$INVENTORY"

log() { printf '[+] %s\n' "$*" >&2; }
die() { printf '[X] %s\n' "$*" >&2; exit 1; }
# Detect which libvirt connection has our project VMs
detect_virsh_uri() {
  if virsh -c qemu:///session list --name --state-running 2>/dev/null | grep -q "^${PROJECT_PREFIX}"; then
    echo "qemu:///session"
  elif virsh -c qemu:///system list --name --state-running 2>/dev/null | grep -q "^${PROJECT_PREFIX}"; then
    echo "qemu:///system"
  elif virsh -c qemu:///session list --all --name 2>/dev/null | grep -q "^${PROJECT_PREFIX}"; then
    echo "qemu:///session"
  elif virsh -c qemu:///system list --all --name 2>/dev/null | grep -q "^${PROJECT_PREFIX}"; then
    echo "qemu:///system"
  else
    echo "qemu:///system"
  fi
}


get_ip() {
  local dom=$1
  virsh -c "$VIRSH_URI" domifaddr "$dom" 2>/dev/null |
    awk '/ipv4/ {print $4}' |
    cut -d/ -f1 |
    head -n1 || echo ""
}

wait_ip() {
  local dom=$1 ip
  log "Waiting for IP on $dom ..."
  while :; do
    ip=$(get_ip "$dom")
    [[ -n $ip ]] && { log "IP resolved: $dom → $ip"; echo "$ip"; return 0; }
    sleep 2
  done
}

# Only running VMs belonging to this Vagrant project
VIRSH_URI=$(detect_virsh_uri)
mapfile -t vms < <(virsh -c "$VIRSH_URI" list --name --state-running | grep "^${PROJECT_PREFIX}" || true)
[[ ${#vms[@]} -eq 0 ]] && die "No running VMs found for project prefix '$PROJECT_PREFIX'"

mapfile -t cp_vms     < <(printf '%s\n' "${vms[@]}" | grep "${PROJECT_PREFIX}cp-"     || true)
mapfile -t worker_vms < <(printf '%s\n' "${vms[@]}" | grep "${PROJECT_PREFIX}worker-" || true)

log "Found ${#cp_vms[@]} control-plane and ${#worker_vms[@]} worker node(s)"

cat >> "$INVENTORY" <<EOF
---
all:
  children:
    talos_controlplane:
      hosts:
EOF

for dom in "${cp_vms[@]}"; do
  name="${dom#"${PROJECT_PREFIX}"}"
  ip=$(wait_ip "$dom")
  cat >> "$INVENTORY" <<EOF
        $name:
          ansible_connection: local
          talos_ip: $ip
          node_type: controlplane
EOF
done

cat >> "$INVENTORY" <<EOF
    talos_workers:
      hosts:
EOF

for dom in "${worker_vms[@]}"; do
  name="${dom#"${PROJECT_PREFIX}"}"
  ip=$(wait_ip "$dom")
  cat >> "$INVENTORY" <<EOF
        $name:
          ansible_connection: local
          talos_ip: $ip
          node_type: worker
EOF
done

cat >> "$INVENTORY" <<EOF
  vars:
    cluster_name: $CLUSTER_NAME
EOF

log "Inventory generated → $INVENTORY"