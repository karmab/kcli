#!/usr/bin/python
# coding=utf-8

import json
import requests

user = "admin"
password = "{{ password }}"
rhevuser = "admin@internal"
rhevpassword = "{{ rhev_password }}"
rhevhost = "{{ rhev_host }}"
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
