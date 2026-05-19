#!/usr/bin/python
# roles/talos/library/talos_wait.py
"""talos_wait.py - Ansible module for waiting on Talos cluster readiness

Modes:
  api     -> wait for TCP port (up or down)
  nodes   -> wait for N nodes to be Ready (kubectl)
"""

import socket
import subprocess
import time
from ansible.module_utils.basic import AnsibleModule


def run_command(cmd: list[str], timeout: int | None = None) -> tuple[int, str, str]:
    """Execute command, return (rc, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out"
    except Exception as e:
        return 1, "", str(e)


def wait_for_tcp(
    host: str,
    port: int,
    timeout: int = 300,
    delay: int = 10,
    expect_open: bool = True,
) -> tuple[bool, str]:
    """Wait for TCP port to be open or closed."""
    start = time.time()
    while time.time() - start < timeout:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        if (result == 0) == expect_open:
            status = "open" if expect_open else "closed"
            return True, f"Port {port} on {host} is {status}"
        time.sleep(delay)
    status = "open" if expect_open else "closed"
    return False, f"Timeout waiting for port {port} on {host} to be {status}"


def wait_for_nodes(
    kubeconfig: str,
    label: str,
    count: int,
    timeout: int = 1200,
    delay: int = 10,
) -> tuple[bool, str]:
    """Wait for specified number of nodes to be Ready."""
    cmd = [
        "kubectl",
        "--kubeconfig",
        kubeconfig,
        "get",
        "nodes",
        "-l",
        label,
        "-o",
        'jsonpath={.items[*].status.conditions[?(@.type=="Ready")].status}',
    ]
    start = time.time()
    ready = 0
    while time.time() - start < timeout:
        rc, stdout, _ = run_command(cmd)
        if rc == 0:
            ready = stdout.count("True")
            if ready >= count:
                return True, f"{ready}/{count} nodes ready"
        time.sleep(delay)
    return False, f"Timeout: only {ready}/{count} nodes ready"


def main() -> None:
    module = AnsibleModule(
        argument_spec=dict(
            mode=dict(type="str", required=True, choices=["api", "nodes"]),
            # api
            host=dict(type="str"),
            port=dict(type="int", default=6443),
            expect_open=dict(type="bool", default=True),
            # nodes
            kubeconfig=dict(type="str"),
            label=dict(type="str"),
            count=dict(type="int"),
            # common
            timeout=dict(type="int", default=300),
            delay=dict(type="int", default=10),
        ),
        required_if=[
            ["mode", "api", ["host", "port"]],
            ["mode", "nodes", ["kubeconfig", "label", "count"]],
        ],
        mutually_exclusive=[
            ("host", "kubeconfig"),
            ("host", "label"),
            ("host", "count"),
            ("kubeconfig", "port"),
            ("kubeconfig", "expect_open"),
        ],
        supports_check_mode=False,
    )

    p = module.params
    mode = p["mode"]
    timeout = p["timeout"]
    delay = p["delay"]

    if mode == "api":
        success, msg = wait_for_tcp(
            p["host"], p["port"], timeout, delay, p["expect_open"]
        )
    else:  # nodes
        success, msg = wait_for_nodes(
            p["kubeconfig"], p["label"], p["count"], timeout, delay
        )

    if success:
        module.exit_json(changed=False, msg=msg)
    else:
        module.fail_json(msg=msg)


if __name__ == "__main__":
    main()
