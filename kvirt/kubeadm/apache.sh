PKGMGR="{{ 'apt-get' if ubuntu else 'yum' }}"
PKG="{{ 'apache2' if ubuntu else 'httpd' }}"
$PKGMGR -y install $PKG
systemctl enable --now $PKG
