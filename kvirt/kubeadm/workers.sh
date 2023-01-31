# set cluster credentials
cp /root/admin.conf /etc/kubernetes

{% if config_type == 'gcp' %}
systemctl enable --now gcp-hack
{% endif %}

# join worker to cluster
bash /root/join.sh
