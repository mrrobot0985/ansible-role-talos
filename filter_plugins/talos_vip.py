#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ansible filter plugin — calculate Talos VIP from node IP addresses."""

from collections import Counter
from ipaddress import ip_interface


class FilterModule(object):
    def filters(self):
        return {"talos_vip": self.talos_vip}

    def _extract_ip(self, addresses):
        interfaces = []
        for addr in addresses:
            try:
                iface = ip_interface(addr)
                interfaces.append(iface)
            except (ValueError, TypeError):
                pass
        return interfaces

    def _filter_overlay(self, interfaces):
        overlay_prefixes = (
            "10.244.",
            "10.42.",
            "10.96.",
            "172.18.",
            "169.254.",
            "127.",
            "fe80:",
            "fc",
            "fd",
        )
        return [
            i
            for i in interfaces
            if not any(str(i.ip).startswith(p) for p in overlay_prefixes)
        ]

    def _classify(self, interfaces, total_nodes):
        counter = Counter(str(i) for i in interfaces)
        real = [cidr for cidr, count in counter.items() if count == 1]
        shared = [cidr for cidr, count in counter.items() if count == total_nodes]
        return real, shared

    def _common_network(self, real_cidrs, max_prefixlen=30):
        networks = {
            ip_interface(c).network
            for c in real_cidrs
            if ip_interface(c).network.prefixlen <= max_prefixlen
        }
        if len(networks) != 1:
            msg = (
                f"Real node IPs in multiple networks"
                f" (ignoring /{max_prefixlen}+): {networks}"
            )
            raise ValueError(msg)
        return networks.pop()

    def _is_booted(self, interfaces):
        return any(
            str(i.ip).startswith("10.244.")
            or str(i.ip).startswith("10.42.")
            or str(i.ip).startswith("fd")
            for i in interfaces
        )

    def _calculate_vip(self, network, real_bare_ips, vip_rule):
        octets = [int(ip.split(".")[-1]) for ip in real_bare_ips]
        lowest = min(octets)

        if vip_rule == "-1":
            candidate = lowest - 1
        elif vip_rule == "+1":
            candidate = max(octets) + 1
        else:
            candidate = int(vip_rule)

        first = int(str(network.network_address).split(".")[-1]) + 1
        last = int(str(network.broadcast_address).split(".")[-1]) - 1
        if not (first <= candidate <= last):
            raise ValueError(
                f"VIP octet .{candidate} outside usable range (.{first}–.{last})"
            )

        prefix = str(network.network_address).rsplit(".", 1)[0]
        vip_ip = f"{prefix}.{candidate}"
        return f"{vip_ip}/{network.prefixlen}", f"{prefix}.{lowest}"

    def talos_vip(
        self, all_global_ips, vip_rule="-1", total_nodes=1, control_plane_count=1
    ):
        interfaces = self._extract_ip(all_global_ips)
        is_booted = self._is_booted(interfaces)
        interfaces = self._filter_overlay(interfaces)

        ipv4_interfaces = [i for i in interfaces if i.version == 4]
        ipv6_interfaces = [i for i in interfaces if i.version == 6]

        if not ipv4_interfaces:
            raise ValueError("No infrastructure IPv4 interfaces found after filtering")

        real_cidrs_v4, shared_cidrs_v4 = self._classify(ipv4_interfaces, total_nodes)
        real_bare_ips_v4 = {str(ip_interface(c).ip) for c in real_cidrs_v4}
        shared_bare_ips_v4 = {str(ip_interface(c).ip) for c in shared_cidrs_v4}

        network_v4 = self._common_network(real_cidrs_v4, max_prefixlen=30)

        vip = None
        base_ip = None
        if control_plane_count >= 2:
            vip, base_ip = self._calculate_vip(network_v4, real_bare_ips_v4, vip_rule)
            if vip.split("/")[0] in real_bare_ips_v4.union(shared_bare_ips_v4):
                raise ValueError(f"Calculated VIP {vip} already in use")

        cluster_subnet_v6 = None
        real_node_ips_v6 = []
        if ipv6_interfaces:
            real_cidrs_v6, _ = self._classify(ipv6_interfaces, total_nodes)
            if real_cidrs_v6:
                try:
                    network_v6 = self._common_network(real_cidrs_v6, max_prefixlen=126)
                    cluster_subnet_v6 = str(network_v6)
                except ValueError:
                    pass
            real_node_ips_v6 = sorted({str(ip_interface(c).ip) for c in real_cidrs_v6})

        return {
            "vip": vip,
            "cluster_subnet": str(network_v4),
            "cluster_subnet_v6": cluster_subnet_v6,
            "base_ip": base_ip,
            "real_node_ips": sorted(real_bare_ips_v4),
            "real_node_ips_v6": real_node_ips_v6,
            "shared_ips": sorted(shared_bare_ips_v4),
            "is_maintenance": not is_booted,
            "has_cni": is_booted,
            "has_vip": bool(vip and vip.split("/")[0] in shared_bare_ips_v4),
            "control_plane_count": control_plane_count,
        }
