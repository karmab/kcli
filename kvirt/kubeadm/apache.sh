PKGMGR="{{ 'apt-get' if ubuntu else 'yum' }}"
PKGS="{{ 'apache2 apache2-utils' if ubuntu else 'httpd httpd-tools' }}"
SERVICE="{{ 'apache2' if ubuntu else 'httpd' }}"
$PKGMGR -y install $PKGS
systemctl enable --now $SERVICE
