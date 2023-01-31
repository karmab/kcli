{% if ubuntu %} 
apt-get -y install nfs-kernel-server
{% else %}
dnf -y install nfs-utils
{% endif %}
for i in `seq -f "%03g" 1 20` ; do
mkdir /pv${i}
echo "/pv$i *(rw,no_root_squash)"  >>  /etc/exports
chcon -t svirt_sandbox_file_t /pv${i}
chmod 777 /pv${i}
done
exportfs -r
systemctl start nfs-server ; systemctl enable nfs-server
{% if ctlplanes > 1 %}
IP="{{ api_ip }}"
{% else %}
IP=$(hostname -I | cut -d" " -f1)
{% endif%}
sed -i "s/IP/$IP/" /root/nfs.yml
for i in `seq 1 20` ; do j=`printf "%03d" ${i}` ; sed "s/001/$j/" /root/nfs.yml | kubectl create -f - ; done
