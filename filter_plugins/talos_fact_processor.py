def process_talos_facts(talos_facts, inventory_hostname, hostvars_host):
    processed = {}

    # Global addresses: flat list of non-local specs
    if "addresses" in talos_facts:
        processed["global_addresses"] = [
            {
                "address": addr["spec"]["address"],
                "family": addr["spec"]["family"],
                "link_name": addr["spec"]["linkName"],
                "scope": addr["spec"]["scope"],
            }
            for addr_id, addr in talos_facts["addresses"].items()
            if addr["spec"]["scope"] == "global"
            and not addr["spec"]["address"].startswith(("127.", "::1", "fe80::"))
        ]

    # Usable disks: flat list (>=4GB, non-cdrom/readonly/usb/loop/sr)
    if "disks" in talos_facts:
        usable_disks = [
            {
                "dev_path": disk["spec"]["dev_path"],
                "pretty_size": disk["spec"]["pretty_size"],
                "transport": disk["spec"]["transport"],
                "size": disk["spec"]["size"],
            }
            for disk_id, disk in talos_facts["disks"].items()
            if disk["spec"]["size"] >= 4 * 1024**3
            and not disk["spec"]["cdrom"]
            and not disk["spec"]["readonly"]
            and disk["spec"]["transport"] != "usb"
            and not disk_id.startswith(("loop", "sr"))
        ]
        processed["usable_disks"] = usable_disks

        # Select install disk: smallest usable >=4GB
        if usable_disks:
            smallest = sorted(usable_disks, key=lambda d: d["size"])[0]
            processed["install_disk"] = smallest["dev_path"]

    # Changed kernel params: flat dict {param: {'current':, 'default':}}
    if "kernelparamstatus" in talos_facts:
        processed["changed_kernel_params"] = {
            param_id: {
                "current": param["spec"]["current"],
                "default": param["spec"]["default"],
            }
            for param_id, param in talos_facts["kernelparamstatus"].items()
            if param["spec"]["current"] != param["spec"]["default"]
        }

    # All interfaces: flat list of up ether (non-dummy/excluded)
    if "links" in talos_facts:
        exclude = ["lo", "dummy", "sit0", "ip6tnl0", "teql0", "tunl0", "bond0"]
        processed["all_interfaces"] = [
            {
                "name": link_id,
                "hardware_addr": link["spec"]["hardwareAddr"],
                "driver": link["spec"]["driver"],
                "link_state": link["spec"]["linkState"],
                "mtu": link["spec"]["mtu"],
                "operational_state": link["spec"]["operationalState"],
            }
            for link_id, link in talos_facts["links"].items()
            if link["spec"]["type"] == "ether"
            and link["spec"]["linkState"]
            and link["spec"]["driver"] not in ["dummy", "ip6tnl", "sit", "ipip"]
            and not any(link_id.startswith(ex) for ex in exclude)
        ]

    # Select primary interface: match inventory IP, fallback first global IPv4
    if "global_addresses" in processed:
        host_ip = hostvars_host.get("ansible_host") or hostvars_host.get("talos_ip")
        if host_ip:
            for addr in processed["global_addresses"]:
                if addr["address"].startswith(f"{host_ip}/"):
                    processed["primary_interface"] = addr["link_name"]
                    break
            else:  # Fallback
                ipv4_global = [
                    addr
                    for addr in processed["global_addresses"]
                    if addr["family"] == "inet4"
                ]
                if ipv4_global:
                    processed["primary_interface"] = ipv4_global[0]["link_name"]

    # Machine status: flat dict
    if "machinestatus" in talos_facts:
        spec = talos_facts["machinestatus"].get("spec", {})
        processed["machinestatus_stage"] = spec.get("stage", "unknown")
        processed["machinestatus_ready"] = spec.get("status", {}).get("ready", False)

    # Time servers: flat list
    if "timeservers" in talos_facts:
        processed["timeservers_list"] = (
            talos_facts["timeservers"].get("spec", {}).get("timeServers", [])
        )

    # Version: flat string
    if "version" in talos_facts:
        processed["version"] = (
            talos_facts["version"].get("spec", {}).get("version", "unknown")
        )

    # Machine config: spec only if present
    if "machineconfig" in talos_facts and talos_facts["machineconfig"]:
        processed["machineconfig"] = talos_facts["machineconfig"].get("spec", {})

    return processed


class FilterModule(object):
    def filters(self):
        return {"process_talos_facts": process_talos_facts}
