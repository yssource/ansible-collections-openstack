#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
module: compute_flavor
short_description: Manage OpenStack compute flavors
author: OpenStack Ansible SIG
description:
   - Add or remove flavors from OpenStack.
options:
  state:
    description:
       - Indicate desired state of the resource. When I(state) is 'present',
         then I(ram), I(vcpus), and I(disk) are all required. There are no
         default values for those parameters.
    choices: ['present', 'absent']
    default: present
    type: str
  name:
    description:
       - Flavor name.
    required: true
    type: str
  ram:
    description:
       - Amount of memory, in MB.
    type: int
  vcpus:
    description:
       - Number of virtual CPUs.
    type: int
  disk:
    description:
       - Size of local disk, in GB.
    default: 0
    type: int
  ephemeral:
    description:
       - Ephemeral space size, in GB.
    default: 0
    type: int
  swap:
    description:
       - Swap space size, in MB.
    default: 0
    type: int
  rxtx_factor:
    description:
       - RX/TX factor.
    default: 1.0
    type: float
  is_public:
    description:
       - Make flavor accessible to the public.
    type: bool
    default: 'yes'
  id:
    description:
       - ID for the flavor. This is optional as a unique UUID will be
         assigned if a value is not specified.
       - Note that this ID will only be used when first creating the flavor.
    default: "auto"
    type: str
    aliases: ['flavorid']
  extra_specs:
    description:
       - Metadata dictionary
    type: dict
requirements:
   - "python >= 3.6"
   - "openstacksdk"

extends_documentation_fragment:
- openstack.cloud.openstack
'''

EXAMPLES = '''
- name: Create tiny flavor with 1024MB RAM, 1 vCPU, 10GB disk, 10GB ephemeral
  openstack.cloud.compute_flavor:
    cloud: mycloud
    state: present
    name: tiny
    ram: 1024
    vcpus: 1
    disk: 10
    ephemeral: 10

- name: Delete tiny flavor
  openstack.cloud.compute_flavor:
    cloud: mycloud
    state: absent
    name: tiny

- name: Create flavor with metadata
  openstack.cloud.compute_flavor:
    cloud: mycloud
    state: present
    name: tiny
    ram: 1024
    vcpus: 1
    disk: 10
    extra_specs:
      "quota:disk_read_iops_sec": 5000
      "aggregate_instance_extra_specs:pinned": false
'''

RETURN = '''
flavor:
  description: Dictionary describing the flavor.
  returned: On success when I(state) is 'present'
  type: dict
  contains:
    description:
      description: Description attached to flavor
      returned: success
      type: str
      sample: Example description
    disk:
      description: Size of local disk, in GB.
      returned: success
      type: int
      sample: 10
    ephemeral:
      description: Ephemeral space size, in GB.
      returned: success
      type: int
      sample: 10
    extra_specs:
      description: Flavor metadata
      returned: success
      type: dict
      sample:
        "quota:disk_read_iops_sec": 5000
        "aggregate_instance_extra_specs:pinned": false
    id:
      description: Flavor ID.
      returned: success
      type: str
      sample: "515256b8-7027-4d73-aa54-4e30a4a4a339"
    is_disabled:
      description: Whether the flavor is disabled
      returned: success
      type: bool
      sample: true
    is_public:
      description: Make flavor accessible to the public.
      returned: success
      type: bool
      sample: true
    name:
      description: Flavor name.
      returned: success
      type: str
      sample: "tiny"
    original_name:
      description: The name of this flavor when returned by server list/show
      type: str
      returned: success
    ram:
      description: Amount of memory, in MB.
      returned: success
      type: int
      sample: 1024
    rxtx_factor:
      description: |
        The bandwidth scaling factor this flavor receives on the network
      returned: success
      type: int
      sample: 100
    swap:
      description: Swap space size, in MB.
      returned: success
      type: int
      sample: 100
    vcpus:
      description: Number of virtual CPUs.
      returned: success
      type: int
      sample: 2
'''

from ansible_collections.openstack.cloud.plugins.module_utils.openstack import OpenStackModule


class ComputeFlavorModule(OpenStackModule):
    argument_spec = dict(
        state=dict(default='present',
                   choices=['absent', 'present']),
        name=dict(required=True),

        # required when state is 'present'
        ram=dict(type='int'),
        vcpus=dict(type='int'),

        disk=dict(default=0, type='int'),
        ephemeral=dict(default=0, type='int'),
        swap=dict(default=0, type='int'),
        rxtx_factor=dict(default=1.0, type='float'),
        is_public=dict(default=True, type='bool'),
        id=dict(default='auto', aliases=['flavorid']),
        extra_specs=dict(type='dict'),
    )

    module_kwargs = dict(
        required_if=[
            ('state', 'present', ['ram', 'vcpus', 'disk'])
        ],
        supports_check_mode=True
    )

    def _system_state_change(self, flavor, extra_specs, old_extra_specs):
        state = self.params['state']
        if state == 'present':
            if not flavor:
                return True
            return self._needs_update(flavor) or extra_specs != old_extra_specs
        if state == 'absent' and flavor:
            return True
        return False

    def _needs_update(self, flavor):
        fields = ['ram', 'vcpus', 'disk', 'ephemeral', 'swap', 'rxtx_factor',
                  'is_public']
        for k in fields:
            if self.params[k] is not None and self.params[k] != flavor[k]:
                return True

    def _build_flavor_specs_diff(self, extra_specs, old_extra_specs):
        new_extra_specs = dict([(k, str(v)) for k, v in extra_specs.items()])
        unset_keys = set(old_extra_specs.keys()) - set(extra_specs.keys())
        return new_extra_specs, unset_keys

    def run(self):
        state = self.params['state']
        name = self.params['name']
        extra_specs = self.params['extra_specs'] or {}

        flavor = self.conn.compute.find_flavor(name, get_extra_specs=True)
        old_extra_specs = {}
        if flavor:
            old_extra_specs = flavor['extra_specs']
            if flavor['swap'] == '':
                flavor['swap'] = 0

        if self.ansible.check_mode:
            self.exit_json(changed=self._system_state_change(
                flavor, extra_specs, old_extra_specs))

        if state == 'present':
            flavorid = self.params['id']
            if flavor and self._needs_update(flavor):
                # Because only flavor descriptions are updateable, we have to
                # delete and recreate a flavor to "update" it
                self.conn.compute.delete_flavor(flavor)
                old_extra_specs = {}
                if flavorid == 'auto':
                    flavorid = flavor['id']
                flavor = None

            changed = False
            if not flavor:
                flavor = self.conn.create_flavor(
                    name=name,
                    ram=self.params['ram'],
                    vcpus=self.params['vcpus'],
                    disk=self.params['disk'],
                    flavorid=flavorid,
                    ephemeral=self.params['ephemeral'],
                    swap=self.params['swap'],
                    rxtx_factor=self.params['rxtx_factor'],
                    is_public=self.params['is_public']
                )
                changed = True

            new_extra_specs, unset_keys = self._build_flavor_specs_diff(
                extra_specs, old_extra_specs)

            if unset_keys:
                self.conn.unset_flavor_specs(flavor['id'], unset_keys)

            if old_extra_specs != new_extra_specs:
                self.conn.compute.create_flavor_extra_specs(
                    flavor['id'], extra_specs)
                changed = True

            # Have to refetch updated extra_specs
            flavor = self.conn.compute.fetch_flavor_extra_specs(flavor)

            self.exit_json(
                changed=changed, flavor=flavor.to_dict(computed=False))

        elif state == 'absent':
            if flavor:
                self.conn.compute.delete_flavor(flavor)
                self.exit_json(changed=True)
            self.exit_json(changed=False)


def main():
    module = ComputeFlavorModule()
    module()


if __name__ == '__main__':
    main()
