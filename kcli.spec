#
# spec file for package kcli
#
# Copyright (c) 2017 Karim Boumedhel
#

Name:           {{{ git_dir_name }}}
Version:        99.{{{ git_custom_version }}}
Release:        0%{?dist}
Url:            http://github.com/karmab/kcli
Summary:        Wrapper for libvirt, azure, aws, gcp, kubevirt, ovirt, openstack, packet, proxmox and vsphere
License:        ASL 2.0
Group:          Development/Languages/Python
VCS:            {{{ git_dir_vcs }}}
Source:         {{{ git_dir_pack }}}
AutoReq:        no
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildRequires:  python3-devel rubygem-ronn gzip python3-setuptools git
Requires:       python3 libvirt-python3 genisoimage nmap-ncat python3-prettytable python3-jinja2 python3-PyYAML python3-argcomplete python3-packaging

%description
Kcli is a wrapper for local/remote libvirt, aws, azure, gcp, kubevirt, ovirt, openstack, packet, proxmox and vsphere
It easily deploy single vms from cloud images or several using plans or kubernetes clusters

%global debug_package %{nil}

%prep
{{{ git_dir_setup_macro }}}

%build
sed -i "s/, 'libvirt.*/\]/" setup.py
INSTALL=$(grep -m 1 INSTALL setup.py  | sed 's/INSTALL = //')
sed -i "s/install_requires=INSTALL/install_requires=$INSTALL/" setup.py
sed -i '/INSTALL/d' setup.py
GIT_VERSION="$(git ls-remote https://github.com/karmab/kcli | head -1 | cut -c1-7) $(date +%Y/%m/%d)"
echo $GIT_VERSION > kvirt/version/git
%{python3} setup.py build

%install
%{python3} setup.py install --prefix=%{_prefix} --root=%{buildroot}
mkdir -p %{buildroot}/%{_docdir}/kcli
mkdir -p %{buildroot}/%{_mandir}/man1
LANG=en_US.UTF-8 ronn -r README.md
mv README kcli.1
gzip kcli.1
cp kcli.1.gz %{buildroot}/%{_mandir}/man1

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%doc %{_docdir}/kcli
%{_mandir}/man1/kcli.1.gz
%{python3_sitelib}/*
%attr(0755,root,root) %{_bindir}/kcli
%attr(0755,root,root) %{_bindir}/kweb
%attr(0755,root,root) %{_bindir}/klist.py
%attr(0755,root,root) %{_bindir}/ksushy
%attr(0755,root,root) %{_bindir}/ignitionmerger
%attr(0755,root,root) %{_bindir}/ekstoken
%attr(0755,root,root) %{_bindir}/gketoken


%changelog
{{{ git_dir_changelog }}}
