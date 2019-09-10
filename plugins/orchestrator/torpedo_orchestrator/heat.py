import random
import string

from time import time

from base import Base
from logger_agent import logger
from openstack import Openstack


class Heat(Base, Openstack):

    def __init__(self, tc, auth, **kwargs):
        super().__init__(tc, auth, **kwargs)

    def get(self):
        (tc_status, message) = self.gc.GET(self.url, self.headers,
                                           data=self.data)
        return tc_status, message, self.tc

    def post(self):
        random_string = ''.join(random.choice(
            string.ascii_lowercase + string.digits) for _ in range(6))
        self.tc['data']['stack_name'] = "resiliency_stack_" + random_string
        response = self.gc.POST(self.url, self.headers, data=self.data)
        if response.status_code >= 200 and response.status_code < 400:
            tc_status = "PASS"
            message = "Stripped not printing"
            stack_id = response.json()['stack']['id']
            stack_name = self.tc['data']['stack_name']
            url = "{}/{}/{}".format(self.url, stack_name, stack_id)
            result = self.gc.check_resource_status(url, self.headers)
            ts = time()
            logger.info("Waiting for %s stack to complete " % (stack_id))
            while result.json()['stack']['stack_status'] != 'CREATE_COMPLETE':
                if result.json()['stack']['stack_status'] == "CREATE_FAILED":
                    tc_status = 'FAIL'
                    message = result.text
                    break
                if (time() - ts) == 900:
                    tc_status = "FAIL"
                    message = "Timed out waiting for the stack to complete"
                    break
                result = self.gc.check_resource_status(url, self.headers)
            logger.info('Deleting the created stack: {}'.format(
                stack_id))
            result = self.gc.DELETE(url, self.headers)
            if result.status_code >= 200 and result.status_code < 400:
                tc_status = 'PASS'
                message = 'stripped not printing'
            else:
                tc_status = 'FAIL'
                message = result.text
                logger.info("Error message: {}".format(message))
            logger.info('Stack Deleted')
        else:
            tc_status = "FAIL"
            message = response.text
        return tc_status, message, self.tc
