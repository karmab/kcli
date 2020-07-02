#!/usr/bin/bash

TOKEN="{{ config_auth_token }}"
CURRENTDEVICEID=$(curl -s https://metadata.packet.net/2009-04-04/meta-data/instance-id)
export PATH=/root:$PATH

which jq >/dev/null 2>&1
if [ "$?" != "0" ] ; then
  curl -Ls https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64 > /root/jq
  chmod u+x /root/jq
fi

PROJECT_ID="$(curl -s https://metadata.packet.net/2009-04-04/meta-data/tags | grep project | sed 's/project_//')"
DEVICEIDS=$(curl -H "X-Auth-Token: $TOKEN" -H "Content-Type: application/json" https://api.packet.net/projects/$PROJECT_ID/devices | jq -r '.devices[] | select(.hostname | startswith("{{ cluster }}-")) | .id')
for DEVICEID in $DEVICEIDS ; do
  RESERVATIONID=$(curl -sH "X-Auth-Token: $TOKEN" -H "Content-Type: application/json" https://api.packet.net/devices/$DEVICEID/ips | jq -r '.ip_addresses[] | select(.address == "{{ api_ip }}") | .id')
  if [ "$RESERVATIONID" != "" ] ; then
    if [ "$DEVICEID" == "$CURRENTDEVICEID" ] ; then
      exit 0
    fi
    echo "Deleting old reservation $RESERVATIONID in device $DEVICEID"
    curl -H "X-Auth-Token: $TOKEN" -H "Content-Type: application/json" -X DELETE https://api.packet.net/ips/$RESERVATIONID
    break
  fi
done
echo "Creating new reservation for $CURRENTDEVICEID"
curl -sH "X-Auth-Token: $TOKEN" -H "Content-Type: application/json" -X POST -d "{\"address\": \"{{ api_ip }}/32\",\"manageable\": \"true\"}" https://api.packet.net/devices/$CURRENTDEVICEID/ips
exit 0
