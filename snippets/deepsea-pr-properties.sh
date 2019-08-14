### BEGIN OF FILE snippets/deepsea-pr-properties.sh ###

PRTGT_BRANCH=${ghprbTargetBranch:-"ses5"}
if [[ "$PRTGT_BRANCH" == "master" ]] ; then
    CEPH_BRANCH="ses6"
    SUITE_BRANCH="ses6-deepsea-pr"
    SUITE="deepsea:tier2"
else
    CEPH_BRANCH="${PRTGT_BRANCH,,}"
    SUITE_BRANCH="${PRTGT_BRANCH,,}-deepsea-pr"
    SUITE="deepsea:tier2"
fi

parse_comment "$ghprbCommentBody"

cat > deepsea-pr.properties << EOF
PUBLISH_DIR=/mnt/logs/artifacts/jenkins/deepsea-pr/${SUITE}/${BUILD_ID}
DEEPSEA_REPO=http://10.86.0.120/artifacts/jenkins/deepsea-pr/${SUITE}/${BUILD_ID}
CEPH_BRANCH=${CEPH_BRANCH}
SUITE_BRANCH=${SUITE_BRANCH}
SUITE_REPO=${SUITE_REPO}
SUITE=${SUITE}
EOF

### END OF FILE snippets/deepsea-pr-properties.sh ###
