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
$ kcli create dns -d karmalabs.com -i 192.168.122.253 api.jhendrix

# Do the same for a different network
$ kcli create dns -n network2 -d karmalabs.com -i 192.168.122.253 api.jhendrix

# Do the same with an extra wildcard alias
$ kcli create dns -d karmalabs.com -i 104.197.157.226 -a '*' api.jhendrix
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
$ kcli create plan -f multi.yml -P masters=1 -P nodes=2 -P crio=true

# Create a plan from a remote url, customizing some parameters
$ kcli create plan -u https://github.com/karmab/kcli-plans/blob/master/kubernetes/kubernetes.yml -P masters=3
"""

planinfo = """# Get info from a local plan file
$ kcli info plan -f multi.yml

# Get info of a plan with a remote url
$ kcli info plan -u https://github.com/karmab/kcli-plans/blob/master/kubernetes/kubernetes.yml
"""

productinfo = """# Get info from product kubernetes
$ kcli info product kubernetes
"""

repocreate = """# Create a product repo from karmab samples repo
$ kcli create repo -u https://github.com/karmab/kcli-plans karmab
"""

start = """# Start vms named vm1 and vm2
$ kcli start vm1 vm2

# Start all vms of plan X
$ kcli start plan X

# Start container named my container
$ kcli start container mycontainer
"""

vmcreate = """# Create a centos vm from image centos7 with a random name
$ kcli create vm -i centos7

# Create a centos vm named myvm customizing its memory and cpus
$ kcli create vm -i centos7 -P memory=4096 -P numcpus=4

# Pass disks, networks and even cmds
$ kcli create vm -i CentOS-7-x86_64-GenericCloud.qcow2 -P disks=[10,20] -P nets=[default] -P cmds=['yum -y install nc']

# Use more advanced information for nets
$ kcli create vm -i centos8 -P nets=['{"name": "default", "type": "e1000"}']

# Or specify a custom mtu
$ kcli create vm -i centos8 -P nets=['{"name": "default", "mtu": 1400}']

# Create a vm with static ip
$ img=centos8
$ kcli create vm -i $img -P nets=['{"name":"default","ip":"192.168.122.250","netmask":"24","gateway":"192.168.122.1"}']

# Use more advanced information for disks
$ kcli create vm -i centos8 -P disks=['{"size": 10, "interface": "sata"}']

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
$ kcli create kube generic -P masters=1 -P workers=2 mykube

# Use a parameter file
$ kcli create kube generic --paramfile=myparameters.yml mykube2
"""

kubek3screate = """# Create a kube k3s instance named mykube with default values
$ kcli create kube k3s mykube

# Do the same with workers
$ kcli create kube k3s -P workers=2 mykube

# Use a parameter file
$ kcli create kube generic --paramfile=myparameters.yml mykube2
"""

kubeopenshiftcreate = """# Create a kube instance named mykube with default values
$ kcli create kube openshift mykube

# Do the same but customize some parameters
$ kcli create kube openshift -P masters=1 -P workers=2 mykube

# Use a parameter file
$ kcli create kube openshift --paramfile=myparameters.yml mykube2
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
$ kcli create vmdata -i centos8 myname
"""

plandatacreate = """# Generate all the ignition/cloudinit userdatas from a plan file
$ kcli create plandata -f my_plan.yml
"""

isocreate = """# Generate an openshift iso
$ kcli create openshift-iso testk.karmalabs.com

# Do the same for a 4.5 install
$ kcli create openshift-iso -P version=4.5 testk.karmalabs.com

# Embed a local target ignition in the iso
$ kcli create openshift-iso -f my_ignition.ign testk

# Only creates the ignition for the iso
$ kcli create openshift-iso -P iso=false testk.karmalabs.com

# Force the ip to use in /etc/hosts of the machine at first boot
$ kcli create openshift-iso -P api_ip=192.168.1.20 testk.karmalabs.com

# Disable ens4 in the iso
$ kcli create openshift-iso -P disable_nics=[ens4] testk.karmalabs.com

# Inject static ip for ens3
$ kcli create openshift-iso -P nic=ens3 -P ip=192.168.122.45 -P netmask=24 -P gateway=192.168.122.1 testk.karmalabs.com

# Provide extra args for first boot of the node
$ kcli create openshift-iso -P extra_args="super_string_of_args" testk.karmalabs.com
"""

disconnectercreate = """# Generate an openshift disconnecter vm for 4.8
$ kcli create openshift-disconnecter -P version=stable -P tag=4.7

# Do the same over an ipv4 network
$ kcli create openshift-disconnecter -P version=nightly -P tag=4.8 -P disconnected_ipv6_network=false

# Use specific version and add extra operators (from 4.7)
$ kcli create openshift-disconnecter -P version=nightly -P tag=4.8.0-fc.5 -P disconnected_operators=[sriov-operator]
"""

appopenshiftcreate = """# Deploy sriov operator
$ kcli create app openshift sriov-operator

# Deploy local storage using parameters from your openshift install and creating a localvolume for each node
$ kcli create app openshift local-storage --paramfile your_paramfile.yml

# Deploy local storage without the cr
$ kcli create app openshift local-storage -P install_cr=false
"""
