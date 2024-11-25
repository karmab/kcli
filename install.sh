#!/bin/bash

# set some printing colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;36m'
NC='\033[0m'

shell=$(basename $SHELL)
packagefound=false
if [ "$(which dnf)" != "" ] ; then
  packagefound=true
  echo -e "${BLUE}Installing using copr package${NC}"
  sudo dnf -y copr enable karmab/kcli
  sudo dnf -y install kcli
  if [ "$?" != "0" ] ; then
    echo -e "${RED}Package installation didnt work${NC}"
    exit 1
  fi
elif [ "$(which apt-get)" != "" ] ; then
  packagefound=true
  echo -e "${BLUE}Installing using deb package${NC}"
  grep -q Pop /etc/lsb-release && EXTRA="distro=ubuntu"
  curl -1sLf https://dl.cloudsmith.io/public/karmab/kcli/cfg/setup/bash.deb.sh | sudo -E $EXTRA bash
  sudo apt-get update 
  sudo apt-get -y install python3-kcli
  if [ "$?" != "0" ] ; then
    echo -e "${RED}Package installation didnt work${NC}"
    exit 1
  fi
fi

if [ "$packagefound" == "true" ] ; then
  echo -e "${GREEN}kcli installed${NC}"
  echo -e "${BLUE}Consider installing completion by following https://kcli.readthedocs.io/#auto-completion${NC}"
  exit 0
fi

engine=""
which docker >/dev/null 2>&1 && engine="docker"
which podman >/dev/null 2>&1 && engine="podman"
if [ "$engine" == "" ] ; then
  echo -e "${BLUE}No container engine found nor compatible package manager. Install podman or docker first${NC}"
  exit 1
else
  echo -e "${BLUE}Using engine $engine ${NC}"
fi

alias kcli >/dev/null 2>&1
ALIAS="$?"

if [ "$ALIAS" != "0" ]; then
  TAG="latest"
  [ "$(uname -m)" == "aarch64" ] && TAG="arm64"
  echo -e "${BLUE}Installing container alias ${NC}"
  $engine pull quay.io/karmab/kcli:$TAG
  SSHVOLUME="-v $(realpath $HOME/.ssh):/root/.ssh"
  if [ -d /var/lib/libvirt/images ] && [ -d /var/run/libvirt ]; then
    VOLUMES="-v /var/lib/libvirt/images:/var/lib/libvirt/images -v /var/run/libvirt:/var/run/libvirt"
  fi
  [ -d $HOME/.kcli ] || mkdir -p $HOME/.kcli
  [ -d $HOME/.ssh  ] || ssh-keygen -t rsa -N '' -f $HOME/.ssh/id_rsa
  echo -e '#/bin/bash\n'$engine run -p 9000:9000 --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir --entrypoint=/usr/local/bin/klist.py quay.io/karmab/kcli' > $HOME/klist.py
case $shell in
bash|zsh)
  shellfile="$HOME/.bashrc"
  [ "$shell" == zsh ] && shellfile="$HOME/.zshrc"
  grep -q kcli= $shellfile || echo alias kcli=\'$engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir' quay.io/karmab/kcli:$TAG\' >> $shellfile
  grep -q kclishell= $shellfile || echo alias kclishell=\'$engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir' --entrypoint=/bin/sh quay.io/karmab/kcli:$TAG\' >> $shellfile
  grep -q kcliweb= $shellfile || echo alias kweb=\'$engine run -p 9000:9000 --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir' --entrypoint=/usr/local/bin/kweb quay.io/karmab/kcli:$TAG\' >> $shellfile
  alias kcli="$engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES -v $PWD:/workdir quay.io/karmab/kcli:$TAG"
  ;;
fish)
  shellfile="$HOME/.config/fish/config.fish"
  [ ! -d ~/.config/fish ] && mkdir -p ~/.config/fish
  grep -q 'kcli ' $shellfile || echo alias kcli $engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir' quay.io/karmab/kcli:$TAG >> $shellfile
  grep -q kclishell $shellfile || echo alias kclishell $engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir' --entrypoint=/bin/sh quay.io/karmab/kcli:$TAG >> $shellfile
  grep -q kcliweb $shellfile || echo alias kweb $engine run -p 9000:9000 --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES '-v $PWD:/workdir' --entrypoint=/usr/local/bin/kweb quay.io/karmab/kcli:$TAG >> $shellfile
  alias kcli $engine run --net host -it --rm --security-opt label=disable -v $HOME/.kcli:/root/.kcli $SSHVOLUME $VOLUMES -v $PWD:/workdir quay.io/karmab/kcli:$TAG
  ;;
*)
  echo -e "${RED}Installing aliases for $shell is not supported ${NC}"
  ;;
esac
  shopt -s expand_aliases
  COMMIT=$(kcli version | sed -n 's/.*commit: \([a-z0-9]\{7\}\).*/\1/p')
  echo -e """${GREEN}Installed kcli $COMMIT
Launch a new shell for aliases kcli, kclishell and kweb to work${NC}"""
else
  echo -e "${BLUE}Skipping already installed kcli${NC}"
fi

if [ "$(id -u)" != "0" ] && [ -d /var/lib/libvirt/images ] && [ -d /var/run/libvirt ]; then
 echo -e """${BLUE}Make sure you have libvirt access from your user by running:
sudo usermod -aG qemu,libvirt $(id -un)
newgrp qemu
newgrp libvirt
sudo setfacl -m u:$(id -un):rwx /var/lib/libvirt/images${NC}"""
fi
