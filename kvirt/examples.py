diskcreate = """# Add a 10G disk to vm, using default pool
$ kcli create disk -s 10 vm1

# Add 5GB disk to vm1, using a pool named images
$ kcli create disk -s 5 -p images vm2
"""

diskdelete = """# Delete disk named xxx.img
$ kcli delete disk xxx.img

# Delete disk named vm1_2.img from vm vm1
$ kcli delete disk --vm vm1 vm1_2.img
"""

dnscreate = """# Create a dns entry
$ kcli create dns -d karmalabs.corp -i 192.168.122.253 api.jhendrix

# Do the same for a different network
$ kcli create dns -n network2 -d karmalabs.corp -i 192.168.122.253 api.jhendrix

# Do the same with an extra wildcard alias
$ kcli create dns -d karmalabs.corp -i 104.197.157.226 -a '*' api.jhendrix
"""

hostcreate = """# Add a kvm host
$ kcli create host kvm -H 192.168.1.6 twix

# Add an aws host
$ kcli create host aws --access_key_id xxx  --access_key_secret xxx  -k KEYPAIR mypair -r eu-west-3 myaws

# Add a gcp host
$ kcli create host gcp --credentials ~/.kcli/xx.json --project myproject-209909 --zone us-central1-b mygcp

# Add an ovirt host
$ kcli create host ovirt -c mycluster -d mydatacenter -H 192.168.1.2 -u admin@internal -p pass -o org1 --pool x myovirt

# Add a vsphere host
$ kcli create host vsphere -c mycluster -d mydatacenter -H 192.168.1.3 -u admin@xxx.es -p pass mysphere

# Add an openstack host
$ kcli create host openstack --auth-url http://10.19.114.91:5000/v3 -u admin -p pass --project myproject myosp

# Add a kubevirt host using existing k8s credentials
$ kcli create host kubevirt mykubevirt

# Add an ibm host
$ kcli create host ibm --iam_api_key xyz --vpc myvpc --zone eu-de -r eu-de-2 myibm

# Add a host group
$ kcli create host group --members [hypervisor1,hypervisor2] --algorithm random mygroup
"""

_list = """# Get list of vms
$ kcli list vm

# Get list of vms from all hosts/clients
$ kcli -C all list vm

# Get list of products
$ kcli list product

# Get list of clients/hosts
$ kcli list host
"""

niccreate = """# Add a nic from default network to vm1
$ kcli create nic -n default vm1
"""

nicdelete = """# Delete nic named eth2 from vm1
$ kcli delete nic -i eth2 vm1
"""

plancreate = """# Create a plan named ocp311 from a file
$ kcli create plan -f multi.yml ocp311

# Do the same but customize some parameters
$ kcli create plan -f multi.yml -P ctlplanes=1 -P nodes=2 -P crio=true

# Create a plan from a remote url, customizing some parameters
$ kcli create plan -u https://github.com/karmab/kcli-plans/blob/main/kubernetes/kubernetes.yml -P ctlplanes=3
"""

planinfo = """# Get info from a local plan file
$ kcli info plan -f multi.yml

# Get info of a plan with a remote url
$ kcli info plan -u https://github.com/karmab/kcli-plans/blob/main/kubernetes/kubernetes.yml
"""

productinfo = """# Get info from product kubernetes
$ kcli info product kubernetes
"""

repocreate = """# Create a product repo from karmab samples repo
$ kcli create repo -u https://github.com/karmab/kcli-plans karmab
"""

start = """# Start vms named vm1 and vm2
$ kcli start vm vm1 vm2

# Start all vms of plan X
$ kcli start plan X

# Start container named my container
$ kcli start container mycontainer
"""

vmcreate = """# Create a centos vm from image centos8stream with a random name
$ kcli create vm -i centos8stream

# Create a centos vm named myvm customizing its memory and cpus
$ kcli create vm -i centos8stream -P memory=4096 -P numcpus=4

# Pass disks, networks and even cmds
$ kcli create vm -i centos8stream -P disks=[10,20] -P nets=[default] -P cmds=['yum -y install nc']

# Use more advanced information for nets
$ kcli create vm -i centos8stream -P nets=['{"name": "default", "type": "e1000"}']

# Or specify a custom mtu
$ kcli create vm -i centos8stream -P nets=['{"name": "default", "mtu": 1400}']

# Create a vm with static ip
$ img=centos8stream
$ kcli create vm -i $img -P nets=['{"name":"default","ip":"192.168.122.250","netmask":"24","gateway":"192.168.122.1"}']

# Use more advanced information for disks
$ kcli create vm -i centos8stream -P disks=['{"size": 10, "interface": "sata"}']

# Create a vm from a custom profile
$ kcli create vm -p myprofile myvm

# Boot an empty vm from a given iso
$ kcli create vm -P iso=xxx.iso myvm
"""

vmconsole = """# Open a graphical console for vm ( only shows the command if using container)
$ kcli console myvm

# Get a serial console to the vm
$ kcli console -s myvm
"""

vmexport = """# Export vm myvm with a specific name for the generated image
$ kcli export -i myimage myvm
"""

kubegenericcreate = """# Create a kube instance named mykube with default values
$ kcli create kube generic mykube

# Do the same but customize some parameters
$ kcli create kube generic -P ctlplanes=1 -P workers=2 mykube

# Use a parameter file
$ kcli create kube generic --paramfile=myparameters.yml mykube
"""

kubekindcreate = """# Create a kube kind instance named mykube with default values
$ kcli create kube kind mykind

# Do the same with workers
$ kcli create kube kind -P workers=2 mykind

# Use a parameter file
$ kcli create kube kind --paramfile=myparameters.yml mykind
"""

kubemicroshiftcreate = """# Create a kube microshift instance named mymicroshift with default values
$ kcli create kube microshift mymicroshift

# Create a kube microshift instance named mymicroshift providing rhn creds on the commandline
$ kcli create kube microshift -P rhnuser=xxx@good.es -P rhnpassword=supercool mymicroshift

# Create a kube microshift instance named mymicroshift based on centos8stream
$ kcli create kube microshift -P image=cento8stream mymicroshift

# Use a parameter file
$ kcli create kube microshift --paramfile=myparameters.yml mymicroshift
"""

kubek3screate = """# Create a kube k3s instance named mykube with default values
$ kcli create kube k3s myk3s

# Do the same with workers
$ kcli create kube k3s -P workers=2 myk3s

# Use a parameter file
$ kcli create kube k3s --paramfile=myparameters.yml myk3s
"""

kubehypershiftcreate = """# Create a kube hypershift instance named mykube with default values
$ kcli create kube hypershift myhypershift

# Do the same but customize some parameters
$ kcli create kube hypershift -P workers=3 myhypershift

# Use a parameter file
$ kcli create kube hypershift --paramfile=myparameters.yml myhypershift
"""

kubeopenshiftcreate = """# Create a kube openshift instance named mykube with default values
$ kcli create kube openshift myopenshift

# Do the same but customize some parameters
$ kcli create kube openshift -P ctlplanes=1 -P workers=2 myopenshift

# Use a parameter file
$ kcli create kube openshift --paramfile=myparameters.yml myopenshift
"""

vmdatacreate = """# Generate a basic ignition file for rhcos4.6
$ kcli create vmdata -i rhcos46

# Do the same without injecting any hostname
$ kcli create vmdata -i rhcos46 -P minimal=true

# Do the same but force the name
$ kcli create vmdata -i rhcos46 myname

# Inject a custom script and a file in /root
$ kcli create vmdata -i rhcos -P scripts=[myscript.sh] -P files=[myfile.txt] zzz

# Generate a cloudinit userdata
$ kcli create vmdata -i centos8stream myname
"""

plandatacreate = """# Generate all the ignition/cloudinit userdatas from a plan file
$ kcli create plandata -f my_plan.yml
"""

plantemplatecreate = """# Create a sample plan template and store it in mydir
$ kcli create plantemplate mydir
"""

isocreate = """# Generate an openshift iso
$ kcli create openshift-iso myopenshift.karmalabs.corp

# Do the same for a 4.5 install
$ kcli create openshift-iso -P version=4.5 myopenshift.karmalabs.corp

# Embed a local target ignition in the iso
$ kcli create openshift-iso -f my_ignition.ign myopenshift

# Only creates the ignition for the iso
$ kcli create openshift-iso -P iso=false myopenshift.karmalabs.corp

# Force the ip to use in /etc/hosts of the machine at first boot
$ kcli create openshift-iso -P api_ip=192.168.1.20 myopenshift.karmalabs.corp

# Disable ens4 in the iso
$ kcli create openshift-iso -P disable_nics=[ens4] myopenshift.karmalabs.corp

# Inject static ip for ens3
$ CLUSTER="myopenshift.karmalabs.corp"
$ kcli create openshift-iso -P nets=['{"ip":"192.168.0.8","netmask":"24","gateway":"192.168.0.1"}'] $CLUSTER

# Provide extra args for first boot of the node
$ kcli create openshift-iso -P extra_args="super_string_of_args" myopenshift.karmalabs.corp
"""

disconnectedcreate = """# Generate an openshift disconnected vm for 4.12
$ kcli create openshift-registry -P version=stable -P tag='4.12'

# Do the same over an ipv4 network
$ kcli create openshift-registry -P version=nightly -P tag='4.12' -P disconnected_ipv6_network=false

# Use specific version and add extra operators (from 4.13)
$ kcli create openshift-registry -P version=nightly -P tag=4.13 -P disconnected_operators=[sriov-network-operator]

# Deploy registry without content
$ kcli create openshift-registry -P disconnected_sync=false
"""

appopenshiftcreate = """# Deploy sriov network operator
$ kcli create app openshift sriov-network-operator

# Deploy local storage using parameters from your openshift install and creating a localvolume for each node
$ kcli create app openshift local-storage --paramfile your_paramfile.yml

# Deploy local storage without the cr
$ kcli create app openshift local-storage -P install_cr=false

# Force a specific csv for a given operator
$ kcli create app openshift serverless-operator -P csv=serverless-operator.v1.22.0

# Set installplan to manual
$ kcli create app openshift serverless-operator -P installplan=manual
"""

changelog = """Get commits between current version and main
$ kcli changelog

# Do the same between current version and a given sha
$ kcli changelog sha1

# Use a commit number
$ kcli changelog f173cb7e032a5b72092451255c58dfec8b11af35

# Get commits between two shas
$ kcli changelog sha1 sha2
"""

workflowcreate = """# Run workflow from a single script
$ kcli run workflow myscript.sh

# Run workflow based on some scripts and files
$ kcli run workflow -P scripts=[deploy.sh] -P files=[file1,file2] myworkflow

# Run workflow on a kcli vm
$ kcli run workflow myscript.sh -P target=myvm

# Force the user
$ kcli run workflow myscript.sh -P target=root@myvm

# Run workflow on another target/host
$ kcli run workflow myscript.sh -P target=192.168.1.1

# Run workflow from some commands
$ kcli run workflow myworkflow -P cmds=[hostname]

# Only output assets to dir without running
$ kcli run workflow myscript.sh -do mydir

"""

kubegenericscale = """# Scale workers from generic cluster myclu
$ kcli scale cluster generic -P workers=3 myclu

# Scale ctlplanes
$ kcli scale cluster generic -P ctlplanes=3 myclu

# Scale both ctlplanes and workers
$ kcli scale cluster generic -P ctlplanes=3 -P workers=2 myclu

# Alternative way to indicate workers
$ kcli scale cluster generic --workers 3 myclu
"""

kubek3sscale = """# Scale workers from k3s cluster myclu
$ kcli scale cluster k3s -P workers=3 myclu

# Scale ctlplanes
$ kcli scale cluster k3s -P ctlplanes=3 myclu

# Scale both ctlplanes and workers
$ kcli scale cluster k3s -P ctlplanes=3 -P workers=2 myclu

# Alternative way to indicate workers
$ kcli scale cluster k3s --workers 3 myclu

# Alternative way to indicate ctlplanes
$ kcli scale cluster k3s --ctlplanes 3 myclu
"""

kubeopenshiftscale = """# Scale workers from openshift cluster myclu
$ kcli scale cluster openshift -P workers=3 myclu

# Scale ctlplanes
$ kcli scale cluster openshift -P ctlplanes=3 myclu

# Scale both ctlplanes and workers
$ kcli scale cluster openshift -P ctlplanes=3 -P workers=2 myclu

# Alternative way to indicate workers
$ kcli scale cluster openshift --workers 3 myclu

# Alternative way to indicate ctlplanes
$ kcli scale cluster openshift --ctlplanes 3 myclu
"""

networkupdate = """# Change network to isolated
$ kcli update network mynetwork -i

# Disable dhcp
$ kcli update network mynetwork --nodhcp

# Enable dhcp
$ kcli update network mynetwork -P dhcp=true

# Change domain
$ kcli update network mynetwork --domain superdomain.com

# Update plan
$ kcli update network mynetwork -P plan=newplan
"""

starthosts = """# Start Baremetal hosts declared in a parameter file from specific ISO url

$ kcli start baremetal-hosts --pf baremetal_hosts.yml -P iso_url=http://192.168.122.1/my.iso

baremetal_hosts.yml contains
bmc_user: admin
bmc_password: admin
baremetal_hosts:
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm1
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm2

# Start single host
$ iso_url=http://192.168.122.1/my.iso
$ bmc_url=http://192.168.122.1:9000/redfish/v1/Systems/local/vm1
$ kcli start baremetal-host -P url=$bmc_url -P iso_url=$iso_url -P user=admin -P password=admin
"""

stophosts = """# Stop Baremetal hosts declared in a parameter file

$ kcli stop baremetalhosts --pf baremetal_hosts.yml

baremetal_hosts.yml contains
bmc_user: admin
bmc_password: admin
baremetal_hosts:
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm1
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm2

# Stop single host
$ bmc_url=http://192.168.122.1:9000/redfish/v1/Systems/local/vm1
$ kcli stop baremetal-host -P url=$bmc_url -P user=admin -P password=admin
"""

infohosts = """# Report info on Baremetal hosts declared in a parameter file

$ kcli info baremetalhosts --pf baremetal_hosts.yml

baremetal_hosts.yml contains
bmc_user: admin
bmc_password: admin
baremetal_hosts:
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm1
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm2

# Report info on a single host
$ bmc_url=http://192.168.122.1:9000/redfish/v1/Systems/local/vm1
$ kcli info baremetal-host -P url=$bmc_url -P user=admin -P password=admin
"""

ocdownload = """# Download 4.12 stable
$ kcli download oc -P version=stable -P tag=4.12

# Download specific tag
$ kcli download oc -P version=tag -P tag=4.11.16

# Download nightly
$ kcli download oc -P version=nightly -P tag=4.12

# Download older version from CI
$ kcli download oc -P version=ci -P tag=4.10
"""

openshiftdownload = """# Download 4.12 stable
$ kcli download openshift-install -P version=stable -P tag=4.12

# Download specific tag
$ kcli download openshift-install -P version=tag -P tag=4.11.16

# Download nightly
$ kcli download openshift-install -P version=nightly -P tag=4.12

# Download older version from CI
$ kcli download openshift-install -P version=ci -P tag=4.10
"""

securitygroupcreate = """# Create a security group named mygroup and opening tcp ports 22 and 25
$ kcli create security-group -P ports=[22,25] mygroup

# Do the same, but with udp port 53 too
$ kcli create security-group -P ports=['22,25,{"from": "53", "protocol": "udp"}'] mygroup

# Open a port range
$ kcli create security-group -P ports=['{"from": "8000", "to": "9000"}'] mygroup
"""

networkcreate = """# Create a network
$ kcli create network -c 192.168.123.0/24 mynetwork

# Create a network with specific dhcp range
$ kcli create network -c 192.168.123.0/24 -P dhcp_start=192.168.123.40 -P dhcp_end=192.168.123.60 mynetwork

# Create a network without dhcp
$ kcli create network -c 192.168.123.0/24 --nodhcp mynetwork

# Create an isolated network
$ kcli create network -c 192.168.123.0/24 -i mynetwork

# Create a network with a dedicated pxe server
$ kcli create network -c 192.168.123.0/24 -P pxe=192.168.123.2 mynetwork

# Create an ipv6 network
$ kcli create -c 2620:52:0:1302::/64 mynetwork

# Create a dual network
$ kcli create -c 192.168.123.0/24 -d 2620:52:0:1302::/64 mynetwork

# Create a network allowing specific networks communication
$ kcli create network -c 192.168.123.0/24 -P allowed_nets=[default,mynetwork2] mynetwork

# Create a network with a forward bridge
$ kcli create network -P bridge=true br0

# Create a network with a forward bridge and specifying the target bridge name
$ kcli create network -P bridge=true -P bridgename=br0 superbr0

# Create a network with an ovs bridge and specific vlans
$ kcli create network -P ovs=true -P vlans=[10,20] myovsbridge

# Create a network using macvtap an a given nic
$ kcli create network -P macvtap=true -P nic=eno2 mytap

# Create a network with custom dnsmasq options
$ kcli create network -c 192.168.123.0/24 -P arp-timeout=120 mynetwork

# Create a br-ex network attachment definition using ovs cni (on kubevirt)
$ kcli create network -P type=ovs br-ex

# Create a br-ex network attachment definition using ovs cni (on kubevirt)
$ kcli create network -P ovs=true br-ex

# Create an ovs bridge br0 network (on libvirt)
$ kcli create network -P ovs=true br0
"""

profilecreate = """# Create profile with specific image
$ kcli create profile -i ubuntu-22.10-server-cloudimg-amd64.img -P memory=4096 -P disks=[20,30] myprofile

# Do the same providing everything as parameter
$ kcli create profile -P image=ubuntu-22.10-server-cloudimg-amd64.img -P memory=4096 -P disks=[20,30] myprofile

# Create a profile without image, with uefi and without startingthe corresponding vm
$ kcli create profile -P uefi=true -P start=false -P memory=4096 -P disks=[20,30] myprofile
"""
