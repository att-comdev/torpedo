#!/bin/bash

#mkdir -p LOG_DIR
LOG_DIR=$1
if [ ! -d $LOG_DIR ]
then
    mkdir -p $LOG_DIR
fi

PODS=`kubectl get pods -n metacontroller -l resiliency=enabled | grep -i 'completed' | cut -d ' ' -f1 | tr '\r\n' ' '`
if [[ ! -z $PODS ]]
then
    for i in $PODS; do
        `kubectl logs -n metacontroller $i > $LOG_DIR/$i.log`
    done
fi
