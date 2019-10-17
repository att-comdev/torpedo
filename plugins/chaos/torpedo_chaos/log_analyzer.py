import ast
import json
import logging
import os
import subprocess
import sys

from datetime import datetime

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


def log_analyzer(log_dir, service_list):

    result_list = []
    log_list = []
    log_list.extend(pod_conn.get_pods(
        namespace="metacontroller",
        label_selector="resiliency=enabled")[0])
    cur_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    for svc in service_list:
        svc_file = "".join(
            [x for x in log_list if (svc['service'] in x and "traffic" in x)])
        pass_search = (
            "grep -inr %s/%s.log -e 'pass'|wc -l") % (log_dir,
                                                      svc_file)
        fail_search = (
            "grep -inr %s/%s.log -e 'fail'|wc -l") % (log_dir,
                                                      svc_file)
        pass_tc = subprocess.check_output(pass_search,
                                          stderr=subprocess.STDOUT,
                                          shell=True).decode(
                                          'utf-8').strip("\n")
        fail_tc = subprocess.check_output(fail_search,
                                          stderr=subprocess.STDOUT,
                                          shell=True).decode(
                                          'utf-8').strip("\n")
        result_dict = {
                       "Test Case": svc['service'],
                       "TimeStamp": cur_time,
                       "Duration": svc['duration'],
                       "Pass test count": pass_tc,
                       "Fail test count": fail_tc
                      }
        result_list.append(result_dict)
    with open(os.path.join(log_dir, "test_results"), "w") as f:
        json.dump(result_list, f)
    LOG.info("Resiliency Test Results \n" + json.dumps(
             result_list, indent=2))
    LOG.info("All the logs are written to %s" % (log_dir))


if __name__ == "__main__":
    inputs = sys.argv
    cur_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_dir = os.path.join("/var/log/resiliency", "resiliency_" + cur_time)
    cmd = "bash log_collector.sh %s" % (log_dir)
    subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                            shell=True).decode('utf-8')
    service_list = ast.literal_eval(inputs[1])
    log_analyzer(log_dir, service_list)
