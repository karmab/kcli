yum --nogpgcheck -y install ovirt-engine wget
wget -O /root/answers.txt https://raw.githubusercontent.com/karmab/kcli/master/plans/ovirt/answers.txt
sed -i "s/0000/`hostname -s`.default/" /root/answers.txt
yum -y install rng-tools
sed -i 's@ExecStart=.*@ExecStart=/sbin/rngd -f -r /dev/urandom@' /usr/lib/systemd/system/rngd.service
systemctl start rngd
engine-setup --config-append=/root/answers.txt
