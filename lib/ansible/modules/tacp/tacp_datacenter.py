#!/usr/bin/python

# Copyright: (c) 2020, Lenovo
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.tacp_ansible import tacp_utils

import tacp
from tacp.rest import ApiException

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: tacp_info

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


'''

EXAMPLES = '''

'''

RETURN = '''
resource:
  description: A dict containing a key with the name of the resource type,
    and a list of the returned resources as a value.
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
    'networks': {'type': 'list', 'required': True}
}


RESULT = dict(
    changed=False,
    args=[]
)

MODULE = AnsibleModule(
    argument_spec=module_args,
    supports_check_mode=True
)

CONFIGURATION = tacp_utils.get_configuration(MODULE.params['api_key'],
                                             MODULE.params['portal_url'])
API_CLIENT = tacp.ApiClient(CONFIGURATION)

RESOURCES = {
    'category': tacp_utils.CategoryResource(API_CLIENT),
    'datacenter': tacp_utils.DatacenterResource(API_CLIENT),
    'migration_zone': tacp_utils.MigrationZoneResource(API_CLIENT),
    'storage_pool': tacp_utils.StoragePoolResource(API_CLIENT),
    'marketplace_template': tacp_utils.MarketplaceTemplateResource(API_CLIENT),
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
    for resource_type in ['migration_zone', 'storage_pool', 'network']:
        resources = get_nonexistent_resources_of_type(resource_type)
        if resources:
            nonexistent_resources[resource_type] = resources

    if nonexistent_resources:
        fail_with_reason(
            'The following resources could not be found: ' +
            ', '.join(["{}: {}".format(k, v)
                       for k, v in nonexistent_resources.items()]))


def create_datacenter():
    body = get_datacenter_payload(playbook_dc)
    RESULT['body'] = str(body)
    # MODULE.exit_json(**RESULT)
    response = RESOURCES['datacenter'].create(body)

    if not hasattr(response, 'uuid'):
        fail_with_reason(str(response))

    return RESOURCES['datacenter'].get_by_uuid(
        response.uuid)


def playbook_dc_is_new(playbook_dc_name):
    return playbook_dc_name not in existing_datacenter_names


def get_nonexistent_resources_of_type(playbook_resource):
    nonexistent_resources = []
    if playbook_resource in ['migration_zone', 'storage_pool']:
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


def run_module():
  #  validate_inputs()

    RESULT['datacenter'] = create_datacenter()
    RESULT['changed'] = True

    MODULE.exit_json(**RESULT)


def main():
    run_module()


if __name__ == '__main__':
    main()
