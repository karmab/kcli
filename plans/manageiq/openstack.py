#!/usr/bin/python
# coding=utf-8

import json
import requests

user = "admin"
password = "[[ password ]]"
openstackuser = "admin"
openstackpassword = "[[ openstack_password ]]"
openstackhost = "[[ openstack_host ]]"
headers = {'content-type': 'application/json', 'Accept': 'application/json'}
postdata = {
    "type": "ManageIQ::Providers::Openstack::CloudManager",
    "name": openstackhost,
    "hostname": openstackhost,
    "tenant_mapping_enabled": False,
    "security_protocol": "non-ssl",
    "port": 5000,
    "credentials": [{
                    "userid": openstackuser,
                    "password": openstackpassword
                    },
                    {
                    "userid": "guest",
                    "password": "guest",
                    "auth_type": "amqp"
                    }],
}

url = "https://127.0.0.1/api/providers"
r = requests.post(url, verify=False, headers=headers, auth=(user, password), data=json.dumps(postdata))
results = r.json()

id = results['results'][0]['id']
url = "https://127.0.0.1/api/providers/%s" % id
postdata = {"action": "refresh"}
r = requests.post(url, verify=False, headers=headers, auth=(user, password), data=json.dumps(postdata))
print r.json()
