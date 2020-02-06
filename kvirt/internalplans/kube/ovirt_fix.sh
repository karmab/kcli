url="https://{{ host }}/ovirt-engine/api"
user="{{ user }}"
password="{{password }}"
plan="{{ plan }}"

sleep 420
VMIDS=`curl -sk -H "Accept: application/xml" -u  "${user}:${password}" "${url}/vms?search=plan=${plan}*" | grep '<vm href=' | sed 's/.*id="\(.*\).*">/\1/'`

for vmid in $VMIDS ; do
  name=`curl -sk -H "Accept: application/xml" -u  "${user}:${password}" "${url}/vms/${vmid}" |  grep -m1 '<name>'| sed 's@.*<name>\(.*\)</name>@\1@'`
  ip=`curl -sk -H "Accept: application/xml" -u  "${user}:${password}" "${url}/vms/${vmid}/reporteddevices" | grep -v : | grep -m1 address | sed 's@.*<address>\(.*\)</address>@\1@'`
  echo ${ip} ${name}.{{ domain }} >> /etc/hosts
done
