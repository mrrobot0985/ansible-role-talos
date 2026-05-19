#!/usr/bin/env bash
# generate-vnc.sh — generate .vagrant/open-vnc.sh for current Talos Vagrant cluster
# Only cp-* and worker-* nodes, clean, modern, fast

set -euo pipefail

VNC_DIR=".vagrant"
VNC_SCRIPT="${VNC_DIR}/open-vnc.sh"
PROJECT_PREFIX="$(basename "$(pwd)")_"

mkdir -p "$VNC_DIR"
: > "$VNC_SCRIPT"

log()  { printf '[+] %s\n' "$*" >&2; }
warn() { printf '[!] %s\n' "$*" >&2; }
die()  { printf '[X] %s\n' "$*" >&2; exit 1; }
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


# VNC password from env (optional)
VNC_PASSWORD="${VNC_PASSWORD:-}"

# Detect available VNC clients (priority order)
vnc_clients=()
[[ -x "$(command -v remmina)"       ]] && vnc_clients+=("remmina")
[[ -x "$(command -v tigervncviewer)" ]] && vnc_clients+=("tigervnc")
[[ -x "$(command -v vinagre)"       ]] && vnc_clients+=("vinagre")
[[ -x "$(command -v vncviewer)"     ]] && vnc_clients+=("vncviewer")

if [[ ${#vnc_clients[@]} -eq 0 ]]; then
  warn "No VNC client found (remmina, tigervncviewer, vinagre, vncviewer)"
else
  log "Using VNC client: ${vnc_clients[0]}"
fi

# Helper: get VNC port from libvirt domain
get_vnc_port() {
  local dom=$1
  virsh -c "$VIRSH_URI" dumpxml "$dom" 2>/dev/null |
    xmllint --xpath 'string(//graphics[@type="vnc"]/@port)' - 2>/dev/null ||
    echo "5900"
}

# Handle --options (show command templates)
if [[ "${1:-}" == "--options" ]]; then
  [[ ${#vnc_clients[@]} -eq 0 ]] && die "No VNC client installed"
  for client in "${vnc_clients[@]}"; do
    case $client in
      remmina)
        [[ -n $VNC_PASSWORD ]] &&
          echo "remmina -c 'vnc://:$VNC_PASSWORD@127.0.0.1:<port>' --disable-toolbar" ||
          echo "remmina -c 'vnc://127.0.0.1:<port>' --disable-toolbar"
        ;;
      tigervnc)
        [[ -n $VNC_PASSWORD ]] &&
          echo "echo '$VNC_PASSWORD' | tigervncviewer -passwd /dev/stdin 127.0.0.1::<port>" ||
          echo "tigervncviewer 127.0.0.1::<port>"
        ;;
      vinagre)
        [[ -n $VNC_PASSWORD ]] &&
          echo "vinagre --vnc-password='$VNC_PASSWORD' 127.0.0.1::<port>" ||
          echo "vinagre 127.0.0.1::<port>"
        ;;
      vncviewer)
        [[ -n $VNC_PASSWORD ]] &&
          echo "echo '$VNC_PASSWORD' | vncviewer -passwd /dev/stdin 127.0.0.1::<port>" ||
          echo "vncviewer 127.0.0.1::<port>"
        ;;
    esac
  done
  exit 0
fi

# Only running VMs from this project
VIRSH_URI=$(detect_virsh_uri)
mapfile -t doms < <(virsh -c "$VIRSH_URI" list --name --state-running | grep "^${PROJECT_PREFIX}" || true)
[[ ${#doms[@]} -eq 0 ]] && die "No running VMs found for project prefix '$PROJECT_PREFIX'"

cat >> "$VNC_SCRIPT" <<'EOF'
#!/usr/bin/env bash
# Auto-generated VNC launcher for Talos Vagrant cluster
# Run this script to open all node consoles
EOF

for dom in "${doms[@]}"; do
  name="${dom#"${PROJECT_PREFIX}"}"
  port=$(get_vnc_port "$dom")
  log "Adding $name → VNC 127.0.0.1:$port"

  if [[ ${#vnc_clients[@]} -eq 0 ]]; then
    cat >> "$VNC_SCRIPT" <<EOF

echo "[!] No VNC client installed — connect manually to 127.0.0.1:$port ($name)"
EOF
  else
    client="${vnc_clients[0]}"
    case $client in
      remmina)
        if [[ -n $VNC_PASSWORD ]]; then
          cat >> "$VNC_SCRIPT" <<EOF

echo "Opening $name (Remmina) → VNC 127.0.0.1:$port [password protected]"
remmina -c "vnc://:$VNC_PASSWORD@127.0.0.1:$port" --disable-toolbar --disable-news --disable-stats &
EOF
        else
          cat >> "$VNC_SCRIPT" <<EOF

echo "Opening $name (Remmina) → VNC 127.0.0.1:$port"
remmina -c "vnc://127.0.0.1:$port" --disable-toolbar --disable-news --disable-stats &
EOF
        fi
        ;;
      tigervnc)
        if [[ -n $VNC_PASSWORD ]]; then
          cat >> "$VNC_SCRIPT" <<EOF

echo "Opening $name (TigerVNC) → VNC 127.0.0.1:$port [password]"
echo '$VNC_PASSWORD' | tigervncviewer -passwd /dev/stdin 127.0.0.1::$port &
EOF
        else
          cat >> "$VNC_SCRIPT" <<EOF

echo "Opening $name (TigerVNC) → VNC 127.0.0.1:$port"
tigervncviewer 127.0.0.1::$port &
EOF
        fi
        ;;
      vinagre)
        if [[ -n $VNC_PASSWORD ]]; then
          cat >> "$VNC_SCRIPT" <<EOF

echo "Opening $name (Vinagre) → VNC 127.0.0.1:$port [password]"
vinagre --vnc-password='$VNC_PASSWORD' 127.0.0.1::$port &
EOF
        else
          cat >> "$VNC_SCRIPT" <<EOF

echo "Opening $name (Vinagre) → VNC 127.0.0.1:$port"
vinagre 127.0.0.1::$port &
EOF
        fi
        ;;
      vncviewer)
        if [[ -n $VNC_PASSWORD ]]; then
          cat >> "$VNC_SCRIPT" <<EOF

echo "Opening $name (VNC Viewer) → VNC 127.0.0.1:$port [password]"
echo '$VNC_PASSWORD' | vncviewer -passwd /dev/stdin 127.0.0.1::$port &
EOF
        else
          cat >> "$VNC_SCRIPT" <<EOF

echo "Opening $name (VNC Viewer) → VNC 127.0.0.1:$port"
vncviewer 127.0.0.1::$port &
EOF
        fi
        ;;
    esac
  fi
  echo "sleep 0.8" >> "$VNC_SCRIPT"
done

chmod +x "$VNC_SCRIPT"
log "VNC launcher generated → $VNC_SCRIPT"
[[ ${#vnc_clients[@]} -gt 0 ]] && log "Run with --options to see command templates"