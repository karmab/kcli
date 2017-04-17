##plans deployment 

As an advanced use of kcli, i have created a deployment plan and specific scripts that will deploy the following elements.

- openstack rdo
- ovirt
- manageiq
- openshift origin
- foreman

Note that a single vm is deployed for every project and as such all services are provided in a "allinone" fashion


##installation

- The deployment makes use of your private default routed network on your libvirt host, with dhcp,  using 192.168.122.0, reserving ips starting from 192.168.5.200 as openstack floating ip pool. You can then use the plan files and scripts in the [plans](https://github.com/karmab/kcli/tree/master/plans) directory

```
kcli plan -f uci.yml uci
```

##i want rhci

Provided you have the subscriptions, you can save the sample [register.sh script](register.sh) to your home directory, edit it to match your credentials and pool info and launch the deployment:

```
kcli plan -f rhci.yml rhci
```

##Launching single product 

You can also easily launch individual upstream/downstream product directly from the corresponding directory . For instance to launch upstream ovirt, run the following commands (optionally specifying a plan name)

```
cd plans/ovirt
kcli plan -f upstream.yml
```
You can do the same for downstream. Note that for openstack, there are per version downstream plan files to ease testing ( currently kilo, liberty and mitaka )


##limitations 

- Using static networking with rhel/centos cloud images is complicated as those images are per default configured to have a single dhcp nic. Best Solution is to run virt-customize in those images to enable BOOTPROTO=static
- I had issues injecting cloudinit beyond network configuration in the manageiq image. Ideally one would use appliance_console_cli and curl calls to set it up, but it refuses to work....

##Problems?

Send me a mail at [karimboumedhel@gmail.com](mailto:karimboumedhel@gmail.com) !

Mac Fly!!!

karmab
