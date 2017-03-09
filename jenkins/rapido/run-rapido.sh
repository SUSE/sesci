#!/bin/bash

HOME_PATH=${WORKSPACE:-${PWD}}

TAP_USER=${USER}

# Cleanup before each round
CPU_THREADS=$(grep -c ^processor /proc/cpuinfo)
CPU_THREADS_MAKE=$(($CPU_THREADS / 2))
echo $HOME_PATH
echo $label_exp
if [ -z $os_version ]; then echo os_version not set && exit 1; fi
if [ -z $ses_version ]; then echo ses_version not set && exit 1; fi
if [ -z $tests ]; then echo tests not set && exit 1; fi

#[ "${ses_version}" = "ses2" ] && echo SES2 does not support cephfs && exit 1 #and SLE12 then exit directly at the top

test -d ${HOME_PATH} && echo "$HOME_PATH exists" || mkdir -p ${HOME_PATH}
pushd ${HOME_PATH}

mkdir -p ${HOME_PATH}/logs

sudo pkill qemu-system-x86 || true

function finish {
	sudo pkill qemu-system-x86 || true
	pushd ${HOME_PATH}/ceph/src
	sh stop.sh  || true
	popd
	#for i in $(btrfs subvolume list -t -a /| grep ${HOME_PATH} | awk '{print $4}' | sed -r 's/@(.*)/\1/g') ; do 
	#    btrfs subvolume delete $i
	#done
	#rm -rf ${HOME_PATH}/ceph/src/dev || true
	exit ${TEST_RESULT}
}


if  [ "${ses_version}" = "ses2" ]; then
	if [ "${tests}" = "cephfs" ]; then
		echo "no support for cephfs in ses2 - skipping..."
		exit 0
	fi
fi

DEPS="libvirt
tunctl
qemu-kvm
bridge-utils-devel
fio
git-core
libacl-devel
libattr-devel
libedit-devel
lttng-modules
lttng-modules-kmp-default
nss_ldap
python3
python3-Cython"

DEPS_LEAP42_2="cunit-devel dbench libcryptopp-devel"

zypper install -y $DEPS
if [ "${os_version}" == "openSUSE-42.2" ]; then
	zypper install -y $DEPS_LEAP42_2
fi
pushd ${HOME_PATH}/ceph
	./install-deps.sh
popd

echo ==== Setup rapido ====
pushd ${HOME_PATH}/rapido
sed -i "s:^[# ]*KERNEL_SRC=.*:KERNEL_SRC=\"${HOME_PATH}/kernel\":g; \
	s:^[# ]*CEPH_SRC=.*:CEPH_SRC=\"${HOME_PATH}/ceph/src\":g; \
	s:^[# ]*TAP_USER=.*:TAP_USER=\"${TAP_USER}\":g; \
	s/^[# ]*MAC_ADDR1=.*/MAC_ADDR1=\"b8:ac:24:45:c6:01\"/g; \
	s/^[# ]*MAC_ADDR2=.*/MAC_ADDR2=\"b8:ac:24:45:c6:02\"/g; \
	s/^[# ]*TARGET_IQN=.*/TARGET_IQN=\"iqn.1996-04.de.suse:rapido\"/g; \
	s:^[# ]*CEPH_RBD_POOL=.*:CEPH_RBD_POOL=\"rbd\":g; \
	s:^[# ]*CEPH_RBD_IMAGE=.*:CEPH_RBD_IMAGE=\"iscsi_test\":g; \
	s:^[# ]*FSTESTS_AUTORUN_CMD=.*:FSTESTS_AUTORUN_CMD=\"./check -g auto; shutdown\":g; \
	s:^[# ]*FSTESTS_DIR=.*:FSTESTS_DIR=\"${HOME_PATH}/xfstests\":g" \
	rapido.conf
if  [ "${os_version}" = "SLE12-SP1" ]; then
	cp kernel/sle12sp1_config ${HOME_PATH}/kernel/.config
elif  [ "${os_version}" = "SLE12-SP2" ]; then
	cp kernel/sle12sp2_config ${HOME_PATH}/kernel/.config
elif  [ "${os_version}" = "openSUSE-42.2" ]; then
	cp kernel/sle12sp2_config ${HOME_PATH}/kernel/.config
else
	cp kernel/vanilla_config ${HOME_PATH}/kernel/.config
fi

sudo tools/br_setup.sh || echo "Failed to configure bridges"

popd

pushd ${HOME_PATH}/kernel

yes "" | make oldconfig
make -j ${CPU_THREADS_MAKE}
INSTALL_MOD_PATH=./mods make modules_install
sudo ln -sf $PWD/mods/lib/modules/$(make kernelrelease) /lib/modules/$(make kernelrelease)
popd


pushd ${HOME_PATH}/ceph
BUILD_HOME=${HOME_PATH}/ceph/src
if [ "_$ses_version" == "_ses5" ] ; then
	BUILD_HOME=${HOME_PATH}/ceph/build
	rm -rf build
	mkdir build
	pushd build
	cmake -DBOOST_J=$(nproc) -DENABLE_GIT_VERSION=false -DWITH_LTTNG=false ..
	# minimal config to find plugins
	cat <<EOF > ceph.conf
plugin dir = lib
erasure code dir = lib
EOF

	# give vstart a (hopefully) unique mon port to start with
	echo $(( RANDOM % 1000 + 40000 )) > .ceph_port

	echo done.
	make -j ${CPU_THREADS_MAKE} tests
	popd
	pushd ${HOME_PATH}/ceph/build
	OSD=3 MON=1 RGW=0 MDS=1 ../src/vstart.sh -i 192.168.155.1 -n
	bin/rbd create iscsi_test --size 5000 --image-format 1
	popd
else
	./autogen.sh
	./configure --without-tcmalloc
	make -j ${CPU_THREADS_MAKE}
	pushd ${HOME_PATH}/ceph/src
	OSD=3 MON=1 RGW=0 MDS=1 ./vstart.sh -i 192.168.155.1 -n
	./rbd create iscsi_test --size 5000 --image-format 1
	popd
fi
#mkdir -p /tmp/ceph || true
#CEPH_OUT_DIR="/tmp/ceph"
popd

case $tests in
cephfs)
	pushd ${HOME_PATH}/xfstests
	make -j ${CPU_THREADS_MAKE}
	sh configure
	popd
	pushd ${HOME_PATH}/rapido
	./cut_fstests_cephfs.sh
	./vm.sh # add a timeout
	TEST_RESULTS=$?
	popd
	;;
iscsi)
	pushd ${HOME_PATH}/libiscsi
	sh autogen.sh
	sh configure
	make -j ${CPU_THREADS_MAKE}
	popd
	#pushd ${HOME_PATH}/ceph/src
	#./rbd create iscsi_test --size 5000 --image-format 1
	#popd
	pushd ${HOME_PATH}/rapido
	sed -i "s:QEMU_EXTRA_ARGS=.*:QEMU_EXTRA_ARGS=\"-display none -daemonize\":g" rapido.conf
	./cut_lio_rbd.sh
	./vm.sh
	./vm.sh
	sleep 60
	pushd ${HOME_PATH}/libiscsi/test-tool/
	# libiscsi test list. CompareAndWrite.Unwritten *must* remain first:
	cat << EOF > tests.txt
ALL.CompareAndWrite.Unwritten
ALL.CompareAndWrite.Simple
ALL.GetLBAStatus.Simple
ALL.OrWrite.Simple
ALL.Prefetch10.Simple
ALL.Prefetch16.Simple
ALL.PreventAllow.Simple
ALL.PrinReadKeys.Simple
ALL.ProutRegister.Simple
ALL.ProutReserve.Simple
ALL.Read6.Simple
ALL.Read10.Simple
ALL.Read12.Simple
ALL.Read16.Simple
ALL.ReadCapacity10.Simple
ALL.ReadCapacity16.Simple
ALL.ReportSupportedOpcodes.Simple
ALL.Reserve6.Simple
ALL.StartStopUnit.Simple
ALL.TestUnitReady.Simple
ALL.Unmap.Simple
ALL.Write10.Simple
ALL.Write12.Simple
ALL.Write16.Simple
ALL.WriteAtomic16.Simple
ALL.WriteSame10.Simple
ALL.WriteSame16.Simple
ALL.WriteSame10.Check
ALL.WriteSame16.Check
ALL.WriteVerify10.Simple
ALL.WriteVerify12.Simple
ALL.WriteVerify16.Simple
ALL.MultipathIO.Simple

ALL.WriteSame16.unmap

ALL.MultipathIO.CompareAndWrite
SCSI.CompareAndWrite.Miscompare
SCSI.MultipathIO.CompareAndWriteAsync

ALL.Reserve6.2Initiators
SCSI.Reserve6.LUNReset
SCSI.ProutReserve.*
ALL.PrinReportCapabilities.Simple
SCSI.ProutClear.Simple

SCSI.READ10.Async
SCSI.Write10.Async

iSCSI.iSCSIcmdsn.iSCSICmdSnTooHigh
iSCSI.iSCSIcmdsn.iSCSICmdSnTooLow

ALL.ExtendedCopy.DescrLimits
ALL.ExtendedCopy.DescrType
ALL.ExtendedCopy.Simple
ALL.ExtendedCopy.ParamHdr
ALL.ExtendedCopy.ValidTgtDescr
#ALL.ExtendedCopy.ValidSegDescr	- LIO advertises SPC3 but behaves like SPC4
#ALL.ReceiveCopyResults.CopyStatus - Not supported by LIO
ALL.ReceiveCopyResults.OpParams
EOF
	for i in `cat tests.txt | grep -v "^#"`; do
		./iscsi-test-cu -V --test="$i" --dataloss \
			iscsi://192.168.155.102:3260/iqn.1996-04.de.suse:rapido/0 \
			iscsi://192.168.155.101:3260/iqn.1996-04.de.suse:rapido/0 2>&1 > ${HOME_PATH}/logs/$i.log || break
		#&> ${HOME}/workspace/storage-cephfs-kernel/$tests.mp.log

	done
	TEST_RESULTS=$?
	# finish cleans up daemonized VMs, etc.
	popd

	;;
*)
	echo "Error.."
	trap finish EXIT
esac


trap finish EXIT


