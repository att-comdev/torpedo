from base import Base
from openstack import Openstack


class Keystone(Base, Openstack):

    def __init__(self, tc, auth, **kwargs):
        super().__init__(tc, auth, **kwargs)

    def get(self, **kwargs):
        tc_status, message = self.gc.GET(self.url, self.headers,
                                         data=self.data)
        return tc_status, message, self.tc

    def post(self, **kwargs):
        tc_status, message = self.gc.POST(self.url, self.headers,
                                          data=self.data)
        return tc_status, message, self.tc
