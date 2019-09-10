#!/usr/bin/env bash
# Copyright 2019 AT&T Intellectual Property.  All other rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


set -ux

SUBDIR_NAME=debug-$(hostname)

# NOTE(mark-burnett): This should add calicoctl to the path.
export PATH=${PATH}:/opt/cni/bin

TEMP_DIR=/var/log/resiliency/debug-report-$(date +"%Y-%m-%d_%H-%M-%S")
export TEMP_DIR
export BASE_DIR="${TEMP_DIR}/${SUBDIR_NAME}"
#export HELM_DIR="${BASE_DIR}/helm"
#export CALICO_DIR="${BASE_DIR}/calico"

mkdir -p "${BASE_DIR}"

PARALLELISM_FACTOR=2

function get_namespaces () {
    kubectl get namespaces -o name | awk -F '/' '{ print $NF }'|grep -E "openstack|kube-system|osh-infra|ceph|tenant-ceph"
}

function get_pods () {
    NAMESPACE=$1
    kubectl get pods -n "${NAMESPACE}" -o name | awk -F '/' '{ print $NF }' | xargs -L1 -P 1 -I {} echo "${NAMESPACE}" {}
}
export -f get_pods

function get_pod_logs () {
    NAMESPACE=${1% *}
    POD=${1#* }
    INIT_CONTAINERS=$(kubectl get pod "${POD}" -n "${NAMESPACE}" -o json | jq -r '.spec.initContainers[]?.name')
    CONTAINERS=$(kubectl get pod "${POD}" -n "${NAMESPACE}" -o json | jq -r '.spec.containers[].name')
    POD_DIR="${BASE_DIR}/pod-logs/${NAMESPACE}/${POD}"
    mkdir -p "${POD_DIR}"
    for CONTAINER in ${INIT_CONTAINERS} ${CONTAINERS}; do
        echo "get_pod_logs() [${NAMESPACE}] ${POD} ${CONTAINER}"
        kubectl logs "${POD}" -n "${NAMESPACE}" -c "${CONTAINER}" > "${POD_DIR}/${CONTAINER}.txt"
    done
}


export -f get_pod_logs

#function get_releases () {
#    helm list --all --short
#}
#
#function get_release () {
#    input=($1)
#    RELEASE=${input[0]}
#    helm status "${RELEASE}" > "${HELM_DIR}/${RELEASE}.txt"
#
#}
#export -f get_release
#
#if which helm; then
#    mkdir -p "${HELM_DIR}"
#    helm list --all > "${HELM_DIR}/list"
#    get_releases | \
#        xargs -r -n 1 -P "${PARALLELISM_FACTOR}" -I {} bash -c 'get_release "$@"' _ {}
#fi

kubectl get --all-namespaces -o wide pods > "${BASE_DIR}/pods.txt"

get_namespaces | \
    xargs -r -n 1 -P "${PARALLELISM_FACTOR}" -I {} bash -c 'get_pods "$@"' _ {} | \
    xargs -r -n 2 -P "${PARALLELISM_FACTOR}" -I {} bash -c 'get_pod_logs "$@"' _ {}

# iptables-save > "${BASE_DIR}/iptables"
#
# cat /var/log/syslog > "${BASE_DIR}/syslog"
#cat /var/log/armada/bootstrap-armada.log > "${BASE_DIR}/bootstrap-armada.log"

# ip addr show > "${BASE_DIR}/ifconfig"
# ip route show > "${BASE_DIR}/ip-route"
# cp -p /etc/resolv.conf "${BASE_DIR}/"
#
# env | sort --ignore-case > "${BASE_DIR}/environment"
#docker images > "${BASE_DIR}/docker-images"
#
#if which calicoctl; then
#    mkdir -p "${CALICO_DIR}"
#    for kind in bgpPeer hostEndpoint ipPool nodes policy profile workloadEndpoint; do
#        calicoctl get "${kind}" -o yaml > "${CALICO_DIR}/${kind}.yaml"
#    done
#fi

tar zcf "${SUBDIR_NAME}.tgz" -C "${TEMP_DIR}" "${SUBDIR_NAME}"
