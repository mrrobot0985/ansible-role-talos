#!/usr/bin/python
# roles/talos/library/talos_node_type.py
"""
talos_node_type.py:
  • standalone   → 1 CP + 0 workers
  • controlplane → any other CP
  • worker       → worker node
"""

from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            all_groups=dict(type="dict", required=True),
            inventory_hostname=dict(type="str", required=True),
        ),
        supports_check_mode=True,
    )

    groups = module.params["all_groups"]
    hostname = module.params["inventory_hostname"]

    cp_group = groups.get("talos_controlplane", [])
    worker_group = groups.get("talos_workers", [])

    in_cp = hostname in cp_group
    in_worker = hostname in worker_group

    # External host → do nothing
    if not (in_cp or in_worker):
        module.exit_json(changed=False)

    cp_count = len(cp_group)
    worker_count = len(worker_group)

    # ←←← ORDER IS CRITICAL: check standalone FIRST
    if in_cp and cp_count == 1 and worker_count == 0:
        node_type = "standalone"
    elif in_cp:
        node_type = "controlplane"
    else:  # in_worker
        node_type = "worker"

    module.exit_json(changed=False, ansible_facts={"node_type": node_type})


if __name__ == "__main__":
    main()
