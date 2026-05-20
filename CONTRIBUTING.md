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

   - The role ships with a minimal `tests/` directory (inventory + test.yml)
   - **Preferred testing method**: spin up real Talos nodes (VMs or bare-metal) booted from the official ISO and run the playbook against them.
   - For quick sanity checks you can use Vagrant + libvirt or Proxmox boxes with the Talos ISO attached.
   - There is currently no Molecule/Docker scenario because Talos is immutable and has no SSH/package manager.

5. **Run linting locally** (optional but recommended)

   ```bash
   ansible-lint .
   yamllint .
   black --check library/ filter_plugins/
   flake8 library/ filter_plugins/
   ```

6. **Open a Pull Request**
   - Reference any related issues
   - Clearly describe what was changed and why
   - Include before/after behavior if applicable
   - PRs must pass CI (GitHub Actions runs ansible-lint, yamllint, and basic syntax checks)

## Development Notes

- Custom Python modules live in `library/`
- Filter plugins live in `filter_plugins/`
- All new features should preserve backward compatibility when possible
- Documentation updates (README, reports) are highly valued

## License

By contributing, you agree that your contributions will be licensed under the project’s Apache 2.0 license.

Thank you for helping improve this role!

— Another Intelligence / mrrobot0985
