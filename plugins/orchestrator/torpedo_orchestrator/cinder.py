from time import time

from base import Base
from logger_agent import logger
from openstack import Openstack


class Cinder(Base, Openstack):

    def __init__(self, tc, auth, **kwargs):

        super().__init__(tc, auth, **kwargs)

    def get(self):

        tc_status, message = self.gc.GET(self.url, self.headers,
                                         data=self.data)
        return tc_status, message, self.tc

    def post(self, **kwargs):
        response = self.gc.POST(self.url, self.headers, data=self.data)
        if response.status_code >= 200 and response.status_code < 400:
            tc_status = "PASS"
            message = response.text
            volume_id = response.json()['volume']['id']
            logger.info("Created volume %s" % (volume_id))
            poll_url = "{}/{}".format(self.url, volume_id)
            result = self.gc.check_resource_status(poll_url, self.headers)
            logger.info("Waiting for the volume %s to be available" % (
                volume_id))
            ts = time()
            while result.json()['volume']['status'] != "available":
                result = self.gc.check_resource_status(poll_url, self.headers)
                if result.status_code < 200 and result.status_code > 400:
                    tc_status = 'FAIL'
                    message = result.text
                    break
                if (time() - ts) == 600:
                    tc_status = "FAIL"
                    message = "Timed out waiting for the stack to complete"
                    break
                if result.json()['volume']['status'] == "error":
                    tc_status = "FAIL"
                    message = result.text
            logger.info("Deleting volume %s" % (volume_id))
            response = self.gc.DELETE(poll_url, self.headers)
            if response.status_code >= 200 and response.status_code < 400:
                tc_status = "PASS"
            else:
                tc_status = "FAIL"
                message = response.text
        return tc_status, message, self.tc
