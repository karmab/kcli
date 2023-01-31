if [ -d /root/manifests ] ; then
 mkdir -p /var/lib/microshift/manifests
 cp /root/manifests/*y*ml /var/lib/microshift/manifests
fi
KUBEADMINDIR=/var/lib/microshift/resources/kubeadmin
{% if podman %}
dnf -y install podman
mkdir -p $KUBEADMINDIR
curl -o /etc/systemd/system/microshift.service https://raw.githubusercontent.com/redhat-et/microshift/main/packaging/systemd/microshift-containerized.service
{% else %}
dnf copr enable -y @redhat-et/microshift{{ '-nightly' if nightly else ''}}
dnf -y install microshift
{% endif %}
systemctl enable microshift --now
until [ -f $KUBEADMINDIR/kubeconfig ] ; do
 echo Waiting on kubeconfig to be available
 sleep 5
 {% if podman %}
 podman cp microshift:$KUBEADMINDIR/kubeconfig $KUBEADMINDIR
 {% endif %}
done
ln -s $KUBEADMINDIR/kubeconfig /root/kubeconfig
