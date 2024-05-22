oc delete ns {{ nfs_namespace }}
{% if nfs_ip == None %}
SHARE={{ nfs_share|default('/var/nfsshare-%s' % cluster) }}
sudo rm -rf $SHARE
sudo sed -i /$SHARE/d /etc/exports
sudo exportfs -r
{% endif %}
