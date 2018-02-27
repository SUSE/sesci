#!/bin/bash

# Job specific variables
TEUTH_NAME=${TEUTH_NAME:-"ci"}
TEUTH_BRANCH=${TEUTH_BRANCH:-"master"}
PRTGT_BRANCH=${ghprbTargetBranch:-"ses5"}

if [[ "$PRTGT_BRANCH" == "master" ]] ; then
    CEPH_BRANCH="ses6"
    SUITE_BRANCH="ses6"
else
    CEPH_BRANCH="${PRTGT_BRANCH,,}"
    SUITE_BRANCH="${PRTGT_BRANCH,,}"
fi


TEUTH_PATH=${TEUH_PATH:-"$HOME/teuthology"}
TEUTH_SUITE=${SUITE:-"deepsea:basic:health-ok"}

CEPH_REPO=${CEPH_REPO:-"http://github.com/SUSE/ceph"}
TEUTH_REPO=${TEUTH_REPO:-"http://github.com/SUSE/teuthology"}
SUITE_REPO=${SUITE_REPO:-"http://github.com/SUSE/ceph"}

# Jenkins specific variables
JOB_NAME=${JOB_NAME:-"deepsea-teuthology"}
BUILD_ID=${BUILD_ID:-"0"}
OVH_CONF=${OVH_CONF:-"ovh.net"}
ART_PATH=${ART_PATH:-"deepsea/PR/${JOB_NAME/-trigger/}-${BUILD_ID}"}

# Next parameters supposed to be always declared by the Jenkins job.
# The PUBLISH_DIR is used by rpmbuild to copy built rpms for later
# repository creation. The ACCESS_URL is used by teuthology to add
# is a test repo with deepsea artifacts, which will override the once
# in SCC because they have always newer version.
#
# Value examples below:
#
# PUBLISH_DIR   /mnt/logs/artifacts/jenkins/$ART_PATH
# ACCESS_URL    http://storage-ci.suse.de/artifacts/jenkins/$ART_PATH

PUBLISH_DIR=${PUBLISH_DIR:-"/mnt/logs/artifacts/jenkins/$ART_PATH"}
ACCESS_URL=${ACCESS_URL:-"http://storage-ci.suse.de/artifacts/jenkins/$ART_PATH"}

# ------------------------------------------------------------------------------
# BUILD RPMS

# #RPMBUILD=${RPMBUILD:-"/var/lib/jenkins/rpmbuild"}
# #RPMBUILD=${RPMBUILD:-"/var/rpmbuild"}
# RPMBUILD=${RPMBUILD:-"${HOME}/rpmbuild"}
# 
# # Clear any old deepsea rpms
# rm -rf ${RPMBUILD}/RPMS/noarch/deepsea*.rpm
# 
# # setup
# make rpm || {
#     echo "ERROR: Can't build RPMs"
#     exit 1
# }
# 
# # copy generated rpms and create a repo
# 
# mkdir -p $PUBLISH_DIR
# cp ${RPMBUILD}/RPMS/noarch/deepsea*.rpm $PUBLISH_DIR
# createrepo --repo deespea_testing $PUBLISH_DIR


# ==============================================================================
# RUN TEUTHOLOGY TESTS NOW

DEEPSEAREPOURL=$ACCESS_URL

echo DeepSea repo: $DEEPSEAREPOURL


# include OVH_CONF
source $OVH_CONF
# include teuthology
echo Home directory: $HOME
source $TEUTH_PATH/v/bin/activate

# (kyr) Notes: 
# - deepsea does not install deepsea and deepsea-qa packages at the moment,
#   it installs deepsea from source with given git repo and branch,
#   i.e. no hash support yet (maybe ask Nathan for support)
# - we need to use --test-repo, since it is the only way not to build ceph
# - we have following options to make working correctly for PR:
#   > refactor deepsea task to install packages instead of building from git repo
#   > add sha1 hash value to build for particular commit
# - there are failures while trying to install ceph from SCC,
#   probably this is a bug in teuthology images (ask Nathan for support?)
# - this example, uses --wait feature of teuthology-openstack, 
#   it sometimes fails due to socket connect error and probably will
#   continue failing if many jobs scheduled.
# - we can later switch to more advanced job monitory and reporting script,
#   so there are logs fetched as well 
#
cat <<EOF > $PWD/deepsea-overrides.yaml
overrides:
    install:
        ceph:
            packages:
                deb: []
                rpm: []
    deepsea:
        repo: ''

EOF

teuthology-openstack -v \
    --name ci \
    --key-name storage-automation \
    --key-filename $SECRET_FILE \
    --teuthology-git-url ${TEUTH_REPO} \
    --teuthology-branch ${TEUTH_BRANCH} \
    --suite-repo ${SUITE_REPO} \
    --suite-branch ${SUITE_BRANCH} \
    --ceph-repo ${CEPH_REPO} \
    --ceph ${CEPH_BRANCH} \
    --suite ${TEUTH_SUITE} \
    --test-repo deepsea-b$BUILD_ID:$DEEPSEAREPOURL \
    $PWD/deepsea-overrides.yaml \
    --wait 2>&1 | tee teuth-deepsea-b$BUILD_ID.log

#    --test-repo ses5:http://storage-ci.suse.de/artifacts/13efbdd685728106cb7ca9ec29a967236c402aafbd23efdb98e998df8474f98a/SUSE-Enterprise-Storage-5-POOL-x86_64-Build0609 \
#    --test-repo ses5-internal:http://storage-ci.suse.de/artifacts/941df0216e4adc9eeed1d607bc20bce6dc854255ac346c79301ed2a8de787e98/SUSE-Enterprise-Storage-5-POOL-Internal-x86_64-Build0609 \
    
    # verify if RC is accurate

fails=$(grep -sc 'teuthology.suite:fail' teuth-deepsea-b$BUILD_ID.log)
deads=$(grep -sc 'teuthology.suite:dead' teuth-deepsea-b$BUILD_ID.log)
passed=$(grep -sc 'teuthology.suite:pass' teuth-deepsea-b$BUILD_ID.log)

echo PASS: $passed
echo FAIL: $fails
echo DEAD: $deads


[ $((fails + deads)) -eq 0 ] || {
    echo "ERROR: There are failed jobs"
    exit 1
}
[ $((fails + deads + passed)) -gt 0 ] || {
    echo "ERROR: Neither jobs passed, nor failed"
    exit 2
}

