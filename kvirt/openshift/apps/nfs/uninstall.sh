oc delete ns {{ nfs_namespace }}
{% if nfs_ip == None %}
SHARE={{ nfs_share|default('/var/nfsshare-%s' % cluster) }}
rm -rf $SHARE
sed -i /$SHARE/d /etc/exports
exportfs -r
{% endif %}
