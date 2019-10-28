from base import Base
from openstack import Openstack


class Keystone(Base, Openstack):

    def __init__(self, tc, auth, **kwargs):
        super().__init__(tc, auth, **kwargs)

    def get(self, **kwargs):
        try:
            tc_status, message = self.gc.GET(self.url, self.headers,
                                             data=self.data)
            return tc_status, message, self.tc
        except Exception as e:
            error_msg = "{}: {}".format(e.__class__.__name__, e)
            response = requests.Response()
            response.status_code = -1
            response._content = str.encode(error_msg)
            return response

    def post(self, **kwargs):
        try:
            tc_status, message = self.gc.POST(self.url, self.headers,
                                              data=self.data)
            return tc_status, message, self.tc
        except Exception as e:
            error_msg = "{}: {}".format(e.__class__.__name__, e)
            response = requests.Response()
            response.status_code = -1
            response._content = str.encode(error_msg)
            return response
