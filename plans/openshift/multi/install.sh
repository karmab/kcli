#!/bin/bash
sleep 360
[% if upstream %]
yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
sed -i -e "s/^enabled=1/enabled=0/" /etc/yum.repos.d/epel.repo
yum -y --enablerepo=epel  install ansible openshift-ansible-playbooks git
export PLAYBOOKS=/root
cd /root
git clone https://github.com/openshift/openshift-ansible
cd openshift-ansible
git checkout remotes/origin/release-[[ openshift_version ]]
[% else  %]
yum -y install ansible openshift-ansible-playbooks
export PLAYBOOKS=/usr/share/ansible
[% endif  %]
[% if masters > 1 %]
ssh-keyscan -H lb.[[ domain ]] >> ~/.ssh/known_hosts
[% endif %]
[% for master in range(0, masters) %]
ssh-keyscan -H master0[[ master + 1 ]].[[ domain ]] >> ~/.ssh/known_hosts
[% endfor %]
[% for node in range(0, nodes) %]
ssh-keyscan -H node0[[ node + 1 ]].[[ domain ]] >> ~/.ssh/known_hosts
[% endfor %]
export IP=`dig +short node01.[[ domain ]]`
sed -i "s/#log_path/log_path/" /etc/ansible/ansible.cfg
sed -i "s/openshift_master_default_subdomain=.*/openshift_master_default_subdomain=$IP.xip.io/" /root/hosts
[% if deploy %]
ansible-playbook -i /root/hosts $PLAYBOOKS/openshift-ansible/playbooks/byo/config.yml
[% for master in range(0, masters) %]
ssh master0[[ master + 1 ]].[[ domain ]] "htpasswd -b /etc/origin/master/htpasswd [[ user ]] [[ password ]]"
[% endfor %]
[% if nfs %]
for i in `seq -f "%03g" 1 20` ; do
sed "s/001/$i/" /root/nfs.yml | oc create -f -
done
[% endif %]
[% else %]
echo ansible-playbook -i /root/hosts /usr/share/ansible/openshift-ansible/playbooks/byo/config.yml >> /root/install2.sh
[% for master in range(0, masters) %]
echo ssh master0[[ master + 1 ]].[[ domain ]] "htpasswd -b /etc/origin/master/htpasswd [[ user ]] [[ password ]]" >> /root/install2.sh
[% endfor %]
[% if nfs %]
for i in `seq -f "%03g" 1 20` ; do
echo sed "s/001/$i/" /root/nfs.yml | oc create -f - >> /root/install2.sh
done
[% endif %]
[% endif %]
