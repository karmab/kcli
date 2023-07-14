# kfish

![Screenshot](kfish.png)

This is a side class created to interact with redfish without a need for extra libraries and used in [kcli](https://github.com/karmab/kcli) and [aicli](https://github.com/karmab/aicli) projects

## Installation

```
pip3 install kfish
```

Alternatively you can download the [source file](https://raw.githubusercontent.com/karmab/kcli/main/kvirt/kfish/__init__.py) directly

## How to use

```
from kfish import Redfish

iso_url = 'http://192.168.122.1/my.iso'
bmc_url = '192.168.122.80'
bmc_user, bmc_password = 'root', 'calvin'
model = 'dell'
debug = False
red = Redfish(bmc_url, bmc_user, bmc_password, model=bmc_model, debug=debug)
red.set_iso(iso_url)
```

The class contains the following methods

- insert_iso
- eject_iso
- info
- reset
- restart
- set_iso (which wraps insert_iso, set_iso_once and restart)
- set_iso_once
- start
- status
- stop
