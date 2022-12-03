from urllib.parse import urlparse
from urllib.request import urlopen, Request
import base64
import json
import os
import ssl
import sys
from uuid import UUID


class Redfish(object):
    def __init__(self, url, user='root', password='calvin', insecure=True, model='dell', debug=False):
        self.debug = debug
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
        try:
            p = urlparse(url)
        except:
            if self.model in ['hp', 'hpe', 'supermicro']:
                url = f"https://{url}/redfish/v1/Systems/1"
            elif self.model == 'dell':
                url = f"https://{url}/redfish/v1/Systems/System.Embedded.1"
            else:
                print(f"Invalid url {url}")
                sys.exit(0)
            p = urlparse(url)
        self.url = url
        if self.debug:
            print(f"Using base url {self.url}")
        self.user = user
        self.password = password
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        credentials = base64.b64encode(bytes(f'{user}:{password}', 'ascii')).decode('utf-8')
        self.headers["Authorization"] = f"Basic {credentials}"
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
        iso_url = f"{manager_url}/VirtualMedia/{self.cdpath}"
        if self.debug:
            print(f"Getting {iso_url}")
        request = Request(iso_url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return f"{response['Inserted']}"

    def eject_iso(self):
        if self.model == 'supermicro':
            self.eject_iso_supermicro()
            return
        manager_url = self.get_manager_url()
        eject_url = f"{manager_url}/VirtualMedia/{self.cdpath}/Actions/VirtualMedia.EjectMedia"
        if self.debug:
            print(f"Sending POST to {eject_url} with empty data")
        data = json.dumps({}).encode('utf-8')
        request = Request(eject_url, headers=self.headers, method='POST', data=data)
        urlopen(request, context=self.context)

    def eject_iso_supermicro(self):
        manager_url = self.get_manager_url()
        headers = self.headers.copy()
        headers['Content-Length'] = 0
        eject_url = f"{manager_url}/VM1/CfgCD/Actions/IsoConfig.UnMount"
        if self.debug:
            print(f"Sending POST to {eject_url} with empty data")
        request = Request(eject_url, data={}, headers=headers)
        urlopen(request, context=self.context)

    def insert_iso(self, iso_url):
        if self.model == 'supermicro':
            self.insert_iso_supermicro(iso_url)
            return
        data = {"Image": iso_url, "Inserted": True}
        manager_url = self.get_manager_url()
        insert_url = f"{manager_url}/VirtualMedia/{self.cdpath}/Actions/VirtualMedia.InsertMedia"
        if self.debug:
            print(f"Sending POST to {insert_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(insert_url, data=data, headers=self.headers)
        urlopen(request, context=self.context)

    def insert_iso_supermicro(self, iso_url):
        p = urlparse(iso_url)
        data = {"Host": f"{p.scheme}://{p.netloc}", "Path": p.path}
        manager_url = self.get_manager_url()
        cd_url = f"{manager_url}/VM1/CfgCD"
        if self.debug:
            print(f"Sending PATCH to {cd_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(cd_url, data=data, headers=self.headers, method='PATCH')
        urlopen(request, context=self.context)
        headers = self.headers.copy()
        headers['Content-Length'] = 0
        insert_url = f"{manager_url}/VM1/CfgCD/Actions/IsoConfig.Mount"
        if self.debug:
            print(f"Sending POST to {insert_url} with empty data")
        request = Request(insert_url, data={}, headers=headers)
        urlopen(request, context=self.context)

    def set_iso_once(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
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
        urlopen(request, context=self.context)

    def restart(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        reset_type = 'On' if response['PowerState'] == 'Off' else 'ForceRestart'
        data = {"ResetType": reset_type}
        reset_url = f"{self.url}/Actions/ComputerSystem.Reset"
        if self.debug:
            print(f"Sending POST to {reset_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(reset_url, data=data, headers=self.headers)
        urlopen(request, context=self.context)

    def stop(self):
        data = {"ResetType": "ForceOff"}
        reset_url = f"{self.url}/Actions/ComputerSystem.Reset"
        if self.debug:
            print(f"Sending POST to {reset_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(reset_url, data=data, headers=self.headers)
        urlopen(request, context=self.context)

    def start(self):
        data = {"ResetType": "On"}
        reset_url = f"{self.url}/Actions/ComputerSystem.Reset"
        if self.debug:
            print(f"Sending POST to {reset_url} with {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(reset_url, data=data, headers=self.headers)
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
        data = {"ResetType": "GracefulRestart"}
        if self.debug:
            print(f"Sending POST to {reset_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(reset_url, headers=self.headers, method='POST', data=data)
        urlopen(request, context=self.context)

    def set_iso(self, iso_url):
        try:
            self.eject_iso()
        except:
            pass
        self.insert_iso(iso_url)
        self.set_iso_once()
        self.restart()
