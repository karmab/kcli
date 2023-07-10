from urllib.parse import urlparse
from urllib.request import urlopen, Request
import base64
import json
import os
import ssl
import re
import sys
from uuid import UUID


def valid_uuid(uuid):
    try:
        UUID(uuid)
        return True
    except:
        return False


def get_info(url, user, password):
    match = re.match('.*/redfish/v1/Systems/(.*)', url)
    if '/redfish/v1/Systems' in url and\
       (valid_uuid(os.path.basename(url)) or (match is not None and len(match.group(1).split('/')) == 2)):
        model = 'virtual'
        user = user or 'fake'
        password = password or 'fake'
        return model, url, user, password
    oem_url = f"https://{url}" if '://' not in url else url
    p = urlparse(oem_url)
    headers = {'Accept': 'application/json'}
    request = Request(f"https://{p.netloc}/redfish/v1", headers=headers)
    oem = json.loads(urlopen(request).read())['Oem']
    model = "dell" if 'Dell' in oem else "hp" if 'Hpe' in oem else 'supermicro' if 'Supermicro' in oem else 'N/A'
    if '://' not in url:
        if model in ['hp', 'supermicro']:
            url = f"https://{url}/redfish/v1/Systems/1"
        elif model == 'dell':
            url = f"https://{url}/redfish/v1/Systems/System.Embedded.1"
            user = user or 'root'
            password = password or 'calvin'
        else:
            print(f"Invalid url {url}")
            sys.exit(0)
    return model, url, user, password


class Redfish(object):
    def __init__(self, url, user='root', password='calvin', insecure=True, debug=False, model=None):
        self.debug = debug
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if insecure:
            ssl._create_default_https_context = ssl._create_unverified_context
        url = url.replace('idrac-virtualmedia', 'https').replace('ilo5-virtualmedia', 'https')
        self.model, self.url, self.user, self.password = get_info(url, user, password)
        if self.debug:
            print(f"Using base url {self.url}")
        p = urlparse(self.url)
        self.baseurl = f"{p.scheme}://{p.netloc}"
        credentials = base64.b64encode(bytes(f'{self.user}:{self.password}', 'ascii')).decode('utf-8')
        self.headers["Authorization"] = f"Basic {credentials}"
        self.manager_url = None

    def get_manager_url(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request).read())
        return f"{self.baseurl}{response['Links']['ManagedBy'][0]['@odata.id']}"

    def get_iso_url(self):
        manager_url = self.get_manager_url()
        request = Request(f'{manager_url}', headers=self.headers)
        results = json.loads(urlopen(request).read())
        if 'VirtualMedia' in results:
            virtual_media_url = results['VirtualMedia']['@odata.id']
        else:
            virtual_media_url = results['Status']['VirtualMedia']['@odata.id']
        request = Request(f'{self.baseurl}{virtual_media_url}', headers=self.headers)
        results = json.loads(urlopen(request).read())
        if 'Oem' in results:
            odata = results['Oem']['Supermicro']['VirtualMediaConfig']['@odata.id']
        else:
            for member in results['Members']:
                odata = member['@odata.id']
                if odata.endswith('CD') or odata.endswith('Cd') or odata.endswith('2'):
                    break
        return f'{self.baseurl}{odata}'

    def get_iso_status(self):
        iso_url = self.get_iso_url()
        if self.debug:
            print(f"Getting {iso_url}")
        request = Request(iso_url, headers=self.headers)
        response = json.loads(urlopen(request).read())
        return f"{response['Image']}"

    def get_iso_eject_url(self):
        iso_url = self.get_iso_url()
        request = Request(iso_url, headers=self.headers)
        actions = json.loads(urlopen(request).read())['Actions']
        target = '#IsoConfig.UnMount' if self.model == 'supermicro' else '#VirtualMedia.EjectMedia'
        t = actions[target]['target']
        return f"{self.baseurl}{t}"

    def get_iso_insert_url(self):
        iso_url = self.get_iso_url()
        request = Request(iso_url, headers=self.headers)
        actions = json.loads(urlopen(request).read())['Actions']
        target = '#IsoConfig.Mount' if self.model == 'supermicro' else '#VirtualMedia.InsertMedia'
        t = actions[target]['target']
        return f"{self.baseurl}{t}"

    def eject_iso(self):
        headers = self.headers.copy()
        data = json.dumps({}).encode('utf-8')
        if self.model == 'supermicro':
            headers['Content-Length'] = 0
            # data = {}
        eject_url = self.get_iso_eject_url()
        if self.debug:
            print(f"Sending POST to {eject_url} with empty data")
        request = Request(eject_url, headers=headers, method='POST', data=data)
        urlopen(request)

    def insert_iso(self, iso_url):
        headers = self.headers.copy()
        if self.model == 'supermicro':
            p = urlparse(iso_url)
            data = {"Host": f"{p.scheme}://{p.netloc}", "Path": p.path}
            manager_url = self.get_manager_url()
            cd_url = f"{manager_url}/VM1/CfgCD"
            if self.debug:
                print(f"Sending PATCH to {cd_url} with data {data}")
            data = json.dumps(data).encode('utf-8')
            request = Request(cd_url, data=data, headers=self.headers, method='PATCH')
            urlopen(request)
            headers['Content-Length'] = 0
        data = {"Image": iso_url, "Inserted": True}
        insert_url = self.get_iso_insert_url()
        if self.debug:
            print(f"Sending POST to {insert_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(insert_url, data=data, headers=headers)
        urlopen(request)

    def set_iso_once(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request).read())
        currentboot = response['Boot']
        newboot = {}
        if currentboot['BootSourceOverrideEnabled'] != 'Once':
            newboot['BootSourceOverrideEnabled'] = 'Once'
        if currentboot['BootSourceOverrideTarget'] != 'Cd':
            newboot['BootSourceOverrideTarget'] = 'Cd'
        if 'BootSourceOverrideMode' not in currentboot or currentboot['BootSourceOverrideMode'] != 'UEFI':
            newboot['BootSourceOverrideMode'] = 'UEFI'
        data = {"Boot": newboot}
        if self.debug:
            print(f"Sending PATCH to {self.url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(self.url, data=data, headers=self.headers, method='PATCH')
        urlopen(request)

    def restart(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request).read())
        reset_type = 'On' if response['PowerState'] == 'Off' else 'ForceRestart'
        data = {"ResetType": reset_type}
        reset_url = f"{self.url}/Actions/ComputerSystem.Reset"
        if self.debug:
            print(f"Sending POST to {reset_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(reset_url, data=data, headers=self.headers)
        urlopen(request)

    def stop(self):
        data = {"ResetType": "ForceOff"}
        reset_url = f"{self.url}/Actions/ComputerSystem.Reset"
        if self.debug:
            print(f"Sending POST to {reset_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(reset_url, data=data, headers=self.headers)
        urlopen(request)

    def start(self):
        data = {"ResetType": "On"}
        reset_url = f"{self.url}/Actions/ComputerSystem.Reset"
        if self.debug:
            print(f"Sending POST to {reset_url} with {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(reset_url, data=data, headers=self.headers)
        urlopen(request)

    def status(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request).read())
        return response['PowerState']

    def info(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request).read())
        return response

    def reset(self):
        manager_url = self.get_manager_url()
        reset_url = f"{manager_url}/Actions/Manager.Reset"
        data = {"ResetType": "GracefulRestart"}
        if self.debug:
            print(f"Sending POST to {reset_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(reset_url, headers=self.headers, method='POST', data=data)
        urlopen(request)

    def set_iso(self, iso_url):
        try:
            self.eject_iso()
        except:
            pass
        self.insert_iso(iso_url)
        try:
            self.set_iso_once()
        except:
            self.set_iso_once()
        self.restart()
