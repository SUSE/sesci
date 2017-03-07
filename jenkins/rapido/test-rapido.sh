#!/bin/bash

SOURCEDIR=$(dirname ${BASH_SOURCE[0]})
. ${SOURCEDIR}/rapido-prepare.sh

scp ${SOURCEDIR}/run-rapido.sh ${KVM_HOST}:$DEST_PATH/
scp ${TEST_CONF} ${KVM_HOST}:$DEST_PATH/rapido-test-config
ssh ${KVM_HOST} "(cd $DEST_PATH ; source rapido-test-config ; bash -ex run-rapido.sh)"


