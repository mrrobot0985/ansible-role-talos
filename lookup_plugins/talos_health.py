#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ansible lookup plugin — post-deploy health check for Talos clusters."""

import json
import subprocess

from ansible.plugins.lookup import LookupBase


class LookupModule(LookupBase):
    def _run(self, cmd):
        result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
        return result.stdout.strip(), result.returncode

    def run(self, terms, variables=None, **kwargs):
        kubeconfig = kwargs.get("kubeconfig", "")
        talosconfig = kwargs.get("talosconfig", "")
        cp_ip = kwargs.get("cp_ip", "")
        expected_cp = int(kwargs.get("expected_cp", 1))
        expected_workers = int(kwargs.get("expected_workers", 0))

        health = {
            "api_reachable": False,
            "nodes_ready": 0,
            "nodes_total": 0,
            "control_planes_ready": 0,
            "workers_ready": 0,
            "etcd_members": 0,
            "kube_system_pods_ready": 0,
            "kube_system_pods_total": 0,
            "healthy": False,
        }

        kc_args = ["--kubeconfig", kubeconfig] if kubeconfig else []

        # Kubernetes API health
        stdout, rc = self._run(["kubectl"] + kc_args + ["get", "nodes", "-o", "json"])
        if rc == 0:
            health["api_reachable"] = True
            try:
                nodes = json.loads(stdout)
                items = nodes.get("items", [])
                health["nodes_total"] = len(items)
                for node in items:
                    labels = node.get("metadata", {}).get("labels", {})
                    conditions = node.get("status", {}).get("conditions", [])
                    ready = any(
                        c.get("type") == "Ready" and c.get("status") == "True"
                        for c in conditions
                    )
                    if ready:
                        health["nodes_ready"] += 1
                        if "node-role.kubernetes.io/control-plane" in labels:
                            health["control_planes_ready"] += 1
                        else:
                            health["workers_ready"] += 1
            except json.JSONDecodeError:
                pass

        # etcd members
        if talosconfig and cp_ip:
            stdout, rc = self._run(
                [
                    "talosctl",
                    "--talosconfig",
                    talosconfig,
                    "etcd",
                    "members",
                    "--nodes",
                    cp_ip,
                ]
            )
            if rc == 0:
                health["etcd_members"] = (
                    sum(1 for line in stdout.splitlines() if line.strip()) - 1
                )  # subtract header

        # kube-system pods
        stdout, rc = self._run(
            ["kubectl"] + kc_args + ["get", "pods", "-n", "kube-system", "-o", "json"]
        )
        if rc == 0:
            try:
                pods = json.loads(stdout)
                items = pods.get("items", [])
                health["kube_system_pods_total"] = len(items)
                for pod in items:
                    statuses = pod.get("status", {}).get("containerStatuses", []) or []
                    if all(s.get("ready") for s in statuses):
                        health["kube_system_pods_ready"] += 1
            except json.JSONDecodeError:
                pass

        # Overall health
        health["healthy"] = (
            health["api_reachable"]
            and health["nodes_ready"] == expected_cp + expected_workers
            and health["control_planes_ready"] == expected_cp
            and health["workers_ready"] == expected_workers
            and health["etcd_members"] == expected_cp
        )

        return [health]
