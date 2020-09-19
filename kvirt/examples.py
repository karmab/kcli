assetcreate = """# Generate a minimal ignition file
$ kcli create asset -i rhcos46

# Do the same but force the name
$ kcli create asset -i rhcos46 myname

# Inject a custom script and a file in /root
$ kcli create asset -i rhcos -P scripts=[myscript.sh] -P files=[myfile.txt] zzz

# Generate a cloudinit userdata
$ kcli create asset -i centos8 myname

# Generate all the ignition/cloudinit assets from a plan file
$ kcli create asset -f my_plan.yml
"""

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

# Create a vm from a custom profile
$ kcli create vm -p myprofile myvm
"""

vmconsole = """# Open a graphical console for vm ( only shows the command if using container)
$ kcli console myvm

# Get a serial console to the vm
$ kcli console -s myvm
"""

vmexport = """# Export vm myvm with a specific name for the generated image
$ kcli export -i myimage vmyvm
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
