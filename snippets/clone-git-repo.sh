#!/bin/bash -ex
# jenkins style sha1 pull request checkout

REPO_PATH=${1:-"."}
REPO_URL=${2:-"https://github.com/suse/ceph"}
REPO_BRANCH=${3:-"master"}

mkdir -p $REPO_PATH
git init $REPO_PATH

pushd $REPO_PATH

echo Fetch upstream changes from $REPO_URL
git fetch --tags --progress $REPO_URL +refs/heads/*:refs/remotes/origin/*
git config remote.origin.url $REPO_URL
git config --add remote.origin.fetch +refs/heads/*:refs/remotes/origin/*
git config remote.origin.url $REPO_URL

# Check if branch has form origin/pr/*/merge
isPR="^origin\/pr\/"
if [[ "$REPO_BRANCH" =~ $isPR ]] ; then
    git fetch --tags --progress $REPO_URL +refs/pull/*:refs/remotes/origin/pr/*
    rev=$(git rev-parse refs/remotes/$REPO_BRANCH^{commit})

    git config core.sparseCheckout true
    git checkout -f $rev
else
    git checkout $REPO_BRANCH
fi

popd

