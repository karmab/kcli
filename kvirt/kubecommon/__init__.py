from base64 import b64decode
import json
import os
from shutil import which
import ssl
from tempfile import NamedTemporaryFile
from urllib.request import urlopen, Request
import yaml


def _create_resource(kubectl, data, namespace=None, debug=False):
    if debug:
        print(f"CREATE with {data}")
    cmd = f"echo '{json.dumps(data)}' | {kubectl} create -o yaml -f -"
    if namespace is not None:
        cmd += f" -n {namespace}"
    return yaml.safe_load(os.popen(cmd).read())


def _delete_resource(kubectl, resource, name, namespace, debug=False):
    return os.popen(f'{kubectl} delete -n {namespace} {resource} {name} 2>/dev/null').read()


def _get_resource(kubectl, resource, name, namespace=None, debug=False):
    namespace = f" -n {namespace}" if namespace is not None else ''
    return yaml.safe_load(os.popen(f'{kubectl} get {resource} {namespace} -o yaml {name} 2>/dev/null').read())


def _get_all_resources(kubectl, resource, namespace=None, debug=False):
    namespace = f" -n {namespace}" if namespace is not None else ''
    cmd = f"{kubectl} get {resource} {namespace} -o yaml 2>/dev/null"
    return yaml.safe_load(os.popen(cmd).read())['items']


def _replace_resource(kubectl, data, namespace, debug=False):
    if 'status' in data:
        del data['status']
    if debug:
        print(f"REPLACE with {data}")
    return os.popen(f"echo '{json.dumps(data)}' | {kubectl} replace -n {namespace} -f -").read()


def _patch_resource(kubectl, resource, name, data, namespace, debug=False):
    if 'status' in data:
        del data['status']
    if debug:
        print(f"PATCH {resource} {name} with {data}")
    return os.popen(f"{kubectl} patch -n {namespace} {resource} {name} -p '{json.dumps(data)}'").read()


def _put(subresource, data, debug=False):
    headers = {'Content-Type': 'application/json'}
    kubectl = which('kubectl') or which('oc')
    cmd = '%s config view --minify --output jsonpath="{.clusters[*].cluster.server}"' % kubectl
    baseurl = os.popen(cmd).read()
    url = f'{baseurl}/{subresource}'
    cmd = "%s config view -o jsonpath='{.clusters[0]}' --raw" % kubectl
    ca_cert_data = json.loads(os.popen(cmd).read())['cluster']['certificate-authority-data']
    ca_cert_file = NamedTemporaryFile(delete=False)
    ca_cert_file.write(b64decode(ca_cert_data))
    ca_cert_file.close()
    context = ssl.create_default_context(cafile=ca_cert_file.name)
    cmd = "%s config view -o jsonpath='{.users[0]}' --raw" % kubectl
    kubeconfig_data = json.loads(os.popen(cmd).read())
    kubeconfig_user = kubeconfig_data['user']
    if 'client-certificate-data' in kubeconfig_user:
        client_cert_data = kubeconfig_user['client-certificate-data']
        client_cert_file = NamedTemporaryFile(delete=False)
        client_cert_file.write(b64decode(client_cert_data))
        client_cert_file.close()
        client_key_data = kubeconfig_user['client-key-data']
        client_key_file = NamedTemporaryFile(delete=False)
        client_key_file.write(b64decode(client_key_data))
        client_key_file.close()
        context.load_cert_chain(certfile=client_cert_file.name, keyfile=client_key_file.name)
    else:
        headers["Authorization"] = f"Bearer {kubeconfig_data['token']}"
    data = json.dumps(data).encode('utf-8')
    request = Request(url, headers=headers, method='PUT', data=data)
    urlopen(request, context=context)
