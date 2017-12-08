#!/usr/bin/python

import requests

user = "admin@internal"
password = "unix1234"
engine = "rhvengine.default"
headers = {'content-type': 'application/xml', 'Accept': 'application/xml'}
hostname = "rhvnode02.default"
hostpassword = "unix1234"

data = """<host>
  <name>%s</name>
  <address>%s</address>
  <root_password>%s</root_password>
</host>""" % (hostname, hostname, hostpassword)

url = "https://%s/ovirt-engine/api/hosts?deploy_hosted_engine=true" % engine
r = requests.post(url, verify=False, headers=headers, auth=(user, password), data=data)
print(r.text)
