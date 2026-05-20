# --------------------------------------------------------------
#  Talos + Vagrant + Libvirt – Smart defaults + session override
# --------------------------------------------------------------

.PHONY: help install up down inventory vnc test clean flush

# ---------- Smart defaults (only used if not set in session) ----------
CP_COUNT      ?= 1
WORKER_COUNT  ?= 0
TALOS_VERSION ?= v1.11.5
PROJECT_PREFIX := $(shell basename "$(PWD)")_

# ---------- Pass everything to Vagrant (session vars win) ----------
VAGRANT := env TALOS_CP=$(CP_COUNT) TALOS_WORKERS=$(WORKER_COUNT) TALOS_VERSION=$(TALOS_VERSION) vagrant

# ---------- Scripts ----------
FLUSH     := ./scripts/flush-libvirt.sh
INSTALL   := ./scripts/install-deps.sh
INVENTORY := ./scripts/generate-inventory.sh
VNC       := ./scripts/generate-vnc.sh

# ---------- Help (shows current values!) ----------
help:
	@echo "Talos Vagrant Development Environment"
	@echo ""
	@echo "Current values:"
	@echo "  CP_COUNT      = $(CP_COUNT)"
	@echo "  WORKER_COUNT  = $(WORKER_COUNT)"
	@echo "  TALOS_VERSION = $(TALOS_VERSION)"
	@echo ""
	@echo "Targets:"
	@echo "  install     → Install deps"
	@echo "  up          → vagrant up + inventory + VNC"
	@echo "  down        → vagrant destroy -f"
	@echo "  inventory   → Regenerate .vagrant/inventory.yml"
	@echo "  vnc         → Regenerate + launch VNC"
	@echo "  test        → Run tests/test.yml"
	@echo "  clean       → Nuke everything"
	@echo "  flush       → Flush everything"
	@echo ""
	@echo "Override any value from shell:"
	@echo "  CP_COUNT=3 WORKER_COUNT=2 TALOS_VERSION=v1.10.0 make up"

# ---------- Core ----------
install:
	$(INSTALL)

up:
	sg libvirt -c '$(VAGRANT) up'
	@echo "[+] Waiting for VMs to show as running..."
	@for i in 1 2 3 4 5 6 7 8 9 10; do \
		(sg libvirt -c 'virsh -c qemu:///session list --state-running --name' | grep -q "$(PROJECT_PREFIX)") || \
		(sg libvirt -c 'virsh -c qemu:///system list --state-running --name' | grep -q "$(PROJECT_PREFIX)") && break; \
		echo "  ...waiting ($$i/10)"; \
		sleep 2; \
	done
	@$(MAKE) inventory

down:
	sg libvirt -c '$(VAGRANT) destroy -f'

inventory:
	@echo "[+] Generating inventory (CP=$(CP_COUNT), WORKERS=$(WORKER_COUNT), $(TALOS_VERSION))..."
	@sg libvirt -c '$(INVENTORY)'

vnc:
	@echo "[+] Generating + launching VNC..."
	@sg libvirt -c '$(VNC)'
	@./.vagrant/open-vnc.sh

test:
	@echo "[+] Running test playbook..."
	ansible-playbook -i .vagrant/inventory.yml tests/test.yml

clean:
	@echo "[+] Full cleanup..."
	-sg libvirt -c '$(VAGRANT) destroy -f' 2>/dev/null || true
	@sg libvirt -c 'virsh vol-list default --details | awk "NR>2 && /$(PROJECT_PREFIX)/{print \$$1}" | while read vol; do virsh vol-delete --pool default "$$vol" 2>/dev/null || true; done' 2>/dev/null || true
	@rm -rf .vagrant ./tests/.talos 2>/dev/null || true
	@echo "[+] Done."

flush: clean
	@echo "[+] Emergency flush..."
	@sg libvirt -c '$(FLUSH)'
	@echo "[+] Done."

molecule-test:
	molecule test -s default
	molecule test -s ha

.DEFAULT_GOAL := help