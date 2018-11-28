setenforce 0 
sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
echo options kvm_intel nested=1 > /etc/modprobe.d/kvm.conf
yum -y install make git docker vim golang-bin
mkdir -p ~/.vim/autoload ~/.vim/bundle
curl -LSso ~/.vim/autoload/pathogen.vim https://tpo.pe/pathogen.vim
git clone https://github.com/fatih/vim-go.git ~/.vim/bundle/vim-go
echo 'execute pathogen#infect()' >> ~/.vimrc
systemctl start docker
systemctl enable docker
cd /root
git clone https://github.com/karmab/kubevirt
cd kubevirt
git remote add upstream https://github.com/kubevirt/kubevirt
git config --global user.name {{ github_user }}
git config --global user.email {{ github_mail }}
export KUBEVIRT_PROVIDER=k8s-1.11.0
make cluster-up
make cluster-sync
