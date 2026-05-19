#!/usr/bin/python
# roles/talos/library/talos_gen_config.py
"""talos_gen_config.py - Ansible module to generate Talos cluster config."""

import subprocess
from ansible.module_utils.basic import AnsibleModule


def run_talosctl(cmd: list[str]) -> tuple[bool, str, str]:
    """Run talosctl command, return (success, stdout, stderr)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


def main() -> None:
    module = AnsibleModule(
        argument_spec=dict(
            cluster_name=dict(type="str", required=True),
            endpoint=dict(type="str", required=True),
            output_dir=dict(type="str", required=True),
            secrets_file=dict(type="str", required=True),
            force=dict(type="bool", default=False),
        )
    )

    cmd = [
        "talosctl",
        "gen",
        "config",
        module.params["cluster_name"],
        module.params["endpoint"],
        "-o",
        module.params["output_dir"],
        "--with-secrets",
        module.params["secrets_file"],
    ]
    if module.params["force"]:
        cmd.append("--force")

    success, stdout, stderr = run_talosctl(cmd)

    if not success:
        module.fail_json(msg=f"talosctl gen config failed: {stderr}", cmd=cmd)

    module.exit_json(changed=True, stdout=stdout, stderr=stderr)


if __name__ == "__main__":
    main()
