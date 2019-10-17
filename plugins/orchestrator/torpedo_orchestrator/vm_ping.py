import subprocess

from logger_agent import logger
from nova import Nova


class VmPing(Nova):

    def __init__(self, tc, auth, **kwargs):

        super().__init__(tc, auth, **kwargs)
        self.pod_labels = kwargs.get("pod_labels", None)

    def get(self):

        (tc_status, message) = self.gc.GET(self.url, self.headers,
                                           data=self.data)
        return tc_status, message, self.tc

    def post(self, **kwargs):

        tc_status, message, vm_id, hostname = self.create_vm()
        if tc_status is not 'FAIL':
            port_id = self.gc.get_vm_port_id(self.headers, vm_id)
            (floating_ip_id, floating_ip) = self.gc.create_floating_ip(
                self.headers, port_id, self.tc['public_network'])
            logger.info(
                'Performing ping test on floating ip,'
                '{} of vm {}'.format(
                    floating_ip, self.tc['data']['server']['name']))
            pod_delete_cmd = (
                "kubectl delete po -n openstack --field-selector"
                " spec.nodeName=%s -l %s|awk 'FNR == 2 {print $1}'" % (
                    hostname, self.pod_labels))
            logger.info(pod_delete_cmd)
            logger.info(subprocess.check_output(pod_delete_cmd,
                        stderr=subprocess.STDOUT,
                        shell=True).decode('utf-8').strip("\n"))
            cmd = "ping -c {} {}".format("180", floating_ip)
            exit_code = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                shell=True).decode('utf-8').strip("\n")
            # count = time()
            logger.info(exit_code)
            cmd = (
                "echo '" + exit_code + "'|grep 'transmitted' | awk -F"
                "',' '{print $3}' | awk -F '%' '{print $1}'")
            ping_result = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                shell=True).decode('utf-8').strip("\n")
            if ping_result == ' 0':
                tc_status = 'PASS'
            else:
                tc_status = 'FAIL'
            logger.info('Deleting the created floating ip {}'.format(
                floating_ip_id))
            network_url = self.gc.get_endpoint(service='network',
                                               interface='public')
            delete_url = "{}/v2.0/floatingips/{}".format(
                network_url, floating_ip_id)
            result = self.gc.DELETE(delete_url, self.headers)
            if result.status_code >= 200 and result.status_code < 400:
                # tc_status = 'PASS'
                message = 'Deleted floating IP'
            else:
                tc_status = 'FAIL'
                message = result.text
            tc_status, message = self.delete_vm(vm_id)
        return tc_status, message, self.tc
