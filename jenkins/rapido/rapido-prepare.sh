#!/bin/bash

KVM_HOST=${KVM_HOST:-localhost}
HOME_PATH=${WORKSPACE:-${PWD}}
DEST_PATH=${DEST_PATH:-"test-iscsi"}
HOST_IMAGE=${HOST_IMAGE:-"opensuse-42.2-x86_64"}
HOST_FLAVOR=${HOST_FLAVOR:-"hg-30-ssd-flex"}
HOST_NAME=${HOST_NAME:-"iscsi"}
SOURCEDIR=$(dirname ${BASH_SOURCE[0]})
TEST_CONF=${TEST_CONF:-"${SOURCEDIR}/conf/default"}

#RAPIDO_REPO=https://gitlab.suse.de/dmdiss/rapido.git
RAPIDO_REPO=https://github.com/ddiss/rapido.git
#KERNEL_REPO=git://kerncvs.suse.de/kernel.git
#KERNEL_REPO=https://github.com/openSUSE/kernel-source
KERNEL_REPO=git://kernel.suse.com/kernel.git

LIBISCSI_REPO=${LIBISCSI_REPO:-https://github.com/sahlberg/libiscsi.git}
XFSTESTS_REPO=${XFSTESTS_REPO:-https://github.com/ddiss/xfstests.git}
CEPH_REPO=${CEPH_REPO:-"https://github.com/SUSE/ceph.git"}

TAP_USER=${USER}
echo ${BASH_SOURCE[0]}

source ${TEST_CONF}

# Cleanup before each round
CPU_THREADS=$(grep -c ^processor /proc/cpuinfo)
CPU_THREADS_MAKE=$(($CPU_THREADS / 2))
echo $HOME_PATH
echo $label_exp
if [ -z $os_version ]; then 
	echo The 'os_version' variable is not set
	echo Available values: openSUSE-42.2, SLE12-SP1, SLE12-SP2
	exit 1
fi
if [ -z $ses_version ]; then 
	echo The 'ses_version' variable is not set
	echo Available values: ses5, ses4
	exit 1
fi
if [ -z $tests ]; then 
	echo The 'tests' variable is not set
	echo Available values: cephfs, iscsi
	exit 1
fi

#[ "${ses_version}" = "ses2" ] && echo SES2 does not support cephfs && exit 1 #and SLE12 then exit directly at the top

test -d ${HOME_PATH} && echo "$HOME_PATH exists" || mkdir -p ${HOME_PATH}
pushd ${HOME_PATH}

SSH=ssh
RSYNC=rsync

if [ "_${SECRET_FILE}" != "_" ] ; then
	SSH="ssh -i ${SECRET_FILE} -o StrictHostKeyChecking=no -l root"
	RSYNC="rsync -e \"ssh -i ${SECRET_FILE} -o StrictHostKeyChecking=no\" -l root"
fi

# check repo rapido master
function git_clone() {
	REPO_URL="$1"
	REPO_HOME="$2"
	REPO_BRANCH=${3:-master}
	REPO_NAME=$(echo $REPO_HOME | sed -r "s/^.*[\/](([^\/]+)\.git|([^\/]+))$/\2\3/g")
	if [ -d $REPO_HOME ]; then
		echo "Switching [$REPO_NAME] to the branch $REPO_BRANCH"
		pushd $REPO_HOME
		git clean -fd
		git checkout $REPO_BRANCH
		git pull
		popd
	else
		echo "Cloning $[REPO_NAME]"
		git clone -b ${REPO_BRANCH} ${REPO_URL} ${REPO_HOME} 
	fi
	pushd $REPO_HOME
	git submodule sync
	git submodule update --force --init --recursive

	TARBALL=${REPO_NAME}.tar.gz
	rm -rf ${HOME_PATH}/${REPO_NAME}.tar.gz
	echo "Archiving [${REPO_NAME}] to home directory [${HOME_PATH}]"
	#git archive -o ${HOME_PATH}/${REPO_NAME}.tar.gz $REPO_BRANCH
	tar czf ${HOME_PATH}/${REPO_NAME}.tar.gz --owner=0 --group=0 --exclude=.git .
	echo "Copying repo [${REPO_NAME}] to host [${KVM_HOST}] to [${DEST_PATH}] directory"
	$SSH ${KVM_HOST} rm -rf ${DEST_PATH}/${REPO_NAME}
	$SSH ${KVM_HOST} mkdir -p ${DEST_PATH}/${REPO_NAME}
	$RSYNC ${HOME_PATH}/${REPO_NAME}.tar.gz ${KVM_HOST}:${DEST_PATH}/
	$SSH $KVM_HOST "(cd $DEST_PATH/${REPO_NAME}; tar xf ../${REPO_NAME}.tar.gz)"
	popd
}


if  [ "${ses_version}" = "ses2" ]; then
	if [ "${tests}" = "cephfs" ]; then
		echo "no support for cephfs in ses2 - skipping..."
		exit 0
	fi
fi


time git_clone ${RAPIDO_REPO} ${HOME_PATH}/rapido
time git_clone ${KERNEL_REPO} ${HOME_PATH}/kernel $os_version
time git_clone ${LIBISCSI_REPO} ${HOME_PATH}/libiscsi
time git_clone ${XFSTESTS_REPO} ${HOME_PATH}/xfstests
time git_clone ${CEPH_REPO} ${HOME_PATH}/ceph $ses_version


