#!/usr/bin/python
# -*- coding: utf-8 -*-

# <bitbar.title>kcli list</bitbar.title>
# <bitbar.version>v1.0</bitbar.version>
# <bitbar.author>Karim Boumedhel</bitbar.author>
# <bitbar.author.github>karmab</bitbar.author.github>
# <bitbar.desc>Lists running vms using kcli</bitbar.desc>
# <bitbar.image>https://raw.githubusercontent.com/karmab/kcli/master/kcli-small.png</bitbar.image>
# <bitbar.abouturl>https://github.com/karmab/kcli</bitbar.abouturl>

import sys
try:
    from kvirt.config import Kconfig
except:
    warning = u"\u26A0"
    warning = warning.encode('utf-8')
    print("%s\n" % warning)
    print("---\n")
    print("Kcli could not be found in your path. Is it installed?")
    sys.exit(1)

config = Kconfig(quiet=True)
k = config.k
vms = k.list()
running = [vm[0] for vm in vms if vm[1] == 'up']
off = [vm[0] for vm in vms if vm[1] == 'down']
print("Kcli %s/%s Running" % (len(running), len(vms)))
print('---')
for vm in sorted(running):
    print("%s| color=green" % vm)
    # print("%s| color=green bash=kcli param1=ssh param2=%s" % (vm, vm))
print('---')
for vm in sorted(off):
    print(vm)
    # print("%s| terminal=false refresh=true bash=kcli param1=start param2=%s" % (vm, vm))
