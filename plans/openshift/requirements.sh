[%- set releaseurls = {
                  '3.2'  : 'v1.2.2/openshift-origin-client-tools-v1.2.2-565691c',
                  '3.3'  : 'v1.3.3/openshift-origin-client-tools-v1.3.3-bc17c1527938fa03b719e1a117d584442e3727b8',
                  '3.4'  : 'v1.4.1/openshift-origin-client-tools-v1.4.1-3f9807a',
                  '3.5'  : 'v1.5.1/openshift-origin-client-tools-v1.5.1-7b451fc',
                  '3.6'  : 'v3.6.1/openshift-origin-client-tools-v3.6.1-008f2d5',
                  '3.7'  : 'v3.7.0/openshift-origin-client-tools-v3.7.0-7ed6862',
                  '3.9'  : 'v3.9.0/openshift-origin-client-tools-v3.9.0-191fece',
                  '3.10' : 'v3.10.0/openshift-origin-client-tools-v3.10.0-dd10d17',
                  '3.11' : 'v3.11.0/openshift-origin-client-tools-v3.11.0-0cbc58b',
               }
-%]
sleep 30
yum -y install wget docker git
systemctl enable docker
sed -i "s@# INSECURE_REGISTRY=.*@INSECURE_REGISTRY='--insecure-registry 172.30.0.0/16'@" /etc/sysconfig/docker
echo -e "DEVS=/dev/vdb\nVG=dockervg" > /etc/sysconfig/docker-storage-setup
docker-storage-setup
wget -O /root/oc.tar.gz https://github.com/openshift/origin/releases/download/[[ releaseurls[openshift_version] ]]-linux-64bit.tar.gz
cd /root ; tar zxvf oc.tar.gz
mv /root/openshift-origin-client-tools-*/oc /usr/bin
rm -rf  /root/openshift*
curl -L https://storage.googleapis.com/kubernetes-release/release/`curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt`/bin/linux/amd64/kubectl -o /usr/bin/kubectl
chmod +x /usr/bin/kubectl
