#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ansible filter plugin — build RFC6902 JSON patch from Talos node facts."""

from ipaddress import ip_network


class FilterModule(object):
    def filters(self):
        return {"talos_patch": self.talos_patch}

    def talos_patch(
        self,
        talos_facts,
        inventory_hostname,
        is_controlplane=False,
        cluster_dns_servers=None,
        cluster_ntp_servers=None,
        customization=None,
        total_controlplanes=1,
        total_workers=0,
    ):
        if cluster_dns_servers is None:
            cluster_dns_servers = []
        if cluster_ntp_servers is None:
            cluster_ntp_servers = []
        if customization is None:
            customization = {}

        patch = []

        # Hostname + disk
        patch.append(
            {
                "op": "add",
                "path": "/machine/network/hostname",
                "value": inventory_hostname,
            }
        )
        if talos_facts.get("install_disk"):
            patch.append(
                {
                    "op": "add",
                    "path": "/machine/install/disk",
                    "value": talos_facts["install_disk"],
                }
            )

        # DNS
        if cluster_dns_servers:
            patch.append(
                {
                    "op": "add",
                    "path": "/machine/network/nameservers",
                    "value": cluster_dns_servers,
                }
            )

        # NTP
        if cluster_ntp_servers:
            patch.append({"op": "add", "path": "/machine/time", "value": {}})
            patch.append(
                {
                    "op": "add",
                    "path": "/machine/time/servers",
                    "value": cluster_ntp_servers,
                }
            )

        # extraKernelArgs
        if customization.get("extraKernelArgs"):
            patch.append(
                {
                    "op": "add",
                    "path": "/machine/install/extraKernelArgs",
                    "value": [],
                }
            )
            for arg in customization["extraKernelArgs"]:
                patch.append(
                    {
                        "op": "add",
                        "path": "/machine/install/extraKernelArgs/-",
                        "value": arg,
                    }
                )

        # extensions
        if customization.get("systemExtensions", {}).get("officialExtensions"):
            patch.append(
                {"op": "add", "path": "/machine/install/extensions", "value": []}
            )
            for ext in customization["systemExtensions"]["officialExtensions"]:
                patch.append(
                    {
                        "op": "add",
                        "path": "/machine/install/extensions/-",
                        "value": {"image": ext},
                    }
                )

        # Network + VIP
        if talos_facts.get("primary_interface"):
            ipv4 = next(
                (
                    a["address"]
                    for a in talos_facts.get("global_addresses", [])
                    if a["family"] == "inet4"
                ),
                None,
            )
            if ipv4:
                gateway = str(ip_network(ipv4, strict=False).network_address + 1)
                iface = {
                    "interface": talos_facts["primary_interface"],
                    "dhcp": False,
                    "addresses": [ipv4],
                    "routes": [{"network": "0.0.0.0/0", "gateway": gateway}],
                }
                if is_controlplane and talos_facts.get("vip"):
                    iface["vip"] = {"ip": talos_facts["vip"].split("/")[0]}

                patch.append(
                    {"op": "add", "path": "/machine/network/interfaces", "value": []}
                )
                patch.append(
                    {
                        "op": "add",
                        "path": "/machine/network/interfaces/-",
                        "value": iface,
                    }
                )

        # Labels
        if is_controlplane:
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
        if is_controlplane and total_controlplanes == 1 and total_workers == 0:
            patch.append(
                {
                    "op": "add",
                    "path": "/cluster/allowSchedulingOnControlPlanes",
                    "value": True,
                }
            )

        return patch
