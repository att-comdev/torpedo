import random
import string

from base import Base
from logger_agent import logger
from openstack import Openstack


class Neutron(Base, Openstack):

    def __init__(self, tc, auth, **kwargs):
        super().__init__(tc, auth, **kwargs)

    def get(self):
        (tc_status, message) = self.gc.GET(self.url, self.headers,
                                           data=self.data)
        return tc_status, message, self.tc

    def post(self):
        random_string = ''.join(random.choice(
            string.ascii_lowercase + string.digits) for _ in range(6))
        self.data['router']['name'] = "test-resiliency-{}".format(
            random_string)
        response = self.gc.POST(self.url, self.headers, data=self.data)
        if response.status_code >= 200 and response.status_code < 400:
            router_id = response.json()['router']['id']
            logger.info("Created router %s" % (router_id))
            tc_status = 'PASS'
            logger.info(
                'Deleting the created router: {}'.format(router_id))
            delete_url = "{}/{}".format(self.url, router_id)
            result = self.gc.DELETE(delete_url, self.headers)
            if result.status_code >= 200 and result.status_code < 400:
                tc_status = 'PASS'
                message = 'stripped not printing'
            else:
                tc_status = 'FAIL'
                message = result.text
                logger.info("Error message: {}".format(message))
            logger.info('Router Deleted')
        return tc_status, message, self.tc
