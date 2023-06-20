#!/usr/bin/env python
# coding=utf-8

import base64
import boto3
from kvirt.config import Kconfig
import json
import sys


def _get(params, context, **kwargs):
    if "x-k8s-aws-id" in params:
        context["x-k8s-aws-id"] = params.pop("x-k8s-aws-id")


def _inject(**kwargs):
    req = kwargs['request']
    if "x-k8s-aws-id" in req.context:
        kwargs['request'].headers["x-k8s-aws-id"] = req.context["x-k8s-aws-id"]


def cli():
    if len(sys.argv) != 3:
        print("Usage ekstoken $client $cluster")
        sys.exit(1)
    client = sys.argv[1]
    cluster = sys.argv[2]
    k = Kconfig(client).k
    sts = boto3.client('sts', aws_access_key_id=k.access_key_id, aws_secret_access_key=k.access_key_secret,
                       region_name=k.region)
    sts.meta.events.register("provide-client-params.sts.GetCallerIdentity", _get)
    sts.meta.events.register("before-sign.sts.GetCallerIdentity", _inject)
    data = sts.generate_presigned_url("get_caller_identity", Params={"x-k8s-aws-id": cluster}, ExpiresIn=60,
                                      HttpMethod="GET")
    encoded = base64.urlsafe_b64encode(data.encode("utf-8"))
    token = f'k8s-aws-v1.{encoded.decode("utf-8").rstrip("=")}'
    result = {'apiVersion': 'client.authentication.k8s.io/v1beta1', 'kind': 'ExecCredential', 'spec': {},
              'status': {'expirationTimestamp': '2030-10-01T15:05:17Z', 'token': token}}
    print(json.dumps(result))


if __name__ == '__main__':
    cli()
