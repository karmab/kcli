KUBEADMINFILE=/var/lib/microshift/resources/kubeadmin/{{ "$(hostname)/kubeconfig" if 'rhel' in image else "kubeconfig" }}
until [ -f $KUBEADMINFILE ] ; do
 echo Waiting on kubeconfig to be available
 sleep 5
{% if podman %}
podman cp microshift:$KUBEADMINFILE $(dirname $KUBEADMINFILE)
{% endif %}
done
ln -s $KUBEADMINFILE /root/kubeconfig
