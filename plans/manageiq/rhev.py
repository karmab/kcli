#!/usr/bin/python

import json
import requests

user = "admin"
password = "unix1234"
rhevuser = "admin@internal"
rhevpassword = "unix1234"
rhevhost = "engine.default"
headers = {'content-type': 'application/json', 'Accept': 'application/json'}
postdata = {
    "type": "ManageIQ::Providers::Redhat::InfraManager",
    "name": "rhev",
    "hostname": rhevhost,
    "ipaddress": rhevhost,
    "credentials": {
        "userid": rhevuser,
        "password": rhevpassword
    }
}

url = "https://127.0.0.1/api/providers"
r = requests.post(url, verify=False, headers=headers, auth=(user, password), data=json.dumps(postdata))
print r.json()
