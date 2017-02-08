export PASSWORD="unix1234"
export DOMAIN="UX.LOCAL"
echo `hostname -I` `hostname -s`.ux.local `hostname -s` >> /etc/hosts
echo `hostname -s`.ux.local > /etc/hostname
yum -y install freeipa-server bind bind-dyndb-ldap ipa-server-dns
ipa-server-install  --unattended --setup-dns --forwarder 8.8.8.8 --auto-reverse --ip-address `hostname -I` --hostname=`hostname` -a $PASSWORD -n $DOMAIN -p $PASSWORD  -r $DOMAIN --idstart=8000 --idmax=10000
