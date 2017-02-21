#!/usr/bin/env python

import urllib2
import json
import os


def symlinks(user, repo):
    mappings = []
    url1 = 'https://api.github.com/repos/%s/%s/git/refs/heads/master' % (user, repo)
    r = urllib2.urlopen(url1)
    base = json.load(r)
    sha = base['object']['sha']
    url2 = 'https://api.github.com/repos/%s/%s/git/trees/%s?recursive=1' % (user, repo, sha)
    r = urllib2.urlopen(url2)
    try:
        base = json.load(r)
    except:
        return []
    for e in base['tree']:
        if e['mode'] == '120000':
            mappings.append(e['path'])
    return mappings


def download(url, path):
    filename = os.path.basename(url)
    print("Fetching %s" % filename)
    url = urllib2.urlopen(url)
    with open("%s/%s" % (path, filename), 'wb') as output:
        output.write(url.read())


def makelink(url, path):
    filename = os.path.basename(url)
    url = urllib2.urlopen(url)
    target = url.read()
    print("Creating symlink for %s pointing to %s" % (filename, target))
    os.symlink(target, "%s/%s" % (path, filename))


def fetch(url, path, syms=None):
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
        syms = symlinks(user, repo)
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
        filepath = b['path']
        download_url = b['download_url']
        if filepath in syms:
            makelink(download_url, path)
        elif filetype == 'file':
            download(download_url, path)
        elif filetype == 'dir':
            fetch("%s/%s" % (url, filename), "%s/%s" % (path, filename), syms=syms)
