#!/bin/bash

# set some printing colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;36m'
NC='\033[0m'

shell=$(basename $SHELL)
engine="docker"
packagemanager="dnf"
local=false
which podman >/dev/null 2>&1 && engine="podman"
which $engine >/dev/null 2>&1
if [ "$?" != "0" ] ; then
  echo -e "${BLUE}No container engine found. Installing with package manager${NC}"
  if [ $(which dnf) != "" ] ; then 
    sudo dnf -y copr enable karmab/kcli
    sudo dnf -y install kcli
    exit 0
  elif [ $(which apt-get) != "" ] ; then
    curl -s https://packagecloud.io/install/repositories/karmab/kcli/script.deb.sh | sudo bash
    exit 0
  else
    echo -e "${RED}Missing container engine or a compatible package manager(dnf, apt-get). Install podman first${NC}"
    exit 1
  fi
fi
which kcli >/dev/null 2>&1
BIN="$?"
alias kcli >/dev/null 2>&1
ALIAS="$?"

if [ "$BIN" != "0" ] && [ "$ALIAS" != "0" ]; then
  echo -e "${BLUE}Installing as alias for $engine${NC}"
  $engine pull karmab/kcli
  SSHVOLUME="-v $(realpath $HOME/.ssh):/root/.ssh"
  if [ -d /var/lib/libvirt/images ] && [ -d /var/run/libvirt ]; then
      echo -e """${BLUE}Make sure you have libvirt access from your user by running:
sudo usermod -aG qemu,libvirt $(id -un)
newgrp qemu
newgrp libvirt${NC}"""
      VOLUMES="-v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt"
  fi
  [ -d $HOME/.kcli ] || mkdir -p $HOME/.kcli
  echo -e '#/bin/bash\n'$engine run -p 9000:9000 --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/usr/bin/kweb karmab/kcli' > $HOME/klist.py
case $shell in
bash|zsh)
  shellfile="$HOME/.bashrc"
  [ "$shell" == zsh ] && shellfile="$HOME/.zshrc" 
  grep -q kcli= $shellfile || echo alias kcli=\'$engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir -v /var/tmp:/ignitiondir karmab/kcli'\' >> $shellfile
  grep -q kclishell= $shellfile || echo alias kclishell=\'$engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/bin/sh karmab/kcli'\' >> $shellfile
  grep -q kcliweb= $shellfile || echo alias kweb=\'$engine run -p 9000:9000 --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/usr/bin/kweb karmab/kcli'\' >> $shellfile
  alias kcli="$engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES -v $PWD:/workdir -v /var/tmp:/ignitiondir karmab/kcli"
  ;;
fish)
  shellfile="$HOME/.config/fish/config.fish"
  [ ! -d ~/.config/fish ] && mkdir -p ~/.config/fish
  grep -q 'kcli ' $shellfile || echo alias kcli $engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir -v /var/tmp:/ignitiondir karmab/kcli' >> $shellfile
  grep -q kclishell $shellfile || echo alias kclishell $engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/bin/sh karmab/kcli' >> $shellfile
  grep -q kcliweb $shellfile || echo alias kweb $engine run -p 9000:9000 --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir -v /var/tmp:/ignitiondir --entrypoint=/usr/bin/kweb karmab/kcli' >> $shellfile
  alias kcli $engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES -v $PWD:/workdir -v /var/tmp:/ignitiondir karmab/kcli
  ;;
*)
  echo -e "${RED} Installing aliases for $shell is not supported :(${NC}"
  ;;
esac
  shopt -s expand_aliases
  VERSION=$(kcli -v)
  echo -e "${GREEN}Installed kcli $VERSION ${NC}"
  echo -e "${GREEN}Launch a new shell for aliases kcli, kclishell and kweb to work${NC}"
else
  echo -e "${BLUE}Skipping already installed kcli${NC}"
fi
