import ast
import json
import importlib
import sys
import traceback

from time import time

from cinder import Cinder
from glance import Glance
from heat import Heat
from horizon import Horizon
from keystone import Keystone
from logger_agent import logger
from nova import Nova
from neutron import Neutron
from node_drain import NodeDrain
from node_power_off import NodePowerOff
from ucp import UCP
from vm_ping import VmPing


class Runner():
    """Placeholder to run the tasks concurrently"""

    def __init__(self, concurrency=1, repeat=1):
        # These values can be overrided per testcase
        # Concurrency is not handled yet
        self.concurrency = concurrency
        self.repeat = repeat

    def execute(self, auth, tc, nodes, extra_args, pod_labels):

        if tc['duration'] > 0:
            repeat = time() + tc['duration']
            count = time()
        else:
            count = 0
            repeat = tc.get('repeat', self.repeat)
        test_count = 1
        if 'data' not in tc:
            tc['data'] = "{}"
        current_module = importlib.import_module('main')
        klass = getattr(current_module, tc['service-mapping'])
        obj = klass(tc, auth, nodes=nodes, extra_args=extra_args,
                    pod_labels=pod_labels)
        target_method = getattr(obj, tc['operation'].lower())
        while count < repeat:
            tc_name = tc['name']+'-'+str(test_count)
            tc_status, message, tc = target_method()
            logger.info("Test Case: %-20s Status: %4s Message: %s "
                        % (tc_name,
                           tc_status,
                           message))
            if tc['duration'] > 0:
                count = time()
            else:
                count += 1
            test_count += 1


if __name__ == "__main__":
    inputs = sys.argv
    auth = ast.literal_eval(inputs[1])
    component = inputs[2]
    duration = int(inputs[3])
    count = int(inputs[4])
    if inputs[5]:
        nodes = ast.literal_eval(inputs[5])
    else:
        nodes = []
    if inputs[6]:
        extra_args = ast.literal_eval(inputs[6])
    else:
        extra_args = []
    if inputs[7]:
        pod_labels = ast.literal_eval(inputs[7])
    else:
        pod_labels = []
    run = Runner()
    logger.info('Starting with test case execution')
    testcases = json.loads(open("testcases.json", "r").read())
    testcases[component]["duration"] = duration
    testcases[component]["repeat"] = count
    try:
        run.execute(auth, testcases[component], nodes, extra_args, pod_labels)
    except Exception as e:
        logger.error("%s: %s" % (e.__class__.__name__, e))
        logger.error(traceback.print_exc())
