from base64 import b64encode
import json
from kvirt.common import error, pprint
from urllib.request import urlopen, Request
import ssl


class KsphereTag:
    def __init__(self, vcip, user, password):
        ssl._create_default_https_context = ssl._create_unverified_context
        self.url = f'https://{vcip}/rest/com/vmware/cis/tagging'
        auth_url = f'https://{vcip}/rest/com/vmware/cis/session'
        b64_auth = b64encode(f"{user}:{password}".encode()).decode()
        headers = {'Authorization': f"Basic {b64_auth}"}
        request = Request(auth_url, headers=headers, method='POST')
        resp = urlopen(request)
        status_code = resp.getcode()
        if status_code != 200:
            error(f'Error! API responded with: {status_code}')
            error(resp.reason)
            return
        self.sid = json.loads(resp.read())['value']

    def _delete(self, url):
        request = Request(url, headers={'vmware-api-session-id': self.sid}, method='DELETE')
        resp = urlopen(request)
        if resp.getcode() not in [200, 201]:
            error(resp.reason)

    def _get(self, url):
        request = Request(url, headers={'vmware-api-session-id': self.sid})
        resp = urlopen(request)
        if resp.getcode() not in [200, 201]:
            error(resp.reason)
            return None
        else:
            return json.loads(resp.read())

    def _post(self, url, data):
        data = json.dumps(data).encode('utf-8')
        request = Request(url, data=data, headers={'vmware-api-session-id': self.sid,
                                                   'content-type': 'application/json'})
        resp = urlopen(request)
        if resp.getcode() not in [200, 201]:
            error(resp.reason)
        else:
            return json.loads(resp.read())

    def list_categories(self):
        data = self._get(f'{self.url}/category')['value']
        return data

    def create_category(self, category):
        pprint(f"Creating category {category}")
        create_spec = {"associable_types": ["VirtualMachine"], "cardinality": "MULTIPLE", "description": category,
                       "name": category}
        data = {'create_spec': create_spec}
        return self._post(f'{self.url}/category', data=data)['value']

    def delete_category(self, category):
        pprint(f"Deleting category {category}")
        category_id = self.get_category_id(category)
        self._delete(f'{self.url}/category/id:{category_id}')

    def get_category_id(self, category):
        if category.startswith('urn:vmomi'):
            return category
        for c in self.list_categories():
            resp = self._get(f'{self.url}/category/id:{c}')['value']
            if resp['name'] == category:
                return resp['id']

    def get_tag_id(self, tag):
        for t in self.list_tags():
            resp = self._get(f'{self.url}/tag/id:{t}')['value']
            if resp['name'] == tag:
                return resp['id']

    def get_tag_name(self, tag_id):
        for t in self.list_tags():
            resp = self._get(f'{self.url}/tag/id:{t}')['value']
            if resp['id'] == tag_id:
                return resp['name']

    def list_tags(self):
        data = self._get(f'{self.url}/tag')['value']
        return data

    def create_tag(self, category, tag):
        pprint(f"Creating tag {tag}")
        if category.startswith('urn:vmomi'):
            category_id = category
        else:
            category_id = self.get_category_id(category)
        create_spec = {"category_id": category_id, "description": tag, "name": tag, "tag_id": ""}
        data = {'create_spec': create_spec}
        return self._post(f'{self.url}/tag', data=data)['value']

    def delete_tag(self, tag):
        pprint(f"Deleting tag {tag}")
        tag_id = self.get_tag_id(tag)
        self._delete(f'{self.url}/tag/id:{tag_id}')

    def add_tag(self, vm_id, tag):
        pprint(f"Attaching tag {tag}")
        if tag.startswith('urn:vmomi'):
            tag_id = tag
        else:
            tag_id = self.get_tag_id(tag)
        object_id = {"id": vm_id, "type": "VirtualMachine"}
        data = {'object_id': object_id}
        return self._post(f'{self.url}/tag-association/id:{tag_id}?~action=attach', data=data)['value']

    def add_tags(self, vm_id, tag_ids):
        object_id = {"id": vm_id, "type": "VirtualMachine"}
        data = {'object_id': object_id, 'tag_ids': tag_ids}
        return self._post(f'{self.url}/tag-association?~action=attach-multiple-tags-to-object', data=data)

    def list_vm_tags(self, vm_id):
        tags = []
        object_id = {"id": vm_id, "type": "VirtualMachine"}
        data = {'object_id': object_id}
        for tag_id in self._post(f'{self.url}/tag-association?~action=list-attached-tags', data=data)['value']:
            tags.append(self.get_tag_name(tag_id))
        return tags
