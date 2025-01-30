if [ "$(which dnf)" != "" ] ; then
echo "fastestmirror=1" >> /etc/dnf/dnf.conf
dnf -y install podman httpd httpd-tools jq skopeo libseccomp-devel haproxy
else
apt-get update
apt-get -y install podman apache2 apache2-utils jq skopeo haproxy
fi

curl https://mirror.openshift.com/pub/openshift-v4/x86_64/clients/ocp/stable/openshift-client-linux.tar.gz | tar zxf - oc
chmod +x oc
mv oc /root/bin
