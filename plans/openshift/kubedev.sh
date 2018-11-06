setenforce 0 
sed -i "s/SELINUX=enforcing/SELINUX=permissive/" /etc/selinux/config
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
make cluster-up
make cluster-sync
