#!/usr/bin/env python

import argparse
import collections
import sys
import os
import logging

try:
    import json
except:
    import simplejson as json

try:
    import paramiko
    __PARAMIKO_NOT_IMPORTED__ = False
except:
    # Import subprocess for ssh
    import subprocess
    __PARAMIKO_NOT_IMPORTED__ = True

__DEFAULT_SSH_EXEC__ = 'ssh'
__DEFAULT_SSH_USER__ = 'root'
__DEFAULT_SSH_KEY__ = '~/.ssh/id_rsa'

def get_vmadm_list_from_ssh():
    """
        Returns list of all VMs in valid JSON from SSH host
    """
    smartos_vmadm_cmd = 'vmadm lookup -j'

    if __PARAMIKO_NOT_IMPORTED__:
        # Use ssh command
        ssh_cmd = get_ssh_cmd_from_paths()
        ret_raw_json = subprocess.check_output([__DEFAULT_SSH_EXEC__, "root@10.0.3.2", "vmadm lookup -j"], universal_newlines=True)
    else:
        # Use paramiko module
        pass

    # Check that we have valid json
    try:
        ret_json = json.loads(ret_raw_json)
    except ValueError as e:
        logging.info("Invalid JSON returned from ssh server")
        sys.exit(1)

    return ret_json

def get_vmadm_host_from_ssh(hostname):
    """
        Returns valid json with of VM
    """
    smartos_vmadm_cmd = 'vmadm lookup -j { hostname }'

def get_ssh_cmd_from_paths(check_cwd=True):
    """
        Finds ssh executable from cwd and system PATHS

        Returns full path of first found ssh executable
    """

    exec_file = __DEFAULT_SSH_EXEC__

    if check_cwd:
        ssh_paths = [os.getcwd()]  # Check current directory FIRST
    else:
        ssh_paths = []

    ssh_paths.extend(os.environ["PATH"].split(':'))

    logging.debug("Found paths {}".format(str(ssh_paths)))

    for path in ssh_paths:
        if is_exec_in_path(exec_file, path):
            # Found exec
            full_path = os.path.join(path, exec_file)
            break

    return full_path

def is_exec_in_path(exec_file, path=None):

    found = False

    if path is None:
        full_path = exec_file
    else:
        full_path = os.path.join(path, exec_file)

    if os.path.isfile(full_path):
        # Verify file is executable
        if os.access(full_path, os.X_OK):
            found = True

    logging.debug("Found exec: {} at {}".format(exec_file, full_path))

    return found


def parse_args():
    parser = argparse.ArgumentParser(description='SmartOS Inventory Module')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debug output')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list', action='store_true',
                       help='List active servers')
    group.add_argument('--host', help='List details about the specific host')

    return parser.parse_args()

def to_json(in_dict):
    return json.dumps(in_dict, sort_keys=True, indent=2)

def main():
    args = parse_args()

    output = get_ansible_json_from_ssh()

    print(output)
    sys.exit(0)

def get_ansible_json_from_ssh():
    vm_json = get_vmadm_list_from_ssh()

    groups = collections.defaultdict(list)
    firstpass = collections.defaultdict(list)
    hostvars = {}


    for server in vm_json:
        try:
            firstpass[server['hostname']].append(server)
        except KeyError as e:
            # No hostname var, use alias
            firstpass[server['alias']].append(server)

    for name, server in firstpass.items():
       hostvars[name] = dict(ansible_ssh_host=server[0]['nics'][0]['ip'],smartos=server)

    groups['_meta'] = {'hostvars': hostvars}

    return groups

if __name__ == '__main__':
    main()
