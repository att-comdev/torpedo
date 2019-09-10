from http.server import BaseHTTPRequestHandler, HTTPServer

import copy
import jinja2
import json
import os
import re
import subprocess
import yaml


def is_job_finished(job):
    if 'status' in job:
        status_phase = job['status'].get('phase', "NO_STATUS_PHASE_YET")
        if status_phase == "Succeeded":
            return True
    """
    desiredNumberScheduled = job['status'].get('desiredNumberScheduled',1)
    numberReady = job['status'].get('numberReady',0)
    if desiredNumberScheduled == numberReady and desiredNumberScheduled > 0:
    return True
    """
    return False


def new_workflow(job):

    wf = {}
    template_filename = 'torpedo_argo.j2'
    script_path = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_path, "templates")
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(
                                     template_path))
    wf_text = re.sub(
        (re.compile('[\s]+None')), '', environment.get_template(
         template_filename).render(job))
    wf = yaml.load(wf_text)

    return wf


class Controller(BaseHTTPRequestHandler):

    def sync(self, job, children):

        desired_status = {}
        child = '%s-dj' % (job['metadata']['name'])

        self.log_message(" Job: %s", job)
        self.log_message(" Children: %s", children)
        orchestrator_template = job['spec']['orchestrator_plugin'] + ".yaml"
        chaos_template = job['spec']['chaos_plugin'] + ".yaml"
        orchestrator_path = os.path.join("/hooks/templates",
                                         orchestrator_template)
        chaos_path = os.path.join("/hooks/templates", chaos_template)
        traffic_path = os.path.join("/hooks/templates",
                                    "traffic-parameters.yaml")
        chaos_param_path = os.path.join("/hooks/templates",
                                        "chaos-parameters.yaml")
        sanity_path = os.path.join("/hooks/templates", "sanity_checks.yaml")
        if 'remote-cluster' not in job['spec'] or \
                job['spec']['remote-cluster'] is "False":
            token = subprocess.check_output(
                "cat /var/run/secrets/kubernetes.io/serviceaccount/token",
                stderr=subprocess.STDOUT,
                shell=True).decode('utf-8').strip("\n")
            job['spec']['remote-cluster-endpoint'] = \
                "https://kubernetes-apiserver.kube-system.svc.cluster.local:6443"
            job['spec']['remote-cluster-token'] = token
        with open(orchestrator_path, "r") as f:
            wf = yaml.load(f)
        with open(chaos_path, "r") as f:
            wf1 = yaml.load(f)
        with open(traffic_path, "r") as f:
            traffic_parameters = yaml.load(f)
        with open(chaos_param_path, "r") as f:
            chaos_parameters = yaml.load(f)
        with open(sanity_path, "r") as f:
            sanity_checks = yaml.load(f)
        job['spec']['torpedo_sanity_checks'] = sanity_checks['manifest']
        job['spec']['torpedo_traffic_job_manifest'] = wf['manifest']
        job['spec']['torpedo_chaos_job_manifest'] = wf1['manifest']
        job['spec']['traffic_parameters'] = \
            traffic_parameters['traffic-parameters']
        job['spec']['chaos_parameters'] = chaos_parameters['chaos-parameters']
        # If the job already finished at some point, freeze the status,
        # delete children, and take no further action.
        if is_job_finished(job):
            desired_status = copy.deepcopy(job['status'])
            desired_status['conditions'] = [{'type': 'Complete',
                                            'status': 'True'}]
            return {'status': desired_status, 'children': []}

    # Compute status based on what we observed, before building desired state.
    # Our .status is just a copy of the Argo Workflow.
        desired_status = copy.deepcopy(
            children['Workflow.argoproj.io/v1alpha1'].get(
                child, {}).get('status', {}))
        if is_job_finished(
                children['Workflow.argoproj.io/v1alpha1'].get(
                    child, {})):
            desired_status['conditions'] = [{'type': 'Complete',
                                            'status': 'True'}]
        else:
            desired_status['conditions'] = [{'type': 'Complete',
                                            'status': 'False'}]

        # Always generate desired state for child if we reach this point.
        # We should not delete children until after we know we've recorded
        # completion in our status, which was the first check we did above.
        desired_child = new_workflow(job)
        self.log_message(" Workflow: %s", desired_child)
        return {'status': desired_status, 'children': [desired_child]}

    def do_POST(self):

        content_in_bytes = self.rfile.read(
            int(self.headers.get('content-length')))
        observed = json.loads(content_in_bytes.decode('utf-8'))
        desired = self.sync(observed['parent'], observed['children'])

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(desired).encode('utf-8'))


HTTPServer(('', 30025), Controller).serve_forever()
