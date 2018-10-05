#!/usr/bin/env bash
yum -y install wget bash-completion
curl -L https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl -o /usr/bin/kubectl
chmod +x /usr/bin/kubectl
echo "source <(kubectl completion bash)" >> ~/.bashrc
curl -Lo /usr/bin/minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
chmod +x /usr/bin/minikube
[% if driver == 'none' %]
yum -y install docker
sed -i "s@# INSECURE_REGISTRY=.*@INSECURE_REGISTRY='--insecure-registry 172.30.0.0/16'@" /etc/sysconfig/docker
systemctl enable docker
systemctl start docker
minikube start --vm-driver none --extra-config=kubelet.CgroupDriver=systemd --feature-gates=DevicePlugins=true --memory 6144
[% else %]
echo options kvm-intel nested=1 >> /etc/modprobe.d/kvm-intel.conf
modprobe -r kvm_intel
modprobe kvm_intel
yum -y install libvirt-daemon-kvm qemu-kvm libvirt-client
systemctl start libvirtd
systemctl enable libvirtd
curl -LO https://storage.googleapis.com/minikube/releases/latest/docker-machine-driver-kvm2 && chmod +x docker-machine-driver-kvm2 && sudo mv docker-machine-driver-kvm2 /usr/bin/
virsh net-define /root/network.yml
virsh net-start default
minikube start --vm-driver kvm2 --feature-gates=DevicePlugins=true --memory 4096
[% endif %]
