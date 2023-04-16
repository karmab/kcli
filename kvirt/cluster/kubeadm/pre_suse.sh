zypper addrepo --refresh https://download.opensuse.org/repositories/system:/snappy/openSUSE_Leap_15.2 snappy
zypper --gpg-auto-import-keys refresh
zypper dup --from snappy
zypper install snapd
systemctl enable snapd
systemctl enable snapd
snap install kubectl --classic

