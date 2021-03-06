#!/usr/bin/python

# Copyright (C) 2020 Lenovo.  All rights reserved.

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
from uuid import uuid4

import tacp
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.tacp_ansible import tacp_exceptions, tacp_utils
from ansible.module_utils.tacp_ansible.tacp_constants import (
    ApiState, PlaybookState
)


ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tacp_instance

short_description: Creates and modifies power state of application instances on
  ThinkAgile CP.

description:
  - "This module can be used to create new application instances on the
    ThinkAgile CP cloud platform, as well as delete and modify power states
    of existing application instances."
  - "Currently this module cannot modify the resources of existing
    application instances aside from performing deletion and power state
    operations."
author:
  - Lenovo (@lenovo)
  - Xander Madsen (@xmadsen)

requirements:
  - tacp

options:
  api_key:
    description:
      - An API key generated in the Developer Options in the ThinkAgile
        CP portal. This is required to perform any operations with this
        module.
    required: true
    type: str
  name:
    description:
      - This is the name of the instance to be created or modified
    required: true
    type: str
  state:
    description:
      - The desired state for the application instance in question. All
        options except 'absent' will perform a power operation if
        necessary, while 'absent' deletes the application instance with
        the provided name if it exists.
    choices:
      - started
      - shutdown
      - stopped
      - restarted
      - force_restarted
      - paused
      - absent
  datacenter:
    description:
      - The name of the virtual datacenter that the instance will be
        created in. Only required when creating a new instance.
    required: false
    type: str
  migration_zone:
    description:
      - The name of the migration zone that the instance will be created
        in. Only required when creating a new instance.
    required: false
    type: str
  template:
    description:
      - The name of the template used as a basis for the creation of the
        instance. Only required when creating a new instance.
    required: false
    type: str
  storage_pool:
    description:
      - The name of the storage pool that the instance's disks will be
        stored in. Only required when creating a new instance.
    required: false
    type: str
  num_cpus:
    description:
      - The number of virtual CPU cores that the application instance
        will have when it is created. Only required when creating a new
        instance.
    required: false
    type: int
  memory_mb:
    description:
      - The amount of virtual memory (RAM) that the application instance
        will have when it is created. Only required when creating a new
        instance.
    required: false
    type: str
  disks:
    description:
      - An array of disks that will be associated with the application
        instance when it is created.
      - Must contain any disks that the template contains, and the names
        must match for any of those such disks. Only required when
        creating a new instance.
    required: false
    type: list
    suboptions:
      name:
        description:
          - The name of the disk. If the specified disk is not part
            of the template, it can be named anything (except the
            name of a disk in the template).
        required: true
        type: str
      bandwidth_limit:
        description:
          - A limit to the bandwidth usage allowed for this disk.
            Must be at least 5000000 (5 Mbps).
        required: false
        type: int
      iops_limit:
        description:
          - A limit to the total IOPS allowed for this disk.
            Must be at least 50.
        required: false
        type: int
      size_gb:
        description:
          - The size of the disk in GB. Can be expressed as a float.
        required: true
        type: float
      boot_order:
        description:
          - The place in the boot order for the disk. The overall
            boot order must begin at 1, and every NIC and disk must
            have an order provided.
        required: true
        type: int
  nics:
    description:
      - An array of NICs that will be associated with the application
        instance when it is created.
      - Must contain any NICs that the template contains, and the names
        must match for any of those such NICs. Only required when
        creating a new instance.
    required: false
    type: list
    suboptions:
      name:
        description:
          - The name of the NIC. If the specified NIC is not part
            of the template, it can be named anything (except the
            name of a NIC in the template).
        required: true
        type: str
      type:
        description:
          - The type of network that the NIC will be a part of.
          - Valid chocies are either "VNET" or "VLAN".
        required: true
        type: str
      network:
        description:
          - The name of the network that the NIC will be a part of.
          - There must be an existing network of the provided type
            that has the provided network name to succeed.
        required: true
        type: str
      boot_order:
        description:
          - The place in the boot order for the NIC. The overall boot
            order must begin at 1, and every NIC and disk must have
            an order provided.
        required: true
        type: int
      automatic_mac_address:
        description:
          - Whether this interface should be automatically assigned
            a MAC address.
          - Providing a MAC address to the mac field sets
            this value to false.
        required: false
        type: bool
      mac:
        description:
          - A static MAC address to be assigned to the NIC. Should
            not exist on any other interfaces on the network.
          - Should be of the format aa:bb:cc:dd:ee:ff
          - If this is set, 'automatic_mac_address' is automatically
            set to false.
        required: false
        type: str
      firewall_override:
        description:
          - The name of a firewall override that exists in the
            datacenter that the NIC's instance will reside in.
        required: false
        type: str
  vtx_enabled:
    description:
      - Whether or not VT-x nested virtualization features should be
        enabled for the instance. Enabled by default.
    required: false
    type: bool
  auto_recovery_enabled:
    description:
      - Whether or not the instance should be restarted on a different
        host node in the event that its host node fails. Defaults to
        true.
    required: false
    type: bool
  description:
    description:
      - A textual description of the instance. Defaults to any
        description that the source template come with.
    required: false
    type: str
  vm_mode:
    description:
      - Sets the instance mode. Set to "Enhanced" by default.
      - Valid choices are "Enhanced" and "Compatibility"
      - Any instance can boot in Compatibility mode.
      - In Enhanced mode, Virtio drivers must be present in the template
        in order to boot.
      - Additionally, in Enhanced mode
        - Storage disks are exported as virtio iSCSI devices
        - vNICs are exported as virtio vNICs
        - Snapshots will be application consistent (when ThinkAgile CP
        Guest Agent is installed) if the guest OS supports freeze and
        thaw
        - CPU and Memory Statistics are available (When ThinkAgile CP
        Guest Agent is installed)
    required: false
    type: str
  application_group:
    description:
      - The name of an application group that the instance will be put
        in. Creates it in the virtual datacenter if it does not yet exist
        .
    required: false
    type: str

'''

EXAMPLES = '''
- name: Create a basic VM on ThinkAgile CP
  tacp_instance:
      api_key: "{{ api_key }}"
      name: Basic_VM1
      state: started
      datacenter: Datacenter1
      migration_zone: Zone1
      template: CentOS 7.5 (64-bit) - Lenovo Template
      storage_pool: Pool1
      num_cpus: 1
      memory_mb: 4096
      disks:
      - name: Disk 0
          size_gb: 50
          boot_order: 1
      nics:
      - name: vNIC 0
          type: VNET
          network: VNET-TEST
          boot_order: 2

- name: Create a shutdown VM with multiple disks and set its NIC to the first
        boot device
  tacp_instance:
      api_key: "{{ api_key }}"
      name: Basic_VM2
      state: started
      datacenter: Datacenter1
      migration_zone: Zone1
      template: RHEL 7.4 (Minimal) - Lenovo Template
      storage_pool: Pool1
      num_cpus: 1
      memory_mb: 8192
      disks:
      - name: Disk 0
          size_gb: 50
          boot_order: 2
      - name: Disk 1
          size_gb: 200
          boot_order: 3
      nics:
      - name: vNIC 0
          type: VLAN
          network: VLAN-300
          boot_order: 1

- name: Create a VM with multiple disks with limits, and two NICs with static
        MAC addresses, and don't power it on after creation
  tacp_instance:
      api_key: "{{ api_key }}"
      name: Basic_VM3
      state: shutdown
      datacenter: Datacenter1
      migration_zone: Zone1
      template: RHEL 7.4 (Minimal) - Lenovo Template
      storage_pool: Pool1
      num_cpus: 1
      memory_mb: 8192
      disks:
      - name: Disk 0
          size_gb: 50
          boot_order: 2
      - name: Disk 1
          size_gb: 200
          boot_order: 3
      nics:
      - name: vNIC 0
          type: VLAN
          network: VLAN-300
          boot_order: 4
          firewall_override: Allow-All
      - name: vNIC 1
          type: VNET
          network: PXE-VNET
          boot_order: 1
          mac: b4:d1:35:00:00:01

- name: Create a VM from a custom template without virtio drivers
  tacp_instance:
      api_key: "{{ api_key }}"
      name: Custom_VM
      state: started
      datacenter: Datacenter1
      migration_zone: Zone1
      template: MyCustomTemplate
      storage_pool: Pool1
      num_cpus: 1
      memory_mb: 4096
      vm_mode: Compatibility
      disks:
      - name: Disk 0
          size_gb: 50
          boot_order: 1
      nics:
      - name: vNIC 0
          type: VNET
          network: VNET-TEST
          boot_order: 2

- name: Pause Basic_VM1 on ThinkAgile CP
  tacp_instance:
      api_key: "{{ api_key }}"
      name: Basic_VM1
      state: paused

- name: Restart all of my Basic_VMs on ThinkAgile CP
  tacp_instance:
      api_key: "{{ api_key }}"
      name: "{{ instance }}"
      state: restarted
  loop:
    - Basic_VM1
    - Basic_VM2
    - Basic_VM3
  loop_control:
    loop_var: instance

- name: Delete Basic_VM1 from ThinkAgile CP
  tacp_instance:
      api_key: "{{ api_key }}"
      name: Basic_VM1
      state: absent

- name: Create a variety of VMs on TACP in a loop
  tacp_instance:
      api_key: "{{ api_key }}"
      name: "{{ instance.name }}"
      state: "{{ instance.state }}"
      datacenter: Datacenter2
      migration_zone: Zone2
      template: "{{ instance.template }}"
      storage_pool: Pool2
      num_cpus: "{{ instance.num_cpus }}"
      memory_mb: "{{ instance.memory_mb }}"
      disks:
        - name: Disk 0
          size_gb: 100
          boot_order: 1
      nics:
        - name: vNIC 0
          type: "{{ instance.network_type }}"
          network: "{{ instance.network_name }}"
          mac: "{{ instance.mac }}"
          boot_order: 2
  loop:
      - { name: CentOS VM 1,
          state: started,
          template: "CentOS 7.5 (64-bit) - Lenovo Template",
          num_cpus: 2,
          memory_mb: 4096,
          network_type: VLAN,
          network_name: VLAN-15,
          mac: b4:d1:35:00:0f:f0 }
      - { name: RHEL VM 11,
          state: stopped,
          template: "RHEL 7.4 (Minimal) - Lenovo Template",
          num_cpus: 6,
          memory_mb: 6144,
          network_type: VNET,
          network_name: Production-VNET,
          mac: b4:d1:35:00:0f:f1 }
      - { name: Windows Server 2019 VM 1,
          state: started,
          template: "Windows Server 2019 Standard - Lenovo Template",
          num_cpus: 8,
          memory_mb: 16384,
          network_type: VNET,
          network_name: Internal-VNET,
          mac: b4:d1:35:00:0f:f2 }
  loop_control:
      loop_var: instance
'''

RETURN = '''
instance:
  description: The final state of the application instance if it still exists.
  type: dict
  returned: success

msg:
  description: An error message in the event of invalid input or other
    unexpected behavior during module execution.
  type: str
  returned: failure

'''


'''
This dict keys are a tuple of the format (current_state, target_state)
where the current state has been retrieved from an API response
and the target_state is provided by the playbook input. The values
are a list of PlaybookStates that when set in order will get an
instance from the current state to the target state.
'''
ACTIONS_TO_CHANGE_FROM_API_STATE_TO_PLAYBOOK_STATE = {
    (ApiState.RUNNING, PlaybookState.STARTED): [],
    (ApiState.RUNNING, PlaybookState.SHUTDOWN): [PlaybookState.SHUTDOWN],
    (ApiState.RUNNING, PlaybookState.STOPPED): [PlaybookState.STOPPED],
    (ApiState.RUNNING, PlaybookState.RESTARTED): [PlaybookState.RESTARTED],
    (ApiState.RUNNING, PlaybookState.FORCE_RESTARTED): [
        PlaybookState.FORCE_RESTARTED],
    (ApiState.RUNNING, PlaybookState.PAUSED): [PlaybookState.PAUSED],
    (ApiState.RUNNING, PlaybookState.ABSENT): [PlaybookState.ABSENT],
    (ApiState.SHUTDOWN, PlaybookState.STARTED): [PlaybookState.STARTED],
    (ApiState.SHUTDOWN, PlaybookState.SHUTDOWN): [],
    (ApiState.SHUTDOWN, PlaybookState.STOPPED): [],
    (ApiState.SHUTDOWN, PlaybookState.RESTARTED): [PlaybookState.STARTED],
    (ApiState.SHUTDOWN, PlaybookState.FORCE_RESTARTED): [
        PlaybookState.STARTED],
    (ApiState.SHUTDOWN, PlaybookState.PAUSED): [
        PlaybookState.STARTED, PlaybookState.PAUSED],
    (ApiState.SHUTDOWN, PlaybookState.ABSENT): [PlaybookState.ABSENT],
    (ApiState.PAUSED, PlaybookState.STARTED): [PlaybookState.RESUMED],
    (ApiState.PAUSED, PlaybookState.SHUTDOWN): [
        PlaybookState.RESUMED, PlaybookState.SHUTDOWN],
    (ApiState.PAUSED, PlaybookState.STOPPED): [PlaybookState.STOPPED],
    (ApiState.PAUSED, PlaybookState.RESTARTED): [
        PlaybookState.RESUMED, PlaybookState.RESTARTED],
    (ApiState.PAUSED, PlaybookState.FORCE_RESTARTED):
        [PlaybookState.RESUMED, PlaybookState.FORCE_RESTARTED],
    (ApiState.PAUSED, PlaybookState.PAUSED): [],
    (ApiState.PAUSED, PlaybookState.ABSENT): [PlaybookState.ABSENT]
}

MODULE_ARGS = {
    'api_key': {'type': 'str', 'required': True},
    'portal_url': {'type': 'str', 'required': False,
                   'default': 'https://manage.cp.lenovo.com'},
    'name': {'type': 'str', 'required': True},
    'state': {'type': 'str', 'required': True,
              'choices': PlaybookState._all()},
    'datacenter': {'type': 'str', 'required': False},
    'migration_zone': {'type': 'str', 'required': False},
    'storage_pool': {'type': 'str', 'required': False},
    'template': {'type': 'str', 'required': False},
    'num_cpus': {'type': 'int', 'required': False},
    'memory_mb': {'type': 'int', 'required': False},
    'disks': {'type': 'list', 'required': False},
    'nics': {'type': 'list', 'required': False},
    'vtx_enabled': {'type': 'bool', 'default': True, 'required': False},
    'auto_recovery_enabled': {'type': 'bool', 'default': True,
                              'required': False},
    'description': {'type': 'str', 'required': False},
    'vm_mode': {'type': 'str', 'default': 'Enhanced',
                'choices': ['enhanced', 'Enhanced',
                            'compatibility', 'Compatibility']},
    'application_group': {
        'type': 'str',
        'required': False,
    }
}

MINIMUM_BW_FIVE_MBPS_IN_BYTES = 5000000
MINIMUM_IOPS = 50

RESULT = {
    'changed': False,
    'args': []
}

MODULE = AnsibleModule(
    argument_spec=MODULE_ARGS,
    supports_check_mode=True
)

# Define configuration
CONFIGURATION = tacp_utils.get_configuration(MODULE.params['api_key'],
                                             MODULE.params['portal_url'])
API_CLIENT = tacp.ApiClient(CONFIGURATION)

RESOURCES = {
    'app': tacp_utils.ApplicationResource(API_CLIENT),
    'application_group': tacp_utils.ApplicationGroupResource(API_CLIENT),
    'datacenter': tacp_utils.DatacenterResource(API_CLIENT),
    'migration_zone': tacp_utils.MigrationZoneResource(API_CLIENT),
    'storage_pool': tacp_utils.StoragePoolResource(API_CLIENT),
    'template': tacp_utils.TemplateResource(API_CLIENT),
    'update_app': tacp_utils.ApplicationUpdateResource(API_CLIENT),
    'vlan': tacp_utils.VlanResource(API_CLIENT),
    'vnet': tacp_utils.VnetResource(API_CLIENT)
}


def fail_with_reason(reason):
    RESULT['msg'] = reason
    MODULE.fail_json(**RESULT)


def fail_and_rollback_instance_creation(reason, instance):
    RESULT['msg'] = reason + "\n Rolled back application instance creation."
    RESOURCES['app'].delete(instance.uuid)
    MODULE.fail_json(**RESULT)


def fail_and_rollback_vnic_addition(reason, instance, vnic_uuids):
    RESULT['msg'] = reason + "\n Rolled back NIC additions."
    for vnic_uuid in vnic_uuids:
        RESOURCES['update_app'].delete_vnic(instance.uuid, vnic_uuid)
    MODULE.fail_json(**RESULT)


def fail_and_rollback_disk_addition(reason, instance, disk_uuids):
    RESULT['msg'] = reason + "\n Rolled back disk additions."
    for disk_uuid in disk_uuids:
        RESOURCES['update_app'].delete_disk(instance.uuid, disk_uuid)
    MODULE.fail_json(**RESULT)


def get_parameters_to_create_new_application(playbook_instance):
    """Given the input configuration for an instance, generate
        parameters for creating the appropriate payload elsewhere.

    Args:
        playbook_instance (dict): The specified instance configuration from
        the playbook input

    Returns:
        dict: The parameters to be provided to an ApiCreateApplicationPayload
            object.
    """
    data = {'instance_name': None,
            'datacenter_uuid': None,
            'migration_zone_uuid': None,
            'storage_pool_uuid': None,
            'template': None,
            'boot_order': None,
            'application_group_uuid': None,
            'networks': None,
            'vcpus': None,
            'memory_mb': None,
            'vm_mode': None,
            'vtx_enabled': None,
            'auto_recovery_enabled': None,
            'description': None
            }

    data['instance_name'] = playbook_instance['name']

    for item in ('datacenter', 'migration_zone', 'storage_pool', 'template'):
        resource = RESOURCES[item].get_by_name(
            playbook_instance[item])

        if not resource:
            fail_with_reason(
                "Could not create instance. {} with name {} not found.".format(  # noqa
                    item.capitalize(), playbook_instance[item]
                ))

        resource_uuid = resource.uuid

        data['{}_uuid'.format(item)] = resource_uuid

        if item != 'template':
            continue

        template = RESOURCES[item].get_by_uuid(resource_uuid)
        template_boot_order = template.boot_order
        data['boot_order'] = template_boot_order

    if playbook_instance['application_group']:
        uuid = RESOURCES['application_group'].get_uuid_by_name(
            playbook_instance['application_group']
        )
        if uuid is None:
            resp = RESOURCES['application_group'].create(
                playbook_instance['application_group'],
                data['datacenter_uuid']
            )
            uuid = resp.object_uuid

        data['application_group_uuid'] = uuid

    network_payloads = []
    template_vnics = [boot_device for boot_device in template_boot_order
                      if boot_device.vnic_uuid]

    playbook_vnics_in_template = {
        playbook_vnic['name']: template_vnic
        for playbook_vnic in playbook_instance['nics']
        for template_vnic in template_vnics
        if template_vnic.name == playbook_vnic['name']
    }
    corresponding_playbook_vnics = [
        vnic for vnic in playbook_instance['nics']
        if vnic['name'] in playbook_vnics_in_template
    ]

    for playbook_vnic in corresponding_playbook_vnics:
        template_vnic = playbook_vnics_in_template[playbook_vnic['name']]
        vnic_uuid = template_vnic.vnic_uuid
        template_order = template_vnic.order

        parameters_to_create_new_vnic = get_parameters_to_create_vnic(
            datacenter_uuid=data['datacenter_uuid'],
            playbook_vnic=playbook_vnic,
            template_order=template_order
        )

        add_vnic_payload = get_add_vnic_payload(parameters_to_create_new_vnic)
        add_network_payload = get_add_network_payload(
            add_vnic_payload, vnic_uuid)
        network_payloads.append(add_network_payload)

    data['networks'] = network_payloads
    data['vcpus'] = playbook_instance['num_cpus']
    data['memory'] = tacp_utils.convert_memory_abbreviation_to_bytes(
        str(playbook_instance['memory_mb']) + "MB")
    data['vm_mode'] = playbook_instance.get('vm_mode').capitalize()
    data['vtx_enabled'] = playbook_instance.get('vtx_enabled')
    data['auto_recovery_enabled'] = playbook_instance.get(
        'auto_recovery_enabled')
    data['description'] = playbook_instance.get('description')

    return data


def get_instance_payload(parameters_to_create_new_application):
    """Create a ApiCreateApplicationPayload with the input parameters.

    Args:
        parameters_to_create_new_application (dict): All the parameters
            necessary to populate an ApiCreateApplicationPayload.

    Returns:
        ApiCreateApplicationPayload: A populated payload for creating
            a new application instance.
    """
    data = tacp.ApiCreateApplicationPayload(
        name=parameters_to_create_new_application.get('instance_name'),
        datacenter_uuid=parameters_to_create_new_application.get(
            'datacenter_uuid'),
        flash_pool_uuid=parameters_to_create_new_application.get(
            'storage_pool_uuid'),
        migration_zone_uuid=parameters_to_create_new_application.get(
            'migration_zone_uuid'),
        template_uuid=parameters_to_create_new_application.get(
            'template_uuid'),
        vcpus=parameters_to_create_new_application.get('vcpus'),
        memory=parameters_to_create_new_application.get('memory'),
        vm_mode=parameters_to_create_new_application.get('vm_mode'),
        networks=parameters_to_create_new_application.get('networks'),
        boot_order=parameters_to_create_new_application.get('boot_order'),
        hardware_assisted_virtualization_enabled=parameters_to_create_new_application.get('vtx_enabled'),  # noqa
        enable_automatic_recovery=parameters_to_create_new_application.get(
            'auto_recovery_enabled'),
        description=parameters_to_create_new_application.get('description'),
        application_group_uuid=parameters_to_create_new_application.get(
            'application_group_uuid')
    )

    return data


def create_instance(playbook_instance):
    """Create an application instance and return the API response object.

    Args:
        playbook_instance (dict): The specified instance configuration from
        the playbook input

    Returns:
        ApiResponsePayload: The response from the create application request.
    """
    parameters_to_create_new_application = get_parameters_to_create_new_application(  # noqa
        playbook_instance)
    create_instance_payload = get_instance_payload(
        parameters_to_create_new_application)

    created_instance_response = RESOURCES['app'].create(
        create_instance_payload)

    return created_instance_response


def instance_power_action(instance, action):
    RESOURCES['app'].power_action_on_instance_by_uuid(
        instance.uuid, action
    )
    RESULT['changed'] = True


def update_instance_state(instance, target_state):
    if instance.status in [ApiState.RUNNING,
                           ApiState.SHUTDOWN,
                           ApiState.PAUSED]:
        actions = ACTIONS_TO_CHANGE_FROM_API_STATE_TO_PLAYBOOK_STATE[
            (instance.status, target_state)]
        if actions:
            for action in actions:
                instance_power_action(instance, action)
            RESULT['changed'] = True


def add_playbook_vnics(playbook_vnics, instance):
    """Given a list of vnics as dicts, add them to the given instance if they
        are not already part of the instance template, since they would
        necessarily already be part of the instance at creation time.

    Args:
        playbook_vnics (list): The vNICs from the playbook to be added.
        instance (ApiApplicationInstancePropertiesPayload): A payload
            containing the properties of the instance
    """
    playbook_template = RESOURCES['template'].get_by_uuid(
        instance.template_uuid)
    template_boot_order = playbook_template.boot_order

    template_vnics = [
        device.name for device in template_boot_order if device.vnic_uuid]

    for playbook_vnic in playbook_vnics:
        if playbook_vnic['name'] not in template_vnics:
            add_vnic_to_instance(playbook_vnic, instance)


def add_playbook_vnics_to_preexisting_instance(playbook_vnics, instance):
    """Given a list of vnics as dicts, add them to the preexisting instance
    if a vnic with the same name is not already present on the instance,
    including vnics added during the runtime of this function. Any failures
    will result in rolling back any new vnic additions here.

    Args:
        playbook_vnics (list): The vNICs from the playbook to be added.
        instance (ApiApplicationInstancePropertiesPayload): A payload
            containing the properties of the instance
    """

    created_vnic_uuids = []
    for playbook_vnic in playbook_vnics:
        if playbook_vnic.get('state') != 'absent':
            try:
                add_vnic_to_instance(playbook_vnic, instance)
            except tacp_exceptions.AddVnicException as e:
                fail_and_rollback_vnic_addition(
                    reason="Failed to add NIC {}: {}.".format(
                        playbook_vnic['name'], str(e)),
                    instance=instance,
                    vnic_uuids=created_vnic_uuids)

            instance = RESOURCES['app'].get_by_uuid(instance.uuid)
            vnic_uuid = next(
                device.vnic_uuid for device in instance.boot_order
                if device.name == playbook_vnic['name'])
            created_vnic_uuids.append(vnic_uuid)


def add_vnic_to_instance(playbook_vnic, instance):
    """Adds a vNIC to an instance if a vNIC with the same name is not already
        present in that instance.

    Args:
        playbook_vnic (dict): The vNIC configuration as given by the Ansible
            playbook.
        instance (ApiApplicationInstancePropertiesPayload): A payload
            containing the properties of the instance
    """
    datacenter_uuid = instance.datacenter_uuid

    parameters_to_create_vnic = get_parameters_to_create_vnic(
        datacenter_uuid,
        playbook_vnic)

    vnic_payload = get_add_vnic_payload(parameters_to_create_vnic)
    vnic_uuid = str(uuid4())
    network_payload = get_add_network_payload(vnic_payload, vnic_uuid)

    response = RESOURCES['update_app'].create_vnic(body=network_payload,
                                                   uuid=instance.uuid)

    if not hasattr(response, 'object_uuid'):
        message = json.loads(response.body)['message']
        if message:
            raise tacp_exceptions.AddVnicException(message)


def get_parameters_to_create_vnic(datacenter_uuid, playbook_vnic,
                                  template_order=None):
    """Generates a dict of the parameters necessary to create an
        ApiAddVnicPayload.

    Args:
        datacenter_uuid (str): UUID of the vNIC's instance's datacenter
        playbook_vnic (dict): Configuration of vNIC from Ansible playbook.
        template_order (int, optional): The boot order number from the template
            if applicable. Defaults to None.

    Raises:
        InvalidVnicNameException
        InvalidNetworkTypeException
        InvalidNetworkNameException
        InvalidFirewallOverrideNameException

    Returns:
        dict: The parameters necessary to create an ApiAddVnicPayload.
    """
    data = {
        'name': None,
        'mac': None,
        'automatic_mac_address': None,
        'network_type': None,
        'network_uuid': None,
        'firewall_override_uuid': None,
        'boot_order': None
    }

    data['name'] = playbook_vnic.get('name')

    data['mac'] = playbook_vnic.get('mac')

    data['automatic_mac_address'] = not bool(
        playbook_vnic.get('mac'))

    network_type = playbook_vnic.get('type').lower()
    if network_type not in ['vnet', 'vlan']:
        raise tacp_exceptions.InvalidNetworkTypeException(
            'Failed to create vNIC payload; vNICs must have a type of "VNET" or "VLAN"'  # noqa
        )

    network_resource = RESOURCES[network_type]

    network = network_resource.get_by_name(playbook_vnic['network'])
    if not network:
        raise tacp_exceptions.InvalidNetworkNameException(
            'Failed to create vNIC payload; an invalid network name was provided.'  # noqa
    )

    data['network_uuid'] = network.uuid

    if 'firewall_override' in playbook_vnic:
        firewall_override = RESOURCES['datacenter'].get_firewall_override_by_name(  # noqa
            datacenter_uuid, playbook_vnic['firewall_override']
        )
        if not firewall_override:
            raise tacp_exceptions.InvalidFirewallOverrideNameException(
        'Failed to create vNIC payload; an invalid firewall override name was provided.')  # noqa
        data['firewall_override_uuid'] = firewall_override.uuid

    data['boot_order'] = template_order

    return data


def get_add_vnic_payload(vnic_parameters):
    """Creates an ApiAddVnicPayload that can be used to add a vNIC to a new
        instance, or used as a basis to create an
        ApiCreateOrEditApplicationNetworkOptionsPayload.

    Args:
        vnic_parameters (dict): The parameters necessary to create an
        ApiAddVnicPayload.

    Returns:
        ApiAddVnicPayload: The payload that can be used in the 'vnics' field
            when creating an ApiCreateApplicationPayload.
    """

    vnic_payload = tacp.ApiAddVnicPayload(
        boot_order=vnic_parameters['boot_order'],
        automatic_mac_address=vnic_parameters['automatic_mac_address'],  # noqa
        firewall_override_uuid=vnic_parameters['firewall_override_uuid'],  # noqa
        mac_address=vnic_parameters['mac'],
        name=vnic_parameters['name'],
        network_uuid=vnic_parameters['network_uuid'])

    return vnic_payload


def get_add_network_payload(vnic_payload, vnic_uuid):
    """Create an API Network payload based on a provided ApiAddVnicPayload
        payload and UUID.

    Args:
        vnic_payload (ApiAddVnicPayload): A payload for adding a vNIC to a new
            application instance.

        vnic_uuid (str): The UUID of the corresponding vNIC

    Returns:
        ApiCreateOrEditApplicationNetworkOptionsPayload: The object provided
            to actually run the create vNIC operation.

    """

    network_payload = tacp.ApiCreateOrEditApplicationNetworkOptionsPayload(  # noqa
        automatic_mac_assignment=vnic_payload.automatic_mac_address,
        firewall_override_uuid=vnic_payload.firewall_override_uuid,
        mac_address=vnic_payload.mac_address,
        name=vnic_payload.name,
        network_uuid=vnic_payload.network_uuid,
        vnic_uuid=vnic_uuid
    )

    return network_payload


def add_playbook_disks(playbook_disks, instance):
    """Given a list of disks from the Ansible playbook, add them to the
        specified instance.

    Args:
        playbook_disks (list): The list of dicts of disk configurations
            specified in the Ansible playbook.
        instance (ApiApplicationInstancePropertiesPayload): A payload
            containing the properties of the instance
    """
    playbook_template = RESOURCES['template'].get_by_uuid(
        instance.template_uuid)
    template_boot_order = playbook_template.boot_order

    template_disks = [
        device.name for device in template_boot_order if device.disk_uuid]

    for playbook_disk in playbook_disks:
        if playbook_disk['name'] in template_disks:
            update_default_disk(playbook_disk, instance)
            continue

        add_disk_to_instance(playbook_disk, instance)


def add_playbook_disks_to_preexisting_instance(playbook_disks, instance):
    """Given a list of disks as dicts, add them to the preexisting instance
    if a vnic with the same name is not already present on the instance,
    including disks added during the runtime of this function. Any failures
    will result in rolling back any new vnic additions here.

    Args:
        playbook_disks (list): The vNICs from the playbook to be added.
        instance (ApiApplicationInstancePropertiesPayload): A payload
            containing the properties of the instance
    """

    created_disk_uuids = []
    for playbook_disk in playbook_disks:
        if playbook_disk.get('state') != 'absent':
            try:
                add_disk_to_instance(playbook_disk, instance)
            except Exception as e:
                fail_and_rollback_disk_addition(
                    reason="Failed to add disk {}: {}.".format(
                        playbook_disk['name'], str(e)),
                    instance=instance,
                    disk_uuids=created_disk_uuids)

            instance = RESOURCES['app'].get_by_uuid(instance.uuid)
            disk_uuid = next(
                device.disk_uuid for device in instance.boot_order
                if device.name == playbook_disk['name'])
            created_disk_uuids.append(disk_uuid)


def add_disk_to_instance(playbook_disk, instance):
    """Adds a new disk to an application instance if a disk with the same name
        is not already present in that instance.

    Args:
        playbook_disk (dict): The configuration of a single disk from the
            Ansible playbook
        instance (ApiApplicationInstancePropertiesPayload): A payload
            containing the properties of the instance
    """

    try:
        disk_payload = get_disk_payload(playbook_disk)
    except Exception as e:
        fail_and_rollback_instance_creation(str(e), instance)

    response = RESOURCES['update_app'].create_disk(body=disk_payload,
                                                   uuid=instance.uuid)

    if hasattr(response, 'body'):
        response_body = json.loads(response.body)

        if "Invalid Request" in response_body['code']:
            fail_and_rollback_instance_creation(response_body['message'],
                                                instance)


def get_disk_payload(playbook_disk):
    """Generates a payload for creating a new disk in an application.

    Args:
        playbook_disk (dict): The configuration of a single disk from the
            Ansible playbook

    Raises:
        InvalidDiskBandwidthLimitException
        InvalidDiskIopsLimitException
        InvalidDiskSizeException
        InvalidDiskNameException

    Returns:
        ApiDiskSizeAndLimitPayload: The populated payload object to be provided
            to the function that actually creates the disk.
    """

    bandwidth_limit = playbook_disk.get('bandwidth_limit')
    if bandwidth_limit:
        if int(bandwidth_limit) < MINIMUM_BW_FIVE_MBPS_IN_BYTES:
            raise tacp_exceptions.InvalidDiskBandwidthLimitException(
                'Could not add disk to instance; disks must have a bandwidth limit of at least 5 MBps (5000000).'  # noqa
        )

    iops_limit = playbook_disk.get('iops_limit')
    if iops_limit:
        if int(iops_limit) < MINIMUM_IOPS:
            raise tacp_exceptions.InvalidDiskIopsLimitException(
                'Could not add disk to instance; disks must have a total IOPS limit of at least 50.'  # noqa
        )

    size_gb = playbook_disk.get('size_gb')
    if not size_gb:
        raise tacp_exceptions.InvalidDiskSizeException(
            'Could not add disk to instance; disks must have a positive size in GB provided.'  # noqa
    )

    size_bytes = tacp_utils.convert_memory_abbreviation_to_bytes(
        str(playbook_disk['size_gb']) + 'GB')

    name = playbook_disk.get('name')
    if not name:
        raise tacp_exceptions.InvalidDiskNameException(
            'Could not add disk to instance; disks must have a name provided.'
        )

    disk_payload = tacp.ApiDiskSizeAndLimitPayload(
        name=name,
        size=size_bytes,
        uuid=str(uuid4()),
        iops_limit=iops_limit,
        bandwidth_limit=bandwidth_limit
    )

    return disk_payload


def update_default_disk(playbook_disk, instance):
    """Updates a disk that was created from a template by default.

    Args:
        playbook_disk (dict): The configuration of a single disk from the
            Ansible playbook
        instance (ApiApplicationInstancePropertiesPayload): A payload
            containing the properties of the instance
    """
    existing_disk = next(disk for disk in instance.disks
                         if disk.name == playbook_disk['name'])
    if 'size_gb' in playbook_disk:
        target_disk_size_bytes = tacp_utils.convert_memory_abbreviation_to_bytes(  # noqa
                        str(playbook_disk['size_gb']) + "GB"
        )
        if target_disk_size_bytes < existing_disk.size:
            fail_and_rollback_instance_creation(
                "Failed to resize disk {} from {} bytes to {} bytes. "
                "Cannot shrink a template's disk.".format(
                    existing_disk.name, existing_disk.size,
                    target_disk_size_bytes), instance)

        RESOURCES['update_app'].edit_disk_size(
            existing_disk.uuid,
            instance.uuid,
            target_disk_size_bytes)

    if 'bandwidth_limit' in playbook_disk:
        RESOURCES['update_app'].edit_disk_bw_limit(
            existing_disk.uuid,
            instance.uuid,
            playbook_disk['bandwidth_limit']
        )

    if 'iops_limit' in playbook_disk:
        RESOURCES['update_app'].edit_disk_iops_limit(
            existing_disk.uuid,
            instance.uuid,
            playbook_disk['iops_limit']
        )


def update_boot_order(playbook_instance, instance):
    """Updates the boot order of an instance using the boot order information
        provided in the Ansible playbook input.

    Args:
        playbook_instance (dict): The specified instance configuration from
        the playbook input
    """

    boot_order_payload = get_full_boot_order_payload_for_playbook(
        playbook_instance)
    instance_uuid = RESOURCES['app'].get_by_name(
        playbook_instance['name']).uuid

    try:
        RESOURCES['update_app'].edit_boot_order(
            boot_order_payload, instance_uuid)
        RESULT['changed'] = True
    except Exception as e:
        fail_with_reason(e)


def get_full_boot_order_payload_for_playbook(playbook_instance):
    """Given the playbook input, generate a payload to update the boot order
        for the created instance.

    Args:
        playbook_instance (dict): The specified instance configuration from
        the playbook input

    Returns:
        ApiEditApplicationPayload: A payload object containing all the boot
            order objects needed to perform the update operation.
    """
    playbook_devices = {}
    playbook_devices['disks'] = playbook_instance['disks']
    playbook_devices['nics'] = playbook_instance['nics']

    existing_instance = RESOURCES['app'].get_by_name(playbook_instance['name'])
    existing_instance_boot_devices = existing_instance.boot_order

    new_boot_order = []

    for boot_device in existing_instance_boot_devices:
        new_boot_order_entry = get_new_boot_order_entry_for_device(
            boot_device, playbook_devices)

        boot_order_payload = get_boot_order_payload(new_boot_order_entry)
        new_boot_order.append(boot_order_payload)

    new_boot_order = sorted(new_boot_order, key=lambda payload: payload.order)
    full_boot_order_payload = tacp.ApiEditApplicationPayload(
        boot_order=new_boot_order)

    return full_boot_order_payload


def get_new_boot_order_entry_for_device(boot_device, playbook_devices):
    """Generates a dict of values necessary to populate an ApiBootOrderPayload
        object for updating the boot order.

    Args:
        boot_device (ApiBootOrderPayload): The preexisting boot device
            in the instance in question.
        playbook_devices (list): A list of the vNICs and disks as provided
            in the Ansible playbook, especially indicating the desired boot
            order.

    Returns:
        dict: [description]
    """
    new_boot_order_entry = {}

    name = boot_device.name
    new_boot_order_entry['name'] = name

    if boot_device.vnic_uuid:
        new_boot_order_entry['vnic_uuid'] = boot_device.vnic_uuid
        new_boot_order_entry['disk_uuid'] = None
        playbook_nic = next(nic for nic in playbook_devices['nics']
                            if nic['name'] == name)
        new_boot_order_entry['order'] = playbook_nic['boot_order']
    else:
        new_boot_order_entry['vnic_uuid'] = None
        new_boot_order_entry['disk_uuid'] = boot_device.disk_uuid
        playbook_disk = next(disk for disk in playbook_devices['disks']
                             if disk['name'] == name)
        new_boot_order_entry['order'] = playbook_disk['boot_order']

    return new_boot_order_entry


def get_boot_order_payload(boot_order_entry):
    boot_order_payload = tacp.ApiBootOrderPayload(
        disk_uuid=boot_order_entry['disk_uuid'],
        name=boot_order_entry['name'],
        order=boot_order_entry['order'],
        vnic_uuid=boot_order_entry['vnic_uuid'])

    return boot_order_payload


def validate_nic_inputs(playbook_nics):
    checks = {nics_names_are_unique:
              'All NICs of an instance must have unique names.',
              nics_have_valid_networks:
              'NICs must be assigned to existing VLAN or VNET networks.'}

    for check, fail_reason in checks.items():
        result = check(playbook_nics)

        if not result:
            fail_with_reason(fail_reason)


def nics_names_are_unique(playbook_nics):
    playbook_names = [nic['name']
                      for nic in playbook_nics if nic.get('state') != 'absent']

    return len(playbook_names) == len(set(playbook_names))


def nics_have_valid_networks(playbook_nics):
    networks = {'vnet': [vnet.name for vnet in RESOURCES['vnet'].filter()],
                'vlans': [vlan.name for vlan in RESOURCES['vlan'].filter()]}

    networks['vlan'] = networks['vlans']

    for nic in playbook_nics:
        if 'state' in nic:
            if nic['state'] == 'absent':
                continue
        if nic['network'] not in networks[nic['type'].lower()]:
            return False
    return True


def boot_order_needs_update(playbook_instance, instance):

    instance_nics = {
        nic.name: nic.order for nic in instance.boot_order if nic.vnic_uuid}

    if 'nics' in playbook_instance:
        for nic in playbook_instance['nics']:
            if nic.get('state') != 'absent':
                if nic['boot_order'] != instance_nics.get(nic['name']):
                    return True

    instance_disks = {disk.name: disk.order for disk in instance.boot_order
                      if disk.disk_uuid}

    if 'disks' in playbook_instance:
        for disk in playbook_instance['disks']:
            if disk.get('state') != 'absent':
                if disk['boot_order'] != instance_disks.get(disk['name']):
                    return True
    return False


def playbook_parameters_not_matching_instance_state(
        playbook_instance, instance):
    parameters_not_matching = []

    parameter_matches = {
        'datacenter': playbook_datacenter_matches_instance_datacenter,
        'storage_pool': playbook_storage_pool_matches_instance_storage_pool,
        'vtx_enabled': playbook_vtx_matches_instance_vtx,
        'migration_zone': playbook_migration_zone_matches_instance_migration_zone,  # noqa
        'template': playbook_template_matches_instance_template,
        'num_cpus': playbook_num_cpus_matches_instance_num_cpus,
        'memory_mb': playbook_memory_mb_matches_instance_memory_mb,
        'application_group': playbook_application_group_matches_instance_application_group,  # noqa
        'vm_mode': playbook_vm_mode_matches_instance_vm_mode
    }
    for parameter in playbook_instance:
        if parameter in parameter_matches and playbook_instance.get(parameter):
            if not parameter_matches[parameter](
                    playbook_instance[parameter], instance):
                parameters_not_matching.append(parameter)

    return parameters_not_matching


def playbook_datacenter_matches_instance_datacenter(value, instance):
    return getattr(RESOURCES['datacenter'].get_by_name(value), 'uuid', None) \
        == instance.datacenter_uuid


def playbook_storage_pool_matches_instance_storage_pool(value, instance):
    return getattr(RESOURCES['storage_pool'].get_by_name(value), 'uuid',
                   None) \
        == instance.flash_pool_uuid


def playbook_vtx_matches_instance_vtx(value, instance):
    return value == instance.hardware_assisted_virtualization_enabled


def playbook_migration_zone_matches_instance_migration_zone(value, instance):
    return getattr(RESOURCES['migration_zone'].get_by_name(value), 'uuid',
                   None) \
        == instance.migration_zone_uuid


def playbook_template_matches_instance_template(value, instance):
    return value == \
        getattr(RESOURCES['template'].get_by_uuid(
            instance.template_uuid), 'name', None)


def playbook_num_cpus_matches_instance_num_cpus(value, instance):
    return value == instance.vcpus


def playbook_memory_mb_matches_instance_memory_mb(value, instance):
    return value * 1024 * 1024 == instance.memory


def playbook_application_group_matches_instance_application_group(
        value, instance):
    return getattr(RESOURCES['application_group'].get_by_name(value), 'uuid',
                   None) \
        == instance.application_group_uuid


def playbook_vm_mode_matches_instance_vm_mode(value, instance):
    return value == instance.vm_mode


def playbook_nics_match_instance_nics(playbook_nics, instance):
    instance_nics = instance.nics
    for nic in playbook_nics:
        if nic['name'] not in [vnic['name'] for vnic in instance_nics]:
            return False

        instance_vnic = next(vnic.uuid for vnic in instance.boot_order if
                             vnic.name == nic['name'] and vnic.vnic_uuid)

        if 'boot_order' in nic:
            if nic['boot_order'] != instance_vnic.order:
                return False


def get_new_vnics(playbook_vnics, instance):
    instance_nic_names = [vnic.name for vnic in instance.boot_order if
                          vnic.vnic_uuid]

    return [nic for nic in playbook_vnics
            if nic['name'] not in instance_nic_names]


def get_vnics_to_remove(playbook_vnics, instance):
    absent_vnics = [nic['name'] for nic in playbook_vnics
                    if nic.get('state') == 'absent']

    instance_nics = [vnic for vnic in instance.boot_order if vnic.vnic_uuid]

    return [vnic.vnic_uuid for vnic in instance_nics
            if vnic.name in absent_vnics]


def remove_vnics_from_instance(vnics_to_remove, instance):
    initial_nic_count = len(instance.vnics)
    for vnic_uuid in vnics_to_remove:
        try:
            RESOURCES['update_app'].delete_vnic(instance.uuid, vnic_uuid)
        except Exception as e:
            fail_with_reason(e)
    if len(instance.vnics) < initial_nic_count:
        RESULT['changed'] = True


def get_new_disks(playbook_disks, instance):
    instance_disk_names = [disk.name for disk in instance.boot_order if
                           disk.disk_uuid]

    return [disk for disk in playbook_disks
            if disk['name'] not in instance_disk_names]


def get_disks_to_remove(playbook_disks, instance):
    absent_disks = [disk['name'] for disk in playbook_disks
                    if disk.get('state') == 'absent']

    instance_disks = {
        disk.name: disk.disk_uuid for disk in instance.boot_order
        if disk.disk_uuid}

    return [uuid for name, uuid in instance_disks.items()
            if name in absent_disks]


def remove_disks_from_instance(disks_to_remove, instance):
    initial_disk_count = len(instance.disks)
    for disk_uuid in disks_to_remove:
        try:
            RESOURCES['update_app'].delete_disk(instance.uuid, disk_uuid)
        except Exception as e:
            fail_with_reason(e)
    instance = RESOURCES['app'].get_by_name(instance.name)
    if len(instance.disks) < initial_disk_count:
        RESULT['changed'] = True


def make_instance_disks_match_playbook_disks(playbook_disks, instance):
    for instance_disk in instance.disks:
        playbook_disk = next(disk for disk in playbook_disks if
                             disk['name'] == instance_disk.name)
        if playbook_disk.get('state') != 'absent':
            resolve_disk_size(playbook_disk, instance_disk, instance)
            resolve_disk_bw_limit(playbook_disk, instance_disk, instance)
            resolve_disk_iops_limit(playbook_disk, instance_disk, instance)


def resolve_disk_bw_limit(playbook_disk, instance_disk, instance):
    if 'bandwidth_limit' in playbook_disk:
        if playbook_disk['bandwidth_limit'] >= MINIMUM_BW_FIVE_MBPS_IN_BYTES:
            if playbook_disk['bandwidth_limit'] != instance_disk.bandwidth_limit:  # noqa
                RESOURCES['update_app'].edit_disk_bw_limit(
                    instance_disk.uuid,
                    instance.uuid,
                    playbook_disk['bandwidth_limit'])
                RESULT['changed'] = True
        else:
            fail_with_reason("Could not update disk {} bandwidth limit - "
                             "disks must have a bandwidth limit of at least 5 "
                             "MBps(5000000).".format(instance_disk.name))


def resolve_disk_iops_limit(playbook_disk, instance_disk, instance):
    if 'iops_limit' in playbook_disk:
        if playbook_disk['iops_limit'] >= MINIMUM_IOPS:
            if playbook_disk['iops_limit'] != instance_disk.iops_limit:  # noqa
                RESOURCES['update_app'].edit_disk_iops_limit(
                    instance_disk.uuid,
                    instance.uuid,
                    playbook_disk['iops_limit'])
                RESULT['changed'] = True
        else:
            fail_with_reason("Could not update disk {} IOPS limit - "
                             "disks must total IOPS limit of at least 50."
                             .format(instance_disk.name))


def resolve_disk_size(playbook_disk, instance_disk, instance):
    playbook_disk_size_bytes = playbook_disk['size_gb'] * \
        1024 * 1024 * 1024
    if instance_disk.size != playbook_disk_size_bytes:
        resize_disk(playbook_disk_size_bytes, instance_disk, instance)


def resize_disk(playbook_disk_size_bytes, instance_disk, instance):
    if instance_disk.size < playbook_disk_size_bytes:
        RESOURCES['update_app'].edit_disk_size(
            instance_disk.uuid, instance.uuid, playbook_disk_size_bytes)
        RESULT['changed'] = True
    else:
        fail_with_reason("Cannot shrink existing disks. Disk {} has a"
                         " size of {} bytes. The size_gb field must be"
                         " >= {}.".format(
                             instance_disk.name,
                             instance_disk.size,
                             instance_disk.size / 1024 / 1024 / 1024))


def run_module():
    # define available arguments/parameters a user can pass to the module
    if MODULE.check_mode:
        MODULE.exit_json(**RESULT)

    playbook_instance = MODULE.params

    instance_name = playbook_instance['name']

    instance = RESOURCES['app'].get_by_name(instance_name)
    if instance:
        if playbook_instance['state'] == PlaybookState.ABSENT:
            RESOURCES['app'].delete(instance.uuid)
            RESULT['changed'] = True
            MODULE.exit_json(**RESULT)

        target_state = playbook_instance['state']

        update_instance_state(instance, target_state)

        unmatching_params = playbook_parameters_not_matching_instance_state(
            playbook_instance, instance)

        if unmatching_params:
            fail_with_reason(
                "The following parameters do not match the running instance's"
                " state, and their in-place modification is not supported at "
                "this time: {}".format(','.join(unmatching_params)))

        if playbook_instance.get('nics') is not None:
            validate_nic_inputs(playbook_instance['nics'])
            new_vnics = get_new_vnics(playbook_instance['nics'], instance)
            add_playbook_vnics_to_preexisting_instance(
                new_vnics, instance)
            vnics_to_remove = get_vnics_to_remove(
                playbook_instance['nics'], instance)
            remove_vnics_from_instance(vnics_to_remove, instance)

        if playbook_instance.get('disks') is not None:
            new_disks = get_new_disks(playbook_instance['disks'], instance)
            if new_disks:
                add_playbook_disks_to_preexisting_instance(
                    new_disks, instance)
            disks_to_remove = get_disks_to_remove(
                playbook_instance['disks'], instance)
            if disks_to_remove:
                remove_disks_from_instance(disks_to_remove, instance)
            if boot_order_needs_update(playbook_instance, instance):
                update_boot_order(playbook_instance, instance)
            make_instance_disks_match_playbook_disks(
                playbook_instance['disks'], instance)

    else:
        if playbook_instance['state'] == PlaybookState.ABSENT:
            MODULE.exit_json(**RESULT)
        create_instance(playbook_instance)

        instance = RESOURCES['app'].get_by_name(instance_name)

        if 'nics' in playbook_instance:
            validate_nic_inputs(playbook_instance['nics'])
            add_playbook_vnics(playbook_instance['nics'], instance)
        add_playbook_disks(playbook_instance['disks'], instance)

        if boot_order_needs_update(playbook_instance, instance):
            update_instance_state(instance, PlaybookState.STOPPED)
            update_boot_order(playbook_instance, instance)

        target_state = playbook_instance['state']

        update_instance_state(instance, target_state)

    if target_state != PlaybookState.ABSENT:
        final_instance = RESOURCES['app'].get_by_name(instance_name)

        RESULT['instance'] = final_instance.to_dict()

    MODULE.exit_json(**RESULT)


def main():
    run_module()


if __name__ == '__main__':
    main()
