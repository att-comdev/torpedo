BUILD_DIR           := $(shell mktemp -d)
IMAGE_PREFIX        ?= kiriti29
TRAFFIC_IMAGE_NAME  ?= torpedo-traffic-generator
CHAOS_IMAGE_NAME    ?= torpedo-chaos-plugin
IMAGE_TAG           ?= v1
PROXY               ?= http://proxy.foo.com:8000
NO_PROXY            ?= localhost,127.0.0.1,.svc.cluster.local
USE_PROXY           ?= false
PUSH_TRAFFIC_IMAGE  ?= false
PUSH_CHAOS_IMAGE    ?= false
# use this variable for image labels added in internal build process
PYTHON              = python3
TRAFFIC_IMAGE       := ${IMAGE_PREFIX}/${TRAFFIC_IMAGE_NAME}:${IMAGE_TAG}
CHAOS_IMAGE         := ${IMAGE_PREFIX}/${CHAOS_IMAGE_NAME}:${IMAGE_TAG}
UBUNTU_BASE_IMAGE   ?=

.PHONY: all
all: install_argo install_metacontroller install_torpedo_controller

#.PHONY: install_metacontroller
#install_metacontroller: install_argo
#
#.PHONY: install_torpedo_controller
#install_torpedo_controller: install_metacontroller
#
#.PHONY: build_torpedo_orchestrator
#build_torpedo_orchestrator: install_torpedo_controller
#
#.PHONY: build_torpedo_chaos
#build_torpedo_chaos: build_torpedo_orchestrator

.PHONY: docs
docs: clean build_docs

.PHONY: build_docs
build_docs:
	tox -e docs

_BASE_IMAGE_ARG := $(if $(UBUNTU_BASE_IMAGE),--build-arg FROM="${UBUNTU_BASE_IMAGE}" ,)

.PHONY: build_torpedo_orchestrator
build_torpedo_orchestrator:
ifeq ($(USE_PROXY), true)
	docker build -t $(TRAFFIC_IMAGE) --label $(LABEL) \
		--label "org.opencontainers.image.revision=$(COMMIT)" \
		--label "org.opencontainers.image.created=$(shell date --rfc-3339=seconds --utc)" \
		--label "org.opencontainers.image.title=$(IMAGE_NAME)" \
		-f images/torpedo/Dockerfile.torpedo_orchestrator \
		--build-arg http_proxy=$(PROXY) \
		--build-arg https_proxy=$(PROXY) \
		--build-arg HTTP_PROXY=$(PROXY) \
		--build-arg HTTPS_PROXY=$(PROXY) \
		--build-arg no_proxy=$(NO_PROXY) \
		--build-arg NO_PROXY=$(NO_PROXY) .
else
	docker build -t $(TRAFFIC_IMAGE) \
		--label "org.opencontainers.image.revision=$(COMMIT)" \
		--label "org.opencontainers.image.created=$(shell date --rfc-3339=seconds --utc)" \
		--label "org.opencontainers.image.title=$(TRAFFIC_IMAGE_NAME)" \
		-f images/torpedo/Dockerfile.torpedo_orchestrator .
endif

ifeq ($(PUSH_TRAFFIC_IMAGE), true)
		docker push $(TRAFFIC_IMAGE)
endif

.PHONY: build_torpedo_chaos
build_torpedo_chaos:
ifeq ($(USE_PROXY), true)
	docker build -t $(CHAOS_IMAGE) \
		--label "org.opencontainers.image.revision=$(COMMIT)" \
		--label "org.opencontainers.image.created=$(shell date --rfc-3339=seconds --utc)" \
		--label "org.opencontainers.image.title=$(CHAOS_IMAGE_NAME)" \
		-f images/torpedo/Dockerfile.torpedo_chaos \
		--build-arg http_proxy=$(PROXY) \
		--build-arg https_proxy=$(PROXY) \
		--build-arg HTTP_PROXY=$(PROXY) \
		--build-arg HTTPS_PROXY=$(PROXY) \
		--build-arg no_proxy=$(NO_PROXY) \
		--build-arg NO_PROXY=$(NO_PROXY) .
else
	docker build -t $(CHAOS_IMAGE) \
		--label "org.opencontainers.image.revision=$(COMMIT)" \
		--label "org.opencontainers.image.created=$(shell date --rfc-3339=seconds --utc)" \
		--label "org.opencontainers.image.title=$(CHAOS_IMAGE_NAME)" \
		-f images/torpedo/Dockerfile.torpedo_chaos .
endif

ifeq ($(PUSH_CHAOS_IMAGE), true)
                docker push $(CHAOS_IMAGE)
endif

.PHONY: install_metacontroller
install_metacontroller:
		kubectl create ns metacontroller
		kubectl create -n metacontroller -f torpedo/metacontroller-rbac.yaml
		kubectl create -n metacontroller -f torpedo/install_metacontroller.yaml

.PHONY: install_argo
install_argo:
		kubectl create ns argo
		kubectl create -n argo -f torpedo/install_argo.yaml

.PHONY: install_torpedo_controller
install_torpedo_controller:
		kubectl create configmap torpedo-metacontroller -n metacontroller --from-file=torpedo-metacontroller=torpedo/torpedo_metacontroller.py
		kubectl create -n metacontroller -f torpedo/torpedo-controller.yaml 
		kubectl create -n metacontroller -f torpedo/webhook.yaml
		kubectl create -f torpedo/torpedo_crd.yaml
		kubectl create -f torpedo/controller.yaml
		kubectl create -f torpedo/resiliency_rbac.yaml

.PHONY: clean
clean:
		kubectl delete -f torpedo/torpedo_crd.yaml
		kubectl delete -f torpedo/controller.yaml
		kubectl delete -n metacontroller -f torpedo/metacontroller-rbac.yaml
		kubectl delete -n metacontroller -f torpedo/install_metacontroller.yaml
		kubectl delete -n argo -f torpedo/install_argo.yaml
		kubectl delete -f torpedo/resiliency_rbac.yaml
		kubectl delete configmap torpedo-metacontroller -n metacontroller
		kubectl delete -n metacontroller -f torpedo/torpedo-controller.yaml
		kubectl delete -n metacontroller -f torpedo/webhook.yaml
		kubectl delete ns metacontroller
		kubectl delete ns argo
