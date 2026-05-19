#!/usr/bin/python
# roles/talos/library/get_cluster_report.py
"""
get_cluster_report.py — Post-bootstrap cluster health report
"""

import json
import subprocess
import os
from ansible.module_utils.basic import AnsibleModule


def run(cmd, ignore_error=False):
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    if result.returncode != 0 and not ignore_error:
        return result.returncode, "", result.stderr.strip()
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def main():
    module = AnsibleModule(
        argument_spec=dict(
            kubeconfig=dict(type="str", required=False),
            talosconfig=dict(type="str", required=True),
            first_cp_ip=dict(type="str", required=True),
        ),
        supports_check_mode=True,
    )

    kubeconfig = module.params.get("kubeconfig")
    first_cp_ip = module.params["first_cp_ip"]  # talosconfig not used anymore

    debug = {
        "kubeconfig_exists": bool(kubeconfig and os.path.exists(kubeconfig)),
        "kubeconfig_path": kubeconfig,
        "first_cp_ip": first_cp_ip,
    }

    # Test kubectl connectivity
    kubectl_ok = False
    kubectl_err = "no kubeconfig"
    if kubeconfig and os.path.exists(kubeconfig):
        rc, _, err = run(
            ["kubectl", "--kubeconfig", kubeconfig, "get", "nodes"], ignore_error=True
        )
        kubectl_ok = rc == 0
        kubectl_err = err if rc != 0 else "OK"

    debug["kubectl_test"] = {"ok": kubectl_ok, "error": kubectl_err}

    nodes = []
    system_pods = []
    cni = "unknown"

    if kubectl_ok:
        # Nodes
        rc, out, _ = run(
            ["kubectl", "--kubeconfig", kubeconfig, "get", "nodes", "-o", "json"]
        )
        if rc == 0 and out:
            data = json.loads(out)
            for n in data.get("items", []):
                roles = [
                    label.split("/")[-1]
                    for label in n["metadata"].get("labels", {})
                    if label.startswith("node-role.kubernetes.io/")
                ]
                ready = any(
                    c["type"] == "Ready" and c["status"] == "True"
                    for c in n["status"]["conditions"]
                )
                ip = next(
                    (
                        a["address"]
                        for a in n["status"]["addresses"]
                        if a["type"] == "InternalIP"
                    ),
                    "unknown",
                )
                nodes.append(
                    {
                        "name": n["metadata"]["name"],
                        "roles": ",".join(roles) or "none",
                        "status": "True" if ready else "False",
                        "internal_ip": ip,
                        "version": n["status"]["nodeInfo"].get(
                            "kubeletVersion", "unknown"
                        ),
                    }
                )

        # System pods
        rc, out, _ = run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig,
                "get",
                "pods",
                "-n",
                "kube-system",
                "-o",
                "json",
            ]
        )
        if rc == 0 and out:
            data = json.loads(out)
            for p in data.get("items", []):
                ready = sum(
                    1
                    for s in p["status"].get("containerStatuses", [])
                    if s.get("ready")
                )
                total = len(p["spec"]["containers"])
                restarts = sum(
                    s.get("restartCount", 0)
                    for s in p["status"].get("containerStatuses", [])
                )
                system_pods.append(
                    {
                        "name": p["metadata"]["name"],
                        "ready": f"{ready}/{total}",
                        "restarts": restarts,
                        "node": p["spec"].get("nodeName", "<none>"),
                    }
                )

        # CNI
        rc, out, _ = run(
            [
                "kubectl",
                "--kubeconfig",
                kubeconfig,
                "get",
                "ds",
                "-n",
                "kube-system",
                "-o",
                "name",
            ]
        )
        if rc == 0:
            if "flannel" in out:
                cni = "flannel"
            elif "cilium" in out:
                cni = "cilium"
            elif "calico" in out:
                cni = "calico"

    module.exit_json(
        changed=False,
        kube_api_reachable=kubectl_ok,
        cni=cni,
        nodes=nodes,
        system_pods=system_pods,
        component_statuses=[],
        debug=debug,
    )


if __name__ == "__main__":
    main()
