yum -y install httpd xinetd syslinux tftp-server wget
wget http://repo.nixval.com/CentOS/7/isos/x86_64/CentOS-7-x86_64-Minimal-1804.iso
mount -o loop CentOS-7-x86_64-Minimal-1804.iso /mnt/
cp -a /mnt/* /var/www/html
cp /root/ks.cfg /var/www/html
chmod -R 755 /var/www/html
setenforce 0
cp -a /usr/share/syslinux/* /var/lib/tftpboot/
mkdir /var/lib/tftpboot/centos7
cp /mnt/images/pxeboot/vmlinuz  /var/lib/tftpboot/centos7
cp /mnt/images/pxeboot/initrd.img  /var/lib/tftpboot/centos7
mkdir /var/lib/tftpboot/pxelinux.cfg
cp /root/pxeserver_default /var/lib/tftpboot/pxelinux.cfg/default
chmod 777 /var/lib/tftpboot/pxelinux.cfg/default
sed -i "s/disable.*/disable = no/" /etc/xinetd.d/tftp
systemctl restart xinetd
systemctl restart httpd
systemctl enable xinetd
systemctl enable httpd

