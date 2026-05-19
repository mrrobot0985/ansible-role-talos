#!/usr/bin/python
# roles/talos/library/talos_patch_module.py
# FINAL — PURE JSON, YOUR ORIGINAL STYLE, FIXED

import os
import json
from ipaddress import ip_network
from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            talos_facts=dict(type="dict", required=True),
            inventory_hostname=dict(type="str", required=True),
            is_controlplane=dict(type="bool", default=False),
            cluster_dns_servers=dict(type="list", elements="str", default=[]),
            cluster_ntp_servers=dict(type="list", elements="str", default=[]),
            patch_dir=dict(type="str", required=True),
            customization=dict(type="dict", default={}),
            total_controlplanes=dict(type="int", required=True),
            total_workers=dict(type="int", required=True),
        ),
    )

    f = module.params["talos_facts"]
    hostname = module.params["inventory_hostname"]
    is_cp = module.params["is_controlplane"]
    cluster_dns = module.params["cluster_dns_servers"]
    cluster_ntp = module.params["cluster_ntp_servers"]
    patch_dir = module.params["patch_dir"]
    custom = module.params["customization"]
    total_cp = module.params["total_controlplanes"]
    total_workers = module.params["total_workers"]

    os.makedirs(patch_dir, exist_ok=True)
    patch_file = os.path.join(patch_dir, f"{hostname}.json")
    patch = []

    # Hostname + disk
    patch.append({"op": "add", "path": "/machine/network/hostname", "value": hostname})
    if f.get("install_disk"):
        patch.append(
            {"op": "add", "path": "/machine/install/disk", "value": f["install_disk"]}
        )

    # DNS
    if cluster_dns:
        patch.append(
            {"op": "add", "path": "/machine/network/nameservers", "value": cluster_dns}
        )

    # NTP
    if cluster_ntp:
        patch.append({"op": "add", "path": "/machine/time", "value": {}})
        patch.append(
            {"op": "add", "path": "/machine/time/servers", "value": cluster_ntp}
        )

    # extraKernelArgs — MUST create array first
    if custom.get("extraKernelArgs"):
        patch.append(
            {"op": "add", "path": "/machine/install/extraKernelArgs", "value": []}
        )
        for arg in custom["extraKernelArgs"]:
            patch.append(
                {
                    "op": "add",
                    "path": "/machine/install/extraKernelArgs/-",
                    "value": arg,
                }
            )

    # extensions — MUST create array first
    if custom.get("systemExtensions", {}).get("officialExtensions"):
        patch.append({"op": "add", "path": "/machine/install/extensions", "value": []})
        for ext in custom["systemExtensions"]["officialExtensions"]:
            patch.append(
                {
                    "op": "add",
                    "path": "/machine/install/extensions/-",
                    "value": {"image": ext},
                }
            )

    # ORIGINAL NETWORK + VIP — 100% UNTOUCHED
    if f.get("primary_interface"):
        ipv4 = next(
            (
                a["address"]
                for a in f.get("global_addresses", [])
                if a["family"] == "inet4"
            ),
            None,
        )
        if not ipv4:
            module.fail_json(msg="No IPv4 address found on primary interface")

        gateway = str(ip_network(ipv4, strict=False).network_address + 1)

        iface = {
            "interface": f["primary_interface"],
            "dhcp": False,
            "addresses": [ipv4],
            "routes": [{"network": "0.0.0.0/0", "gateway": gateway}],
        }
        if is_cp and f.get("vip"):
            iface["vip"] = {"ip": f["vip"].split("/")[0]}

        patch.append({"op": "add", "path": "/machine/network/interfaces", "value": []})
        patch.append(
            {"op": "add", "path": "/machine/network/interfaces/-", "value": iface}
        )

    # Labels
    if is_cp:
        patch.append(
            {
                "op": "add",
                "path": "/machine/nodeLabels",
                "value": {
                    "node.kubernetes.io/exclude-from-external-load-balancers": ""
                },
            }
        )

    # Single-node only
    if is_cp and total_cp == 1 and total_workers == 0:
        patch.append(
            {
                "op": "add",
                "path": "/cluster/allowSchedulingOnControlPlanes",
                "value": True,
            }
        )

    with open(patch_file, "w") as fh:
        json.dump(patch, fh, indent=2)

    module.exit_json(changed=True, patch_file=patch_file)


if __name__ == "__main__":
    main()
