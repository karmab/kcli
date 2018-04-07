#!/usr/bin/python

import json
import requests

user = "admin"
password = "[[ password ]]"
oshiftuser = "admin@internal"
oshiftpassword = "[[ openshift_password ]]"
oshifthost = "[[ openshift_host ]]"
oshiftkey = "XXX"
headers = {'content-type': 'application/json', 'Accept': 'application/json'}
postdata = {
    # "type": "ManageIQ::Providers::OpenshiftEnterprise::ContainerManager",
    "type": "ManageIQ::Providers::Openshift::ContainerManager",
    "name": "oshift",
    "hostname": oshifthost,
    "ipaddress": oshifthost,
    "credentials": [{
        "auth_type": "bearer",
        "auth_key": oshiftkey,
    }]
}

url = "https://127.0.0.1/api/providers"
r = requests.post(url, verify=False, headers=headers, auth=(user, password), data=json.dumps(postdata))
print r.json()
