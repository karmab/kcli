#!/usr/bin/python

import json
import requests

user = "admin"
password = "smartvm"
oshiftuser = "admin@internal"
oshiftpassword = "unix1234"
oshifthost = "lb.example.com"
oshiftkey = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJtYW5hZ2VtZW50LWluZnJhIiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6Im1hbmFnZW1lbnQtYWRtaW4tdG9rZW4tYnVycnAiLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoibWFuYWdlbWVudC1hZG1pbiIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6ImUwMzVhNGQ2LTBhOTMtMTFlNy1hOTM4LTUyNTQwMDM4OTk0ZSIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDptYW5hZ2VtZW50LWluZnJhOm1hbmFnZW1lbnQtYWRtaW4ifQ.cXuG_z25En3rbi-nmOR76YhxZV9qRFw_RsC74STy4VEaz7mrKlobQYaGIVGoPkIPnl6ioo0dnuL4iV2lGUq272nKl9uUblewdy4i8ntQAWJlL1D2fVTKmS0DtNbC6ZIRryk7QiY8jHr3LKJ2iUx_d7uvznY5dYaTMmWsAl5EFkvY3gjdYCIRexmAAm-LQ9zrH_rq4OPVbonOKRXBdIG2vEs1MTbPxWUKypRP67r0Cyge2VTjy_gdLcL6BJYm8_Q_UUql610P5eNpCcTqV4rtDCBCnVPcEOhB9F4VaUA2zVA5xYSgAyyO2vUL6K9SGYeJZqoym1zxGn-RN4IjBNYVFg"
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
