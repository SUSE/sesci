#!/bin/bash
set -x

# Job specific variables
TEUTH_NAME=${TEUTH_NAME:-"ci"}
TEUTH_BRANCH=${TEUTH_BRANCH:-"master"}
CEPH_BRANCH=${CEPH_BRANCH:-"ses5"}
TEUTH_PATH=${TEUH_PATH:-"$HOME/teuthology"}
TEUTH_SUITE=${SUITE:-"deepsea:basic:health-ok"}

# Jenkins specific variables
JOB_NAME=${JOB_NAME:-"deepsea-teuthology"}
BUILD_ID=${BUILD_ID:-"0"}
OVH_CONF=${OVH_CONF:-"ovh.net"}

# Clear any old deepsea rpms
rm /var/lib/jenkins/rpmbuild/RPMS/noarch/deepsea*.rpm

# setup
mkdir repo/
make rpm

# copy generated rpms and create a repo
cp /var/lib/jenkins/rpmbuild/RPMS/noarch/deepsea*.rpm repo/
createrepo --repo deespea_testing repo/

# mv where to?
sub_dir=artifacts/jenkins/default/${JOB_NAME/-trigger/}-${BUILD_ID}
path=/mnt/logs/$sub_dir
mkdir -p $path

mv repo/ $path

DEEPSEAREPOURL=http://storage-ci.suse.de/$sub_dir/repo
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
    --teuthology-git-url https://github.com/SUSE/teuthology \
    --teuthology-branch ${TEUTH_BRANCH} \
    --suite-repo http://github.com/SUSE/ceph \
    --suite-branch wip-no-repo-deepsea \
    --ceph-repo http://github.com/SUSE/ceph \
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

