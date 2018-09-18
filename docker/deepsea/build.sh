#!/bin/bash -ex
TARGETPATH=$(cd ${1:-"$PWD"}; echo $PWD)
TARGETNAME=${TARGETPATH##*/}
TARGETBASE=${TARGETNAME,,}
TARGETBUILD=${TARGETBASE}-rpm
echo TARGET PATH=$TARGETPATH
echo TARGET NAME=${TARGETPATH##*/}
export DHOME=${DHOME:-$(cd $(dirname $BASH_SOURCE); echo $PWD)}
echo Docker home: $DHOME

[[ -d deepsea ]] ||
    git clone https://github.com/SUSE/DeepSea.git deepsea

BASEIMAGE=$(grep FROM $TARGETPATH/Dockerfile-base | cut -d ' ' -f 2)

docker pull $BASEIMAGE

docker build \
	-t $TARGETBASE \
	-f $TARGETPATH/Dockerfile-base \
	$TARGETPATH

[[ "$PWD" == "$TARGETPATH" ]] || {
    rm -rf $TARGETPATH/deepsea
    cp -a deepsea $TARGETPATH
}

docker build \
	--no-cache \
	-t $TARGETBUILD \
	-f $TARGETPATH/Dockerfile-rpm \
	$TARGETPATH

rm -rf ./repo
docker run -v $(pwd):/mnt $TARGETBUILD:latest sh -c 'mkdir -p /mnt/repo && cp -a rpmbuild/RPMS/* /mnt/repo'
test -d ./repo
echo "New deepsea RPMs in ./repo"
find ./repo
