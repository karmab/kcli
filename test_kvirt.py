#!/usr/bin/python 
import sys
sys.path.append("/Users/kboumedh/CODE/git/KARIM/kcli/kvirt")
from kvirt import Kvirt

k = Kvirt('192.168.0.6')

# print k.list()
#k.info('contador')
#k.create(name='gh2', net1='private1')
#k.create(name='rapetou', net1='private1', pool='vms', backing='centos7.qcow2')
#k.create(name='blancanieves', net1='private1', pool='vms', backing='centos7.qcow2', cloudinit=True)
#k._cloudinit('wilibonka')
#k._uploadiso('wilibonka', 'vms')
k.report()
