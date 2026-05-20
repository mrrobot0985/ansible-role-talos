#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ansible filter plugin — determine Talos node type from inventory groups."""


class FilterModule(object):
    def filters(self):
        return {"talos_node_type": self.talos_node_type}

    def talos_node_type(self, inventory_hostname, groups):
        cp_group = groups.get("talos_controlplane", [])
        worker_group = groups.get("talos_workers", [])
        cp_count = len(cp_group)
        worker_count = len(worker_group)

        if inventory_hostname in cp_group and cp_count == 1 and worker_count == 0:
            return "standalone"
        if inventory_hostname in cp_group:
            return "controlplane"
        if inventory_hostname in worker_group:
            return "worker"
        return "unknown"
