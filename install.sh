#!/bin/bash

# set some printing colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;36m'
NC='\033[0m'

if [ -d /Users ] ; then
    SYSTEM=macosx
else
    SYSTEM=linux
fi

shell=$(basename $SHELL)
engine="docker"
local=false
which podman >/dev/null 2>&1 && engine="podman"
which $engine >/dev/null 2>&1
if [ "$?" != "0" ] ; then
  echo -e "${RED}Missing container engine. Install docker or podman first${NC}"
  exit 1
fi
which kcli >/dev/null 2>&1
BIN="$?"
alias kcli >/dev/null 2>&1
ALIAS="$?"

if [ "$BIN" != "0" ] && [ "$ALIAS" != "0" ]; then
  $engine pull karmab/kcli
  VOLUMES="-v $(realpath $HOME/.ssh):/root/.ssh"
  if [ -d /var/lib/libvirt/images ] && [ -d /var/run/libvirt ]; then
      echo -e """${BLUE}Make sure you have libvirt access from your user:
      sudo usermod -aG qemu,libvirt $(id -un)
      sudo newgrp qemu
      sudo newgrp libvirt${NC}"""
      VOLUMES="-v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt"
  fi
  [ -d $HOME/.kcli ] || mkdir -p $HOME/.kcli
  echo -e '#/bin/bash\n'$engine run -p 9000:9000 --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $VOLUMES '-v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/usr/bin/kweb karmab/kcli' > $HOME/klist.py
case $shell in
bash|zsh)
  shellfile="$HOME/.bashrc"
  [ "$shell" == zsh ] && shellfile="$HOME/.zshrc" 
  grep -q kcli= $shellfile || echo alias kcli=\'$engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $VOLUMES '-v $PWD:/workdir -v /var/tmp:/ignitiondir karmab/kcli'\' >> $shellfile
  alias kcli="$engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $VOLUMES -v $PWD:/workdir -v /var/tmp:/ignitiondir karmab/kcli"
  grep -q kclishell= $shellfile || echo alias kclishell=\'$engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $VOLUMES '-v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/bin/sh karmab/kcli'\' >> $shellfile
  grep -q kcliweb= $shellfile || echo alias kweb=\'$engine run -p 9000:9000 --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $VOLUMES '-v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/usr/bin/kweb karmab/kcli'\' >> $shellfile
  ;;
fish)
  shellfile="$HOME/.config/fish/config.fish"
  [ ! -d ~/.config/fish ] && mkdir -p ~/.config/fish
  grep -q 'kcli ' $shellfile || echo alias kcli $engine 'run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $VOLUMES -v $PWD:/workdir -v /var/tmp:/ignitiondir karmab/kcli' >> $shellfile
  alias kcli "$engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $VOLUMES -v $PWD:/workdir -v /var/tmp:/ignitiondir karmab/kcli"
  grep -q kclishell $shellfile || echo alias kclishell $engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $VOLUMES '-v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/bin/sh karmab/kcli' >> $shellfile
  grep -q kcliweb $shellfile || echo alias kweb $engine run -p 9000:9000 --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $VOLUMES '-v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/usr/bin/kweb karmab/kcli' >> $shellfile
  ;;
*)
  echo -e "${RED}Installing aliases for $shell is not supported :(${NC}"
  ;;
esac
  shopt -s expand_aliases
  VERSION=$(kcli -v)
  echo -e "${GREEN}Installed kcli $VERSION ${NC}"
  echo -e "${GREEN}Launch a new shell for aliases kcli, kclishell and kweb to work ${NC}"
else
  echo -e "${BLUE}Skipping already installed kcli ${NC}"
fi
