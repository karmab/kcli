#
# spec file for package kcli
#
# Copyright (c) 2017 Karim Boumedhel/ Miguel P.C
#

Name:           kcli
Version:        7.12
Release:        1%{?dist}
Url:            http://github.com/karmab/kcli
Summary:        Libvirt/VirtualBox wrapper on steroids
License:        ASL 2.0
Group:          Development/Languages/Python
Source:         https://files.pythonhosted.org/packages/source/k/kcli/kcli-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildRequires:  python-devel
Requires:       libvirt-python genisoimage qemu-kvm nmap-ncat python-prettytable python-pillow PyYAML python-flask python-netaddr python-docker-py docker-client python-iptools

%description
Kcli is meant to interact with a local/remote libvirt daemon and
to easily deploy from templates (optionally using cloud-init). It will
also report ips for any vm connected to a dhcp-enabled libvirt network
and generally for every vm deployed from this client.

%global debug_package %{nil}

%prep
%setup -q -n kcli-%{version}

%build
sed -i.bak '/pyvbox/d' setup.py
sed -i.bak '/docker/d' setup.py
sed -i.bak '/libvirt/d' setup.py
python setup.py build

%install
python setup.py install --prefix=%{_prefix} --root=%{buildroot}

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{python_sitelib}/*
%attr(0755,root,root) %{_bindir}/kcli
%attr(0755,root,root) %{_bindir}/kweb

%changelog
