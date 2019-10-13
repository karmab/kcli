#!/bin/bash

# set some printing colors
RED='\033[0;31m'
BLUE='\033[0;36m'
NC='\033[0m'

if [ -d /Users ] ; then
    SYSTEM=macosx
else
    SYSTEM=linux
fi

SHELLFILE="~/.bashrc"
engine="docker"
which -s podman && engine="podman"
which -s kcli
BIN="$?"
alias kcli >/dev/null 2>&1
ALIAS="$?"

if [ "$BIN" != "0" ] && [ "$ALIAS" != "0" ]; then
  VOLUMES=""
  [ -d /var/lib/libvirt/images ] && [ -d /var/run/libvirt ] && VOLUMES="-v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt"
  [ -d $HOME/.kcli ] || mkdir -p $HOME/.kcli
  echo alias kcli=\'$engine 'run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $VOLUMES -v $PWD:/workdir -v /var/tmp:/ignitiondir karmab/kcli'\' >> $SHELLFILE
  alias kcli="$engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $VOLUMES -v $PWD:/workdir -v /var/tmp:/ignitiondir karmab/kcli"
  echo alias kclishell=\'$engine 'run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $VOLUMES -v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/bin/bash karmab/kcli'\' >> $SHELLFILE
  echo alias kweb=\'$engine 'run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $VOLUMES -v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/usr/bin/kweb karmab/kcli'\' >> $SHELLFILE
  shopt -s expand_aliases
  VERSION=$(kcli -v)
  echo "${RED}Installed kcli $VERSION${NC}"
else
  echo -e "${BLUE}Skipping already installed kcli${NC}"
fi
