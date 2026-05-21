# Contributing to ansible-role-talos

Thank you for considering contributing! This role is actively maintained and all constructive contributions are welcome.

## How to Contribute

1. **Fork** the repository and clone your fork.
2. Create a new branch:

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-fix-description
   ```

3. **Make your changes**

   - Follow existing code style:
     - YAML: 2-space indentation, no tabs
     - Python: Black-formatted, flake8-compliant
     - Commit messages: Conventional Commits style preferred
   - Keep the role idempotent and production-safe
   - Do not add external dependencies beyond `talosctl`

4. **Test your changes**

   See [Testing Tiers](#testing-tiers) below for the full testing matrix.

5. **Run linting locally** (required before PR)

   ```bash
   ansible-lint .
   yamllint .
   black --check filter_plugins/ tests/
   flake8 filter_plugins/ tests/
   ```

6. **Open a Pull Request**
   - Reference any related issues
   - Clearly describe what was changed and why
   - Include before/after behavior if applicable
   - PRs must pass CI (lint + config-smoke on public runners)

## Testing Tiers

This role uses a tiered testing strategy because Talos is an immutable OS with no SSH or package manager. Standard Docker-based testing does not exercise the actual deployment path.

### Tier 1: Fast Smoke Tests (CI on every push/PR)

Runs on `ubuntu-latest` GitHub-hosted runners. No VMs required.

Validates:

- Lint: `ansible-lint`, `yamllint`, `black`, `flake8`
- Filter unit tests: `pytest tests/test_filters.py`
- Config generation: generates secrets, base configs, per-node patches, and machineconfigs against a dummy inventory
- Config validation: `talosctl validate` on all generated configs
- YAML lint: generated configs pass `yamllint`

**How to run locally:**

```bash
ansible-lint .
yamllint .
PYTHONPATH=${PWD}:$PYTHONPATH pytest tests/test_filters.py -v
# The config-smoke job runs the full dry-run playbook:
ansible-playbook -i tests/inventory.docs.yml tests/test.yml \
  -e talos_apply_dry_run=true -e talos_force_generate=true
```

### Tier 2: Single-Node Integration (Local development)

Requires a machine with KVM/libvirt (Ubuntu 22.04+ recommended).

Spins up one control-plane VM from the Talos ISO and deploys the role with `talos_apply_dry_run: false`.

**How to run:**

```bash
make install  # install deps
make flush    # clean slate
make up       # boot VM + generate inventory
ansible-playbook -i .vagrant/inventory.yml tests/test.yml
make down     # destroy VM
```

### Tier 3: Full HA Integration (Local or self-hosted runner)

Requires KVM/libvirt. Spawns 3 control-plane + 2 worker VMs.

**How to run with Molecule:**

```bash
molecule test -s default   # 1 CP, ~15 minutes
molecule test -s ha        # 3 CP + 2 workers, ~20 minutes
```

Or via Makefile:

```bash
make molecule-test
```

**Note:** The Molecule CI workflow is gated (`continue-on-error: true`) because GitHub-hosted free runners do not support nested virtualization. Run Molecule on your local machine or a self-hosted runner with `runs-on: [self-hosted, linux, kvm]`.

## Development Notes

- Filter plugins live in `filter_plugins/`
- All new features should preserve backward compatibility when possible
- Documentation updates (README, guides) are highly valued

## License

By contributing, you agree that your contributions will be licensed under the project's Apache 2.0 license.

Thank you for helping improve this role!

— Another Intelligence / mrrobot0985
