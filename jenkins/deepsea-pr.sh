#!/bin/bash

mkdir -p logs

# Job specific variables
TEUTH_NAME=${TEUTH_NAME:-"ci"}
TEUTH_BRANCH=${TEUTH_BRANCH:-"master"}

CEPH_BRANCH=${CEPH_BRANCH:-"ses6"}
SUITE_BRANCH=${SUITE_BRANCH:-"ses6"}

#PRTGT_BRANCH=${ghprbTargetBranch:-"ses5"}
#if [[ "$PRTGT_BRANCH" == "master" ]] ; then
#    CEPH_BRANCH="ses6"
#    SUITE_BRANCH="ses6"
#else
#    CEPH_BRANCH="${PRTGT_BRANCH,,}"
#    SUITE_BRANCH="${PRTGT_BRANCH,,}"
#fi


TEUTH_PATH=${TEUH_PATH:-"$HOME/teuthology"}
TEUTH_SUITE=${SUITE:-"deepsea:basic:health-ok"}
TEUTH_EXTRA=${TEUTH_FILTER:-"--filter sle"}

CEPH_REPO=${CEPH_REPO:-"http://github.com/SUSE/ceph"}
TEUTH_REPO=${TEUTH_REPO:-"http://github.com/SUSE/teuthology"}
SUITE_REPO=${SUITE_REPO:-"http://github.com/SUSE/ceph"}

# Jenkins specific variables
JOB_NAME=${JOB_NAME:-"deepsea-teuthology"}
BUILD_ID=${BUILD_ID:-"0"}
OVH_CONF=${OVH_CONF:-"ovh.net"}
ART_PATH=${ART_PATH:-"deepsea/PR/${JOB_NAME/-trigger/}-${BUILD_ID}"}
PULL_ID=${ghprbPullId:-"0"}

TEUTH_LOG=logs/teuth-deepsea-pr$PULL_ID-b$BUILD_ID.log

echo DeepSea repo: $DEEPSEAREPOURL


# include OVH_CONF
source $OVH_CONF
# include teuthology
echo Home directory: $HOME
source $TEUTH_PATH/v/bin/activate

function print_artifacts() {
    local yaml=$1
    python -c "import sys, yaml ; ars = yaml.load(sys.stdin)['artifacts']
print(' '.join(ars.keys()))" < $yaml
}

function teuth_test_repos() {
    local yaml=${1}
    shift
    local artifacts=${@:-"$(print_artifacts $yaml)"}
    for i in $artifacts ; do
        python -c "import sys, yaml
ars=yaml.load(sys.stdin)['artifacts']
print('--test-repo %s:%s' % ('$i', ars['$i']['url']))" \
< $yaml
    done
}

ARTIFACTS=${ARTIFACTS:-"artifacts:
    $DEEPSEAREPONAME:
        url:$DEEPSEAREPOURL
"}

echo "$ARTIFACTS" > artifacts.yaml

TEST_REPO=$(teuth_test_repos artifacts.yaml)

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
    --name ${TEUTH_NAME} \
    --key-name storage-automation \
    --key-filename $SECRET_FILE \
    --teuthology-git-url ${TEUTH_REPO} \
    --teuthology-branch ${TEUTH_BRANCH} \
    --suite-repo ${SUITE_REPO} \
    --suite-branch ${SUITE_BRANCH} \
    --ceph-repo ${CEPH_REPO} \
    --ceph ${CEPH_BRANCH} \
    --suite ${TEUTH_SUITE} \
    $TEST_REPO \
    $TEUTH_EXTRA \
    $PWD/deepsea-overrides.yaml \
    --wait 2>&1 | tee $TEUTH_LOG

#    --test-repo ses5:http://storage-ci.suse.de/artifacts/13efbdd685728106cb7ca9ec29a967236c402aafbd23efdb98e998df8474f98a/SUSE-Enterprise-Storage-5-POOL-x86_64-Build0609 \
#    --test-repo ses5-internal:http://storage-ci.suse.de/artifacts/941df0216e4adc9eeed1d607bc20bce6dc854255ac346c79301ed2a8de787e98/SUSE-Enterprise-Storage-5-POOL-Internal-x86_64-Build0609 \
    
    # verify if RC is accurate

fails=$(grep -sc 'teuthology.suite:fail' $TEUTH_LOG)
deads=$(grep -sc 'teuthology.suite:dead' $TEUTH_LOG)
passed=$(grep -sc 'teuthology.suite:pass' $TEUTH_LOG)
total=$(grep -sc 'Job scheduled with name' $TEUTH_LOG)
alljobs=$(grep 'Job scheduled with name' $TEUTH_LOG | \
          perl -n -e'/ID ([0-9]+)/ && CORE::say $1')
jobname=$(grep 'Job scheduled with name' $TEUTH_LOG | head -1 | \
          perl -n -e'/name ([^ ]+)/ && CORE::say $1')
teuth=$(grep -m1 'ssh access' $TEUTH_LOG | \
        perl -n -e'/ubuntu@([^ ]+) #/ && CORE::say $1')

function make_teuthology_junit() {
    local logdir=$1
    local junit=${2:-"junit-report.xml"}
    cat > $junit << END
<?xml version="1.0" ?>
<testsuite name="suse.smoke">
END
        for i in $(ls $logdir) ; do
            local summary_yaml=$logdir/$i/summary.yaml
            local config_yaml=$logdir/$i/config.yaml
            local name=$(
                python -c "import sys, yaml ; print(yaml.load(sys.stdin)['description'])" < $config_yaml
            )
            local dura=$(
                python -c "import sys, yaml ; print(yaml.load(sys.stdin)['duration'])" < $summary_yaml || echo "0"
            )
            local tlog=$logdir/teuthology-$i.log
            cp $logdir/$i/teuthology.log $tlog
            cat >> $junit << END
  <testcase classname="teuthology.suse:smoke" name="$name" time="$dura">
    <system-out>[[ATTACHMENT|$tlog]]</system-out>
END
            grep "^success:" $summary_yaml | grep -q "true" || {
                local reason=$(
                    python -c "import sys, yaml ; print(yaml.load(sys.stdin)['failure_reason'])" < $summary_yaml
                )
                cat >> $junit << END
    <failure>$reason</failure>
END
            }
            cat >> $junit << END
  </testcase>
END
        done
        cat >> $junit << END
</testsuite>
END
}

if [[ "x$jobname" == "x" ]] ; then
    echo "ERROR: Can't determine jobname"
    exit 3
else
    mkdir -p logs/$jobname
    scp -r -i $SECRET_FILE -o StrictHostKeyChecking=no ubuntu@$teuth:/usr/share/nginx/html/$jobname/* logs/$jobname || true
    make_teuthology_junit logs/$jobname logs/junit-report.xml
fi

echo PASS: $passed
echo FAIL: $fails
echo DEAD: $deads
echo TOTAL: $total
echo JOBS: $alljobs

[ $((fails + deads)) -eq 0 ] || {
    echo "ERROR: There are failed jobs"
    exit 1
}
[ $((fails + deads + passed)) -gt 0 ] || {
    echo "ERROR: Neither jobs passed, nor failed"
    exit 2
}

