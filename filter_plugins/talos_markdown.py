#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ansible filter plugin — align markdown table pipes for MD060 compliance."""


class FilterModule(object):
    def filters(self):
        return {"talos_markdown_align": self.talos_markdown_align}

    def talos_markdown_align(self, text):
        if not isinstance(text, str):
            text = str(text)
        lines = text.splitlines()
        out, table = [], []

        def _flush_table():
            if not table:
                return
            rows = [[c.strip() for c in r[1:-1].split("|")] for r in table]
            cols = max(len(r) for r in rows)
            widths = [0] * cols
            for r in rows:
                for i, c in enumerate(r):
                    if i < cols:
                        widths[i] = max(widths[i], len(c))
            aligned = []
            for r in rows:
                cells = []
                for i in range(cols):
                    cell = r[i] if i < len(r) else ""
                    cells.append(" " + cell.ljust(widths[i]) + " ")
                aligned.append("|" + "|".join(cells) + "|")
            return aligned

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                table.append(stripped)
                continue
            if table:
                out.extend(_flush_table())
                table = []
            out.append(line)

        if table:
            out.extend(_flush_table())

        return "\n".join(out) + "\n"
