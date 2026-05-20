#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ansible filter plugin — parse Talos talosctl get output."""

import json


class FilterModule(object):
    def filters(self):
        return {
            "talos_parse_resource": self.talos_parse_resource,
        }

    def _parse_ndjson(self, raw):
        """Parse NDJSON with possible multiline JSON objects."""
        if not raw or not raw.strip():
            return []
        parts = []
        current = ""
        brace = 0
        for char in raw:
            current += char
            if char == "{":
                brace += 1
            elif char == "}":
                brace -= 1
            if brace == 0 and current.strip():
                parts.append(current)
                current = ""
        if current.strip():
            parts.append(current)
        objs = []
        for p in parts:
            try:
                objs.append(json.loads(p))
            except json.JSONDecodeError:
                continue
        return objs

    def talos_parse_resource(self, raw, parse_mode="ndjson_dict"):
        if parse_mode == "json_single":
            try:
                return json.loads(raw.strip()) if raw and raw.strip() else {}
            except json.JSONDecodeError:
                return {}

        objs = self._parse_ndjson(raw)
        if parse_mode == "ndjson_list":
            return objs

        # ndjson_dict
        result = {}
        for obj in objs:
            if isinstance(obj, dict) and "metadata" in obj and "id" in obj["metadata"]:
                result[obj["metadata"]["id"]] = obj
        return result
