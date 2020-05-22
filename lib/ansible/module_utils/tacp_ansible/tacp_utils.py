#!/usr/bin/python

# Copyright: (c) 2020, Lenovo
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

import json
import re
import tacp
from tacp.rest import ApiException

from ansible.module_utils.tacp_ansible.tacp_exceptions import ActionTimedOutException, InvalidActionUuidException
from ansible.module_utils.tacp_ansible.tacp_constants import *
from uuid import UUID, uuid4
from time import sleep


class ApplicationInstanceResource(object):
    def __init__(self, api_client):
        self.api = tacp.ApplicationsApi(api_client)
        self.api_client = api_client

    def get_all(self):
        """ Get all application instances as a list of dicts
        """
        api_response = self.api.get_applications_using_get()
        if api_response:
            instance_dicts = []
            for instance in api_response:
                instance_dicts.append(instance.to_dict())
            return instance_dicts
        return None

    def get_uuid_by_name(self, name):
        """ Return the UUID of an appplication instance if it exists
            given the name of the instance, None otherwise
        """
        assert name is not None

        all_instances = self.get_all()
        for instance in all_instances:
            if instance['name'] == name:
                return instance['uuid']
        return None

    def get_by_uuid(self, uuid):
        """ Returns an application as a dict specified by UUID, None otherwise
        """
        assert uuid is not None

        api_response = self.api.get_application_using_get(uuid)
        if api_response:
            return api_response.to_dict()
        return None

    def create(self, body):
        """ Creates an application with the provided API request body, returns
            bool of success/failure
        """
        assert body is not None

        api_response = self.api.create_application_from_template_using_post(
            body)
        try:
            wait_for_action_to_complete(
                api_response.action_uuid, self.api_client)
            return api_response.object_uuid
        except ActionTimedOutException:
            return "Exception when waiting for action to complete, action timed out."
        except InvalidActionUuidException:
            return "Exception when waiting for action to complete, invalid action UUID."
        except Exception as e:
            return e

    def delete(self, uuid):
        """ Deletes an application specified by UUID, returns bool of success/failure
        """
        assert uuid is not None

        api_response = self.api.delete_application_using_delete(uuid)
        try:
            wait_for_action_to_complete(
                api_response.action_uuid, self.api_client)
            return True
        except ActionTimedOutException:
            return "Exception when waiting for action to complete, action timed out."
        except InvalidActionUuidException:
            return "Exception when waiting for action to complete, invalid action UUID."
        except Exception as e:
            return e

    def power_action_on_instance_by_uuid(self, uuid, power_action):
        """ Performs a specified power operation on an application instance
            specified by UUID, returns bool of success/failure
        """
        power_action_dict = {
            ACTION_started: self.api.start_application_using_put,
            ACTION_stopped: self.api.stop_application_using_put,
            ACTION_restarted: self.api.restart_application_using_put,
            ACTION_shutdown: self.api.shutdown_application_using_put,
            ACTION_force_restarted: self.api.force_restart_application_using_put,
            ACTION_paused: self.api.pause_application_using_put,
            ACTION_resumed: self.api.resume_application_using_put,
            ACTION_absent: self.api.delete_application_using_delete
        }
        assert uuid is not None
        assert power_action in power_action_dict

        api_response = power_action_dict[power_action](uuid)
        try:
            wait_for_action_to_complete(
                api_response.action_uuid, self.api_client)
            return True
        except ActionTimedOutException:
            return "Exception when waiting for action to complete, action timed out."
        except InvalidActionUuidException:
            return "Exception when waiting for action to complete, invalid action UUID."
        except Exception as e:
            return e


class VlanResource(object):
    def __init__(self, api_client):
        self.api = tacp.VlansApi(api_client)
        self.api_client = api_client

    def get_all(self):
        """ Get all VLAN networks as a list of dicts
        """
        api_response = self.api.get_vlans_using_get()
        if api_response:
            vlan_dicts = []
            for vlan in api_response:
                vlan_dicts.append(vlan.to_dict())
            return vlan_dicts
        return None

    def get_uuid_by_name(self, name):
        """ Return the UUID of a VLAN network if it exists
            given the name of the network, None otherwise
        """
        assert name is not None

        all_vlans = self.get_all()
        for vlan in all_vlans:
            if vlan['name'] == name:
                return vlan['uuid']
        return None

    def get_by_uuid(self, uuid):
        """ Returns an vlan as a dict specified by UUID, None otherwise
        """
        assert uuid is not None

        api_response = self.api.get_vlan_using_get(uuid)
        if api_response:
            return api_response.to_dict()
        return None

    def create(self, body):
        """ Creates a VLAN network with the provided API request body, returns 
            object UUID if success else None
        """
        assert body is not None

        api_response = self.api.create_vlan_using_post(body)
        try:
            wait_for_action_to_complete(
                api_response.action_uuid, self.api_client)
            return api_response.object_uuid
        except ActionTimedOutException:
            return "Exception when waiting for action to complete, action timed out."
        except InvalidActionUuidException:
            return "Exception when waiting for action to complete, invalid action UUID."
        except Exception as e:
            return e

    def delete(self, uuid):
        """ Deletes a VLAN network specified by UUID, returns bool of success/failure
        """
        assert uuid is not None

        api_response = self.api.delete_vlan_using_delete(uuid)
        try:
            wait_for_action_to_complete(
                api_response.action_uuid, self.api_client)
            return True
        except ActionTimedOutException:
            return "Exception when waiting for action to complete, action timed out."
        except InvalidActionUuidException:
            return "Exception when waiting for action to complete, invalid action UUID."
        except Exception as e:
            return e


class VnetResource(object):
    def __init__(self, api_client):
        self.api = tacp.VnetsApi(api_client)
        self.api_client = api_client

    def get_all(self):
        """ Get all VNET networks as a list of dicts
        """
        api_response = self.api.get_vnets_using_get()
        if api_response:
            vnet_dicts = []
            for vnet in api_response:
                vnet_dicts.append(vnet.to_dict())
            return vnet_dicts
        return None

    def get_uuid_by_name(self, name):
        """ Return the UUID of a VNET network if it exists
            given the name of the network, None otherwise
        """
        assert name is not None

        all_vnets = self.get_all()
        for vnet in all_vnets:
            if vnet['name'] == name:
                return vnet['uuid']
        return None

    def get_by_uuid(self, uuid):
        """ Returns a VNET as a dict specified by UUID, None otherwise
        """
        assert uuid is not None
        api_response = self.api.get_vnet_using_get(uuid)
        if api_response:
            return api_response.to_dict()
        return None

    def create(self, body):
        """ Creates a VNET network with the provided API request body, returns 
            object UUID if success, None if failure
        """
        assert body is not None

        api_response = self.api.create_vnet_using_post(body)
        try:
            wait_for_action_to_complete(
                api_response.action_uuid, self.api_client)
            return api_response.object_uuid
        except ActionTimedOutException:
            return "Exception when waiting for action to complete, action timed out."
        except InvalidActionUuidException:
            return "Exception when waiting for action to complete, invalid action UUID."
        except Exception as e:
            return e

    def delete(self, uuid):
        """ Deletes a VNET network specified by UUID, returns bool of success/failure
        """
        assert uuid is not None
        api_response = self.api.delete_vnet_using_delete(uuid)
        try:
            wait_for_action_to_complete(
                api_response.action_uuid, self.api_client)
            return True
        except ActionTimedOutException:
            return "Exception when waiting for action to complete, action timed out."
        except InvalidActionUuidException:
            return "Exception when waiting for action to complete, invalid action UUID."
        except Exception as e:
            return e


def get_component_fields_by_name(name, component,
                                 api_client, fields=['name', 'uuid']):
    """
    Returns the UUID of a named component if it exists in a given
    ThinkAgile CP cloud, otherwise return None.

    :param name The name of the component that may or may not exist yet
    :type name str
    :param component The type of component in question, must be one of
    """

    valid_components = ["storage_pool", "application",
                        "template", "datacenter", "migration_zone",
                        "vnet", "vlan", "firewall_profile", "firewall_override"]

    if component not in valid_components:
        return "Invalid component"
    if component == "storage_pool":
        api_instance = tacp.FlashPoolsApi(api_client)
        try:
            # View flash pools for an organization
            api_response = api_instance.get_flash_pools_using_get(
                fields=fields)
        except ApiException as e:
            return "Exception when calling get_flash_pools_using_get: %s\n" % e
    elif component == "application":
        api_instance = tacp.ApplicationsApi(api_client)
        try:
            # View applications for an organization
            api_response = api_instance.get_applications_using_get(
                fields=fields)
        except ApiException as e:
            return "Exception when calling get_applications_using_get: %s\n" % e
    elif component == "template":
        api_instance = tacp.TemplatesApi(api_client)
        try:
            # View templates for an organization
            api_response = api_instance.get_templates_using_get(
                fields=fields)
        except ApiException as e:
            return "Exception when calling get_templates_using_get: %s\n" % e
    elif component == "datacenter":
        api_instance = tacp.DatacentersApi(api_client)
        try:
            # View datacenters for an organization
            api_response = api_instance.get_datacenters_using_get(
                fields=fields)
        except ApiException as e:
            return "Exception when calling get_datacenters_using_get: %s\n" % e
    elif component == "migration_zone":
        api_instance = tacp.MigrationZonesApi(api_client)
        try:
            # View migration zones for an organization
            api_response = api_instance.get_migration_zones_using_get(
                fields=fields)
        except ApiException as e:
            return "Exception when calling get_migration_zones_using_get: %s\n" % e
    elif component == "vlan":
        api_instance = tacp.VlansApi(api_client)
        try:
            # View VLAN networks for an organization
            api_response = api_instance.get_vlans_using_get(
                fields=fields)
        except ApiException as e:
            return "Exception when calling get_vlans_using_get: %s\n" % e
    elif component == "vnet":
        api_instance = tacp.VnetsApi(api_client)
        try:
            # View VNET networks for an organization
            api_response = api_instance.get_vnets_using_get(
                fields=fields)
        except ApiException as e:
            return "Exception when calling get_vnets_using_get: %s\n" % e
    elif component == "firewall_profile":
        api_instance = tacp.FirewallProfilesApi(api_client)
        try:
            # View Firewall profiles for an organization
            api_response = api_instance.get_firewall_profiles_using_get(
                fields=fields)
        except ApiException as e:
            return "Exception when calling get_firewall_profiles_using_get: %s\n" % e
    elif component == "firewall_override":
        # Need to get all datacenter UUIDs first
        api_instance = tacp.DatacentersApi(api_client)
        try:
            # View datacenters for an organization
            datacenter_list = api_instance.get_datacenters_using_get(
                fields=fields)
        except ApiException as e:
            return "Exception when calling get_datacenters_using_get: %s\n" % e

        api_response = []
        for datacenter in datacenter_list:
            api_instance = tacp.DatacentersApi(api_client)
            try:
                # View Firewall profiles for an organization
                api_response += api_instance.get_datacenter_firewall_overrides_using_get(
                    uuid=datacenter.uuid, fields=fields)
            except ApiException as e:
                return "Exception when calling get_firewall_profiles_using_get"

    if (api_response):
        if fields == ['name', 'uuid']:
            for result in api_response:
                if result.name == name:
                    return result.uuid
        if 'bootOrder' in fields:
            for result in api_response:
                if result.name == name:
                    boot_order = []
                    for order_item in result.boot_order:
                        str_dict = str(order_item).replace(
                            "\n", "").replace("'", '"').replace("None", '""')

                        json_dict = json.loads(str_dict)

                        disk_uuid = json_dict['disk_uuid'] if json_dict['disk_uuid'] else None
                        name = json_dict['name'] if json_dict['name'] else None
                        order = json_dict['order'] if json_dict['order'] else None
                        vnic_uuid = json_dict['vnic_uuid'] if json_dict['vnic_uuid'] else None

                        boot_order_payload = tacp.ApiBootOrderPayload(disk_uuid=disk_uuid,
                                                                      name=name,
                                                                      order=order,
                                                                      vnic_uuid=vnic_uuid)
                        boot_order.append(boot_order_payload)
                    return boot_order
        if 'nfvInstanceUuid' in fields:
            return api_response[0]
    return None


def convert_memory_abbreviation_to_bytes(value):
    """Validate memory argument. Returns the memory value in bytes."""
    MEMORY_RE = re.compile(
        r"^(?P<amount>[0-9]+)(?P<unit>t|tb|g|gb|m|mb|k|kb)?$")

    matches = MEMORY_RE.match(value.lower())
    if matches is None:
        raise ValueError(
            '%s is not a valid value for memory amount' % value)
    amount_str, unit = matches.groups()
    amount = int(amount_str)
    amount_in_bytes = amount
    if unit is None:
        amount_in_bytes = amount
    elif unit in ['k', 'kb', 'K', 'KB']:
        amount_in_bytes = amount * 1024
    elif unit in ['m', 'mb', 'M', 'MB']:
        amount_in_bytes = amount * 1024 * 1024
    elif unit in ['g', 'gb', 'G', 'GB']:
        amount_in_bytes = amount * 1024 * 1024 * 1024
    elif unit in ['t', 'tb', 'T', 'TB']:
        amount_in_bytes = amount * 1024 * 1024 * 1024 * 1024

    return amount_in_bytes


def is_valid_uuid(uuid_to_test, version=4):
    """
    Check if uuid_to_test is a valid UUID.

    Parameters
    ----------
    uuid_to_test : str
    version : {1, 2, 3, 4}

    Returns
    -------
    `True` if uuid_to_test is a valid UUID, otherwise `False`.

    Examples
    --------
    >>> is_valid_uuid('c9bf9e57-1685-4c89-bafb-ff5af830be8a')
    True
    >>> is_valid_uuid('c9bf9e58')
    False
    """
    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False

    return str(uuid_obj) == uuid_to_test


def api_response_to_dict(api_response):
    if type(api_response) != ApiException:
        if isinstance(api_response, str):
            message_str = api_response
            message_str = message_str.replace('\n', '').replace('null', 'None')
        elif hasattr(api_response, 'message'):
            message_str = api_response.message
        else:
            # This is what the default output would look like before processing
            # {
            #     "_automatic_deployment": "True",
            #     "_default_gateway": "192.168.41.1",
            #     "_dhcp_service": "{'domain_name': 'test.local',\n 'end_ip_range': '192.168.41.200',\n 'lease_time': 86400,\n 'primary_dns_server_ip_address': '1.1.1.1',\n 'secondary_dns_server_ip_address': '8.8.8.8',\n 'start_ip_range': '192.168.41.100',\n 'static_bindings': [{'hostname': 'controller',\n                      'id': 36,\n                      'ip_address': '192.168.41.101',\n                      'mac_address': 'b4:d1:35:00:0f:ff'}]}",
            #     "_firewall_override_uuid": "None",
            #     "_firewall_profile_uuid": "None",
            #     "_name": "ANSIBLETEST-VNET",
            #     "_network_address": "192.168.41.0",
            #     "_nfv_instance_uuid": "493a4da6-0662-44a7-8090-55dda4263401",
            #     "_routing_service": "{'address_mode': 'Static',\n 'firewall_override_uuid': None,\n 'gateway': '192.168.100.1',\n 'ip_address': '192.168.100.200',\n 'network_uuid': 'c08c3e72-1031-4a9e-9481-41c9e89b6abe',\n 'subnet_mask': '255.255.255.0',\n 'type': 'VLAN'}",
            #     "_subnet_mask": "255.255.255.0",
            #     "_usable_ip_range": "192.168.41.1-192.168.41.254",
            #     "_uuid": "da1868e5-59f8-46be-97dc-f2c62912e446",
            #     "discriminator": "None"
            # }
            attrs = [key for key in api_response.__dict__.keys(
            ) if not key.startswith("__") and key != "discriminator"]
            api_dict = {}
            for attr in attrs:
                val = str(api_response.__dict__[
                    attr]).replace('\n', '').replace('null', 'None')
                extra_space_pattern = ",\\s{2,}"
                api_dict[str(attr).lstrip("_")] = re.sub(
                    extra_space_pattern, ", ", val)
            return api_dict

    message_str = message_str.replace('\n', '').replace('null', 'None')

    http_text = 'HTTP response body: '
    http_index = message_str.find(http_text)

    message_str = message_str[http_index + len(http_text):]

    message_dict = dict(json.loads(message_str))
    return message_dict


def wait_for_action_to_complete(action_uuid, api_client):
    if action_uuid:
        api_instance = tacp.ActionsApi(api_client)
        action_incomplete = True

        timeout = 60
        time_spent = 0

        while action_incomplete and time_spent < timeout:
            api_response = api_instance.get_action_using_get(action_uuid)
            if api_response.status == 'Completed':
                action_incomplete = False
                return True
            else:
                sleep(1)
                time_spent += 1
        raise ActionTimedOutException
    raise InvalidActionUuidException


def delete_application(name, uuid, api_client):
    assert uuid is not None

    api_instance = tacp.ApplicationsApi(api_client)
    try:
        api_response = api_instance.delete_application_using_delete(
            uuid=uuid)
    except ApiException as e:
        return "Exception when calling get_firewall_profiles_using_get"

    try:
        wait_for_action_to_complete(api_response.action_uuid, api_client)
    except ActionTimedOutException:
        return "Exception when waiting for action to complete, action timed out."
    except InvalidActionUuidException:
        return "Exception when waiting for action to complete, invalid action UUID."


def get_resource_by_uuid(uuid, component, api_client):
    valid_components = ["storage_pool", "application",
                        "template", "datacenter", "migration_zone",
                        "vnet", "vlan", "firewall_profile", "firewall_override"]

    if component not in valid_components:
        return "Invalid component"
    if component == "storage_pool":
        api_instance = tacp.FlashPoolsApi(api_client)
        try:
            api_response = api_instance.get_flash_pool_using_get(uuid)
        except ApiException as e:
            return "Exception when calling get_flash_pool_using_get: %s\n" % e
    elif component == "application":
        api_instance = tacp.ApplicationsApi(api_client)
        try:
            api_response = api_instance.get_application_using_get(uuid)
        except ApiException as e:
            return "Exception when calling get_application_using_get: %s\n" % e
    elif component == "template":
        api_instance = tacp.TemplatesApi(api_client)
        try:
            api_response = api_instance.get_template_using_get(uuid)
        except ApiException as e:
            return "Exception when calling get_template_using_get: %s\n" % e
    elif component == "datacenter":
        api_instance = tacp.DatacentersApi(api_client)
        try:
            # View datacenters for an organization
            api_response = api_instance.get_datacenter_using_get(uuid)
        except ApiException as e:
            return "Exception when calling get_datacenter_using_get: %s\n" % e
    elif component == "migration_zone":
        api_instance = tacp.MigrationZonesApi(api_client)
        try:
            # View migration zones for an organization
            api_response = api_instance.get_migration_zone_using_get(uuid)
        except ApiException as e:
            return "Exception when calling get_migration_zone_using_get: %s\n" % e
    elif component == "vlan":
        api_instance = tacp.VlansApi(api_client)
        try:
            # View VLAN networks for an organization
            api_response = api_instance.get_vlan_using_get(uuid)
        except ApiException as e:
            return "Exception when calling get_vlan_using_get: %s\n" % e
    elif component == "vnet":
        api_instance = tacp.VnetsApi(api_client)
        try:
            # View VNET networks for an organization
            api_response = api_instance.get_vnet_using_get(uuid)
        except ApiException as e:
            return "Exception when calling get_vnet_using_get: %s\n" % e
    elif component == "firewall_profile":
        api_instance = tacp.FirewallProfilesApi(api_client)
        try:
            # View Firewall profiles for an organization
            api_response = api_instance.get_firewall_profile_using_get(uuid)
        except ApiException as e:
            return "Exception when calling get_firewall_profile_using_get: %s\n" % e

    return api_response_to_dict(api_response)
    # elif component == "firewall_override":
    #     # Need to get all datacenter UUIDs first
    #     api_instance = tacp.DatacentersApi(api_client)
    #     try:
    #         # View datacenters for an organization
    #         datacenter_list = api_instance.get_datacenters_using_get(
    #             uuid)
    #     except ApiException as e:
    #         return "Exception when calling get_datacenters_using_get: %s\n" % e

    #     api_response = []
    #     for datacenter in datacenter_list:
    #         api_instance = tacp.DatacentersApi(api_client)
    #         try:
    #             # View Firewall profiles for an organization
    #             api_response += api_instance.get_datacenter_firewall_overrides_using_get(
    #                 uuid=datacenter.uuid, uuid)
    #         except ApiException as e:
    #             return "Exception when calling get_firewall_profiles_using_get"
