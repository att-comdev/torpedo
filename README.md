# Torpedo

Torpedo is a framework to test the resiliency of the Airship deployed
environment. It provides templates and prebuilt tools to test all components
from hardware nodes to service elements of the deployed stack. The report and
logging module helps easy triage of design issues.


## Pre-requisites


### Label the nodes


```
Label the nodes on which argo to be run as argo=enabled

Label the nodes on which metacontroller needs to be enabled as
metacontroller=enabled

Label the nodes on which Torpedo should run as torpedo-controller=enabled

Label the nodes on which traffic and chaos jobs to run as resilency=enabled

Label the nodes on which log-collector jobs to run as log-collector=enabled
```

### Clone the Git repository


```
      git clone https://github.com/att-comdev/torpedo.git
```

### Install Metacontroller


```
kubectl create ns metacontroller

cat torpedo/metacontroller-rbac.yaml | kubectl create -n metacontroller -f –

cat torpedo/install_metacontroller.yaml | kubectl create -n metacontroller -f –
```

### Install Argo


```
kubectl create ns argo
cat torpedo/install_argo.yaml | kubectl create -n argo -f –
```

### Deploy Torpedo controller


```
cat torpedo/torpedo_crd.yaml | kubectl create -f -
cat torpedo/controller.yaml | kubectl create -f -
```

### Apply torpedo RBAC rules


```
      cat torpedo/resiliency_rbac.yaml | kubectl create -f -
      cat torpedo/torpedo_rbac.yaml | kubectl create -f -
```

### Deploy Torpedo


```
kubectl create configmap torpedo-metacontroller -n metacontroller
--from-file=torpedo-metacontroller=torpedo_metacontroller.py
cat torpedo/torpedo-controller.yaml | kubectl create -n metacontroller -f –
cat torpedo/webhook.yaml | kubectl create -n metacontroller -f –
```

### Trigger the test suite

```
      cat <test-suite> | kubectl create -f -
```

#### Note:
In case ceph storage is used to create a pvc, create a ceph secret in the
namespace the pvc needs to created with same name as userSecretName as
mentioned in the ceph storage class.
The ceph secret can be obtained by the following command –

kubectl exec -it -n ceph ceph_mon_pod -- ceph auth get-key client.admin |
base64

Replace the key and name in torpedo/secret.yaml with the key generated in above
command and the name mentioned in the ceph storage class respectively and
execute the following command –

cat torpedo/secret.yaml|kubectl create -f –


## Test cases covered in Torpedo

	1. Openstack
		- Openstack API GET calls
			- Keystone (Service list)
			- Mariadb (Keystone service list)
			- Memcached (Keystone service list)
			- Ingress (Keystone service list)
			- Glance (Image list)
			- Neutron (Port list)
			- Nova (Server list)
			- Cinder (Volume list)
			- Heat (Stack list)
			- Horizon (GET call on horizon landing page)

		- Openstack rabbitmq
			- Glance rabbitmq (POST call to create and upload and delete an image)
			- Neutron rabbitmq (POST call to create and delete a router)
			- Nova rabbitmq (POST call to create and delete a server)
			- Cinder rabbitmq (POST call to create a volume)
			- Heat rabbitmq (POST call to create and delete a stack)

		- Openstack API POST calls
			- Glance (POST call to create and upload and delete an image)
			- Neutron (POST call to create and delete a router)
			- Neutron dhcp-agent (POST call to create a virtual machine, assign a
        floating ip to the virtual machine and initiate a ping request to the
        floating IP)
			- Openvswitch DB (POST call to create a virtual machine,
        assign a floating ip to the virtual machine and initiate a ping request
        to the floating IP)
			- Openvswitch daemon (POST call to create a virtual machine, assign a
        floating ip to the virtual machine and initiate a ping request to the
        floating IP)
			- Nova Compute (POST call to create and delete a server)
			- Nova Scheduler (POST call to create and delete a server)
			- Nova Conductor (POST call to create and delete a server)
			- Libvirt (POST call to create and delete a server)
			- Cinder Volume (POST call to create a volume)
			- Cinder Scheduler (POST call to create a volume)
			- Heat (POST call to create and delete a stack)

	2. UCP
		- UCP API get calls
			- Keystone (Keystone service list)
			- Promenade (Get call to check health)
			- Armada (Releases list)
			- Drydock (nodes list)
			- Shipyard (configdocs list)
			- Barbican (Secrets list)
			- Deckhand (Revisions list)

	3. Kubernetes
		- Kubernetes Proxy (Creates a pod and a service and initiate a ping request
      to the service IP)
		- Kubernetes Apiserver (GET call to the pod list)
		- Kubernetes Scheduler (POST call to create and delete a pod)
		- Ingress (GET call to kube-apiserver)

## Test Suite Description

The test suite contains following sections -

1. Auth
2. Job parameters
3. Namespace
4. Orchestrator Plugin
5. Chaos Plugin
6. Volume storage class
7. Volume storage capacity
8. Volume name

 #### Auth
 Auth section consists of Keystone auth information in case of Openstack and
 UCP and url and token in case of Kubernetes

   ```
		- auth:
		    auth_url: http://keystone-api.openstack.svc.cluster.local:5000/v3
		    username: <username>
		    password: <password>
		    user_domain_name: default
		    project_domain_name: default
		    project_name: admin
   ```

 #### Job Parameters

 Job parameters section further consists 7 sections -

 1. name: name for test case

 2. service - Name of the service against which the tests to be run (example -
   nova, cinder etc)

 3. component - Component of service against which the test to run (example -
   nova-os-api, cinder-scheduler)

 4. job-duration - Duration for which the job needs to run (Both chaos and
   traffic jobs)

 5. count - Number of times chaos/ traffic should be induced on target service.
 Takes precedence only if job-duration is set to 0.

 6. nodes - Used in case of Node power off scenario. Defaults to None in normal
 scenarios. Takes a list of nodes with the following information -
        - ipmi_ip - IPMI IP of the target node
        - password - IPMI password of the target node
        - user - IPMI username of the target node
        - node_name - Node name of the target node

 7. sanity-checks - A list of checks that needs to be performed while the
 traffic and chaos jobs are running. Defaults to None. Example - get a list of
 pods, nodes etc. Takes 3 parameters as input :

        - image: Image to be used to run the sanity-checks
        - name: Name of the sanity-check
        - command: command to be executed

 8. extra-args - A list of extra parameters which can be passed for a specific
 test scenario. Defaults to None.

#### Namespace
Namespace in which the service to verify is running.

#### Orchestrator Plugin
The plugin to be used to initiate traffic.

#### Chaos Plugin
The plugin to be used to initiate chaos.

#### Volume Storage Class
Storage class to be used to create a pvc. Used to choose the type of storage to
be used to create pvc.

#### Volume Storage
Volume capacity of the pvc to be created.

#### Volume Name
Name of the volume pvc

		```
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
			        max-nodes: 2
			        nodes:
			          - ipmi_ip: <ipmi ip>
			            node_name: <node name>
			            user: <username>
			            password: <password>
			        sanity-checks:
			          - name: pod-list
			            image: kiriti29/torpedo-traffic-generator:v1
			            command:
			              - /bin/bash
			              - sanity_checks.sh
			              - pod-list
			              - "2000"
			              - "kubectl get pods --all-namespaces -o wide"
					 extra-args: ""

			  namespace: openstack
			  job-duration: 100
			  count: 60
			  orchestrator_plugin: "torpedo-traffic-orchestrator"
			  chaos_plugin: "torpedo-chaos"
			  volume_storage_class: "general"
			  volume_storage: "10Gi"
			  volume_name: "openstack-torpedo-test"

		```

## Node power off testcase scenario in Torpedo

The framework aims at creating a chaos in a NC environment and thereby
measuring the downtime before the cluster starts behaving normally, parallely
collecting all the logs pertaining to Openstack api calls, pods list, nodes
list and so on.

1. The testcase initially creates a heat stack which in turn creates a stack of
10 vms before introducing any chaos (ORT tests).
2. Once the heat stack is completely validated, we record the state.
3. Initiate sanity checks for -

	a. Checking the health of openstack services -

		Keystone - GET call on service list
		Glance - GET call on image list
		Neutron - GET call on port list
		Nova - GET call on server list
		Heat - GET call on stack list
		Cinder - GET call on volume list
	b. Checks on Kubernetes -

		Pod list - kubectl get pods --all-namespaces -o wide
		Node list - kubectl get nodes
		Rabbitmq cluster status - kubectl exec -it <rabbitmq pod on target node> -n
    <namespace> -- rabbitmqctl cluster_status
		Ceph cluster status  - kubectl exec -it <ceph pod on target node> -n
    <namespace> -- ceph health

4. Now we shutdown the node (IPMI power off)
5. Parallely instantiate the heat stack creation and see how much time it takes
for the heat stack to finish


	-  Verify heat stack is created in 15 minutes(config param).
		If not, re-initiate the stack creation, we try this in loop.
	-  The test exits with a failure after 40 minutes time-limit (this is a
    configurable parameter).


6. If the heat stack creation is complete, then we bring up the shutdown node,
and repeat the steps (1-5) on other nodes.
7. Logs are captured with request/response times, failures/success messages on
the test requests.
8. A report is generated based on the number of testcases that have passed or
failed.

```
	- All the logs of sanity checks(apache common log format)
	- The entire pod logs in all namespaces in the cluster.
	- The heat logs
```


## Authors

Muktevi Kiriti

Gurpreet Singh

Hemanth Kumar Nakkina
