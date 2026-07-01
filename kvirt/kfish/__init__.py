from urllib.parse import urlparse
from urllib.request import urlopen, Request
import base64
import json
import os
import ssl
import re
import sys
from uuid import UUID
import traceback


def pprint(text):
    color = '36'
    print(f'\033[{color}m{text}\033[0m')


def error(text):
    color = '31'
    print(f'\033[{color}m{text}\033[0m', file=sys.stderr)


def success(text):
    color = '32'
    print(f'\033[{color}m{text}\033[0m')


def warning(text):
    color = '33'
    print(f'\033[{color}m{text}\033[0m')


def valid_uuid(uuid):
    try:
        UUID(uuid)
        return True
    except:
        return False


def get_info(url, headers, context):
    match = re.match('.*/redfish/v1/Systems/(.*)', url)
    if '/redfish/v1/Systems' in url and\
       (valid_uuid(os.path.basename(url)) or (match is not None and len(match.group(1).split('/')) == 2)):
        model = 'virtual'
        return model, url
    oem_url = f"https://{url}" if '://' not in url else url
    p = urlparse(oem_url)
    chassis_url = f"{p.scheme}://{p.netloc}/redfish/v1/Chassis"
    try:
        request = Request(chassis_url, headers=headers)
        chassis = json.loads(urlopen(request, context=context).read())['Members'][0]['@odata.id']
    except Exception as e:
        msg = getattr(e, 'msg', str(e))
        error(f"Hit issue {msg} when accessing url {chassis_url}")
        raise e
    request_url = f"{p.scheme}://{p.netloc}{chassis}"
    request = Request(request_url, headers=headers)
    manufacturer = json.loads(urlopen(request, context=context).read()).get('Manufacturer', '').lower()
    if 'dell' in manufacturer:
        model = 'dell'
    elif 'hp' in manufacturer:
        model = 'hp'
    elif 'supermicro' in manufacturer:
        model = 'supermicro'
    elif 'senao corporation' in manufacturer:
        model = 'senao'
    else:
        error(f"Failed to detect model from url '{url}' with manufacturer '{manufacturer}'")
        sys.exit(1)
    if '://' not in url:
        if model in ['hp', 'supermicro', 'lenovo']:
            url = f"https://{url}/redfish/v1/Systems/1"
        elif model == 'dell':
            url = f"https://{url}/redfish/v1/Systems/System.Embedded.1"
        elif model == 'senao':
            url = f"https://{url}/redfish/v1/Systems/system"
    return model, url


class Redfish(object):
    def __init__(self, url, user='root', password='calvin', insecure=True, debug=False, model=None, legacy=False):
        self.debug = debug
        self.headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        credentials = base64.b64encode(bytes(f'{user}:{password}', 'ascii')).decode('utf-8')
        self.headers["Authorization"] = f"Basic {credentials}"
        self.context = ssl._create_unverified_context() if insecure else None
        url = url.replace('idrac-virtualmedia', 'https').replace('ilo5-virtualmedia', 'https')
        self.model, self.url = get_info(url, self.headers, self.context)
        if self.debug:
            pprint(f"Using base url {self.url}")
        p = urlparse(self.url)
        self.baseurl = f"{p.scheme}://{p.netloc}"
        self.manager_url = None
        self.legacy = False
        # Dell iDRAC version detection
        self.idrac_version = None
        # Dell iDRAC9+ (R770): VirtualMedia moved from Manager to System path
        self.idrac_system_path = False
        self.dell_vm_url = None
        if self.model == 'supermicro':
            info = self.info()
            if 'VirtualMedia' not in info or info['VirtualMedia']['@odata.id'] != '/redfish/v1/Managers/1/VirtualMedia':
                self.legacy = True
        elif self.model == 'dell':
            self._detect_dell_idrac_version()
            self._detect_dell_virtualmedia_path()

    def _detect_dell_idrac_version(self):
        """Detect Dell iDRAC version from Manager Model (12G/13G=iDRAC8, 14G-16G=iDRAC9, 17G+=iDRAC10)."""
        try:
            manager_url = f"{self.baseurl}/redfish/v1/Managers/iDRAC.Embedded.1"
            request = Request(manager_url, headers=self.headers)
            manager_info = json.loads(urlopen(request, context=self.context).read())
            model = manager_info.get('Model', '')
            if self.debug:
                pprint(f"Dell Manager Model: {model}")
            if "12" in model or "13" in model:
                self.idrac_version = 8
            elif "14" in model or "15" in model or "16" in model:
                self.idrac_version = 9
            else:
                self.idrac_version = 10
            if self.debug:
                pprint(f"Dell iDRAC version: {self.idrac_version}")
        except Exception as e:
            if self.debug:
                pprint(f"Dell: Could not detect iDRAC version: {e}")
            self.idrac_version = 10

    def _detect_dell_virtualmedia_path(self):
        """Detect if Dell VirtualMedia is at System path (iDRAC9+) or Manager path."""
        try:
            info = self.info()
            if 'VirtualMedia' in info:
                self.idrac_system_path = True
                self.dell_vm_url = info['VirtualMedia']['@odata.id']
            elif 'Links' in info and 'VirtualMedia' in info.get('Links', {}):
                self.idrac_system_path = True
                self.dell_vm_url = info['Links']['VirtualMedia']['@odata.id']
            if self.debug and self.dell_vm_url:
                pprint(f"Dell: VirtualMedia at {self.dell_vm_url}")
        except Exception as e:
            if self.debug:
                pprint(f"Dell: Error detecting VirtualMedia path: {e}")

    def get_manager_url(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        ret_data = f"{self.baseurl}{response['Links']['ManagedBy'][0]['@odata.id']}"
        if self.debug:
            pprint(f"Manager URL is {ret_data}")
        return ret_data

    def get_iso_url(self):
        manager_url = self.get_manager_url()
        request = Request(f'{manager_url}', headers=self.headers)
        results = json.loads(urlopen(request, context=self.context).read())

        virtual_media_url = None
        # Dell iDRAC9+: VirtualMedia is under System, not Manager
        if self.model == 'dell' and self.idrac_system_path and self.dell_vm_url:
            virtual_media_url = self.dell_vm_url
        elif 'VirtualMedia' in results:
            virtual_media_url = results['VirtualMedia']['@odata.id']
        elif 'Status' in results and isinstance(results.get('Status'), dict):
            virtual_media_url = results['Status'].get('VirtualMedia', {}).get('@odata.id')
        if virtual_media_url is None:
            virtual_media_url = f"{manager_url.replace(self.baseurl, '')}/VirtualMedia"
        request = Request(f'{self.baseurl}{virtual_media_url}', headers=self.headers)
        results = json.loads(urlopen(request, context=self.context).read())
        if 'Oem' in results:
            odata = results['Oem']['Supermicro']['VirtualMediaConfig']['@odata.id']
        else:
            member_list = results['Members']
            if not member_list:
                error(f"VirtualMedia Member list in {self.baseurl}{virtual_media_url} is empty")
                sys.exit(1)
            for member in member_list:
                odata = member['@odata.id']
                if odata.endswith('CD') or odata.endswith('Cd') or odata.endswith('2'):
                    break
        ret_data = f'{self.baseurl}{odata}'
        if self.debug:
            pprint(f"ISO URL is {ret_data}")
        return ret_data

    def get_iso_status(self):
        iso_url = self.get_iso_url()
        if self.debug:
            pprint(f"Getting {iso_url}")
        request = Request(iso_url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        # Image can be set to '' or to None to indicate no image is configured
        iso = str(response['Image']) if response['Image'] else ''
        inserted = response['Inserted']
        if self.debug:
            pprint(f"ISO status is Image: {iso} Inserted: {inserted}")
        return iso, inserted

    def get_iso_eject_url(self):
        iso_url = self.get_iso_url()
        request = Request(iso_url, headers=self.headers)
        if self.model == 'lenovo':
            ret_data = f"{iso_url}"
        else:
            actions = json.loads(urlopen(request, context=self.context).read())['Actions']
            target = '#IsoConfig.UnMount' if self.model == 'supermicro' and self.legacy else '#VirtualMedia.EjectMedia'
            ret_data = f"{self.baseurl}{actions[target]['target']}"
        if self.debug:
            pprint(f"ISO eject URL is {ret_data}")
        return ret_data

    def get_iso_insert_url(self):
        iso_url = self.get_iso_url()
        request = Request(iso_url, headers=self.headers)
        if self.model == 'lenovo':
            ret_data = iso_url
        else:
            actions = json.loads(urlopen(request, context=self.context).read())['Actions']
            target = '#IsoConfig.Mount' if self.model == 'supermicro' and self.legacy else '#VirtualMedia.InsertMedia'
            ret_data = f"{self.baseurl}{actions[target]['target']}"
        if self.debug:
            pprint(f"ISO insert URL is {ret_data}")
        return ret_data

    def eject_iso(self):
        headers = self.headers.copy()
        eject_url = self.get_iso_eject_url()
        if self.model == 'lenovo':
            data = {"Inserted": False}
            data = json.dumps(data).encode('utf-8')
            request = Request(eject_url, data=data, headers=headers, method='PATCH')
            if self.debug:
                pprint(f"Sending PATCH to {eject_url} with data {data}")
        else:
            data = json.dumps({}).encode('utf-8')
            if self.model == 'supermicro' and self.legacy:
                headers['Content-Length'] = 0
            request = Request(eject_url, headers=headers, method='POST', data=data)
            if self.debug:
                pprint(f"Sending POST to {eject_url} with empty data")
        result = urlopen(request, context=self.context)

        # Dell fallback: Also try ejecting from Managers endpoint if media is inserted there
        if self.model == 'dell':
            try:
                inserted, _ = self._get_dell_manager_vm_status()
                if inserted:
                    if self.debug:
                        pprint("Dell: Media still inserted at Managers endpoint, ejecting from there")
                    self._eject_iso_via_dell_manager()
            except Exception as e:
                if self.debug:
                    pprint(f"Dell: Fallback eject check failed: {e}")

        return result

    def _get_dell_manager_vm_status(self):
        """Check VirtualMedia status at Dell Managers endpoint."""
        try:
            manager_url = self.get_manager_url()
            vm_url = f"{manager_url}/VirtualMedia/CD"
            if self.debug:
                pprint(f"Checking VirtualMedia status at {vm_url}")
            request = Request(vm_url, headers=self.headers)
            response = json.loads(urlopen(request, context=self.context).read())
            inserted = response.get("Inserted", False)
            image = response.get("Image", "")
            if self.debug:
                pprint(f"Manager VirtualMedia status - Inserted: {inserted}, Image: {image}")
            return inserted, image
        except Exception as e:
            if self.debug:
                pprint(f"Failed to check Manager VirtualMedia status: {e}")
            return False, ""

    def _insert_iso_via_dell_manager(self, iso_url):
        """Insert ISO via Dell Managers endpoint (fallback for NFS)."""
        manager_url = self.get_manager_url()
        insert_url = f"{manager_url}/VirtualMedia/CD/Actions/VirtualMedia.InsertMedia"
        if iso_url.startswith('http://'):
            data = {"Image": iso_url, "TransferProtocolType": "HTTP"}
        elif iso_url.startswith('https://'):
            data = {"Image": iso_url, "TransferProtocolType": "HTTPS"}
        else:
            data = {"Image": iso_url}
        if self.debug:
            pprint(f"Fallback: Sending POST to {insert_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(insert_url, data=data, headers=self.headers)
        return urlopen(request, context=self.context)

    def _eject_iso_via_dell_manager(self):
        """Eject ISO via Dell Managers endpoint."""
        manager_url = self.get_manager_url()
        eject_url = f"{manager_url}/VirtualMedia/CD/Actions/VirtualMedia.EjectMedia"
        if self.debug:
            pprint(f"Fallback: Sending POST to {eject_url}")
        data = json.dumps({}).encode('utf-8')
        request = Request(eject_url, headers=self.headers, method='POST', data=data)
        return urlopen(request, context=self.context)

    def insert_iso(self, iso_url):
        headers = self.headers.copy()
        if self.model == 'supermicro' and self.legacy:
            p = urlparse(iso_url)
            data = {"Host": f"{p.scheme}://{p.netloc}", "Path": p.path}
            manager_url = self.get_manager_url()
            cd_url = f"{manager_url}/VM1/CfgCD"
            if self.debug:
                pprint(f"Sending PATCH to {cd_url} with data {data}")
            data = json.dumps(data).encode('utf-8')
            request = Request(cd_url, data=data, headers=self.headers, method='PATCH')
            urlopen(request, context=self.context)
            headers['Content-Length'] = 0
        if self.model == 'senao':
            iso_url = iso_url.replace(":", "")
            nfs_iso_url = f"nfs://{iso_url}"
            data = {"Image": nfs_iso_url, "TransferProtocolType": "NFS"}
        elif self.model == 'dell':
            # Dell iDRAC9+/iDRAC10: don't include "Inserted: True"
            if iso_url.startswith('http://'):
                data = {"Image": iso_url, "TransferProtocolType": "HTTP"}
            elif iso_url.startswith('https://'):
                data = {"Image": iso_url, "TransferProtocolType": "HTTPS"}
            else:
                data = {"Image": iso_url}
        else:
            data = {"Image": iso_url, "Inserted": True}
        insert_url = self.get_iso_insert_url()
        data = json.dumps(data).encode('utf-8')
        if self.model == 'lenovo':
            request = Request(insert_url, data=data, headers=headers, method='PATCH')
            if self.debug:
                pprint(f"Sending PATCH to {insert_url} with data {data}")
        else:
            request = Request(insert_url, data=data, headers=headers)
            if self.debug:
                pprint(f"Sending POST to {insert_url} with data {data}")
        result = urlopen(request, context=self.context)

        # Dell fallback: If insertion via System endpoint didn't work, try Managers endpoint
        if self.model == 'dell':
            try:
                inserted, _ = self._get_dell_manager_vm_status()
                if not inserted:
                    if self.debug:
                        pprint("Dell: Media not inserted via System endpoint, trying Managers endpoint")
                    result = self._insert_iso_via_dell_manager(iso_url)
                    # Verify the fallback worked
                    inserted, _ = self._get_dell_manager_vm_status()
                    if not inserted:
                        error("Dell: Failed to insert ISO via both System and Managers endpoints")
            except Exception as e:
                if self.debug:
                    pprint(f"Dell: Fallback check failed: {e}")

        return result

    def set_iso_once(self):
        """Set one-time boot to CD/DVD (Virtual Media)."""
        if self.model == 'dell' and self.idrac_version and self.idrac_version >= 10:
            return self._set_iso_once_dell_idrac10()
        return self._set_iso_once_standard()

    def _set_iso_once_standard(self):
        """Standard Redfish boot override for iDRAC9 and other vendors."""
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        currentboot = response['Boot']
        newboot = {}
        if currentboot.get('BootSourceOverrideEnabled') != 'Once':
            newboot['BootSourceOverrideEnabled'] = 'Once'
        if currentboot.get('BootSourceOverrideTarget') != 'Cd':
            newboot['BootSourceOverrideTarget'] = 'Cd'
        # Dell iDRAC9: may require BootSourceOverrideMode
        if self.model == 'dell' and self.idrac_system_path:
            if currentboot.get('BootSourceOverrideMode') != 'UEFI':
                newboot['BootSourceOverrideMode'] = 'UEFI'
        elif self.model == 'senao' or ('BootSourceOverrideMode' not in currentboot):
            newboot['BootSourceOverrideMode'] = 'UEFI'

        # No new boot params override required
        if not newboot:
            if self.debug:
                pprint(f"No changes needed for {self.url}, skipping PATCH request.")
            return None

        data = {"Boot": newboot}
        if self.debug:
            pprint(f"Sending PATCH to {self.url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(self.url, data=data, headers=self.headers, method='PATCH')
        return urlopen(request, context=self.context)

    def _set_iso_once_dell_idrac10(self):
        """Dell iDRAC10 boot override using /Settings endpoint or iDRAC attributes."""
        settings_url = f"{self.url}/Settings"
        try:
            request = Request(settings_url, headers=self.headers)
            response = json.loads(urlopen(request, context=self.context).read())
            currentboot = response.get('Boot', {})
            if self.debug:
                pprint(f"Dell iDRAC10: Boot from /Settings: {currentboot.get('BootSourceOverrideTarget')}")
        except Exception as e:
            if self.debug:
                pprint(f"Dell iDRAC10: /Settings failed ({e}), trying iDRAC attributes")
            return self._set_iso_once_dell_idrac_attributes()

        data = {"Boot": {"BootSourceOverrideTarget": "Cd"}}
        if self.debug:
            pprint(f"Dell iDRAC10: PATCH to {settings_url}")
        data_bytes = json.dumps(data).encode('utf-8')
        request = Request(settings_url, data=data_bytes, headers=self.headers, method='PATCH')
        try:
            result = urlopen(request, context=self.context)
            pprint("Dell iDRAC10: Boot override set via /Settings")
            return result
        except Exception as e:
            if self.debug:
                pprint(f"Dell iDRAC10: /Settings PATCH failed, trying iDRAC attributes")
            return self._set_iso_once_dell_idrac_attributes()

    def _set_iso_once_dell_idrac_attributes(self):
        """Dell iDRAC10 fallback: Use iDRAC ServerBoot attributes."""
        idrac_url = f"{self.baseurl}/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/DellAttributes/iDRAC.Embedded.1"
        for device in ['VCD-DVD', 'vCD-DVD', 'Cd']:
            data = {"Attributes": {"ServerBoot.1.BootOnce": "Enabled", "ServerBoot.1.FirstBootDevice": device}}
            if self.debug:
                pprint(f"Dell iDRAC10: PATCH {idrac_url} with device={device}")
            try:
                data_bytes = json.dumps(data).encode('utf-8')
                request = Request(idrac_url, data=data_bytes, headers=self.headers, method='PATCH')
                result = urlopen(request, context=self.context)
                pprint(f"Dell iDRAC10: Boot set via iDRAC attributes (device={device})")
                return result
            except:
                continue
        raise Exception("Dell iDRAC10: All boot device attempts failed")

    def restart(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        if response['PowerState'] == 'Off':
            reset_type = 'On'
        elif self.model == 'senao':
            reset_type = 'GracefulRestart'
        else:
            reset_type = 'ForceRestart'
        data = {"ResetType": reset_type}
        reset_url = f"{self.url}/Actions/ComputerSystem.Reset"
        if self.debug:
            pprint(f"Sending POST to {reset_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(reset_url, data=data, headers=self.headers)
        return urlopen(request, context=self.context)

    def stop(self):
        current_status = self.status()
        if current_status == 'Off':
            warning("Node already powered off")
            return
        data = {"ResetType": "ForceOff"}
        reset_url = f"{self.url}/Actions/ComputerSystem.Reset"
        if self.debug:
            pprint(f"Sending POST to {reset_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(reset_url, data=data, headers=self.headers)
        return urlopen(request, context=self.context)

    def start(self):
        data = {"ResetType": "On"}
        reset_url = f"{self.url}/Actions/ComputerSystem.Reset"
        if self.debug:
            pprint(f"Sending POST to {reset_url} with {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(reset_url, data=data, headers=self.headers)
        return urlopen(request, context=self.context)

    def status(self):
        request = Request(self.url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        return response['PowerState']

    def info(self):
        request = Request(self.url, headers=self.headers)
        return json.loads(urlopen(request, context=self.context).read())

    def reset(self):
        manager_url = self.get_manager_url()
        reset_url = f"{manager_url}/Actions/Manager.Reset"
        data = {"ResetType": "GracefulRestart"}
        if self.debug:
            pprint(f"Sending POST to {reset_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(reset_url, headers=self.headers, method='POST', data=data)
        return urlopen(request, context=self.context)

    def set_iso(self, iso_url):
        result = None
        current_iso, inserted = self.get_iso_status()
        if current_iso == iso_url and inserted:
            pprint(f"Iso {iso_url} already set")
        else:
            if inserted:
                try:
                    self.eject_iso()
                except Exception as e:
                    if self.debug:
                        traceback.print_exception(e)
                    raise
            try:
                result = self.insert_iso(iso_url)
            except Exception as e:
                if self.debug:
                    traceback.print_exception(e)
                raise
            if result.code not in [200, 202, 204]:
                error(f"Hit {result.reason} When plugging {iso_url}")
                sys.exit(1)
        try:
            self.set_iso_once()
        except Exception as e:
            if self.debug:
                traceback.print_exception(e)
            self.set_iso_once()
        self.restart()

    def enable_secureboot(self):
        secureboot_url = f"{self.url}/SecureBoot"
        request = Request(secureboot_url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        enabled = response['SecureBootEnable']
        if enabled:
            warning("Secureboot already enabled")
            return
        data = {"SecureBootEnable": True}
        if self.debug:
            pprint(f"Sending PATCH to {secureboot_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(secureboot_url, headers=self.headers, method='PATCH', data=data)
        return urlopen(request, context=self.context)

    def disable_secureboot(self):
        secureboot_url = f"{self.url}/SecureBoot"
        request = Request(secureboot_url, headers=self.headers)
        response = json.loads(urlopen(request, context=self.context).read())
        enabled = response['SecureBootEnable']
        if not enabled:
            warning("Secureboot already disabled")
            return
        data = {"SecureBootEnable": False}
        if self.debug:
            pprint(f"Sending PATCH to {secureboot_url} with data {data}")
        data = json.dumps(data).encode('utf-8')
        request = Request(secureboot_url, headers=self.headers, method='PATCH', data=data)
        return urlopen(request, context=self.context)
