#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Facts Module for Arista EOS
Copyright: Contributors to the SENSE Project
GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

Title                   : sdn-sense/sense-aristaeos-collection
Author                  : Justas Balcas
Email                   : juztas (at) gmail.com
@Copyright              : General Public License v3.0+
Date                    : 2023/11/05
"""
import json
import re
# Copyright: Contributors to the Ansible project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import iteritems
from ansible.utils.display import Display
from ansible_collections.sense.aristaeos.plugins.module_utils.network.aristaeos import (
    aristaeos_argument_spec, check_args, run_commands)
from ansible_collections.sense.aristaeos.plugins.module_utils.runwrapper import (
    classwrapper, functionwrapper)

display = Display()


@functionwrapper
def loadJson(indata, raiseExc=False):
    data = {}
    try:
        data = json.loads(indata)
    except Exception:
        display.warning(traceback.format_exc())
        if raiseExc:
            raise Exception(traceback.format_exc())
    return data


@classwrapper
class FactsBase:
    """Base class for Facts"""

    COMMANDS = []

    def __init__(self, module):
        self.module = module
        self.facts = {}
        self.responses = None

    def populate(self):
        """Populate responses"""
        self.responses = run_commands(self.module, self.COMMANDS, check_rc=False)

    def run(self, cmd):
        """Run commands"""
        return run_commands(self.module, cmd, check_rc=False)


@classwrapper
class Default(FactsBase):
    """Default Class to get basic info"""

    COMMANDS = [
        "show version | json",
        "show running-config",
        "show interfaces | json",
        "show lldp neighbors detail | json",
        "show vlan | json",
    ]

    def populate(self):
        super(Default, self).populate()
        # 0 command, get mac of system
        data = loadJson(self.responses[0])
        self.facts.setdefault("info", {"macs": []})
        if data.get("systemMacAddress"):
            self.facts["info"]["macs"].append(data["systemMacAddress"])
        # 1 command, get running config
        data = self.responses[1]
        self.facts["config"] = data
        # 2 command, get interfaces
        data = loadJson(self.responses[2])
        self.facts.setdefault("interfaces", {})
        for key, vals in data.get("interfaces", {}).items():
            self.facts["interfaces"].setdefault(key, {})
            actions = {
                "bandwidth": self.getBW,
                "duplex": self.getDuplex,
                "lineprotocol": self.getLineProtocol,
                "macaddress": self.getMacAddress,
                "description": self.getDescription,
                "mtu": self.getMTU,
                "operstatus": self.getOperStatus,
                "channel-member": self.getChannelMember,
            }
            for key1, action in actions.items():
                out = action(vals)
                if out:
                    self.facts["interfaces"][key][key1] = out
        # 3 - get lldp information
        data = loadJson(self.responses[3])
        self.facts["lldp"] = {}
        for lldpIntf, lldpdata in data.get("lldpNeighbors", {}).items():
            lldpparsed = self.getlldpIntfDict(lldpdata.get("lldpNeighborInfo", []))
            if lldpparsed:
                lldpparsed["local_port_id"] = lldpIntf
                self.facts["lldp"][lldpIntf] = lldpparsed

            # 4 - get vlan tagged interfaces;
        data = loadJson(self.responses[4])
        for key, vals in data.get("vlans", {}).items():
            vlanName = f"Vlan{key}"
            if vlanName in self.facts["interfaces"]:
                for intf in vals.get("interfaces", {}).keys():
                    if intf not in self.facts["interfaces"]:
                        continue
                    self.facts["interfaces"][vlanName].setdefault("tagged", [])
                    self.facts["interfaces"][vlanName]["tagged"].append(intf)

    def getlldpIntfDict(self, lldpneiginfo):
        out = {}
        for item in lldpneiginfo:
            # New Aristas
            if item.get("neighborInterfaceInfo", {}).get("interfaceId_v2", ""):
                out["remote_port_id"] = item["neighborInterfaceInfo"]["interfaceId_v2"]
            # Old Aristas
            elif item.get("neighborInterfaceInfo", {}).get("interfaceIdType", "") in [
                "local",
                "interfaceName",
            ]:
                tmpintf = item["neighborInterfaceInfo"].get("interfaceId", "")
                if tmpintf:
                    out["remote_port_id"] = tmpintf.replace('"', "")
            # Connection to server
            elif item.get("neighborInterfaceInfo", {}).get("interfaceIdType", "") in [
                "macAddress"
            ]:
                tmpintf = item["neighborInterfaceInfo"].get("interfaceDescription", "")
                if tmpintf:
                    out["remote_port_id"] = tmpintf.replace('"', "")
            if item.get("systemName", ""):
                out["remote_system_name"] = item["systemName"]
            if item.get("chassisId", ""):
                mac = item["chassisId"].replace(".", "")
                split_mac = [mac[index : index + 2] for index in range(0, len(mac), 2)]
                mac = ":".join(split_mac)
                out["remote_chassis_id"] = mac
        return out

    # bandwidth -> bandwidth
    def getBW(self, data):
        if "bandwidth" in data:
            return data["bandwidth"] // 1000000
        return None

    # duplex -> duplex
    def getDuplex(self, data):
        if "duplex" in data:
            return data["duplex"]
        return None

    # lineProtocolStatus -> lineprotocol
    def getLineProtocol(self, data):
        if "lineProtocolStatus" in data:
            return data["lineProtocolStatus"]
        return None

    # burnedInAddress -> macaddress
    # physicalAddress -> macaddress
    def getMacAddress(self, data):
        for key in ["physicalAddress", "burnedInAddress"]:
            if key in data:
                if data[key] not in self.facts["info"]["macs"]:
                    self.facts["info"]["macs"].append(data[key])
                return data[key]
        return None

    # description -> description
    def getDescription(self, data):
        if "description" in data:
            return data["description"]
        return None

    # mtu -> mtu
    def getMTU(self, data):
        if "mtu" in data:
            return data["mtu"]
        return None

    # interfaceStatus -> operstatus
    def getOperStatus(self, data):
        if "interfaceStatus" in data:
            return data["interfaceStatus"]
        return None

    def getChannelMember(self, data):
        out = []
        if "memberInterfaces" in data:
            out = data["memberInterfaces"].keys()
        return out


@classwrapper
class Routing(FactsBase):
    """Routing Information Class"""

    COMMANDS = ["show ip route vrf all | json", "show ipv6 route vrf all | json"]

    def populate(self):
        super(Routing, self).populate()
        data = loadJson(self.responses[1], False)
        self.facts["ipv4"] = self.getRoutes(data)
        data = loadJson(self.responses[1], False)
        self.facts["ipv6"] = self.getRoutes(data)

    def getRoutes(self, data):
        out = []
        for vrf, routes in data.get("vrfs", {}).items():
            for rfrom, rdict in routes.get("routes", {}).items():
                route = {"vrf": vrf, "from": rfrom}
                if "vias" in rdict and len(rdict.get("vias", [])) > 0:
                    if "interface" in rdict["vias"][0]:
                        intf = rdict["vias"][0]["interface"]
                        route["intf"] = intf
                    if "nexthopAddr" in rdict["vias"][0]:
                        rto = rdict["vias"][0]["nexthopAddr"]
                        route["to"] = rto
                out.append(route)
        return out


FACT_SUBSETS = {"default": Default, "routing": Routing}

VALID_SUBSETS = frozenset(FACT_SUBSETS.keys())


@functionwrapper
def main():
    """main entry point for module execution"""
    argument_spec = {"gather_subset": {"default": ["!config"], "type": "list"}}
    argument_spec.update(aristaeos_argument_spec)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    gather_subset = module.params["gather_subset"]
    runable_subsets = set()
    exclude_subsets = set()

    for subset in gather_subset:
        if subset == "all":
            runable_subsets.update(VALID_SUBSETS)
            continue
        if subset.startswith("!"):
            subset = subset[1:]
            if subset == "all":
                exclude_subsets.update(VALID_SUBSETS)
                continue
            exclude = True
        else:
            exclude = False
        if subset not in VALID_SUBSETS:
            module.fail_json(msg="Bad subset")
        if exclude:
            exclude_subsets.add(subset)
        else:
            runable_subsets.add(subset)
    if not runable_subsets:
        runable_subsets.update(VALID_SUBSETS)

    runable_subsets.difference_update(exclude_subsets)
    runable_subsets.add("default")

    facts = {"gather_subset": [runable_subsets]}

    instances = []
    for key in runable_subsets:
        instances.append(FACT_SUBSETS[key](module))

    for inst in instances:
        if inst:
            try:
                inst.populate()
                facts.update(inst.facts)
            except Exception:
                display.warning(traceback.format_exc())
                raise Exception(traceback.format_exc())

    ansible_facts = {}
    for key, value in iteritems(facts):
        key = "ansible_net_%s" % key
        ansible_facts[key] = value

    warnings = []
    check_args(module, warnings)
    module.exit_json(ansible_facts=ansible_facts, warnings=warnings)


if __name__ == "__main__":
    main()
