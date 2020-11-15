#!/usr/bin/python

import os
import requests

user = "karmab"
repo = "kcli"
package = "python3-kcli"
token = os.environ['PACKAGE_CLOUD_TOKEN']
baseurl = "https://%s:@packagecloud.io" % token
url = "%s/api/v1/repos/%s/%s/packages.json?per_page=600" % (baseurl, user, repo)
r = requests.get(url)
data = {}
for entry in r.json():
    try:
        version = int(entry['version'].replace('99.0.', ''))
    except:
        continue
    destroy_url = "%s%s" % (baseurl, entry['destroy_url'])
    if version in data:
        data[version].append(destroy_url)
    else:
        data[version] = [destroy_url]

if len(data) > 1:
    for release in sorted(data)[:-1]:
        for package_url in data[release]:
            print("Deleting %s" % package_url)
            x = requests.delete(package_url)
            print(x.status_code, x.reason, x.text)
