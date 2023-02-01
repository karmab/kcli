apt-get -y install curl
{% if sdn != None and sdn == 'cilium' %}
mount bpffs -t bpf /sys/fs/bpf
{% endif %}
bash /root/join.sh
