url="https://{{ host }}/ovirt-engine/api"
user="{{ user }}"
password="{{password }}"
plan="{{ plan }}"

VMIDS=`curl -sk -H "Accept: application/xml" -u  "${user}:${password}" "${url}/vms?search=plan=${plan}*" | grep '<vm href=' | sed 's/.*id="\(.*\).*">/\1/'`

for vmid in $VMIDS ; do
  name=`curl -sk -H "Accept: application/xml" -u  "${user}:${password}" "${url}/vms/${vmid}" |  grep -m1 '<name>'| sed 's@.*<name>\(.*\)</name>@\1@'`
  ip=`curl -sk -H "Accept: application/xml" -u  "${user}:${password}" "${url}/vms/${vmid}/reporteddevices" | grep -v : | grep -m1 address | sed 's@.*<address>\(.*\)</address>@\1@'`
  newname=${name}.${ip}.xip.io
  echo "Substituting ${name} for ${newname} in inventory"
  sed -i "s/${name}\.{{ domain }}/${newname}/g" /root/inventory
  echo ${name} | grep -q m01 && ip_master=$ip
  echo ${name} | grep -q i01 && ip_infra=$ip
  ssh -o 'StrictHostKeyChecking=no' root@${ip} hostnamectl set-hostname ${newname}
done

{% if infras > 0 -%}
default_subdomain=${ip_infra}.xip.io
{% else %}
default_subdomain=${ip_master}.xip.io
{%- endif %}
sed -i "s/#openshift_master_default_subdomain=.*/openshift_master_default_subdomain=apps.${default_subdomain}/" /root/inventory
sed -i "s/#openshift_master_cluster_hostname=.*/openshift_master_cluster_hostname=m01.${ip_master}.xip.io/" /root/inventory
