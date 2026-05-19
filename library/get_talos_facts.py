#!/usr/bin/python
# roles/talos/library/get_talos_facts.py
"""Gather all Talos node facts in one module."""

import subprocess
from ansible.module_utils.basic import AnsibleModule


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def main():
    module = AnsibleModule(
        argument_spec=dict(
            talos_ip=dict(type="str", required=True),
            insecure=dict(type="bool", default=True),
        )
    )

    ip = module.params["talos_ip"]
    insecure = module.params["insecure"]
    base = f"talosctl --insecure={str(insecure).lower()} --nodes {ip} get"

    facts = {}

    # List of (resource, parse_mode, fact_key)
    resources = [
        ("disks", "ndjson_dict", "talos_disks"),
        ("links", "ndjson_dict", "talos_links"),
        ("addresses", "ndjson_dict", "talos_addresses"),
        ("kernelparamstatus", "ndjson_dict", "talos_kernelparamstatus"),
        ("version", "json_single", "talos_version"),
        ("timeservers", "json_single", "talos_timeservers"),
        ("machinestatus", "json_single", "talos_machinestatus"),
    ]

    for res, _, key in resources:
        cmd = f"{base} {res} -o json".split()
        rc, out, _ = run(cmd)
        facts[key] = out if rc == 0 else "{}"

    # machineconfig (namespaced)
    cmd = f"{base} machineconfig.v1alpha1 -n config -o json".split()
    rc, out, _ = run(cmd)
    facts["talos_machineconfig_v1alpha1"] = out if rc == 0 else "{}"

    module.exit_json(changed=False, ansible_facts=facts)


if __name__ == "__main__":
    main()
