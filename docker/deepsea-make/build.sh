#!/bin/bash -ex
TARGET=${TARGET:-"test"}
DEEPSEADIR=${2:-"deepsea"}
TARGETPATH=$(cd ${1:-"$PWD"}; echo $PWD)
TARGETNAME=${TARGETPATH##*/}
TARGETBASE=${TARGETNAME,,}-deepsea-make
TARGETBUILD=${TARGETBASE}-${TARGET}
echo TARGET PATH=$TARGETPATH
echo TARGET NAME=${TARGETPATH##*/}
export DHOME=${DHOME:-$(cd $(dirname $BASH_SOURCE); echo $PWD)}
echo Docker home: $DHOME

rm -rf ./logs

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
	--build-arg target=$TARGET \
	-t $TARGETBUILD \
	-f $TARGETPATH/Dockerfile-make \
	$TARGETPATH

ID=$(docker create $TARGETBUILD:latest)
echo Use \"docker run -it $TARGETBUILD:latest bash\" command to get into container and look around.
docker cp $ID:/home/jenkins/DeepSea/logs logs
docker rm $ID

find ./logs
