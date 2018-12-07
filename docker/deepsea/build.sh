#!/bin/bash -ex
DEEPSEADIR=${2:-"deepsea"}
TARGETPATH=$(cd ${1:-"$PWD"}; echo $PWD)
TARGETNAME=${TARGETPATH##*/}
TARGETBASE=${TARGETNAME,,}
TARGETBUILD=${TARGETBASE}-rpm
echo TARGET PATH=$TARGETPATH
echo TARGET NAME=${TARGETPATH##*/}
export DHOME=${DHOME:-$(cd $(dirname $BASH_SOURCE); echo $PWD)}
echo Docker home: $DHOME

[[ -d ${DEEPSEADIR} ]] ||
    git clone https://github.com/SUSE/DeepSea.git deepsea

BASEIMAGE=$(grep FROM $TARGETPATH/Dockerfile-base | grep -v '^\s*#' | cut -d ' ' -f 2)

docker pull $BASEIMAGE

docker build \
	-t $TARGETBASE \
	-f $TARGETPATH/Dockerfile-base \
	$TARGETPATH

[[ "$PWD" == "$TARGETPATH" ]] || {
    rm -rf $TARGETPATH/deepsea
    cp -a $DEEPSEADIR $TARGETPATH/deepsea
}

docker build \
	--no-cache \
	-t $TARGETBUILD \
	-f $TARGETPATH/Dockerfile-rpm \
	$TARGETPATH

rm -rf ./repo

#docker run -v $(pwd):/mnt $TARGETBUILD:latest sh -c 'mkdir -p /mnt/repo && cp -a rpmbuild/RPMS/* /mnt/repo'
ID=$(docker create $TARGETBUILD:latest)
docker cp $ID:/home/jenkins/rpmbuild/RPMS repo
docker rm $ID

find ./repo
