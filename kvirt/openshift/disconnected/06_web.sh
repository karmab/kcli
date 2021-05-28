yum -y install httpd
sed -i "s/Listen 80/Listen 8080/" /etc/httpd/conf/httpd.conf
systemctl enable --now httpd
{% if disconnected_haproxy %}
yum -y install haproxy
cp /root/haproxy.cfg /etc/haproxy
systemctl enable --now haproxy
{% endif %}
