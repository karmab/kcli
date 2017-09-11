sed -i "s/MYIP/`hostname -I`/" /root/installer.cfg.yml
sed -i "s/MYIP/`hostname -I`/" /root/hosts
atomic-openshift-installer -u -c /root/installer.cfg.yml install
