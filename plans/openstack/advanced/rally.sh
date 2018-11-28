###Rally
source ~/keystonerc_testk
openstack project create rally_project
for i in 1 2 3
do
openstack user create --project rally_project --password {{ password }} test${i}
done
openstack image delete cirros
glance image-create --name "cirros" --disk-format qcow2 --container-format bare --visibility public --file cirros-0.3.4-x86_64-disk.img
wget -q -O- https://raw.githubusercontent.com/openstack/rally/master/install_rally.sh > ~/install_rally.sh
chmod +x ~/install_rally.sh
sed -i "s#\$OS_AUTH_URL#${OS_AUTH_URL}#g" /root/existing_with_predefined_users.json
yum install redhat-lsb-core -y
curl "https://bootstrap.pypa.io/get-pip.py" -o "/root/get-pip.py"
python /root/get-pip.py
~/install_rally.sh --target /opt/rally -y
source /opt/rally/bin/activate
rally  deployment create --filename /root/existing_with_predefined_users.json --name cloud_rally
rally task start --abort-on-sla-failure /root/rally_tasks.yaml
rally task report --out=/root/cloud_rally_report.html
