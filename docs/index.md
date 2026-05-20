# Documentation

Welcome to the `mrrobot0985.talos` documentation. Pick the section that matches what you need right now.

| I want to... | Go to |
| --- | --- |
| Learn how to deploy a cluster from scratch | [Tutorials](tutorials/getting-started.md) |
| Solve a specific problem | [How-To Guides](how-to-guides/) |
| Look up a variable, tag, or module | [Reference](reference/variables.md) |
| Understand why the role works this way | [Explanation](explanation/why-zero-touch.md) |

---

## Quick Start

```bash
ansible-galaxy install mrrobot0985.talos
ansible-playbook -i inventory.yml site.yml       # dry-run by default
ansible-playbook -i inventory.yml site.yml \
  -e talos_apply_dry_run=false -e talos_force_generate=true
```

See [Getting Started](tutorials/getting-started.md) for a full walkthrough.
