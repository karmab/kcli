import os


def basename(path):
    return os.path.basename(path)


def dirname(path):
    return os.path.dirname(path)


def ocpnodes(cluster, platform, masters, workers):
    masters = ['%s-master-%d' % (cluster, num) for num in range(masters)]
    workers = ['%s-worker-%d' % (cluster, num) for num in range(workers)]
    if platform in ['kubevirt', 'openstack', 'vsphere']:
        return ["%s-bootstrap-helper" % cluster] + ["%s-bootstrap" % cluster] + masters + workers
    else:
        return ["%s-bootstrap" % cluster] + masters + workers


jinjafilters = {'basename': basename, 'dirname': dirname, 'ocpnodes': ocpnodes}
