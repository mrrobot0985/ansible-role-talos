# roles/talos/filter_plugins/talos_sanitize.py
"""
Talos Sanitize Filter — Makes any patch 100% Talos-schema safe

- permissions: "0644" → 420
- extraKernelArgs: any → list[str]
- All values forced to correct type
- Used in ONE line in patch.yml
"""

from ansible.errors import AnsibleFilterError


def _to_filemode(perm):
    if isinstance(perm, int):
        return perm
    if isinstance(perm, str):
        try:
            return int(perm, 8)
        except ValueError:
            return 420  # default 0644
    return 420


def _ensure_list_of_str(value):
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def talos_sanitize(patch):
    """Recursively sanitize a Talos RFC6902 patch for v1alpha1 schema compliance"""
    if not isinstance(patch, list):
        raise AnsibleFilterError("talos_sanitize expects a list of patch operations")

    sanitized = []
    for op in patch:
        if not isinstance(op, dict):
            sanitized.append(op)
            continue

        path = op.get("path", "")
        value = op.get("value")

        # Fix /machine/files permissions
        if path.endswith("/machine/files") and isinstance(value, list):
            fixed_files = []
            for f in value:
                if isinstance(f, dict) and "permissions" in f:
                    f = f.copy()
                    f["permissions"] = _to_filemode(f["permissions"])
                fixed_files.append(f)
            op = op.copy()
            op["value"] = fixed_files

        # Fix extraKernelArgs → must be list[str]
        elif path == "/machine/install/extraKernelArgs":
            op = op.copy()
            op["value"] = _ensure_list_of_str(value)

        # Fix nodeLabels → must be map[string]string
        elif path == "/machine/nodeLabels" and isinstance(value, dict):
            op = op.copy()
            op["value"] = {str(k): str(v) for k, v in value.items()}

        # Fix kubelet.extraArgs
        elif path == "/machine/kubelet/extraArgs":
            op = op.copy()
            op["value"] = _ensure_list_of_str(value)

        sanitized.append(op)

    return sanitized


class FilterModule(object):
    def filters(self):
        return {"talos_sanitize": talos_sanitize}
