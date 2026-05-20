#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ansible filter plugin — calculate Talos VIP from node IPv4 addresses."""

from collections import Counter
from ipaddress import ip_interface


class FilterModule(object):
    def filters(self):
        return {"talos_vip": self.talos_vip}

    def _extract_ipv4(self, addresses):
        interfaces = []
        for addr in addresses:
            try:
                iface = ip_interface(addr)
                if iface.version == 4:
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

    def _common_network(self, real_cidrs):
        networks = {
            ip_interface(c).network
            for c in real_cidrs
            if ip_interface(c).network.prefixlen <= 30
        }
        if len(networks) != 1:
            raise ValueError(
                f"Real node IPs in multiple networks (ignoring /31+): {networks}"
            )
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
        interfaces = self._extract_ipv4(all_global_ips)
        is_booted = self._is_booted(interfaces)
        interfaces = self._filter_overlay(interfaces)

        if not interfaces:
            raise ValueError("No infrastructure IPv4 interfaces found after filtering")

        real_cidrs, shared_cidrs = self._classify(interfaces, total_nodes)
        real_bare_ips = {str(ip_interface(c).ip) for c in real_cidrs}
        shared_bare_ips = {str(ip_interface(c).ip) for c in shared_cidrs}

        network = self._common_network(real_cidrs)

        vip = None
        base_ip = None
        if control_plane_count >= 2:
            vip, base_ip = self._calculate_vip(network, real_bare_ips, vip_rule)
            if vip.split("/")[0] in real_bare_ips.union(shared_bare_ips):
                raise ValueError(f"Calculated VIP {vip} already in use")

        return {
            "vip": vip,
            "cluster_subnet": str(network),
            "base_ip": base_ip,
            "real_node_ips": sorted(real_bare_ips),
            "shared_ips": sorted(shared_bare_ips),
            "is_maintenance": not is_booted,
            "has_cni": is_booted,
            "has_vip": bool(vip and vip.split("/")[0] in shared_bare_ips),
            "control_plane_count": control_plane_count,
        }
