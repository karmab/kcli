url="https://[[ host ]]/ovirt-engine/api"
user="[[ user ]]"
password="[[password ]]"
tag="plan_[[ plan ]]"

VMIDS=`curl -sk -H "Accept: application/xml" -u  "${user}:${password}" "${url}/vms?search=tag=${tag}" | grep '<vm href=' | sed 's/.*id="\(.*\).*">/\1/'`

for vmid in $VMIDS ; do
  name=`curl -sk -H "Accept: application/xml" -u  "${user}:${password}" "${url}/vms/${vmid}" |  grep -m1 '<name>'| sed 's@.*<name>\(.*\)</name>@\1@'`
  ip=`curl -sk -H "Accept: application/xml" -u  "${user}:${password}" "${url}/vms/${vmid}/reporteddevices" | grep -m1 address | sed 's@.*<address>\(.*\)</address>@\1@'`
  echo "Substituting ${name} for ${ip} in inventory"
  sed -i "s/${name}.[[ domain ]]/${ip}.xip.io/" /root/inventory
  echo ${name} | grep -q master && ip_master=$ip
  echo ${name} | grep -q infra && ip_infra=$ip
  ssh-keyscan -H ${ip}.xip.io >> ~/.ssh/known_hosts
done

[% if infras > 0 -%]
public_domain=${ip_infra}.xip.io
[% else %]
public_domain=${ip_master}.xip.io
[%- endif %]
sed -i "s/#openshift_master_cluster_public_hostname=.*/openshift_master_cluster_public_hostname=${public_domain}/" /root/inventory
sed -i '/nameserver 192.168.122.1/d' /etc/resolv.conf
