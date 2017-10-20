#!/usr/bin/env python

import argparse
import collections
import sys
import os
import logging
import yaml

try:
    import json
except:
    import simplejson as json

try:
    import paramiko
    __PARAMIKO_NOT_IMPORTED__ = False
    import subprocess
except:
    # Import subprocess for ssh
    import subprocess
    __PARAMIKO_NOT_IMPORTED__ = True

class SmartOSInventory(object):

    def __init__(self):
        # SmartOS SSH Commands
        self._sshcmd_list = 'vmadm lookup -j'
        self._sshcmd_host = 'vmadm lookup -j hostname={hostname}'

        # Start with empty inventory
        self.inventory = {"_meta": {"hostvars": {}}}

        self._parse_args()
        self._parse_settings()

        if self.args.debug:
            logging.basicConfig(level=logging.DEBUG)

        # Check if we to get hostvars on a single host
        if __PARAMIKO_NOT_IMPORTED__:
            logging.debug("Using raw SSH")
            self._get_json_from_ssh()
        else:
            logging.debug("Using paramiko for SSH")
            self._get_json_from_paramiko()

        self._do_inventory()

        print(json.dumps(self.inventory, sort_keys=True, indent=2))

    def _get_json_from_ssh(self):
        ''' Get single host's raw smartos json from ssh subprocess '''
        logging.debug("Using SSH to get single host json")

        ssh_cmd = ["ssh", self._hypervisor_user + "@" + self._hypervisor_host, \
                "-p", str(self._hypervisor_port), self._sshcmd]
        output = subprocess.check_output(ssh_cmd, universal_newlines=True)

        try:
            self._parsed_json = json.loads(output)
        except ValueError as e:
            logging.info("Invalid JSON returned from ssh server")
            sys.exit(1)

    def _get_json_from_paramiko(self):
        ''' Gets raw json from paramiko '''

        logging.debug("Using paramiko to get json data")

        try:
            self._paramiko_connect()
            stdin, stdout, stderr = self._ssh.exec_command(self._sshcmd)

            stdout=stdout.readlines()

        finally:
            logging.debug("Closing paramiko ssh connection")
            self._paramiko_close()

        # Put raw output into a usable string
        output=""
        for line in stdout:
            output=output+line

        # Parse raw json
        try:
            self._parsed_json = json.loads(output)
        except ValueError as e:
            logging.error(e)
            sys.exit(1)

    def _paramiko_connect(self):
        ''' Sets up SSH connection with Paramiko '''

        try:
            logging.debug("Starting paramiko SSH client")
            self._ssh = paramiko.SSHClient()

            logging.debug("Loading Paramiko SSH host keys")
            self._ssh.load_system_host_keys()

            logging.debug("Connecting to SSH with Paramiko")
            self._ssh.connect(self._hypervisor_host, port=self._hypervisor_port, \
                    username=self._hypervisor_user, \
                    key_filename=self._hypervisor_key)

        except Exception as e:
            logging.error(e)

    def _paramiko_close(self):
        ''' Terminates Paramiko SSH connection '''

        self._ssh.close()

    def _do_inventory(self):
        ''' Takes the fetched json and populates the inventory '''

        groups = collections.defaultdict(list)
        firstpass = collections.defaultdict(list)

        # Hostvars for all servers
        hostvars = {}

        # Parse server's json blob and extract hostname
        for server in self._parsed_json:
            try:
                firstpass[server['hostname']].append(server)
                logging.debug("Finished first pass of {}".format(server['hostname']))

            except KeyError as e:
                logging.debug("No hostname found. Using alias {}".format(server['alias']))
                firstpass[server['alias']].append(server)

        for name, vars in firstpass.items():
            # TODO: Set ansible_ssh_host based of valid subnets on host running Ansible
            ansible_host = vars[0]['nics'][0]['ip']

            hostvars[name] = dict(ansible_host=ansible_host, \
                    ansible_ssh_host=ansible_host,smartos=vars[0])

            # Hypervisor Grouping
            try:
                self.inventory['smartos'].append(name)
            except KeyError:
                self.inventory['smartos'] = [name]

            # Brand grouping
            try:
                brand = vars[0]['brand']

                try:
                    self.inventory[brand].append(name)
                except KeyError:
                    self.inventory[brand] = [name]

            except Exception as e:
                logging.error("No brand found in {}".format(name))

            # Vlan grouping
            try:
                vlan = str(vars[0]['nics'][0]['vlan_id'])
                try:
                    self.inventory['vlan_' + vlan].append(name)
                except KeyError:
                    self.inventory['vlan_' + vlan] = [name]
            except KeyError:
                pass

        self.inventory['_meta']['hostvars'] = hostvars

    def _parse_settings(self):
        SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
        CONFIG_LOCATIONS = ['/etc/ansible/smartos.yml', '/etc/ansible/smartos.yaml', SCRIPT_DIR + '/smartos.yml', SCRIPT_DIR + '/smartos.yaml']

        self._hypervisor_host = '10.0.3.2'
        self._hypervisor_port = 22
        self._hypervisor_key = '/home/piranha/.ssh/id_rsa'
        self._hypervisor_user = 'root'

        # Set SSH command based on config
        if self.args.host:
            self._sshcmd = self._sshcmd_host.format(hostname=self.args.host)
        else:
            self._sshcmd = self._sshcmd_list

    def _parse_args(self):
        ''' Parse command line arguments '''

        parser = argparse.ArgumentParser(description='SmartOS Inventory Module')
        parser.add_argument('--debug', action='store_true', default=False,
                            help='Enable debug output')
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--list', action='store_true',
                           help='List active servers')
        group.add_argument('--host', help='List details about the specific host')

        self.args = parser.parse_args()

if __name__ == '__main__':
    SmartOSInventory()
