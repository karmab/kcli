yum -y install httpd xinetd syslinux tftp-server wget
wget -O distro.iso [[ url ]]
mount -o loop distro.iso /mnt/
cp -a /mnt/* /var/www/html
cp /root/default.ks /var/www/html
chmod -R 755 /var/www/html
setenforce 0
cp -a /usr/share/syslinux/* /var/lib/tftpboot/
mkdir /var/lib/tftpboot/distro
cp /mnt/images/pxeboot/vmlinuz  /var/lib/tftpboot/distro
cp /mnt/images/pxeboot/initrd.img  /var/lib/tftpboot/distro
mkdir /var/lib/tftpboot/pxelinux.cfg
cp /root/default.pxe /var/lib/tftpboot/pxelinux.cfg/default
chmod 777 /var/lib/tftpboot/pxelinux.cfg/default
sed -i "s/disable.*/disable = no/" /etc/xinetd.d/tftp
systemctl restart xinetd
systemctl restart httpd
systemctl enable xinetd
systemctl enable httpd
