echo unix1234 | passwd --stdin root
source /etc/profile.d/evm.sh
appliance_console_cli --host=cloudforms --region=01 --internal --password="unix1234" --key --force-key
sleep 60
/var/www/miq/vmdb/bin/rails r /root/password.rb
