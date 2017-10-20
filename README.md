# SmartOS Ansible Dynamic Inventory

Ansible provides many different types of dynamic inventory scripts to pull data about your clouds,
including AWS, OpenStack, DigitalOcean, etc.

This fills in the gap for the SmartOS hypervisor.

More about Ansible dynamic inventory here: http://docs.ansible.com/ansible/latest/intro_dynamic_inventory.html


Things that still need to be tweaked:
- Implement a configuration file. Currently the SmartOS host needs to be hardcoded in the script.
- Only SSH keys are currently working. Would be nice to have passwords work as well.
- Check all NICs on an instance to see which one is accessible via the Ansible host.
 Currently, the very first NIC IP is used.
- Group human redable image names. Need to pull `imgadm` data as well to parse.
