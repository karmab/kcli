#!/usr/bin/env python
# coding=utf-8

# import base64
from kvirt.config import Kconfig
import os
import json
import sys
import google.auth
import google.auth.transport.requests


def cli():
    if len(sys.argv) != 2:
        print("Usage gketoken $client")
        sys.exit(1)
    client = sys.argv[1]
    config = Kconfig(client)
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.expanduser(config.options.get('credentials'))
    credentials, your_project_id = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    token = credentials.token
    result = {'apiVersion': 'client.authentication.k8s.io/v1beta1', 'kind': 'ExecCredential', 'spec': {},
              'status': {'expirationTimestamp': '2030-10-01T15:05:17Z', 'token': token}}
    print(json.dumps(result))


if __name__ == '__main__':
    cli()
