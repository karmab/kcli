### Notes ###
- Those deployment files creates an undercloud and nodes for the overcloud, either 2 for the tripleo-simple.yml and 4 for the tripleo-advanced.yml. Also tripleo-advancedceph.yml for ceph special deployment

- A undercloud_pre.sh is passed to the undercloud machine to prepare it, installing packages, creating users and updating the system.

- Surely you should reboot undercloud ( this could be necessary as a recent kernel is needed for undercloud install to work )

- From there, one can use the undercloud.sh script as a reference for the step, making use of the provided helper scripts. Example:

```
[kcli-server]$ kcli ssh undercloud
Last login: Fri Dec 22 07:14:45 2017 from gateway

[cloud-user@undercloud ~]$ sudo su stack

[stack@undercloud cloud-user]$ cd

[stack@undercloud ~]$ ls -al
total 48
drwx------. 3 stack stack  279 dic 22 07:18 .
drwxr-xr-x. 4 root  root    37 dic 22 06:56 ..
-rw-------. 1 stack stack  380 dic 22 07:17 assignprofiles.sh
-rw-------. 1 stack stack   32 dic 22 07:22 .bash_history
-rw-r--r--. 1 stack stack   18 jul 12  2016 .bash_logout
-rw-r--r--. 1 stack stack  193 jul 12  2016 .bash_profile
-rw-r--r--. 1 stack stack  231 jul 12  2016 .bashrc
-rw-------. 1 stack stack  207 dic 22 07:17 clean.sh
-rw-------. 1 stack stack  379 dic 22 07:17 deploy.sh
drwxrwxr-x. 2 stack stack   36 dic 22 07:18 .instack
-rw-------. 1 stack stack  870 dic 22 07:17 instackenv.sh
-rw-------. 1 stack stack 1458 dic 22 07:17 templates.tar.gz
-rw-------. 1 stack stack  391 dic 22 07:17 undercloud.conf
-rw-rw-r--. 1 stack stack 1650 dic 22 07:18 undercloud-passwords.conf
-rw-------. 1 stack stack 1148 dic 22 07:17 undercloud.sh

[stack@undercloud ~]$ bash undercloud.sh
....

```


- Note we explicitly dont want to used nested cos it s causing some issues on :

  - the undercloud, when trying to customize overcloud images
  - the overcloud, when launching vms. Note that deploy.sh script sets the libvirt type to qemu ( though you wouldnt use this line on real production)

- Important to have the provisioning network without nat also on the hypervisor
```
echo net.ipv4.conf.all.rp_filter=0 >> /etc/sysctl.d/99-sysctl.conf
echo net.ipv4.conf.default.rp_filter=0 >> /etc/sysctl.d/99-sysctl.conf
sysctl -p /etc/sysctl.conf
```

  You can check it with
```
cat /proc/sys/net/ipv4/conf/all/rp_filter
cat /proc/sys/net/ipv4/conf/default/rp_filter
```

- `openstack undercloud install` cant be launched from cloudinit , as a tty is required (for sudo).

- Investigate whether disabling requiretty is enough

- IMPORTANT: you will need http://mirror.centos.org/centos/7/cloud/x86_64/openstack-mitaka/common/ipxe-roms-qemu-20160127-1.git6366fa7a.el7.noarch.rpm if using a centos hypervisor

- If you decide to modify templates, you should compress folder (tar.gz) again. Becaus it's `templates.tar.gz` what is really copied to undercloud.
