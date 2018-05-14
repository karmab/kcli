yum -y install NetworkManager 
systemctl enable NetworkManager
systemctl start NetworkManager
yum -y update
reboot
