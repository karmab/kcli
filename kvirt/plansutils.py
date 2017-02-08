#!/usr/bin/env python

import urllib2
import json
import os


def download(url, path):
    filename = os.path.basename(url)
    print("Fetching %s" % filename)
    url = urllib2.urlopen(url)
    with open("%s/%s" % (path, filename), 'wb') as output:
        output.write(url.read())


def fetch(url, path):
    if not url.startswith('http'):
        url = "https://%s" % url
    if 'github.com' not in url or 'raw.githubusercontent.com' in url:
        download(url, path)
        return
    elif 'api.github.com' not in url:
        url = url.replace('github.com/', 'api.github.com/repos/').replace('tree/master', 'contents')
    if 'contents' not in url:
        tempurl = url.replace('https://api.github.com/repos/', '')
        user = tempurl.split('/')[0]
        repo = tempurl.split('/')[1]
        url = url.replace("%s/%s" % (user, repo), "%s/%s/contents" % (user, repo))
    if not os.path.exists(path):
        os.mkdir(path)
    r = urllib2.urlopen(url)
    try:
        base = json.load(r)
    except:
        print("Invalid url.Leaving...")
        os._exit(1)
    for b in base:
        if 'name' not in b or 'type' not in b or 'download_url' not in b:
            print("Invalid url.Leaving...")
            os._exit(1)
        filename = b['name']
        filetype = b['type']
        download_url = b['download_url']
        if filetype == 'file':
            download(download_url, path)
        elif filetype == 'dir':
            fetch("%s/%s" % (url, filename), "%s/%s" % (path, filename))
