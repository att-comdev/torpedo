..

=======
Torpedo
=======

Torpedo is a framework which tests how resilient the deployed environment
is. The data sources will provide the components on which resiliency tests are
to be performed. The results of the analysis are exported to elastic search and represented graphically on Kibana dashboard.

Problem description
-------------------

Post deployment of NC cloud (Airship), there isn't any mechanism to validate
the resiliency of the services deployed, this is even bigger challenge in a
more complex deployments, how to validate and continuously perform these
checks, and needless to say to collect the audit logs for the future
references.

We needed to perform two types of resiliency checks:
  - Focused to a particular service for example: Nova
  - What will happen if I kill Nova-Server Pod?
  - In case of random service failures, how does the platform behave
  - In case one of the controller nodes is powered off, what is the effect of it on end users and other cloud services.

Tools like Chaos Monkeys : ChaosKube / Powerseal can do well one task, that is
to introduce random failures to the platform. But they lack overall framework
for specific testing needs.

What we need is tooling that can invoke the tests(like take down a node in the cluster while heat tries to launch a stack of 10 vms and launch VM for
nova-case), while the chaos-agent does the destruction.
Framework will have tests executing; and will have an agent to monitor for any
failures and report.

Most importantly, we need something that’s completely driven by
Airship/Kubernetes (“eat your own dog food”) mike drop!!!

We propose to build Torpedo framework



Proposed: Torpedo
-----------------

Proposal here is to develop a standalone stateless automation utility to
test various components (services ucp/k9s/os, ingresses, cephs, nodes)
using a dynamically generated test-client using templates(yamls)
and run against a target environment by introducing pluggable “chaos”es.

Overall Architecture
--------------------

The Torpedo framework contains following components:

*  Metacontroller
*  Argo workflows
*  Test Suite
*  Orchestrator agent
*  Chaos agent

Before proceeding we define what a testcase document is and critical role it
plays in Torpedo.

TestCase:
---------
A document that defines what to test, what plugin is to be loaded to execute the tests, what to destruct and how to measure the success or failure.

This is a very key and critical element of Torpedo framework, it gives user a
finer control on defining a pluggable and customisable test suite.

A test is composed as an yaml, which allows as a platform
developer/tester, to select any service that’s running inside kubernetes.
Data-source defines the component on which the test is expected to run
Duration sets how long a test or kill job has to run.
While an Action, here kill-pod, is executing it will kill pods based on given
‘number of pods to kill’ param. Selection of pods is done using the, node
labels and pod-labels. In case of libvirt, openvswitch and other daemon sets,
pod kill is targetted on the node on which a vm is booted. To enable this we
we enable a parameter "same-node".

All of this is a customisable armada helm chart.


Structure of TestCase document (tc.yaml)
----------------------------------------

Each test suite is a torpedo CRD(custom resource definition). It contains the following spec -
  - Each testcase is defined by the following attributes

    1. job-params: A series of parameters defined to introduce traffic and chaos
       in the Kubernetes environment.

           1.1 name: name for test case

           1.2 service - Name of the service against which the tests to be run (example - nova, cinder etc)

           1.3 component - Component of service against which the test to run (example - nova-os-api, cinder-scheduler)

           1.4 job-duration - Duration for which the job needs to run (Both chaos and traffic jobs)

           1.5 count - Number of times chaos/ traffic should be induced on target service. Takes precedence only if job-duration is set to 0.

           1.6 nodes - Used in case of Node power off scenario. Defaults to None in normal scenarios. Takes a list of nodes with the following information -
               a. ipmi_ip - IPMI IP of the target node
               b. password - IPMI password of the target node
               c. user - IPMI username of the target node
               d. node_name - Node name of the target node

           1.7 sanity-checks - A list of checks that needs to be performed while the traffic and chaos jobs are running. Defaults to None. Example - get a list of pods, nodes etc. Takes 3 parameters as input -
               a. image: Image to be used to run the sanity-checks
               b. name: Name of the sanity-check
               c. command: command to be executed

           1.8 extra-args - A list of extra parameters which can be passed for a specific test scenario. Defaults to None.

    2. auth: It contains all the data that is required by the framework to obtain auth information from keystone, k8s and elastic search to trigger testcases.

    3. namespace: Namespace in which the service to verify is running.

    4. orchestrator_plugin: The plugin to be used to initiate traffic.

    5. chaos_plugin: The plugin to be used to initiate chaos.

    6. volume_storage_class: Storage class to be used to create a pvc. Used to choose the type of storage to be used to create pvc.

    7. volume_storage: Volume capacity of the pvc to be created.

    8. volume_name: Name of the volume

Sample Test Suite
-----------------

::

            apiVersion: torpedo.k8s.att.io/v1
            kind: Torpedo
            metadata:
              name: openstack-torpedo-test
            spec:
              auth:
                auth_url: http://keystone-api.openstack.svc.cluster.local:5000/v3
                username: admin
                password: ********
                user_domain_name: default
                project_domain_name: default
                project_name: admin

              job-params:
                - - service: nova
                    component: os-api
                    kill-interval: 30
                    kill-count: 4
                    same-node: True
                    pod-labels:
                      - 'application=nova'
                      - 'component=os-api'
                    node-labels:
                      - 'openstack-nova-control=enabled'
                    service-mapping: nova
                    name: nova-os-api
                    nodes: '[]'
                    max-nodes: 2
                    sanity-checks: '[]'
                    extra-args: ""

              namespace: openstack
              job-duration: 100
              count: 60
              orchestrator_plugin: "torpedo-traffic-orchestrator"
              chaos_plugin: "torpedo-chaos"
              volume_storage_class: "general"
              volume_storage: "10Gi"
              volume_name: "openstack-torpedo-test"

Torpedo Core
------------

Orchestrator
------------
The job of the orchestrator is to control the complete flow. It performs
following tasks:

  -  Install pre-requites - Argo, Metacontroller and Torpedo controller.
  -  Launch the test suite which generates argo workflows which launch the chaos, traffic, sanity-check jobs and log-analyzer agents.

The orchestrator accepts path the to the testcases.yaml as input.
It is the master test-suite file that will control the testcases that are
executed.

Workers
-------
There are list of workers present in api.yaml file. The task

::

    "nova": {
        "name": "nova_list",
        "service_type": "compute",
        "operation": "GET",
        "url": "/servers",
        "concurrency": 1,
        "repeat": 20,
        "duration": "duration"
        },
    "glance": {
        "name": "glance_image_list",
        "service_type": "image",
        "operation": "GET",
        "url": "/v2/images",
        "concurrency": 1,
        "repeat": 20,
        "duration": "duration"
        },
    "keystone": {
        "name": "keystone_endpoint_list",
        "service_type": "identity",
        "operation": "GET",
        "url": "/services",
        "concurrency": 1,
        "repeat": 20,
        "duration": "duration"
        }

Logs Collection and Analysis
----------------------------

The logs of all the resiliency tests are stored in "/var/log/resiliency"
folder inside a pvc. For each run, there would be a pvc created with the name given in test suite and the logs of each service api traffic and chaos jobs are written into this pvc.
Example: A folder will be created inside pvc under "/var/log/resiliency/resiliency_2019-01-22_12-55-36" and the logs are written into this folder.

The abstract details of the tests (tests performed, Pass test case count and
Fail test case count) conducted are logged in test_results file inside the
same folder.


Report Generation
-----------------

At the end of the each run a report will be generated in the form of an excel
sheet which captures the information related -

  - Test case name
  - Failure scenario
  - State of pods being tested (Active/Passive)
  - Ratings tester
      - Duration for which the test is run.
      - Passed test case count
      - Failed test case count
  - Test case description: The tasks performed upon starting the test case.
  - Failure scenario: Describes the scenario where a test case can be deemed
                      as failure

Example result file -

+------------------------+-----------+--------+----------------------+----------+---------+
|Enter FM name using the |Number of  | Pod    |                      |Comments  | Failure |
|FM naming convention    |pods to    | State  |   Ratings Tester     |/Test-    | scenario|
|(see other tab)         |delete     |        |                      |Type      |         |
+------------------------+-----------+--------+--------+------+------+----------+---------+
|SW component failures   |           |        |        | Pass | Fail |          |         |
|                        |           |        |Duration| Test | Test |          |         |
|                        |           |        |  Secs  | Count| Count|          |         |
+------------------------+-----------+--------+--------+------+------+----------+---------+
|                        |           |        |        |      |      |Performs  |Any      |
|airflow-web             |    2      | Active/|  600   |18935 |  0   |get call  |transient|
|                        |           | Active |        |      |      |to airflow|request/ |
|                        |           |        |        |      |      |web node  |workflow |
|                        |           |        |        |      |      |port      |handled  |
|                        |           |        |        |      |      |          |by the   |
|                        |           |        |        |      |      |          |failed   |
|                        |           |        |        |      |      |          |POD will |
|                        |           |        |        |      |      |          |fail     |
+------------------------+-----------+--------+--------+------+------+----------+---------+
|                        |           |        |        |      |      |Performs  |Any      |
|armada-api              |    2      | Active/|  600   |46    |  0   |get call  |transient|
|                        |           | Active |        |      |      |to list   |request/ |
|                        |           |        |        |      |      |all the   |workflow |
|                        |           |        |        |      |      |available |handled  |
|                        |           |        |        |      |      |releases  |by the   |
|                        |           |        |        |      |      |          |failed   |
|                        |           |        |        |      |      |          |POD will |
|                        |           |        |        |      |      |          |fail     |
+------------------------+-----------+--------+--------+------+------+----------+---------+


Security impact
---------------

The impact would be limited to the use of credentials for token
generation.

Performance impact
------------------

There might be degradation seen in the performance due to the chaos
introduced.

Alternatives
------------

No existing utilities available to transform site information
automatically.


Impacted components
-------------------

None.

Implementation
--------------

| The following high-level implementation tasks are identified:
| a) Helm charts
| b) Torpedo Controller
| c) Argo workflow generation
| d) API call jobs
| e) Chaos jobs
| f) Log collection
| g) Log Analysis


Usage
-----

::

     cat <test-suite> |kubectl create -f
