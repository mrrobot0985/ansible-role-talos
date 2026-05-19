#!/bin/bash
set -euo pipefail

log() { printf '[+] %s\n' "$*" >&2; }
warn() { printf '[!] %s\n' "$*" >&2; }
die() { printf '[X] %s\n' "$*" >&2; exit 1; }

log "Installing system dependencies..."
sudo apt update
sudo apt install -y \
  qemu-kvm \
  libvirt-daemon-system \
  libvirt-clients \
  virtinst \
  bridge-utils \
  remmina \
  remmina-plugin-vnc \
  "linux-modules-extra-$(uname -r)"

log "Loading KVM module..."
sudo modprobe kvm_intel || die "Failed to load kvm_intel"

log "Adding $USER to libvirt and kvm groups..."
sudo usermod -aG libvirt "$USER"
sudo usermod -aG kvm "$USER"

log "Installing Vagrant libvirt plugin..."
if ! vagrant plugin list | grep -q vagrant-libvirt; then
  vagrant plugin install vagrant-libvirt
else
  log "vagrant-libvirt already installed"
fi

log "Setup complete."
warn "Reboot or run: newgrp libvirt && newgrp kvm"