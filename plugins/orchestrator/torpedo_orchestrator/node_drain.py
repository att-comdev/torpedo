from time import sleep
from pyghmi.ipmi import command
from pyghmi.exceptions import IpmiException

from heat import Heat
from logger_agent import logger


class power_operation():
    """
    Manage power operations of a node via IPMI
    """
    def __init__(self, ipmi_ip, user_id, password):
        self.ipmi_ip = ipmi_ip
        self.user_id = user_id
        self.password = password

    def initialize_ipmi_session(self):
        """ Initialize command object with IPMI details """
        attempts = 0
        while attempts < 5:
            try:
                ipmi_object = command.Command(self.ipmi_ip, self.user_id,
                                              self.password)
            except IpmiException as e:
                print(e.args[0])
                logger.warning(
                    "IPMI command failed, retrying after 15 seconds...")
                sleep(15)
                attempts = attempts + 1
                continue
            return ipmi_object

    def set_power_state(self, state):
        """ Set power state to passed state """
        attempts = 0
        while attempts < 5:
            try:
                ipmi_object = self.initialize_ipmi_session()
                ipmi_object.ipmi_session.logout()
                ipmi_object.set_power(state)
            except IpmiException as iex:
                self.logger.error("Error sending command: %s" % str(iex))
                self.logger.warning(
                    "IPMI command failed, retrying after 15 seconds...")
                sleep(15)
                attempts = attempts + 1

    def get_power_state(self):
        """ Get current power state of the node """
        ipmi_object = self.initialize_ipmi_session()
        ipmi_object.get_power()


class NodeDrain(Heat):

    def __init__(self, tc, auth, **kwargs):
        super().__init__(tc, auth, **kwargs)
        self.nodes = kwargs.get('nodes', None)

    def get(self):
        (tc_status, message) = self.gc.GET(self.url, self.headers,
                                           data=self.data)
        return tc_status, message, self.tc

    def post(self, **kwargs):
        tc_status, message, tc = super().post()
        if tc_status != "FAIL":
            for node in self.nodes:
                po = power_operation(node['ipmi_ip'], node['user'],
                                     node['password'])
                logger.info("Powering off the node %s" % (
                            node['node_name']))
                po.set_power_state("off")
                while True:
                    tc_status, message, tc = super().post()
                    if tc_status == "PASS":
                        break
                logger.info("Powering on the node %s" % (
                            node['node_name']))
                po.set_power_state("on")
        return tc_status, message, self.tc
