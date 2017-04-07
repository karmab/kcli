echo unix1234 | passwd --stdin root
hostnamectl set-hostname manageiq
source /etc/profile.d/evm.sh
systemctl start evmserverd.service
systemctl enable evmserverd.service
systemctl restart httpd
sleep 60
/var/www/miq/vmdb/bin/rails r /root/password.rb
