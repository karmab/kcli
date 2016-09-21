systemctl enable rhel-push-plugin
systemctl start rhel-push-plugin
systemctl start docker --ignore-dependencies
oc cluster up
