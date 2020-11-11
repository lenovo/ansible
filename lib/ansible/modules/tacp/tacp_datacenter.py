#!/usr/bin/python

# Copyright: (c) 2020, Lenovo
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json

import tacp
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.tacp_ansible import tacp_utils
from tacp.rest import ApiException

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tacp_datacenter

short_description: Get facts about various resources in ThinkAgile CP.

description:
  - This module can be used to retrieve data about various types of resources
    in the ThinkAgile CP cloud platform.

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
      - The name of the virtual datacenter to be created.
    required: true
    type: str
  support_widget_for_vdc_users:
    description:
      - Whether VDC users will have access to the chat support widget in the
         portal UI.
    required: false
    default: false
    type: bool
  migration_zones:
    description:
      - A list of migration zones, including their CPU cores and/or RAM
         allocations to be assigned to the new virtual datacenter.
    required: false
    type: list
    suboptions:
      name:
        description:
        - The name of the migration zone whose resources will be allocated to
           the virtual datacenter.
        required: true
        type: str
      cpu_cores:
        description:
        - The number of virtual CPU cores to be allocated to the new virtual
           datacenter.
        required: true
        type: int
      memory_gb:
        description:
        - The amount of RAM in GB to be allocated to the new virtual
           datacenter.
        required: true
        type: float
  networks:
    description:
      - A list of networks to be assigned to the new virtual datacenter.
    required: false
    type: list
    suboptions:
      name:
        description:
        - The name of the network to be assigned to the virtual datacenter.
        required: true
        type: str
      network_type:
        description:
        - The type of virtual network to be assigned - must be VLAN or VNET.
        required: true
        type: str
  templates:
    description:
      - A list of application templates to be downloaded into the new virtual
         datacenter's VDC Templates store.
    required: false
    type: list
    suboptions:
      name:
        description:
        - The name of the application template to be downloaded.
        required: true
        type: str
      new_name:
        description:
        - An optional new name for the application template once it is
           downloaded into the VDC Templates store.
        required: false
        type: str
      cpu_cores:
        description:
        - The default number of virtual CPUs to be assigned to the template.
        required: false
        type: int
      memory_mb:
        description:
        - The default amount of RAM in MB to be assigned to the template.
        required: false
        type: int
      description:
        description:
        - A text description for the template.
        required: false
        type: str
      wait_to_download:
        description:
        - Whether to fully download the application template to the VDC
           Templates store before allowing the Ansible task to end.
        required: false
        default: false
        type: bool
'''

EXAMPLES = '''
- name: Test the tacp_datacenter Ansible module
  hosts: localhost
  gather_facts: false
  vars:
    api_key: SECRET_KEY_HERE
  tasks:
    - name: Create a new datacenter on ThinkAgile CP
      tacp_datacenter:
        api_key: "{{ api_key }}"
        name: Datacenter1
        support_widget_for_vdc_users: yes
        migration_zones:
          - name: MZ1
            cpu_cores: 10
            memory_gb: 20
        storage_pools:
          - name: Pool1
            storage_gb: 100
        networks:
          - name: VLAN-1
            network_type: VLAN
          - name: VNET-1
            network_type: VNET
        templates:
          - name: FreeNAS 9.10
            new_name: CustomFreeNAS 9.10
            cpu_cores: 1
            memory_mb: 2048
            description: My custom FreeNAS template
            wait_to_download: yes
          - name: CentOS 7 - Jenkins - Lenovo Template
            cpu_cores: 4
            description: CentOS 7 with custom CPU cores amount
            wait_to_download: no
          - name: RHEL 7.4 (Minimal) - Lenovo Template
            description: RHEL 7.4 with default resources
            wait_to_download: no

'''

RETURN = '''
datacenter:
  description: A dict containing details about the newly-created virtual
     datacenter.
  type: dict
  returned: always

'''

module_args = {
    'api_key': {'type': 'str', 'required': True},
    'portal_url': {'type': 'str', 'required': False,
                   'default': 'https://manage.cp.lenovo.com'},
    'name': {'type': 'str', 'required': True},
    'support_widget_for_vdc_users': {'type': 'bool', 'required': False,
                                     'default': False},
    'migration_zones': {'type': 'list', 'required': True},
    'storage_pools': {'type': 'list', 'required': True},
    'networks': {'type': 'list', 'required': False},
    'templates': {'type': 'list', 'required': False}
}


RESULT = dict(
    changed=False,
    args=[]
)

MODULE = AnsibleModule(
    argument_spec=module_args,
    supports_check_mode=False
)

CONFIGURATION = tacp_utils.get_configuration(MODULE.params['api_key'],
                                             MODULE.params['portal_url'])
API_CLIENT = tacp.ApiClient(CONFIGURATION)

RESOURCES = {
    'category': tacp_utils.CategoryResource(API_CLIENT),
    'datacenter': tacp_utils.DatacenterResource(API_CLIENT),
    'migration_zone': tacp_utils.MigrationZoneResource(API_CLIENT),
    'storage_pool': tacp_utils.StoragePoolResource(API_CLIENT),
    'template': tacp_utils.MarketplaceTemplateResource(API_CLIENT),
    'vlan': tacp_utils.VlanResource(API_CLIENT),
    'vnet': tacp_utils.VnetResource(API_CLIENT)
}

playbook_dc = MODULE.params

existing_datacenter_names = [
    dc.name for dc in RESOURCES['datacenter'].filter()]


def fail_with_reason(reason):
    RESULT['msg'] = reason
    MODULE.fail_json(**RESULT)


def validate_inputs():
    nonexistent_resources = {}
    if not playbook_dc_is_new(playbook_dc['name']):
        fail_with_reason('There is already a datacenter with the provided name'
                         ' in the organization, cannot create another with'
                         ' the same name.')
    for resource_type in ['migration_zone', 'storage_pool', 'network',
                          'template']:
        resources = get_nonexistent_resources_of_type(resource_type)
        if resources:
            nonexistent_resources[resource_type] = resources

    if nonexistent_resources:
        fail_with_reason(
            'The following resources could not be found:\n' +
            ', '.join(["{}: {}".format(k, v)
                       for k, v in nonexistent_resources.items()]))


def create_datacenter():
    body = get_datacenter_payload(playbook_dc)

    try:
        response = RESOURCES['datacenter'].create(body)
        datacenter_uuid = response.uuid
    except ApiException as e:
        message = json.loads(e.body)['message']
        fail_with_reason(message)

    if 'networks' in playbook_dc:
        add_networks_to_datacenter(playbook_dc['networks'], datacenter_uuid)

    if 'templates' in playbook_dc:
        download_templates_to_datacenter(playbook_dc['templates'],
                                         datacenter_uuid)

    return RESOURCES['datacenter'].get_by_uuid(
        datacenter_uuid)


def playbook_dc_is_new(playbook_dc_name):
    return playbook_dc_name not in existing_datacenter_names


def get_nonexistent_resources_of_type(playbook_resource):
    nonexistent_resources = []
    if playbook_resource in ['migration_zone', 'storage_pool', 'template']:
        existing_resources = [resource.name for resource in
                              RESOURCES[playbook_resource].filter()]

        for resource in playbook_dc['{}s'.format(playbook_resource)]:
            if resource['name'] not in existing_resources:
                nonexistent_resources.append(resource['name'])

    elif playbook_resource == 'network':
        existing_networks = {}
        existing_networks['VLAN'] = [
            vlan.name for vlan in RESOURCES['vlan'].filter()]
        existing_networks['VNET'] = [
            vnet.name for vnet in RESOURCES['vnet'].filter()]

        for network in playbook_dc['networks']:
            if network['network_type'].upper() not in ['VLAN', 'VNET']:
                fail_with_reason(
                    "An invalid network type was provided for network {}. "
                    "Valid types are 'VLAN' and 'VNET'.".format(
                        network['name']))
            if network['name'] not in \
                    existing_networks[network['network_type'].upper()]:
                nonexistent_resources.append(network['name'])

    return nonexistent_resources


def get_datacenter_payload(playbook_dc):
    resource_allocations = []

    for playbook_mz in playbook_dc['migration_zones']:
        resource_allocations.append(
            get_migration_zone_resource_payload(playbook_mz))

    for playbook_pool in playbook_dc['storage_pools']:
        resource_allocations.append(
            get_storage_pool_resource_payload(playbook_pool)
        )

    payload = tacp.ApiCreateDatacenterPayload(
        name=playbook_dc['name'],
        is_support_widget_enabled=playbook_dc['support_widget_for_vdc_users'],
        resource_allocations=resource_allocations)

    return payload


def get_migration_zone_resource_payload(playbook_mz):
    migration_zone = RESOURCES['migration_zone'].get_by_name(
        playbook_mz['name'])

    category_name = 'Default' if 'category' not in playbook_mz\
        else playbook_mz['category']

    category = RESOURCES['category'].get_by_name(category_name)

    if category.uuid not in [cat.category_uuid for cat
                             in migration_zone.allocations.categories]:
        fail_with_reason(
            "Category {} is not present in migration zone {}".format(
                category_name, migration_zone.name))

    if not category:
        fail_with_reason("Invalid category name {}".format(category_name))

    memory_bytes = tacp_utils.convert_memory_abbreviation_to_bytes(
        "{}GB".format(playbook_mz['memory_gb']))

    category_allocation_payload = tacp.ApiCreateDatacenterCategoryAllocationPayload(  # noqa
        allocated_cpus=playbook_mz['cpu_cores'],
        allocated_memory_bytes=memory_bytes,
        category_uuid=category.uuid)

    return tacp.ApiCreateDatacenterResourcePayload(
        category_alocations=[category_allocation_payload],
        migration_zone_uuid=migration_zone.uuid)


def get_storage_pool_resource_payload(playbook_pool):
    storage_pool = RESOURCES['storage_pool'].get_by_name(
        playbook_pool['name'])

    allocated_capacity = int(tacp_utils.convert_memory_abbreviation_to_bytes(
        "{}GB".format(playbook_pool['storage_gb'])))

    return tacp.ApiCreateDatacenterResourcePayload(
        allocated_capacity=allocated_capacity,
        flash_pool_uuid=storage_pool.uuid
    )


def add_networks_to_datacenter(playbook_networks, datacenter_uuid):
    network_uuids = []
    for network_type in ['vlan', 'vnet']:
        names = [network['name'] for network in playbook_networks
                 if network['network_type'].lower() == network_type]

        networks = RESOURCES[network_type].filter(name=('=in=', names))

        uuids = [net.uuid for net in networks]
        network_uuids += uuids

    body = tacp.ApiUpdateNetworksForDatacenterPayload(network_uuids)

    try:
        RESOURCES['datacenter'].assign_network(
            body, datacenter_uuid)
    except ApiException as e:
        message = json.loads(e.body)['message']
        fail_with_reason(message + '\nThe datacenter creation has not been'
                         ' rolled back. Currently datacenters must be deleted'
                         ' manually in the ThinkAgile CP portal GUI.')


def download_templates_to_datacenter(playbook_templates, datacenter_uuid):
    for playbook_template in playbook_templates:
        body, template_uuid = get_marketplace_template_payload(
            playbook_template, datacenter_uuid)

        wait_to_download = False if 'wait_to_download' not in\
            playbook_template else bool(playbook_template['wait_to_download'])

        RESOURCES['template'].download_marketplace_template_to_datacenter(
            body, template_uuid, _wait=wait_to_download, _wait_timeout=600
        )


def get_marketplace_template_payload(playbook_template, datacenter_uuid):
    marketplace_template = RESOURCES['template'].get_by_name(
        playbook_template['name'])

    name = marketplace_template.name if 'new_name' not in playbook_template \
        else playbook_template['new_name']

    description = marketplace_template.description if 'description' \
        not in playbook_template else playbook_template['description']

    allocated_cpus = marketplace_template.default_cpus if 'cpu_cores' \
        not in playbook_template else playbook_template['cpu_cores']

    allocated_memory_bytes = marketplace_template.default_memory_bytes if \
        'memory_mb' not in playbook_template else \
        tacp_utils.convert_memory_abbreviation_to_bytes("{}MB".format(
            playbook_template['cpu_cores']))

    payload = tacp.ApiMarketplaceTemplatePayload(
        allocated_cpus=allocated_cpus,
        allocated_memory_bytes=allocated_memory_bytes,
        datacenter_uuid=datacenter_uuid,
        description=description,
        name=name,
        uuid=marketplace_template.uuid,
        version=marketplace_template.version
    )

    return payload, marketplace_template.uuid


def run_module():
    validate_inputs()

    new_datacenter = create_datacenter()
    RESULT['datacenter'] = new_datacenter.to_dict()
    RESULT['changed'] = True

    MODULE.exit_json(**RESULT)


def main():
    run_module()


if __name__ == '__main__':
    main()
