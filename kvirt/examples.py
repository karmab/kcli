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

# Add a proxmox host
$ kcil create host proxmox -H 192.168.1.4 --insecure -u root@pam -p pass --pool local-lvm myproxmox

# Add a host group
$ kcli create host group --members [hypervisor1,hypervisor2] --algorithm random mygroup
"""

providercreate = """# Install aws provider dependencies
$ kcli install provider aws

# Install vsphere provider dependencies through pip
$ kcli install provider vsphere -p
"""

_list = """# Get list of vms
$ kcli list vm

# Get list of vms from all hosts/clients
$ kcli -C all list vm

# Get list of clients/hosts
$ kcli list host
"""

niccreate = """# Add a nic from default network to vm1
$ kcli create nic -n default vm1

# Add a nic with e1000 model
$ kcli create nic -n default -m e1000 vm1
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

# Skip pre check
$ kcli create plan -f multi.yml -P pre=false

# Run plan treating vm with installer in its name as a workflow
$ kcli create plan -P installer_workflow=true
"""

planinfo = """# Get info from a local plan file
$ kcli info plan -f multi.yml

# Get info of a plan with a remote url
$ kcli info plan -u https://github.com/karmab/kcli-plans/blob/main/kubernetes/kubernetes.yml

# Get info for a specific running plan
$ kcli info plan myplan

# Filter information for a specific plan
$ kcli info plan myplan -P field=status

# Filter information for a specific plan and a specific vm
$ kcli info plan myplan -P field=status -P name=myvm01

# Get all vms of a specific plan which are down
$ kcli info plan myplan -P field=status -P value=down
"""

start = """# Start vms named vm1 and vm2
$ kcli start vm vm1 vm2

# Start all vms of plan X
$ kcli start plan X

# Start container named my container
$ kcli start container mycontainer
"""

vmcreate = """# Create a centos vm from image centos9stream with a random name
$ kcli create vm -i centos9stream

# Create a centos vm named myvm customizing its memory and cpus
$ kcli create vm -i centos9stream -P memory=4096 -P numcpus=4 myvm

# Create a centos vm named myvm with specific cpu topology
$ kcli create vm -i centos9stream -P cores=4 -P sockets=2 -P threads=2 myvm

# Pass disks, networks and even cmds
$ kcli create vm -i centos9stream -P disks=[10,20] -P nets=[default] -P cmds=['yum -y install nc']

# Force root password
$ kcli create vm -i centos9stream -P rootpassword=hendrix

# Use more advanced information for nets, such as specifying the nic driver
$ kcli create vm -i centos9stream -P nets=['{"name": "default", "type": "e1000"}']

# Or force mac address
$ kcli create vm -i centos9stream -P nets=['{"name": "default", "mac": "aa:aa:aa:bb:bb:90"}']

# Or specify a custom mtu
$ kcli create vm -i centos9stream -P nets=['{"name": "default", "mtu": 1400}']

# Create a vm with static ip
$ img=centos9stream
$ kcli create vm -i $img -P nets=['{"name":"default","ip":"192.168.122.250","netmask":"24","gateway":"192.168.122.1"}']

# Create a vm with a dns entry
$ kcli create vm -i centos9stream -P nets=['{"name":"default","reservedns":"true"}']

# Create a vm with a dhcp reservation
$ kcli create vm -i centos9stream -P nets=['{"name":"default","ip":"192.168.122.250","reserveip":"true"}']

# Use more advanced information for disks
$ kcli create vm -i centos9stream -P disks=['{"size": 10, "interface": "sata"}']

# Force wwn
$ kcli create vm -i centos9stream -P disks=['{"size": 10, "interface": "scsi", "wwn": "5000c50015ea71ad"}']

# Create a vm with a file /root/myfile.txt, rendered from current directory
$ kcli create vm -i centos9stream -P files=[myfile.txt]

# Use extra variables when rendering this file
$ kcli create vm -i centos9stream -P nets=['{"path": "/etc/motd", "origin": "myfile.txt"}']

# Create a vm with a file /root/myfile.txt, rendered from current directory
$ kcli create vm -i centos9stream -P files=[myfile.txt]

# Create a vm from a custom profile
$ kcli create vm -p myprofile myvm

# Boot an empty vm from a given iso
$ kcli create vm -P iso=xxx.iso myvm

# Create a GCP vm with 2 nvidia-tesla-t4 gpus
$ kcli create vm -i ubuntu-minimal-2204-lts -P gpus=['{"type": "nvidia-tesla-t4", "count": 2}'] myvm

# Create 3 vms to emulate baremetal
$ kcli create vm -P start=false -P memory=20480 -P numcpus=16 -P disks=[200] -P uefi=true -P nets=[default] -c 3 myclu

# Create an sriov enabled vm (on KVM only)
$ kcli create vm -i centos9stream -P nets=['{"name": "default"}','{"name": "default", "sriov": "true"}']
"""

vmconsole = """# Open a graphical console for vm (only show the command if using container)
$ kcli console myvm

# Get a serial console to the vm
$ kcli console -s myvm
"""

vmexport = """# Export vm myvm with a specific name for the generated image
$ kcli export -i myimage myvm
"""

kubeakscreate = """# Create an aks instance named myaks
$ kcli create kube aks -P network=subnet-1 myaks

# Use a parameter file
$ kcli create kube aks --paramfile=myparameters.yml myaks
"""

kubeekscreate = """# Create an eks instance named myeks (specifying two subnets in different AZs)
$ kcli create kube eks -P network=subnet-1 -P extra_networks=[subnet-2] myeks

# Specify custom role for ctlplane
$ kcli create kube eks -P network=subnet-1 -P extra_networks=[subnet-2] -P ctlplane_role=role1 myeks

# Use a parameter file
$ kcli create kube eks --paramfile=myparameters.yml myeks
"""

kubegenericcreate = """# Create a kube instance named mykube with default values
$ kcli create kube generic mykube

# Do the same but customize some parameters
$ kcli create kube generic -P ctlplanes=1 -P workers=2 mykube

# Use a parameter file
$ kcli create kube generic --paramfile=myparameters.yml mykube
"""

kubegkecreate = """# Create a gke instance named mygke with default values
$ kcli create kube gke mygke

# Use a parameter file
$ kcli create kube gke --paramfile=myparameters.yml mygke
"""

kubemicroshiftcreate = """# Create a kube microshift instance named mymicroshift with default values
$ kcli create kube microshift mymicroshift

# Create a kube microshift instance named mymicroshift providing rhn creds on the commandline
$ kcli create kube microshift -P rhnuser=xxx@good.es -P rhnpassword=supercool mymicroshift

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

kuberke2create = """# Create a kube rke2 instance named mykube with default values
$ kcli create kube rke2 myrke2

# Do the same with workers
$ kcli create kube rke2 -P workers=2 myrke2

# Use a parameter file
$ kcli create kube rke2 --paramfile=myparameters.yml myrke2
"""

openshiftsnocreate = """# Create an SNO openshift iso named mysno with default values
$ kcli create openshift-sno myopenshift

# Do the same but wait for install
$ kcli create openshift-sno -P sno_wait=true myopenshift

# Inject an extra vip in the ISO
$ kcli create openshift-sno -P api_ip=192.168.1.251 myopenshift

$ kcli create openshift-sno --paramfile=myparameters.yml myopenshift
"""

vmdatacreate = """# Generate a basic ignition file for rhcos4.6
$ kcli create vm-data -i rhcos46

# Do the same without injecting any hostname
$ kcli create vm-data -i rhcos46 -P minimal=true

# Do the same but force the name
$ kcli create vm-data -i rhcos46 myname

# Inject a custom script and a file in /root
$ kcli create vm-data -i rhcos -P scripts=[myscript.sh] -P files=[myfile.txt] zzz

# Generate a cloudinit userdata
$ kcli create vm-data -i centos9stream myname
"""

plandatacreate = """# Generate all the ignition/cloudinit userdatas from a plan file
$ kcli create plan-data -f my_plan.yml
"""

plantemplatecreate = """# Create a sample plan template and store it in mydir
$ kcli create plan-template mydir
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

disconnectedcreate = """# Generate an openshift disconnected vm for 4.17
$ kcli create openshift-registry -P version=stable -P tag='4.17'

# Do the same over an ipv4 network
$ kcli create openshift-registry -P version=nightly -P tag='4.17' -P disconnected_ipv6_network=false

# Use specific version and add extra operators (from 4.17)
$ kcli create openshift-registry -P version=nightly -P tag='4.17' -P disconnected_operators=[sriov-network-operator]

# Deploy registry without content
$ kcli create openshift-registry -P disconnected_sync=false
"""

disconnectedupdate = """# Update openshift disconnected registry for 4.17
$ kcli update openshift-registry -P version=stable -P tag='4.17' -P disconnected_url=192.168.122.200.sslip.io:5000 myreg

# Update openshift disconnected registry taking parameter from existing cluster install named myopenshift
$ kcli update openshift-registry -P tag='4.17.0' myopenshift
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

# Wait longer on a given operator
$ kcli create app openshift multicluster-engine -P timeout=600
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

imagedownload = """# Download centos9stream image
$ kcli download image centos9stream

# Download in specific pool
$ kcli download image centos9stream -P pool=mypool

# Download specific arch
$ kcli download image centos9stream -P arch=aarch64

# Execute commands after download
$ kcli download image centos9stream -P cmds=['echo welcome here > /etc/motd']

# Download with specific name
$ kcli download image centos9stream -P name=centos9

# Force the size (kubevirt specific)
$ kcli download image rhcoslatest -P size=40

# Download qemu variant for rhcos (kvm specific)
$ kcli download image rhcoslatest -P qemu=true

# Download rhcos associated to current openshift-installer
$ kcli download image rhcoslatest -P installer=true

# Download image from specific url
$ kcli download image -P url=http://super.qcow2 super
"""

isodownload = """# Download debian iso
$ kcli download iso -P url=https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/debian-12.6.0-amd64-netinst.iso

# Download iso to specific pool
$ kcli download iso -P url=http://super.iso -P pool=mypool
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
$ kcli run workflow myscript.sh -o mydir

"""

kubeaksscale = """# Scale nodes from aks cluster myeks
$ kcli scale cluster aks -P workers=3 myaks

# Alternative way to indicate workers
$ kcli scale cluster aks --workers 3 myaks

"""

kubeeksscale = """# Scale nodes from eks cluster myeks
$ kcli scale cluster eks -P workers=3 myeks

# Alternative way to indicate workers
$ kcli scale cluster eks --workers 3 myeks

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

kubegkescale = """# Scale nodes from gke cluster mygke
$ kcli scale cluster gke -P workers=3 mygke

# Alternative way to indicate workers
$ kcli scale cluster gke --workers 3 mygke

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

kuberke2scale = """# Scale workers from rke2 cluster myclu
$ kcli scale cluster rke2 -P workers=3 myclu

# Scale ctlplanes
$ kcli scale cluster rke2 -P ctlplanes=3 myclu

# Scale both ctlplanes and workers
$ kcli scale cluster rke2 -P ctlplanes=3 -P workers=2 myclu

# Alternative way to indicate workers
$ kcli scale cluster rke2 --workers 3 myclu

# Alternative way to indicate ctlplanes
$ kcli scale cluster rke2 --ctlplanes 3 myclu
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

resethosts = """# Reset bare metal hosts declared in a parameter file

$ kcli reset baremetal-hosts --pf baremetal_hosts.yml

baremetal_hosts.yml contains
bmc_user: admin
bmc_password: admin
baremetal_hosts:
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm1
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm2

# Reset a single host
$ kcli reset baremetal-host -P user=admin -P password=admin 10.10.10.10

# Reset a single host with dedicated flags for credentials
$ kcli reset baremetal-host -u admin -p admin 10.10.10.10
"""

starthosts = """# Start bare metal hosts declared in a parameter file from specific ISO url

$ kcli start baremetal-hosts --pf baremetal_hosts.yml -P iso_url=http://192.168.122.1/my.iso

baremetal_hosts.yml contains
bmc_user: admin
bmc_password: admin
baremetal_hosts:
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm1
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm2

# Start a single host
$ kcli start baremetal-host -P user=admin -P password=admin 10.10.10.10

# Start a single host with dedicated flags for credentials
$ kcli start baremetal-host -u admin -p admin 10.10.10.10
"""

stophosts = """# Stop bare metal hosts declared in a parameter file

$ kcli stop baremetalhosts --pf baremetal_hosts.yml

baremetal_hosts.yml contains
bmc_user: admin
bmc_password: admin
baremetal_hosts:
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm1
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm2

# Stop a single host
$ kcli stop baremetal-host -P user=admin -P password=admin 10.10.10.10

# Stop a single host with dedicated flags for credentials
$ kcli stop baremetal-host -u admin -p admin 10.10.10.10
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
$ kcli info baremetal-host -P user=admin -P password=admin 10.10.10.10

# Report info on a single host with dedicated flags for credentials
$ kcli info baremetal-host -u admin -p admin 10.10.10.10
"""

updatehosts = """# Update bare metal hosts declared in a parameter file

$ kcli update baremetal-hosts --pf baremetal_hosts.yml -P secureboot=true

baremetal_hosts.yml contains
bmc_user: admin
bmc_password: admin
baremetal_hosts:
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm1
- bmc_url: http://192.168.122.1:9000/redfish/v1/Systems/local/vm2

# Update a single host
$ kcli update baremetal-host -P user=admin -P password=admin 10.10.10.10 -P secureboot=true

# Update a single host with dedicated flags for credentials
$ kcli update baremetal-host -u admin -p admin 10.10.10.10 -P secureboot=true
"""

ocdownload = """# Download 4.17 stable
$ kcli download oc -P version=stable -P tag=4.17

# Download specific tag
$ kcli download oc -P version=tag -P tag=4.16.4

# Download nightly
$ kcli download oc -P version=nightly -P tag=4.17

# Download older version from CI
$ kcli download oc -P version=ci -P tag=4.14
"""

ocmirrordownload = """# Download 4.17 stable
$ kcli download oc-mirror -P version=stable -P tag=4.17

# Download specific tag
$ kcli download oc-mirror -P version=tag -P tag=4.16.4

# Download nightly
$ kcli download oc-mirror -P version=nightly -P tag=4.17

"""

openshiftdownload = """# Download latest stable
$ kcli download openshift-install

# Download older stable version
$ kcli download openshift-install -P version=tag -P tag=4.14

# Download specific tag
$ kcli download openshift-install -P version=tag -P tag=4.16.4

# Download nightly
$ kcli download openshift-install -P version=nightly -P tag=4.16

# Download dev-preview version
$ kcli download openshift-install -P version=dev-preview -P tag=4.17

# Download older version from CI
$ kcli download openshift-install -P version=ci -P tag=4.14
"""

securitygroupcreate = """# Create a security group named mygroup and opening tcp ports 22 and 25
$ kcli create security-group -P ports=[22,25] mygroup

# Do the same, but with udp port 53 too
$ kcli create security-group -P ports=['22,25,{"from": "53", "protocol": "udp"}'] mygroup

# Open a port range
$ kcli create security-group -P ports=['{"from": "8000", "to": "9000"}'] mygroup
"""

securitygroupupdate = """# Add a rule in subnet mysubnet to allow specific cidr to use a given port
$ kcli update security-group mysg -P ports=[6443,443]

# Do the same but for a specific cidr
$ kcli update security-group mysg -P rules=['{"cidr": "192.168.125.0/24", "ports": [6443,443]}']
"""

lbcreate = """# Create a lb pointing to specific vms and port 80 and 443
$ kcli create lb -P ports=[80,443] -P vms=[myvm1,myvm2]

# Do the same but make it internal
$ kcli create lb -P ports=[80,443] -P vms=[myvm1,myvm2] -P internal=true

# Use a specific network
$ kcli create lb -P ports=[80,443] -P vms=[myvm1,myvm2] -P nets=[baremetal]

# Create an associated dns entry
$ kcli create lb -P ports=[80,443] -P vms=[myvm1,myvm2] -P domain=mysuperdomain.com

# Customize check path and checkport
$ kcli create lb -P ports=[6443] -P vms=[myvm1,myvm2] -P checkport=6080 -P checkpath='/'
"""

networkcreate = """# Create a network
$ kcli create network -c 192.168.123.0/24 mynetwork

# Create a network with specific dhcp range
$ kcli create network -c 192.168.123.0/24 -P dhcp_start=192.168.123.40 -P dhcp_end=192.168.123.60 mynetwork

# Create a network without dhcp
$ kcli create network -c 192.168.123.0/24 --nodhcp mynetwork

# Create a network without dhcp nor dns
$ kcli create network -c 192.168.123.0/24 -P dhcp=false -P dns=false mynetwork

# Create an isolated network
$ kcli create network -c 192.168.123.0/24 -i mynetwork

# Create a network with a dedicated pxe server
$ kcli create network -c 192.168.123.0/24 -P pxe=192.168.123.2 mynetwork

# Create a network with forward mode set to route
$ kcli create network -c 192.168.123.0/24 -P forward_mode=route mynetwork

# Create an ipv6 network
$ kcli create network -c 2620:52:0:1302::/64 mynetwork

# Create a dual network
$ kcli create network -c 192.168.123.0/24 -d 2620:52:0:1302::/64 mynetwork

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

# Create an ovn overlay network (on kubevirt) with a localnet topology and connected to br-ex bridge
$ kcli create network -c 192.168.126.0/24 mynetwork

# Create an ovn overlay network (on kubevirt) with a layer2 topology
$ kcli create network -c 192.168.126.0/24 -P type=ovn -P topology=topology mynetwork

# Do the same using an existing network attachment from some specific namespace
$ kcli create network -c 192.168.126.0/24 -P type=ovn -P nad=default/othernad mynetwork

# Create a br-ex network attachment definition using ovs cni (on kubevirt)
$ kcli create network -P type=ovs br-ex

# Create a br-ex network attachment definition using ovs cni (on kubevirt)
$ kcli create network -P ovs=true br-ex

# Create an ovs bridge br0 network (on libvirt)
$ kcli create network -P ovs=true br0

# Create a network on AWS and make it default vpc
$ kcli create network -c 10.0.0.0/24 -P default=true my-default-vpc

# Create a network on GCP with an alias/secondary network and a specific name
$ kcli create network -P cidr=192.168.123.0/24 -P secondary_cidr=192.168.124.0/24 -P secondary_name=podnetwork mynetwork

# Create a network on AZURE without an associated subnet
$ kcli create network -P cidr=11.0.0.0/16 -P create_subnet=False mynetwork

# Create a dual stack network on AWS
$ kcli create network -P cidr=11.0.0/16 -P subnet_cidr=11.0.1.0/24 -P ipv6=true ipv6

# Create a dual stack network on GCP
$ kcli create network -P cidr=11.0.0.0.0/16 -P ipv6=true mynetwork
"""

profilecreate = """# Create profile with specific image
$ kcli create profile -i ubuntu-22.10-server-cloudimg-amd64.img -P memory=4096 -P disks=[20,30] myprofile

# Do the same providing everything as parameter
$ kcli create profile -P image=ubuntu-22.10-server-cloudimg-amd64.img -P memory=4096 -P disks=[20,30] myprofile

# Create a profile without image, with uefi and without startingthe corresponding vm
$ kcli create profile -P uefi=true -P start=false -P memory=4096 -P disks=[20,30] myprofile
"""

subnetcreate = """# Create a subnet
$ kcli create subnet -c 192.168.123.0/24 myubnet

# Create a subnet with specific dhcp range
$ kcli create subnet -c 192.168.123.0/24 -P dhcp_start=192.168.123.40 -P dhcp_end=192.168.123.60 mysubnet

# Create a subnet on AWS and specify network
$ kcli create subnet -c 10.0.1.0/24 -P network=mynetwork mysubnet

# Create a subnet on AWS but get network from the subnet name
$ kcli create subnet -c 10.0.1.0/24 mynetwork-mysubnet

# Create a subnet on AWS and make it totally isolated
$ kcli create subnet -c 10.0.1.0/24 -P network=mynetwork -P gateway=false mysubnet

# Create a subnet on GCP with an alias/dual network with specific name
$ kcli create subnet -P cidr=192.168.123.0/24 -P dual_cidr=192.168.124.0/24 -P dual_name=podnetwork mysubnet
"""

subnetupdate = """# Add a route in subnet mysubnet to specific cidr using an intermediate vm (aws specific)
$ kcli update subnet mysubnet -P routes=['{"cidr": "192.168.125.0/24", "vm": "myvm"}']
"""

vmupdate = """# Update memory and cpu of a vm
$ kcli update vm -P memory=8192 -P numcpus=8 myvm

# Update disks of a vm, including sizes of existing ones
$ kcli update vm -P disks=[30,50] myvm

# Move disks of a vm to a different pool
$ kcli update vm -P pool=newpool myvm

# Make the vm autostart along with the hypervisor
$ kcli update vm -P autostart=true myvm

# Update specific files of a vm (creating them if they don't exist)
$ kcli update vm testfed -P files=['frout.txt','{"path": "/root/x/y/z", "content": "this is working great"}']

# Change plan of a vm
$ kcli update vm -P plan=myplan myvm

# Remove iso of a vm
$ kcli update vm -P iso=None myvm

# Convert vm to template (vsphere specific)
$ kcli update vm ubuntu-20.04-server-cloudimg-amd64 -P template=true

# Convert vm to template (vsphere specific)
$ kcli update vm ubuntu-20.04-server-cloudimg-amd64 -P template=true

# Add cpuflags to a vm (kvm specific)
$ kcli update vm -P cpuflags=[vmx] myvm

# Remove cpuflags from a vm (kvm specific)
$ kcli update vm -P cpuflags=[vmx] -P disable=true myvm

# Add and remove cpuflags from a vm (kvm specific)
$ kcli update vm -P cpuflags=['{"name": "vmx", "policy": "enable"}, {"name": "ss", "policy": "disable"}'] myvm
"""

vmlist = """# List vms
$ kcli list vm

# Filter vms which are up
$ kcli list vm -P status=up

# Filter vms with a plan name starting with prod
$ kcli list vm -P plan=prod

# Combine filters
$ kcli list vm -P plan=prod -P status=up

# Get vms whose ip starts with 192.168.122
$ kcli list vm -P ip=192.168.122

# Get vms whose name starts with myclu
$ kcli list vm -P name=myclu
"""
