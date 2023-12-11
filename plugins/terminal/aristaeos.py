#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Terminal module for Arista EOS
Copyright: Contributors to the SENSE Project
GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

Title                   : sdn-sense/sense-aristaeos-collection
Author                  : Justas Balcas
Email                   : juztas (at) gmail.com
@Copyright              : General Public License v3.0+
Date                    : 2023/11/06
"""
import json
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
import re

from ansible.errors import AnsibleConnectionFailure
from ansible.module_utils._text import to_bytes, to_text
from ansible.plugins.terminal import TerminalBase


class TerminalModule(TerminalBase):

    terminal_stdout_re = [
        re.compile(rb"[\r\n]?[\w+\-\.:\/\[\]]+(?:\([^\)]+\)){,3}(?:>|#) ?$"),
        re.compile(rb"\[\w+\@[\w\-\.]+(?: [^\]])\] ?[>#\$] ?$"),
    ]

    terminal_stderr_re = [
        re.compile(
            rb"% ?Error: (?:(?!\bdoes not exist\b)(?!\balready exists\b)(?!\bHost not found\b)(?!\bnot active\b).)*\n"
        ),
        re.compile(rb"% ?Bad secret"),
        re.compile(rb"invalid input", re.I),
        re.compile(rb"(?:incomplete|ambiguous) command", re.I),
        re.compile(rb"connection timed out", re.I),
        re.compile(rb"'[^']' +returned error code: ?\d+"),
    ]

    terminal_initial_prompt = rb"\[y/n\]:"

    terminal_initial_answer = b"y"

    def on_open_shell(self):
        try:
            self._exec_cli_command(b"terminal length 0")
        except AnsibleConnectionFailure:
            raise AnsibleConnectionFailure(
                "unable to set terminal parameters"
            ) from AnsibleConnectionFailure

    def on_become(self, passwd=None):
        if self._get_prompt().endswith(b"#"):
            return

        cmd = {"command": "enable"}
        if passwd:
            cmd["prompt"] = to_text(r"[\r\n]?password: $", errors="surrogate_or_strict")
            cmd["answer"] = passwd

        try:
            self._exec_cli_command(
                to_bytes(json.dumps(cmd), errors="surrogate_or_strict")
            )
        except AnsibleConnectionFailure:
            raise AnsibleConnectionFailure(
                "unable to elevate privilege to enable mode"
            ) from AnsibleConnectionFailure

    def on_unbecome(self):
        prompt = self._get_prompt()
        if prompt is None:
            # if prompt is None most likely the terminal is hung up at a prompt
            return

        if prompt.strip().endswith(b")#"):
            self._exec_cli_command(b"end")
            self._exec_cli_command(b"disable")

        elif prompt.endswith(b"#"):
            self._exec_cli_command(b"disable")
