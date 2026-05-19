#!/usr/bin/python
# roles/talos/library/talos_get_resource.py
"""talos_get_resource.py - Ansible module to fetch Talos resources via talosctl."""

import json
import subprocess
from ansible.module_utils.basic import AnsibleModule


def run(cmd: list[str]) -> tuple[int, str, str]:
    """Run command, return (returncode, stdout, stderr)."""
    p = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return p.returncode, p.stdout, p.stderr


def parse_ndjson_multiline(raw: str, to_dict: bool = True) -> dict | list:
    """Parse NDJSON with possible multiline JSON objects."""
    if not raw.strip():
        return {} if to_dict else []
    parts: list[str] = []
    current = ""
    brace = 0
    for char in raw:
        current += char
        if char == "{":
            brace += 1
        elif char == "}":
            brace -= 1
        if brace == 0 and current.strip():
            parts.append(current)
            current = ""
    if current.strip():
        parts.append(current)

    objs: dict | list = {} if to_dict else []
    for p in parts:
        try:
            obj = json.loads(p)
            if (
                to_dict
                and isinstance(obj, dict)
                and "metadata" in obj
                and "id" in obj["metadata"]
            ):
                objs[obj["metadata"]["id"]] = obj
            elif not to_dict:
                objs.append(obj)
        except json.JSONDecodeError:
            continue
    return objs


def main() -> None:
    module = AnsibleModule(
        argument_spec=dict(
            talos_ip=dict(type="str", required=True),
            resource=dict(type="str", required=True),
            namespace=dict(type="str", default=""),
            output=dict(type="str", default="json"),
            insecure=dict(type="bool", default=False),
            talosconfig=dict(type="str", default=None),  # ← NEW: path to talosconfig
            parse_mode=dict(
                type="str",
                default="ndjson_dict",
                choices=["ndjson_dict", "ndjson_list", "json_single"],
            ),
        )
    )

    params = module.params
    cmd = ["talosctl", "get", params["resource"]]
    if params["namespace"]:
        cmd += ["--namespace", params["namespace"]]
    cmd += ["-o", params["output"]]

    # Critical logic: use talosconfig when NOT insecure
    if not params["insecure"]:
        if params["talosconfig"]:
            cmd += ["--talosconfig", params["talosconfig"]]
        # else: fall back to default ~/.talos/config (not used here)
    else:
        cmd.append("--insecure")

    cmd += ["-n", params["talos_ip"]]

    rc, out, err = run(cmd)
    if rc != 0:
        empty = {} if params["parse_mode"] in ["ndjson_dict", "json_single"] else []
        module.exit_json(
            changed=False,
            ansible_facts={f"talos_{params['resource'].replace('.', '_')}": empty},
        )

    if params["parse_mode"] == "json_single":
        try:
            parsed = json.loads(out.strip())
        except json.JSONDecodeError:
            parsed = {}
    elif params["parse_mode"] == "ndjson_list":
        parsed = parse_ndjson_multiline(out, to_dict=False)
    else:  # ndjson_dict
        parsed = parse_ndjson_multiline(out)

    fact_key = f"talos_{params['resource'].replace('.', '_')}"
    module.exit_json(changed=False, ansible_facts={fact_key: parsed})


if __name__ == "__main__":
    main()
