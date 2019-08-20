#!/bin/bash
### BEGIN OF FILE snippets/mkck-target-properties.bash ###

export CEPH_BRANCH=${ghprbTargetBranch:-"$CEPH_BRANCH"}
export CEPH_REF=${sha1:-"$CEPH_REF"}
export tgt=${ghprbTargetBranch:-"$CEPH_BRANCH"}

sles_ses6="sle15_sp1"
sles_ses5="sle12_sp3"
sles_ses4="sle12_sp2"
sles_master="sle12_sp3"
leap_ses6="leap15_1"
leap_ses5="leap42_3"
leap_ses4="leap42_2"
leap_luminous="leap42_3"
leap_mimic="leap15_0"
leap_nautilus="leap15_1"
leap_octopus="leap15_1"
leap_master="leap15_1"
tumbleweed_master="tumbleweed"
conf_sles_ses6="makecheck-sle-15.1"
conf_sles_ses5="makecheck-sle-12.3"
conf_sles_ses4="makecheck-sle-12.2"
conf_sles_master="makecheck-sle-15.1"
conf_leap_ses6="makecheck-opensuse-15.1"
conf_leap_ses5="makecheck-opensuse-42.3"
conf_leap_ses4="makecheck-opensuse-42.2"
conf_leap_luminous="makecheck-opensuse-42.3"
conf_leap_mimic="makecheck-opensuse-15.0"
conf_leap_nautilus="makecheck-opensuse-15.1"
conf_leap_octopus="makecheck-opensuse-15.1"
conf_leap_master="makecheck-opensuse-15.1"
conf_tumbleweed_master="makecheck-opensuse-tumbleweed"

eval "export dst=\$${DIST}_${tgt}"
eval "export cfg=\$conf_${DIST}_${tgt}"

echo TARGET_IMAGE=${!dst}   > target.properties
echo TARGET_MASK=$JOB_NAME-$BUILD_NUMBER \
                     >> target.properties
echo DIST=${dst}           >> target.properties
echo CONF=${cfg}           >> target.properties
echo PR=PR#${PR}              >> target.properties
echo CEPH_REF=${CEPH_REF}           >> target.properties
echo CEPH_BRANCH=${CEPH_BRANCH}     >> target.properties
echo CEPH_REPO_URL=${CEPH_REPO_URL} >> target.properties
cat target.properties

### END OF FILE snippets/mkck-target-properties.bash ###
