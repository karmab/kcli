yum -y install rhevm-setup wget
wget -O /root/answers.txt https://raw.githubusercontent.com/karmab/kcli/master/plans/ovirt/answers.txt
sed -i "s/0000/`hostname -s`/" /root/answers.txt
service iptables stop
chkconfig iptables off
engine-setup --config-append=/root/answers.txt
