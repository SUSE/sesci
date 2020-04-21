#!/bin/bash

mkdir -p logs

export SOURCEPATH=$(cd $(dirname $BASH_SOURCE)/..; echo $PWD)
source $SOURCEPATH/common/util
source $SOURCEPATH/common/teuthology

# Job specific variables
TEUTH_NAME=${TEUTH_NAME:-"ci"}
TEUTH_HOST=${TEUTH_HOST:-"teuth-ses.prv.suse.net"}
TEUTH_ARCHIVE_PATH="/home/worker/archive"
TEUTH_ARCHIVE_USER=worker
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

TEUTH_FILTER=${TEUTH_FILTER:-"--filter sle"}
TEUTH_KERNEL=${TEUTH_KERNEL:-"--kernel none"}
TEUTH_MACHINE_TYPE=${TEUTH_MACHINE_TYPE:-"ovh"}

CEPH_REPO=${CEPH_REPO:-"http://github.com/SUSE/ceph"}
TEUTH_REPO=${TEUTH_REPO:-"http://github.com/SUSE/teuthology"}
SUITE_REPO=${SUITE_REPO:-"http://github.com/SUSE/ceph"}

# Jenkins specific variables
JOB_NAME=${JOB_NAME:-"deepsea-teuthology"}
BUILD_ID=${BUILD_ID:-"0"}
#OVH_CONF=${OVH_CONF:-"ovh.net"}
PULL_ID=${ghprbPullId:-"0"}

TEUTH_LOG=logs/teuth-deepsea-pr$PULL_ID-b$BUILD_ID.log

echo DeepSea repo: $DEEPSEAREPOURL


# include OVH_CONF
# source $OVH_CONF

# include teuthology
echo Home directory: $HOME
source $TEUTH_PATH/v/bin/activate

function teuth_append_artifacts_to_overrides_install_repos() {
    local yaml=${1}
    shift
    python $SOURCEPATH/snippets/append-artifacts.py $yaml $@
    cat $yaml
}

function artifacts_to_repos() {
    python $SOURCEPATH/snippets/artifacts-to-repos.py $@
}

# Copy yaml data from source yaml to destination yaml by key path.
# Print result to standard output.
#
# Argument
# $1    file path to destination yaml data
# $2    ":" separated key sequence, location where to copy data
#       in the destination yaml
# $3    file path to source yaml data
# $4    (optional) ":" separated key sequence, location where from
#       the source yaml to copy data, root if ignored.
function _copy_yaml() {
    python $SOURCEPATH/snippets/copy_yaml.py $@
}

TEUTH_OVERRIDES=overrides-$JOB_NAME-$BUILD_NUMBER.yaml

tee $PWD/deepsea-overrides.yaml << EOF
overrides:
  install:
    ceph:
        packages:
            deb: []
            rpm: []
  deepsea:
    install: package
    repo: ''
  ceph:
    conf:
      global:
        osd heartbeat grace: 100
        # this line to address issue #1017
        mon lease: 15
        mon lease ack timeout: 25
  s3tests:
    idle_timeout: 1200
  ceph-fuse:
    client.0:
       mount_wait: 60
       mount_timeout: 120
archive-on-error: true

EOF

export TEUTH_REPO_YAML=deepsea-teuthology-repos.yaml

for r in teuth-repos-*.yaml ; do
   test -f $r && {
       echo Found repo file $r
   }
   cat $r >> $TEUTH_REPO_YAML
done

test -f artifacts-$CEPH_BRANCH.yaml && {
    echo Found artifact file artifacts-$CEPH_BRANCH.yaml
    artifacts_to_repos artifacts-$CEPH_BRANCH.yaml >> $TEUTH_REPO_YAML
} || {
    if [[ "x$ARTIFACTS" != "x" ]] ; then
        echo "$ARTIFACTS" > artifacts.yaml
        artifacts_to_repos artifacts.yaml >> $TEUTH_REPO_YAML
    fi
}
if [[ "x$DEEPSEA_REPO" != "x" ]] ; then
    cat <<EOF > $PWD/artifacts-deepsea-repo.yaml
artifacts:
    deepsea!1:
        url: "$DEEPSEA_REPO"
EOF
    artifacts_to_repos artifacts-deepsea-repo.yaml >> $TEUTH_REPO_YAML
fi


_copy_yaml $PWD/deepsea-overrides.yaml overrides:install:repos \
       $TEUTH_REPO_YAML | tee $TEUTH_OVERRIDES


scp -i $SECRET_FILE -o StrictHostKeyChecking=no $TEUTH_OVERRIDES runner@$TEUTH_HOST:
ssh -i $SECRET_FILE -o StrictHostKeyChecking=no runner@$TEUTH_HOST "
[[ -f .profile ]]           && source .profile
[[ -f .bashrc_teuthology ]] && source .bashrc_teuthology
teuthology-suite -v \
    --machine-type $TEUTH_MACHINE_TYPE \
    --suite-repo ${SUITE_REPO} \
    --suite-branch ${SUITE_BRANCH} \
    --ceph-repo ${CEPH_REPO} \
    --ceph ${CEPH_BRANCH} \
    --suite ${TEUTH_SUITE} \
    $TEUTH_FILTER \
    $TEUTH_KERNEL \
    \$PWD/${TEUTH_OVERRIDES##*/} \
    --wait 2>&1" | tee $TEUTH_LOG


fails=$(grep -sc 'teuthology.suite:fail' $TEUTH_LOG)
deads=$(grep -sc 'teuthology.suite:dead' $TEUTH_LOG)
passed=$(grep -sc 'teuthology.suite:pass' $TEUTH_LOG)
total=$(grep -sc 'Job scheduled with name' $TEUTH_LOG)
alljobs=$(grep 'Job scheduled with name' $TEUTH_LOG | \
          perl -n -e'/ID ([0-9]+)/ && CORE::say $1')
jobname=$(grep 'Job scheduled with name' $TEUTH_LOG | head -1 | \
          perl -n -e'/name ([^ ]+)/ && CORE::say $1')
#teuth=$(grep -m1 'ssh access' $TEUTH_LOG | \
#        perl -n -e'/ubuntu@([^ ]+) #/ && CORE::say $1')
teuth=$TEUTH_HOST

runname=$jobname
runurl=http://$teuth:8081/$runname
echo "Run summary: suite=$TEUTH_SUITE|name=$runname|url=$runurl"

function make_message() {
    local logdir=$1
    local message=$2
    for i in $(ls $logdir) ; do
        local summary_yaml=$logdir/$i/summary.yaml
        local info_yaml=$logdir/$i/info.yaml
        local name=$(
            python -c "import sys, yaml ; print(yaml.load(sys.stdin)['description'])" < $info_yaml
        )
        name=${name/"$class"\//}
        local dura=$(
            python -c "import sys, yaml ; print(yaml.load(sys.stdin)['duration'])" < $summary_yaml || echo "0"
        )
        local tlog=$logdir/teuthology-$i.log
        cp $logdir/$i/teuthology.log $tlog
        grep "^success:" $summary_yaml | grep -q "true" || {
            local reason=$(
                python -c "import sys, yaml ; from xml.dom.minidom import Text ; \
                    t = Text() ; t.data = yaml.load(sys.stdin)['failure_reason'] ; \
                    print(t.toxml())" < $summary_yaml
            )
            cat >> $junit << END
$(make_brief_deepsea_report $logdir/$i/teuthology.log | to_xml)
END
        }
    done
}

function make_teuthology_html() {
    local logdir=$1
    local report=${2:-"teuthology-report.html"}
    local suite=${3:-"teuthology"}
    local class="teuthology.${suite//[:\/]/\.}"
    cat > $report << END
<html>
<body>
END
    [[ "$ghprbPullLink" == "" ]] || {
        cat > $report << END
<p>$ghprbPullLink</p><br/>
END
    }
    cat > $report << END
Results for run <a href="$runurl">$runname</a>
<table>
<thead>
<tr><th>NAME</th><th>TIME</th><th>STATUS</th></tr>
</thead>
END
        for i in $(ls $logdir) ; do
            local summary_yaml=$logdir/$i/summary.yaml
            local info_yaml=$logdir/$i/info.yaml
            local name=$(
                python -c "import sys, yaml ; print(yaml.load(sys.stdin)['description'])" < $info_yaml
            )
            local dura=$(
                python -c "import sys, yaml ; print(yaml.load(sys.stdin)['duration'])" < $summary_yaml || echo "0"
            )
            local tlog="../$logdir/$i/teuthology.log"
            cat >> $report << END
  <tr>
    <td>$name</td>
    <td>$dura</td>
END
            grep "^success:" $summary_yaml | grep -q "true" && {
                cat >> $report << END
    <td><a href="$tlog" style="text-decoration: none; color: green">passed</a></td>
END
            } || {
                local reason=$(
                    python -c "import sys, yaml ; print(yaml.load(sys.stdin)['failure_reason'])" < $summary_yaml
                )
                cat >> $report << END
    <td><a href="$tlog" style="text-decoration: none; color: red" title="$reason">failed</a></td>
END
            }
            cat >> $report << END
  </tr>
END
        done
        cat >> $report << END
</table>
</body>
</html>
END
}

make_github_report() {
    local logdir=$1
    local report=${2:-"report.txt"}
    cat > $report << END
Results for [teuthology ${TEUTH_SUITE} suite run]($runurl)
Run name: $runname
---

END
        for i in $(ls $logdir) ; do
            local summary_yaml=$logdir/$i/summary.yaml
            local info_yaml=$logdir/$i/info.yaml
            local name=$(
                python -c "import sys, yaml ; print(yaml.load(sys.stdin)['description'])" < $info_yaml
            )
            local dura=$(
                python -c "import sys, yaml ; print(yaml.load(sys.stdin)['duration'])" < $summary_yaml || echo "0"
            )
            (grep "^success:" $summary_yaml | grep -q "true") && {
                cat >> $report << END
- _PASSED_ - $name :+1:
END
            } || {
                local reason=$(
                    python -c "import sys, yaml ; print(yaml.load(sys.stdin)['failure_reason'])" < $summary_yaml
                )
                cat >> $report << END
- _**FAILED**_ - $name :hankey:
END
                if [[ "$reason" != "" ]] ; then
                cat >> $report << END
\`\`\`
$reason
\`\`\`
END
                fi
            }
        done
}

if [[ "x$jobname" == "x" ]] ; then
    echo "ERROR: Can't determine jobname"
    cat > logs/report.txt << EOF
Can't determine teuthology job name
EOF
    exit 3
else
    mkdir -p logs/$jobname
    scp -r -i $SECRET_FILE -o StrictHostKeyChecking=no $TEUTH_ARCHIVE_USER@$teuth:$TEUTH_ARCHIVE_PATH/$jobname/* logs/$jobname || true
    HTML_REPORT=teuthology-${TEUTH_SUITE//\//\:}
    make_github_report logs/$jobname logs/report.txt
    make_teuthology_html logs/$jobname logs/$HTML_REPORT
    (cd logs ; ln -s $HTML_REPORT teuthology-report.html)
    make_teuthology_junit logs/$jobname logs/junit-report.xml $TEUTH_SUITE "teuthology.${TEUTH_SUITE//[:\/]/\:}"
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

