note the downstream plan requires to execute the following on the cloudforms template in order for cloudinit to work properly

```Shell
virt-customize -a cfme-rhos-5.7.1.3-1.x86_64.qcow2 —delete /etc/cloud/cloud.cfg.d/30_miq_datasources.cfg
```
