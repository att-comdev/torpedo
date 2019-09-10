from generic_client import GenericClient
from logger_agent import logger


class Openstack:

    def __init__(self, tc, auth, **kwargs):
        self.auth = auth
        self.gc = GenericClient(auth)
        token = self.gc.get_openstack_token()
        self.tc = tc
        self.nodes = kwargs.get("nodes", None)
        self.extra_args = kwargs.get("nodes", None)
        logger.info(
            'Executing test case: {}'.format(tc['name'])
        )
        self.headers = {
            'X-Auth-Token': token,
            # 'Content-Type': 'application/octet-stream',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        url = self.gc.get_endpoint(service=tc['service_type'],
                                   interface='public')
        url += tc['url']
        url = url.replace('%(tenant_id)s', self.gc.tenant_id)
        self.url = url.replace('%(project_id)s', self.gc.tenant_id)
        self.data = tc['data']
