import json
import requests
import sys
import warnings

from logger_agent import logger
from string import Template

warnings.filterwarnings("ignore")
OPENSTACK_TOKEN = """
{
    "auth": {
        "identity": {
            "methods": [
                "password"
            ],
            "password": {
                "user": {
                    "name": "$username",
                    "domain": {
                        "name": "$user_domain_name"
                    },
                    "password": "$password"
                }
            }
        },
        "scope": {
            "project": {
                "name": "$project_name",
                "domain": { "name": "$project_domain_name" }
            }
        }
    }
}
"""


class GenericClient():
    """Generic client for REST operations"""

    def __init__(self, auth):
        self.auth = auth
        self.token = None
        self.tenant_id = None

    def load_json_data(self, data):
        try:
            return json.loads(data)
        except json.decoder.JSONDecodeError:
            logger.error(
                'Unable to convert following data to json: \n{}'.format(data)
            )
            sys.exit(1)

    def get_openstack_token(self):
        """ Get openstack token """
        logger.info(
            'Get openstack token started'
        )
        data_template = Template(OPENSTACK_TOKEN)
        data = data_template.substitute(self.auth)
        headers = {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
        url = self.auth['auth_url'] + '/auth/tokens'
        response = requests.post(url, headers=headers, data=data, verify=False)
        self.token = response.headers.get('X-Subject-Token', None)
        response_dict = self.load_json_data(response.text)
        # Handle error in case token fails
        if response.status_code == 201:
            self.tenant_id = response_dict['token']['project']['id']
            logger.info(
                'Get openstack token completed successfully'
            )
        else:
            logger.error(
                'Get openstack token failed'
            )
        return self.token

    def get_endpoint(self, service='keystone', interface='public'):
        """ Get openstack endpoints """
        logger.info(
            'Get openstack endpoints started'
            )
        if self.token is None:
            self.token = self.get_openstack_token()
        url = self.auth['auth_url'] + '/services'
        params = {'type': service}
        headers = {
          'X-Auth-Token': self.token,
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers, params=params,
                                verify=False)
        service_dict = self.load_json_data(response.text)
        services = service_dict.get('services', None)

        if services is None:
            return None
        service_id = services[0]['id']
        url = self.auth['auth_url'] + '/endpoints'
        params = {
            'service_id': service_id,
            'interface': interface
        }
        headers = {
          'X-Auth-Token': self.token,
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers, params=params,
                                verify=False)
        endpoint_dict = self.load_json_data(response.text)
        endpoints = endpoint_dict.get('endpoints', None)

        if endpoints is None:
            return None

        endpoint = endpoints[0]['url']
        logger.info(
            'Get openstack endpoints completed successfully'
            )
        return endpoint

    def get_flavor_id(self, url, headers, name):
        url = url.replace('servers', 'flavors')
        if self.token is None:
            self.token = self.get_openstack_token()
        try:
            response = requests.get(url, headers=headers)
            response_json = self.load_json_data(response.text)
            all_flavors = response_json['flavors']
            for flavor in all_flavors:
                if name == flavor['name']:
                    return flavor['id']
        except Exception as e:
            error_msg = "{}: {}".format(e.__class__.__name__, e)
            response = requests.Response()
            response.status_code = -1
            response._content = str.encode(error_msg)
            return response

    def get_network_id(self, headers, name):
        url = self.get_endpoint(service='network', interface='public')
        network_url = url + 'v2.0/networks'
        try:
            response = requests.get(network_url, headers=headers)
        except Exception as e:
            error_msg = "{}: {}".format(e.__class__.__name__, e)
            response = requests.Response()
            response.status_code = -1
            response._content = str.encode(error_msg)
            return response
        response_json = self.load_json_data(response.text)
        networks = response_json['networks']
        for network in networks:
            if network['name'] == name:
                return network['id']  # , response.json()['port']['id']

    def get_vm_port_id(self, headers, vm_id):
        url = self.get_endpoint(service='compute', interface='public')
        url = url.replace('%(tenant_id)s', self.tenant_id)
        interface_url = '{}/servers/{}/os-interface'.format(url, vm_id)
        try:
            response = requests.get(interface_url, headers=headers)
        except Exception as e:
            error_msg = "{}: {}".format(e.__class__.__name__, e)
            response = requests.Response()
            response.status_code = -1
            response._content = str.encode(error_msg)
            return response
        response_json = self.load_json_data(response.text)
        port_id = response_json['interfaceAttachments'][0]['port_id']
        return port_id

    def create_floating_ip(self, headers, port_id, network):
        public_network_id = self.get_network_id(headers, network)
        url = self.get_endpoint(service='network', interface='public')
        network_url = url + 'v2.0/floatingips'
        data = {
            'floatingip': {
                'floating_network_id': public_network_id,
                'port_id': port_id,
            }
        }
        try:
            response = requests.post(network_url, headers=headers,
                                     data=json.dumps(data))
        except Exception as e:
            error_msg = "{}: {}".format(e.__class__.__name__, e)
            response = requests.Response()
            response.status_code = -1
            response._content = str.encode(error_msg)
            return response
        response_json = self.load_json_data(response.text)
        floating_ip = response_json['floatingip']['floating_ip_address']
        floating_ip_id = response_json['floatingip']['id']
        logger.info(
            'Waiting for floating IP {} to be associated'.format(floating_ip)
        )
        status = 'DOWN'
        while status != 'ACTIVE':
            response = requests.get(network_url, headers=headers)
            response_json = self.load_json_data(response.text)
            floating_ip_dicts = response_json['floatingips']
            for floating_ip_dict in floating_ip_dicts:
                if floating_ip_dict['id'] == floating_ip_id:
                    status = floating_ip_dict['status']
        return (floating_ip_id, floating_ip)

    def get_image_id(self, headers):
        url = self.get_endpoint(service='image', interface='public')
        url += '/v2/images'
        try:
            response = requests.get(url, headers=headers)
            response_json = self.load_json_data(response.text)
            images = response_json['images']
            for image in images:
                if image['name'] == 'cirros':
                    return image['id']
        except Exception as e:
            error_msg = "{}: {}".format(e.__class__.__name__, e)
            response = requests.Response()
            response.status_code = -1
            response._content = str.encode(error_msg)
            return response

    def check_resource_status(self, url, headers, data=""):
        try:
            result = requests.get(url, headers=headers)
            return result
        except Exception as e:
            error_msg = "{}: {}".format(e.__class__.__name__, e)
            response = requests.Response()
            response.status_code = -1
            response._content = str.encode(error_msg)
            return response

    def GET(self, url, headers, data=None):
        """ Hit a get request on passed url """
        try:
            response = requests.get(url, headers=headers, verify=False,
                                    data=json.dumps(data))
            if response.status_code >= 200 and response.status_code < 400:
                tc_status = 'PASS'
                message = "Stripped not printing"
            else:
                tc_status = 'FAIL'
                message = response.text
            return tc_status, message
        except Exception as e:
            tc_status = 'FAIL'
            error_msg = "{}: {}".format(e.__class__.__name__, e)
            response = requests.Response()
            response.status_code = -1
            response._content = str.encode(error_msg)
            return tc_status, response._content

    def POST(self, url, headers, data=None):
        """ Hit a post request on passed url """
        try:
            response = requests.post(url, headers=headers, verify=False,
                                     data=json.dumps(data))
        except Exception as e:
            error_msg = "{}: {}".format(e.__class__.__name__, e)
            response = requests.Response()
            response.status_code = -1
            response._content = str.encode(error_msg)
        return response

    def DELETE(self, url, headers):
        """ Hit a delete request on passed url """
        try:
            response = requests.delete(url, headers=headers, verify=False)
        except Exception as e:
            error_msg = "{}: {}".format(e.__class__.__name__, e)
            response = requests.Response()
            response.status_code = -1
            response._content = str.encode(error_msg)
        return response

    def PUT(self, url, headers, data=None, files=None):
        """ Hit a delete request on passed url """
        try:
            response = requests.put(url, headers=headers, verify=False,
                                    data=json.dumps(data),
                                    files=files)
        except Exception as e:
            error_msg = "{}: {}".format(e.__class__.__name__, e)
            response = requests.Response()
            response.status_code = -1
            response._content = str.encode(error_msg)
        return response
