#
# spec file for package kcli
#
# Copyright (c) 2017 Karim Boumedhel
#

Name:           kcli
Version:        14.13
Release:        2
Url:            http://github.com/karmab/kcli
Summary:        Wapper for libvirt,gcp,aws,ovirt and openstack
License:        ASL 2.0
Group:          Development/Languages/Python
Source:         https://files.pythonhosted.org/packages/source/k/kcli/kcli-%{version}.tar.gz
AutoReq:        no
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildRequires:  python3-devel rubygem-ronn gzip
Requires:       python3 libvirt-python3 genisoimage nmap-ncat python3-prettytable python3-PyYAML python3-flask python3-netaddr

%description
Kcli is meant to interact with a local/remote libvirt, gcp, aws ovirt,
openstack, kubevirt and to easily deploy from templates (optionally using cloud-init).
It will also report ips for any vm connected to a dhcp-enabled libvirt network
and generally for every vm deployed from this client.

%global debug_package %{nil}
%global __python /usr/bin/python3
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "import sys; from distutils.sysconfig import get_python_lib; sys.stdout.write(get_python_lib())")}


%prep
%setup -q -n kcli-%{version}

%build
sed -i "s/, 'libvirt.*/\]/" setup.py
INSTALL=$(grep -m 1 INSTALL setup.py  | sed 's/INSTALL = //')
sed -i "s/install_requires=INSTALL/install_requires=$INSTALL/" setup.py
sed -i '/INSTALL/d' setup.py
%{__python} setup.py build

%install
%{__python} setup.py install --prefix=%{_prefix} --root=%{buildroot}
mkdir -p %{buildroot}/%{_docdir}/kcli
mkdir -p %{buildroot}/%{_mandir}/man1
cp -r extras %{buildroot}/%{_docdir}/kcli
cp -r samples %{buildroot}/%{_docdir}/kcli
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

%changelog
* Mon Jun 24 2019 Karim Boumedhel <karimboumedhel@gmail.com> 14.13
- 14.13 Fix print info
