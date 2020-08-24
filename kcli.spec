#
# spec file for package kcli
#
# Copyright (c) 2017 Karim Boumedhel
#

Name:           {{{ git_dir_name }}}
Version:        99.{{{ git_custom_version }}}
Release:        1%{?dist}
Url:            http://github.com/karmab/kcli
Summary:        Wrapper for libvirt,gcp,aws,ovirt,openstack,kubevirt and vsphere
License:        ASL 2.0
Group:          Development/Languages/Python
VCS:            {{{ git_dir_vcs }}}
Source:         kcli-{{{ git_custom_version }}}.tar.gz
AutoReq:        no
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildRequires:  python3-devel rubygem-ronn gzip
Requires:       python3 libvirt-python3 genisoimage nmap-ncat python3-prettytable python3-PyYAML python3-flask python3-netaddr python3-argcomplete python3-requests

%description
Kcli is meant to interact with a local/remote libvirt, gcp, aws ovirt,
openstack, vsphere and kubevirt and to easily deploy single vms from cloud images or several using plans

%global debug_package %{nil}
%global __python /usr/bin/python3
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "import sys; from distutils.sysconfig import get_python_lib; sys.stdout.write(get_python_lib())")}

%prep
%setup -q -n kcli-99.{{{ git_custom_version }}}

%build
sed -i "s/, 'libvirt.*/\]/" setup.py
INSTALL=$(grep -m 1 INSTALL setup.py  | sed 's/INSTALL = //')
sed -i "s/install_requires=INSTALL/install_requires=$INSTALL/" setup.py
sed -i '/INSTALL/d' setup.py
curl -s https://github.com/karmab/kcli/commits/master | grep 'https://github.com/karmab/kcli/commits/master?' | sed 's@.*=\(.......\).*+.*@\1@' > kvirt/version/git
%{__python} setup.py build

%install
%{__python} setup.py install --prefix=%{_prefix} --root=%{buildroot}
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
%{python_sitelib}/*
%attr(0755,root,root) %{_bindir}/kcli
%attr(0755,root,root) %{_bindir}/kweb
%attr(0755,root,root) %{_bindir}/klist.py
%attr(0755,root,root) %{_bindir}/kbmc
%attr(0755,root,root) %{_bindir}/kclirpc
%attr(0755,root,root) %{_bindir}/krpc

%changelog
{{{ git_dir_changelog }}}
