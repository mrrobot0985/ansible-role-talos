#!/usr/bin/python
# roles/talos/library/talos_gen_secrets.py
"""talos_gen_secrets.py - Ansible module to generate Talos secrets bundle."""

import subprocess
from ansible.module_utils.basic import AnsibleModule


def run_talosctl(cmd: list[str]) -> tuple[bool, str, str]:
    """Run talosctl command, return (success, stdout, stderr)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


def main() -> None:
    module = AnsibleModule(
        argument_spec=dict(
            output_file=dict(type="str", required=True),
            force=dict(type="bool", default=False),
        )
    )

    output_file: str = module.params["output_file"]
    force: bool = module.params["force"]

    cmd = ["talosctl", "gen", "secrets", "-o", output_file]
    if force:
        cmd.append("--force")

    success, stdout, stderr = run_talosctl(cmd)

    if not success:
        module.fail_json(msg=f"talosctl gen secrets failed: {stderr}", cmd=cmd)

    module.exit_json(changed=True, stdout=stdout, stderr=stderr)


if __name__ == "__main__":
    main()
