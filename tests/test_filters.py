#!/usr/bin/env python
"""Unit tests for filter plugins."""

import pytest
from filter_plugins.talos_vip import FilterModule as VipModule
from filter_plugins.talos_patch import FilterModule as PatchModule
from filter_plugins.talos_node_type import FilterModule as NodeTypeModule
from filter_plugins.talos_markdown import FilterModule as MarkdownModule
from filter_plugins.talos_parse import FilterModule as ParseModule


class TestTalosVip:
    @pytest.fixture
    def f(self):
        return VipModule().talos_vip

    def test_single_node_no_vip(self, f):
        result = f(["192.168.1.10/24"], control_plane_count=1)
        assert result["vip"] is None
        assert result["is_maintenance"] is True
        assert result["control_plane_count"] == 1

    def test_multi_node_minus_one(self, f):
        result = f(
            ["192.168.1.10/24", "192.168.1.11/24", "192.168.1.12/24"],
            vip_rule="-1",
            total_nodes=3,
            control_plane_count=3,
        )
        assert result["vip"] == "192.168.1.9/24"
        assert result["base_ip"] == "192.168.1.10"

    def test_multi_node_plus_one(self, f):
        result = f(
            ["192.168.1.10/24", "192.168.1.11/24", "192.168.1.12/24"],
            vip_rule="+1",
            total_nodes=3,
            control_plane_count=3,
        )
        assert result["vip"] == "192.168.1.13/24"

    def test_fixed_octet(self, f):
        result = f(
            ["192.168.1.10/24", "192.168.1.11/24"],
            vip_rule="100",
            total_nodes=2,
            control_plane_count=2,
        )
        assert result["vip"] == "192.168.1.100/24"

    def test_overlay_filtering(self, f):
        result = f(
            ["192.168.1.10/24", "10.244.0.1/24", "10.42.0.1/24", "10.96.0.1/24"],
            vip_rule="-1",
            total_nodes=1,
            control_plane_count=2,
        )
        assert result["vip"] == "192.168.1.9/24"
        assert "192.168.1.10" in result["real_node_ips"]
        assert "10.244.0.1" not in result["real_node_ips"]

    def test_shared_vip_conflict(self, f):
        with pytest.raises(ValueError, match="already in use"):
            # 10 appears on all 3 nodes (shared), 11 on only 1 (real)
            # With -1 rule on real IPs: lowest real = 11, candidate = 10
            # 10 is in shared_bare_ips → conflict
            f(
                ["192.168.1.10/24", "192.168.1.11/24", "192.168.1.10/24", "192.168.1.10/24"],
                vip_rule="-1",
                total_nodes=3,
                control_plane_count=2,
            )

    def test_slash_23_subnet(self, f):
        result = f(
            ["192.168.0.10/23", "192.168.0.11/23"],
            vip_rule="-1",
            total_nodes=2,
            control_plane_count=2,
        )
        assert result["cluster_subnet"] == "192.168.0.0/23"

    def test_empty_input_raises(self, f):
        with pytest.raises(ValueError, match="No infrastructure IPv4"):
            f([], control_plane_count=2)

    def test_has_cni_detected(self, f):
        result = f(
            ["192.168.1.10/24", "10.244.0.1/24"],
            vip_rule="-1",
            total_nodes=1,
            control_plane_count=2,
        )
        assert result["has_cni"] is True


class TestTalosPatch:
    @pytest.fixture
    def f(self):
        return PatchModule().talos_patch

    def test_controlplane_includes_vip(self, f):
        facts = {
            "primary_interface": "eth0",
            "vip": "192.168.1.100/24",
            "global_addresses": [
                {"address": "192.168.1.10/24", "family": "inet4"},
            ],
        }
        patch = f(facts, "cp-1", is_controlplane=True)
        paths = [op["path"] for op in patch]
        assert "'vip'" in str(patch)
        assert "/machine/nodeLabels" in paths

    def test_worker_excludes_vip(self, f):
        facts = {"primary_interface": "eth0", "vip": "192.168.1.100/24"}
        patch = f(facts, "worker-1", is_controlplane=False)
        assert "vip" not in str(patch)
        assert "/machine/nodeLabels" not in [op["path"] for op in patch]

    def test_single_node_scheduling(self, f):
        facts = {}
        patch = f(facts, "cp-1", is_controlplane=True, total_controlplanes=1, total_workers=0)
        paths = [op["path"] for op in patch]
        assert "/cluster/allowSchedulingOnControlPlanes" in paths

    def test_multi_node_no_scheduling(self, f):
        facts = {}
        patch = f(facts, "cp-1", is_controlplane=True, total_controlplanes=2, total_workers=1)
        paths = [op["path"] for op in patch]
        assert "/cluster/allowSchedulingOnControlPlanes" not in paths

    def test_empty_customization_minimal(self, f):
        facts = {}
        patch = f(facts, "cp-1", is_controlplane=False)
        paths = [op["path"] for op in patch]
        assert "/machine/network/hostname" in paths
        assert "/machine/install/extraKernelArgs" not in paths

    def test_dns_ntp_when_provided(self, f):
        facts = {}
        patch = f(facts, "cp-1", is_controlplane=False, cluster_dns_servers=["8.8.8.8"], cluster_ntp_servers=["time.google.com"])
        paths = [op["path"] for op in patch]
        assert "/machine/network/nameservers" in paths
        assert "/machine/time/servers" in paths


class TestTalosNodeType:
    @pytest.fixture
    def f(self):
        return NodeTypeModule().talos_node_type

    def test_controlplane(self, f):
        groups = {"talos_controlplane": ["cp-1", "cp-2"], "talos_workers": []}
        assert f("cp-1", groups) == "controlplane"

    def test_worker(self, f):
        groups = {"talos_controlplane": ["cp-1"], "talos_workers": ["worker-1"]}
        assert f("worker-1", groups) == "worker"

    def test_standalone(self, f):
        groups = {"talos_controlplane": ["cp-1"], "talos_workers": []}
        assert f("cp-1", groups) == "standalone"

    def test_unknown(self, f):
        groups = {"talos_controlplane": [], "talos_workers": []}
        assert f("node-1", groups) == "unknown"


class TestTalosMarkdownAlign:
    @pytest.fixture
    def f(self):
        return MarkdownModule().talos_markdown_align

    def test_aligns_simple_table(self, f):
        text = "| a | b |\n|---|---|\n| x | y |\n"
        result = f(text)
        assert "| a   | b   |" in result

    def test_preserves_non_table(self, f):
        text = "Hello world\n"
        assert f(text) == "Hello world\n"

    def test_empty_table(self, f):
        text = "| a | b |\n|---|---|\n"
        result = f(text)
        assert "| a   | b   |" in result

    def test_trailing_newline(self, f):
        text = "| a | b |\n|---|---|\n| x | y |"
        result = f(text)
        assert result.endswith("\n")


class TestTalosParseResource:
    @pytest.fixture
    def f(self):
        return ParseModule().talos_parse_resource

    def test_json_single(self, f):
        raw = '{"spec": {"version": "v1.0"}}'
        result = f(raw, "json_single")
        assert result["spec"]["version"] == "v1.0"

    def test_ndjson_dict(self, f):
        raw = '{"metadata":{"id":"disk1"},"spec":{"size":100}}\n{"metadata":{"id":"disk2"},"spec":{"size":200}}'
        result = f(raw, "ndjson_dict")
        assert "disk1" in result
        assert result["disk2"]["spec"]["size"] == 200

    def test_ndjson_list(self, f):
        raw = '{"a":1}\n{"a":2}'
        result = f(raw, "ndjson_list")
        assert len(result) == 2
        assert result[1]["a"] == 2

    def test_empty_string(self, f):
        assert f("", "json_single") == {}
        assert f("", "ndjson_dict") == {}
        assert f("", "ndjson_list") == []

    def test_multiline_json(self, f):
        raw = '{\n  "metadata": {\n    "id": "item1"\n  },\n  "spec": {\n    "val": 1\n  }\n}\n{"metadata":{"id":"item2"},"spec":{"val":2}}'
        result = f(raw, "ndjson_dict")
        assert "item1" in result
        assert "item2" in result
