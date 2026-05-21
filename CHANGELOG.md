# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-21

### Added

- Molecule integration test scenarios (`default` and `ha`) with CI matrix for Talos v1.10.0 and v1.11.5.
- IPv6 dual-stack address detection in `talos_vip` filter; returns `cluster_subnet_v6` and `real_node_ips_v6` when present.
- Post-deploy health lookup plugin `talos_health` for checking Kubernetes API readiness, node status, etcd members, and kube-system pods.
- Config-smoke CI job for validating config generation on public runners without VMs.

### Changed

- Upgraded GitHub Actions to `actions/checkout@v6` and `actions/setup-python@v6` for Node 24 compatibility.
- Fixed `talos_force_generate` idempotency to remove stale generated configs before patching.
- Fixed Jinja2 `.items` ambiguity in templates by using `['items']` syntax.
- Fixed molecule workflow to remove invalid cross-workflow `needs: lint` dependency.
- Fixed CI workflow to install `pytest` and `yamllint`, and use `talosctl version --client`.

### Removed

- Dropped automatic MkDocs documentation generation (`talos_generate_docs`, `talos_docs_dir`, report templates, and mkdocs-material setup). The feature was off by default and introduced complex inline Jinja2 that broke lint in newer ansible-lint versions. The `.talos/generated/` directory still holds final machineconfigs for review.
- Removed unused defaults and variables (`report_timeout`, `talos_docs_format`, etc.).
- Removed deprecated `talos_network_module.py` and `talos_node_type.py` computation modules (migrated to filter plugins in prior release).
