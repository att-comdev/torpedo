import ast
import logging
import subprocess
import sys

from random import randint, sample
from time import time, sleep

from common.driver.kubernetes.jobs import Jobs
from common.driver.kubernetes.pods import Pods


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
stream_handle = logging.StreamHandler()
formatter = logging.Formatter(
    '(%(name)s): %(asctime)s %(levelname)s %(message)s')
stream_handle.setFormatter(formatter)
LOG.addHandler(stream_handle)

cmd = ("kubectl describe secret -n metacontroller $(kubectl get secrets"
       " -n metacontroller | grep ^resiliency | cut -f1 -d ' ')"
       " | grep -E '^token'"
       "|cut -f2 -d':'|tr -d ' '")

token = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                shell=True).decode('utf-8').strip("\n")
cmd = ('kubectl config view --minify | grep server |'
       'cut -f 2- -d ":" | tr -d " "')
server = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                 shell=True).decode('utf-8').strip("\n")
pod_conn = Pods(token=token, host=server)
job_conn = Jobs(token=token, host=server)


class k8sExecutioner(object):

    def __init__(self, namespace, duration, count, kill_interval,
                 kill_selectors):

        self.namespace = namespace
        self.kill_selectors = kill_selectors
        self.duration = duration
        self.kill_interval = kill_interval
        count = count

    def execute(self):

        # log_list.extend(pod_conn.get_pods(
        #     namespace="default",
        #     label_selector="resiliency=enabled")[0])
        LOG.debug("k8s executioner executed")
        # for i in range(0, len(self.services)):
        #     with open(self.target_dir+'/chaoskube.yaml','r') as f:
        #         body = f.read()
        #         body = body.replace("CHANGESERVICE", self.services[i])
        #         body = body.replace("CHANGE_JOB_DURATION",
        #                             str(self.duration))
        #         body = body.replace("CHANGESELECTOR", self.selector[i])
        #         body = yaml.load(body)
        #         job = job_conn.create_jobs(body=body)
        #         LOG.info("Created job %s" %(job))
        initial_pod_list = []
        final_pod_list = []
        sel = self.kill_selectors[0]
        initial_pod_list.extend(
            pod_conn.get_pods(namespace=self.namespace,
                              label_selector=sel['selector'])[0])
        self.kill_pod(self.duration, self.namespace, sel, self.kill_interval)
        # for sel in self.kill_selectors:
        #     p1 = Process(target=self.kill_pod,
        #                  args=(self.duration, self.namespace, sel,
        #                        self.kill_interval))
        #     p.append(p1)
        #     p1.start()
        # for pr in p:
        #     pr.join()
            # self.kill_pod(self.namespace, sel)
        sleep(30)
        final_pod_list.extend(
            pod_conn.get_pods(namespace=self.namespace,
                              label_selector=sel['selector'])[0])
        if len(initial_pod_list) == len(final_pod_list):
            LOG.info("All pods of the services are brought up successfully")
        else:
            LOG.info("Failed to bring up all the pods."
                     "%d pods have failed to start"
                     % (len(initial_pod_list) - len(final_pod_list)))

    def kill_pod(self, duration, namespace, sel, interval):

        dur = time() + duration
        while True:
            label_selector = ','.join(sel['node-labels'])
            field_selector = "spec.nodeName="
            node_list = pod_conn.get_nodes(label_selector=label_selector)
            same_node = bool(sel['same-node'])
            if len(node_list) >= sel['max-nodes']:
                node_list = sample(node_list, sel['max-nodes'])
            if same_node:
                label_selector = sel['selector']
                for node in node_list:
                    pod_list = pod_conn.get_pods(
                        namespace=namespace,
                        label_selector=label_selector,
                        field_selector=field_selector+node)[0]
                    if pod_list:
                        if sel['kill-count'] >= len(pod_list):
                            sel['kill-count'] = len(pod_list)
                            count = int(sel['kill-count']) - 1
                        elif sel['kill-count'] == 1:
                            count = 0
                        else:
                            count = int(sel['kill-count']) - 1
                        LOG.info("Pods on %s: %s" % (node, pod_list))
                        for i in range(0, int(sel['kill-count'])):
                            del_pod = pod_list.pop(randint(0, count))
                            count -= 1
                            LOG.info("Deleting pod %s" % (del_pod))
                            pod_conn.delete_pod(namespace=namespace,
                                                name=del_pod)
            else:
                pod_list = pod_conn.get_pods(namespace=namespace,
                                             label_selector=sel['selector'])[0]
                count = int(sel['kill-count']) - 1
                if pod_list:
                    LOG.info("Pods: %s" % (pod_list))
                    for i in range(0, int(sel['kill-count'])):
                        del_pod = pod_list.pop(randint(0, count))
                        count -= 1
                        LOG.info("Deleting pod %s" % (del_pod))
                        pod_conn.delete_pod(namespace=namespace, name=del_pod)
                else:
                    LOG.error("No pod with specified selector found")
            sleep(interval)
            if time() >= dur:
                break


if __name__ == "__main__":
    inputs = sys.argv
    namespace = inputs[1]
    duration = int(inputs[2])
    count = int(inputs[3])
    kill_interval = int(inputs[4])
    kill_selectors_list = []
    kill_selectors = {}
    kill_selectors['selector'] = ",".join(ast.literal_eval(inputs[5]))
    kill_selectors['node-labels'] = ast.literal_eval(inputs[6])
    kill_selectors['same-node'] = ast.literal_eval(inputs[7])
    kill_selectors['kill-count'] = int(inputs[8])
    kill_selectors['max-nodes'] = int(inputs[9])
    kill_selectors_list.append(kill_selectors)
    k8s = k8sExecutioner(namespace, duration, count, kill_interval,
                         kill_selectors_list)
    k8s.execute()
