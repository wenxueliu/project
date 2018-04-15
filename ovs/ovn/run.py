#!/usr/bin/env python
# encoding: utf-8

import json
from pprint import pprint


class Cluster(object):

    def __init__(self, config_file):
        with open(config_file) as config_file:
            self.config = json.load(config_file)

    def get_nodes(self):
        #print(self.config["nodes"])
        return self.config["nodes"]

    def get_master(self, master_id):
        for node in self.get_nodes():
            if node["ovn_master"]["id"] == master_id:
                return node["ovn_master"]

    def get_master_ip(self, master_id):
        for node in self.get_nodes():
            if node["ovn_master"]["id"] == master_id:
                return node["ovn_master"]["ip"]

    def get_master_manage_ip(self, master_id):
        for node in self.get_nodes():
            if node["ovn_master"]["id"] == master_id:
                return node["ovn_master"]["ip"]

    def get_slave(self, slave_id):
        for node in self.get_nodes():
            for host in node["ovn_slave"]:
                if host["id"] == slave_id:
                    return host

    def get_slave_ip(self, slave_id):
        for node in self.get_nodes():
            for host in node["ovn_slave"]:
                if host["id"] == slave_id:
                    return host["ip"]

    def get_routes(self):
        #print(self.config["logical_routes"])
        return self.config["logical_routes"]

    def get_route(self, route_id):
        #print(self.config["logical_routes"])
        for route in self.config["logical_routes"]:
            if route["id"] == route_id:
                return route

    def get_switches(self):
        #print(self.config["logical_switches"])
        return self.config["logical_switches"]

    def get_switch(self, switch_id):
        for switch in self.get_switches():
            if switch["id"] == switch_id:
                return switch

    def get_switch_port(self, port_id):
        for switch in self.get_switches():
            for port in switch["ports"]:
                if port["id"] == port_id:
                    return port

    def get_switch_master(self, switch_id):
        for switch in self.get_switches():
            if switch["id"] == switch_id:
                return self.get_master(switch["master_id"])

    #def get_switch_master_ip(self, switch_id):
    #    for switch in self.get_switches():
    #        if switch["id"] == switch_id:
    #            return self.get_master_ip(switch["master_id"])

    #def get_switch_master_manage_ip(self, switch_id):
    #    for switch in self.get_switches():
    #        if switch["id"] == switch_id:
    #            return self.get_master_manage_ip(switch["master_id"])

    def get_vhosts(self):
        #print(self.config["virtual_hosts"])
        return self.config["virtual_hosts"]

    def get_vhost_switch(self, host_id):
        for host in self.get_vhosts():
            if host["id"] == host_id:
                return self.get_switch(host["switch_id"])

    def get_vhost_master(self, host_id):
        for host in self.get_vhosts():
            if host["id"] == host_id:
                return self.get_master(self.get_switch(host["switch_id"])["master_id"])

    def get_vhost_slave(self, host_name):
        for host in self.get_vhosts():
            if host["name"] == host_name:
                return self.get_slave(host["slave_id"])

    def execute(self, host, command):
        print("%s EXECUTE %s" % (host, command))
        return "123"

    def check_route_config():
        return true

    def check_switch_config():
        return true

    def run(self):
        nodes = cluster.get_nodes()
        for node in nodes:
            for host in node["ovn_slave"]:
                self.execute(host["manage_ip"],
                        "ovs-vsctl add-br br-int -- set Bridge br-int fail-mode=secure")
                self.execute(host["manage_ip"],
                        "ovs-vsctl set open .  external-ids:ovn-remote=tcp:%s:%s" %
                        (node["ovn_master"]["ip"], node["ovn_master"]["port"]))
                self.execute(host["manage_ip"],
                        "ovs-vsctl set open . external-ids:ovn-encap-type=geneve")
                self.execute(host["manage_ip"],
                        "ovs-vsctl set open . external-ids:ovn-encap-ip=%s" %
                        host["ip"])

        logical_routes = cluster.get_routes()
        for route in logical_routes:
            if self.check_route_config():
                self.execute(self.get_master(route["master_id"])["manage_ip"],
                    "ovn-nbctl --may-exist lr-add %s" % route["id"])

                for port in route["ports"]:
                    route_to_switch = route["id"] + "-rs-" + port["id"]
                    switch_to_route = port["id"] + "-sr-" + route["id"]
                    self.execute(self.get_master(route["master_id"])["manage_ip"],
                                 "ovn-nbctl lrp-add %s %s %s %s"
                                 % (route["id"], route_to_switch, port["mac"], port["ip"]))

                    self.execute(self.get_vhost_master(route["id"])["manage_ip"],
                                 "ovn-nbctl lsp-add %s %s" %
                                 (route["id"], route_to_switch))

                    self.execute(self.get_vhost_master(route["id"])["manage_ip"],
                                 "ovn-nbctl lsp-set-addresses %s %s"
                                 % (route_to_switch, port["mac"]))

                    self.execute(self.get_vhost_master(route["name"])["manage_ip"],
                                 "ovn-nbctl lsp-set-option %s router-port=%s"
                                 % (route_to_switch, switch_to_route)

        logical_switches = cluster.get_switches()
        for switch in logical_switches:
            if self.check_switch_config():
                switch_to_route = switch["route_id"] + "-" + switch["id"]
                route_to_switch = switch["id"] + "-" + switch["route_id"]
                #self.execute(self.get_master(switch["master_id"])["manage_ip"],
                #    "ovn-nbctl --may-exist lr-add %s" % switch["route_id"])

                #self.execute(self.get_master(switch["master_id"])["manage_ip"],
                #    "ovn-nbctl lrp-add %s %s %s %s"
                #    % (switch["route_id"], route_to_switch, switch["mac"], switch["ip"]))

                #self.execute(self.get_master(switch["master_id"])["manage_ip"],
                #    "ovn-nbctl --may-exist ls-add %s" % switch["id"])

                #for port in switch["ports"]:
                #    self.execute(self.get_master(switch["master_id"])["manage_ip"],
                #        "ovn-nbctl lsp-add %s %s" % (switch["id"], port["name"]))

                #    self.execute(self.get_master(switch["master_id"])["manage_ip"],
                #        "ovn-nbctl lsp-set-type %s router" % port["name"])

                    #if port["type"] == "route":
                    #    self.execute(self.get_master(switch["master_id"])["manage_ip"],
                    #        "ovn-nbctl lsp-set-addresses %s %s" % (port["name"], port["id"]))
                    #elif port["type"] == "host":
                    #    self.execute(self.get_master(switch["master_id"])["manage_ip"],
                    #        "ovn-nbctl lsp-set-addresses %s %s" % (port["name"], port["id"]))

                    #self.execute(self.get_master(switch["master_id"])["manage_ip"],
                    #    "ovn-nbctl lsp-set-options %s router-port=%s"
                    #    % (port["name"], ))

        hosts = cluster.get_vhosts()
        for host in hosts:
            if host["type"] == "namespace":

                # config logical switch

                for switch in host["switches"]:
                    switch_to_namespace = switch["id"] + "-sh-" + host["id"]
                    self.execute(self.get_vhost_master(host["id"])["manage_ip"],
                                 "ovn-nbctl --may-exist ls-add %s" % switch["id"])

                    self.execute(self.get_vhost_master(host["id"])["manage_ip"],
                                 "ovn-nbctl lsp-add %s %s" %
                                 (switch["id"], switch_to_namespace))

                    self.execute(self.get_vhost_master(host["id"])["manage_ip"],
                                 "ovn-nbctl lsp-set-addresses %s %s"
                                 % (switch_to_namespace, host["mac"]))

                    self.execute(self.get_vhost_master(host["name"])["manage_ip"],
                                 "ovn-nbctl lsp-set-port-security %s %s"
                                 % (switch_to_namespace, host["mac"]))

                    # dhcp
                    if host["dhcp_flag"] == "true":
                        port = self.get_switch_port(host["id"])
                        dhcp_id = self.execute(self.get_vhost_master(host["id"])["manage_ip"],
                                               "ovn-nbctl create --may-exist DHCP_Options cidr=%s options=\"server_id\"=\"%s\" \"server_mac\"=\"%s\" \"lease_time\"=\"%s\" \"router\"=\"%s\""
                                               % (port["dhcp"]["cidr"], port["ip"], port["mac"], port["dhcp"]["lease_time"], port["ip"]))

                        self.execute(self.get_vhost_master(host["id"])["manage_ip"],
                                     "ovn-nbctl lsp-set-dhcpv4-options %s %s"
                                     % (dhcp_id, ))

                # config namespace
                namespace_name = host["id"]
                namespace_iface = host["id"]

                self.execute(self.get_vhost_slave(host["id"])["manage_ip"],
                             "ip netns add %s" % namespace_name)

                self.execute(self.get_vhost_slave(host["id"])["manage_ip"],
                             "ovs-vsctl add-port br-int %s -- set interface %s type=internal"
                             % (namespace_iface, namespace_iface))

                self.execute(self.get_vhost_slave(host["id"])["manage_ip"],
                             "ip link set %s netns %s"
                             % (namespace_iface, namespace_name))

                self.execute(self.get_vhost_slave(host["id"])["manage_ip"],
                             "ip netns exec %s ip link set %s address %s"
                             % (namespace_name, namespace_iface, host["mac"]))

                self.execute(self.get_vhost_slave(host["id"])["manage_ip"],
                             "ip netns exec %s ip addr add %s dev %s"
                             % (namespace_name, host["ip"], namespace_iface))

                self.execute(self.get_vhost_slave(host["id"])["manage_ip"],
                             "ip netns exec %s ip link set %s up"
                             % (namespace_name, namespace_iface))

                self.execute(self.get_vhost_slave(host["id"])["manage_ip"],
                             "ovs-vsctl set Interface %s external_ids:iface-id=%s"
                             % (namespace_name, switch_to_namespace))

                if host["dhcp_flag"] == "true":
                    self.execute(self.get_vhost_slave(host["id"])["manage_ip"],
                                 "ip netns exec %s dhclient %s"
                                 % (namespace_name, namespace_iface))


if __name__ == "__main__":
    cluster = Cluster("cluster.json")
    cluster.run()
