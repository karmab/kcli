from urllib.parse import urlparse
from urllib.request import urlopen, Request
import base64
import json
import os
import ssl
import sys
from uuid import UUID


class Redfish(object):
    def __init__(self, url, user='root', password='calvin', insecure=True, model='dell'):
        self.model = model.lower()
        try:
            UUID(os.path.basename(url))
            self.model = 'virtual'
        except:
            pass
        if self.model in ['hp', 'hpe', 'supermicro']:
            self.cdpath = '2'
        elif self.model == 'dell':
            self.cdpath = 'CD'
        else:
            self.cdpath = 'Cd'
        if not url.startswith('http'):
            if self.model in ['hp', 'hpe', 'supermicro']:
                self.url = f"https://{url}/redfish/v1/Systems/1"
            elif self.model == 'dell':
                self.url = f"https://{url}/redfish/v1/Systems/System.Embedded.1"
            else:
                print(f"Invalid url {url}")
                sys.exit(0)
        else:
            self.url = url
        self.user = user
        self.password = password
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        credentials = base64.b64encode(bytes(f'{user}:{password}', 'ascii')).decode('utf-8')
        self.headers["Authorization"] = f"Basic {credentials}"
        p = urlparse(self.url)
        self.baseurl = f"{p.scheme}://{p.netloc}"
        self.manager_url = None
        self.context = ssl.create_default_context()
        if insecure:
            self.context.check_hostname = False
            self.context.verify_mode = ssl.CERT_NONE

    def get_manager_url(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return f"{self.baseurl}{response['Links']['ManagedBy'][0]['@odata.id']}"

    def get_iso_status(self):
        manager_url = self.get_manager_url()
        request = Request(f"{manager_url}/VirtualMedia/{self.cdpath}", headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return f"{response['Inserted']}"

    def eject_iso(self):
        if self.model == 'supermicro':
            self.eject_iso_supermicro()
            return
        manager_url = self.get_manager_url()
        iso_url = f"{manager_url}/VirtualMedia/{self.cdpath}/Actions/VirtualMedia.EjectMedia"
        request = Request(iso_url, headers=self.headers, method='POST', data=json.dumps({}).encode('utf-8'))
        urlopen(request, context=self.context)

    def eject_iso_supermicro(self):
        manager_url = self.get_manager_url()
        headers = self.headers.copy()
        headers['Content-Length'] = 0
        request = Request(f"{manager_url}/VM1/CfgCD/Actions/IsoConfig.UnMount", data={}, headers=headers)
        urlopen(request, context=self.context)

    def insert_iso(self, iso_url):
        if self.model == 'supermicro':
            self.insert_iso_supermicro(iso_url)
            return
        data = {"Image": iso_url, "Inserted": True}
        data = json.dumps(data).encode('utf-8')
        manager_url = self.get_manager_url()
        request = Request(f"{manager_url}/VirtualMedia/{self.cdpath}/Actions/VirtualMedia.InsertMedia", data=data,
                          headers=self.headers)
        urlopen(request, context=self.context)

    def insert_iso_supermicro(self, iso_url):
        p = urlparse(iso_url)
        data = {"Host": f"{p.scheme}://{p.netloc}", "Path": p.path}
        data = json.dumps(data).encode('utf-8')
        manager_url = self.get_manager_url()
        request = Request(f"{manager_url}/VM1/CfgCD", data=data, headers=self.headers, method='PATCH')
        urlopen(request, context=self.context)
        headers = self.headers.copy()
        headers['Content-Length'] = 0
        request = Request(f"{manager_url}/VM1/CfgCD/Actions/IsoConfig.Mount", data={}, headers=headers)
        urlopen(request, context=self.context)

    def set_iso_once(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        currentboot = response['Boot']
        newboot = {}
        if currentboot['BootSourceOverrideEnabled'] != 'Once':
            newboot['BootSourceOverrideEnabled'] = 'Once'
        if currentboot['BootSourceOverrideTarget'] != 'cd':
            newboot['BootSourceOverrideTarget'] = 'Cd'
        if 'BootSourceOverrideMode' not in currentboot or currentboot['BootSourceOverrideMode'] != 'UEFI':
            newboot['BootSourceOverrideMode'] = 'UEFI'
        data = {"Boot": newboot}
        data = json.dumps(data).encode('utf-8')
        request = Request(self.url, data=data, headers=self.headers, method='PATCH')
        urlopen(request, context=self.context)

    def restart(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        reset_type = 'On' if response['PowerState'] == 'Off' else 'ForceRestart'
        data = {"ResetType": reset_type}
        data = json.dumps(data).encode('utf-8')
        request = Request(f"{self.url}/Actions/ComputerSystem.Reset", data=data, headers=self.headers)
        urlopen(request, context=self.context)

    def stop(self):
        data = {"ResetType": "ForceOff"}
        data = json.dumps(data).encode('utf-8')
        request = Request(f"{self.url}/Actions/ComputerSystem.Reset", data=data, headers=self.headers)
        urlopen(request, context=self.context)

    def start(self):
        data = {"ResetType": "On"}
        data = json.dumps(data).encode('utf-8')
        request = Request(f"{self.url}/Actions/ComputerSystem.Reset", data=data, headers=self.headers)
        urlopen(request, context=self.context)

    def status(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response['PowerState']

    def info(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response

    def reset(self):
        manager_url = self.get_manager_url()
        reset_url = f"{manager_url}/Actions/Manager.Reset"
        request = Request(reset_url, headers=self.headers, method='POST', data=json.dumps({}).encode('utf-8'))
        urlopen(request, context=self.context)

    def set_iso(self, iso_url):
        try:
            self.eject_iso()
        except:
            pass
        self.insert_iso(iso_url)
        self.set_iso_once()
        self.restart()
