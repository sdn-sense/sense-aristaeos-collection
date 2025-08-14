#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Config module for Arista EOS
Copyright: Contributors to the SENSE Project
GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

Title                   : sdn-sense/sense-aristaeos-collection
Author                  : Justas Balcas
Email                   : juztas (at) gmail.com
@Copyright              : General Public License v3.0+
Date                    : 2023/11/06
"""
__metaclass__ = type


ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}


DOCUMENTATION = ""
EXAMPLES = ""
RETURN = ""
from ansible.module_utils.basic import AnsibleModule
from ansible.utils.display import Display
from ansible_collections.ansible.netcommon.plugins.module_utils.network.common.config import (
    NetworkConfig, dumps)
from ansible_collections.sense.aristaeos.plugins.module_utils.network.aristaeos import (
    aristaeos_argument_spec, check_args, get_config, load_config)
from ansible_collections.sense.aristaeos.plugins.module_utils.runwrapper import \
    functionwrapper

display = Display()


@functionwrapper
def get_candidate(module):
    """Get the candidate configuration from the module."""
    candidate = NetworkConfig(indent=1)
    if module.params["src"]:
        candidate.load(module.params["src"])
    return candidate


@functionwrapper
def get_running_config(module):
    """Get the running configuration from the module."""
    contents = module.params["config"]
    if not contents:
        contents = get_config(module)
    return contents


@functionwrapper
def main():
    """Main function for the Ansible module."""
    backup_spec = {"filename": {}, "dir_path": {"type": "path"}}
    argument_spec = {
        "lines": {"aliases": ["commands"], "type": "list"},
        "parents": {"type": "list"},
        "src": {"type": "path"},
        "before": {"type": "list"},
        "after": {"type": "list"},
        "match": {"default": "line", "choices": ["line", "strict", "exact", "none"]},
        "replace": {"default": "line", "choices": ["line", "block"]},
        "update": {"choices": ["merge", "check"], "default": "merge"},
        "save": {"type": "bool", "default": False},
        "config": {},
        "backup": {"type": "bool", "default": False},
        "backup_options": {"type": "dict", "options": backup_spec}}

    argument_spec.update(aristaeos_argument_spec)

    mutually_exclusive = [("lines", "src"), ("parents", "src")]
    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=mutually_exclusive,
        supports_check_mode=True)

    warnings = []
    check_args(module, warnings)

    result = {"changed": False, "saved": False, "warnings": warnings}

    candidate = get_candidate(module)

    commands = []

    if candidate.items:
        commands = dumps(candidate.items, "commands")
        if (
            (isinstance(module.params["lines"], list))
            and (isinstance(module.params["lines"][0], dict))
            and set(["prompt", "answer"]).issubset(module.params["lines"][0])
        ):
            cmd = {
                "command": commands,
                "prompt": module.params["lines"][0]["prompt"],
                "answer": module.params["lines"][0]["answer"],
            }
            commands = [module.jsonify(cmd)]
        else:
            commands = commands.split("\n")

        if not module.check_mode and module.params["update"] == "merge":
            config_block = "\n".join(commands)
            load_config(module, config_block)

        result["changed"] = True
        result["commands"] = commands
        result["updates"] = commands

    module.exit_json(**result)


if __name__ == "__main__":
    main()
