#!/usr/bin/python
# roles/talos/library/talos_network_module.py
"""
TalosNetworkModule — FINAL, KUBESPAN-SAFE

- Ignores /32 (KubeSpan peer routes)
- Works in boot mode
- VIP logic unchanged
- No more explosions
"""

from collections import Counter
from ipaddress import ip_interface
from ansible.module_utils.basic import AnsibleModule


def extract_ipv4_interfaces(addresses):
    interfaces = []
    for addr in addresses:
        try:
            iface = ip_interface(addr)
            if iface.version == 4:
                interfaces.append(iface)
        except (ValueError, TypeError):
            pass
    return interfaces


def filter_overlay_interfaces(interfaces):
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


def classify_by_frequency(interfaces, total_nodes):
    counter = Counter(str(i) for i in interfaces)
    real = [cidr for cidr, count in counter.items() if count == 1]
    shared = [cidr for cidr, count in counter.items() if count == total_nodes]
    return real, shared


def evaluate_common_network(real_cidrs):
    # Ignore /31 and /32 (KubeSpan peer routes, VIP, etc.)
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


def evaluate_boot_state(interfaces):
    return any(
        str(i.ip).startswith("10.244.")
        or str(i.ip).startswith("10.42.")
        or str(i.ip).startswith("fd")
        for i in interfaces
    )


def calculate_vip(network, real_bare_ips, vip_rule):
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


def main():
    module = AnsibleModule(
        argument_spec=dict(
            all_global_ips=dict(type="list", elements="str", required=True),
            vip_rule=dict(type="str", default="-1"),
            total_nodes=dict(type="int", required=True),
            control_plane_count=dict(type="int", required=True),
        ),
    )

    all_global_ips = module.params["all_global_ips"]
    vip_rule = module.params["vip_rule"]
    total_nodes = module.params["total_nodes"]
    cp_count = module.params["control_plane_count"]

    interfaces = extract_ipv4_interfaces(all_global_ips)
    is_booted = evaluate_boot_state(interfaces)
    interfaces = filter_overlay_interfaces(interfaces)

    if not interfaces:
        module.fail_json(msg="No infrastructure IPv4 interfaces found after filtering")

    real_cidrs, shared_cidrs = classify_by_frequency(interfaces, total_nodes)
    real_bare_ips = {str(ip_interface(c).ip) for c in real_cidrs}
    shared_bare_ips = {str(ip_interface(c).ip) for c in shared_cidrs}

    network = evaluate_common_network(real_cidrs)

    vip = None
    base_ip = None
    if cp_count >= 2:
        vip, base_ip = calculate_vip(network, real_bare_ips, vip_rule)
        if vip.split("/")[0] in real_bare_ips.union(shared_bare_ips):
            module.fail_json(msg=f"Calculated VIP {vip} already in use")

    module.exit_json(
        changed=False,
        vip=vip,
        cluster_subnet=str(network),
        base_ip=base_ip,
        real_node_ips=sorted(real_bare_ips),
        shared_ips=sorted(shared_bare_ips),
        is_maintenance=not is_booted,
        has_cni=is_booted,
        has_vip=bool(vip and vip.split("/")[0] in shared_bare_ips),
        control_plane_count=cp_count,
        message="VIP calculated (≥2 CP)" if cp_count >= 2 else "Single CP — no VIP",
    )


if __name__ == "__main__":
    main()
