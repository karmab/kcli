#
# spec file for package kcli
#
# Copyright (c) 2017 Karim Boumedhel/ Miguel P.C
#

Name:           kcli
Version:        12.2
Release:        0
Url:            http://github.com/karmab/kcli
Summary:        Libvirt/VirtualBox wrapper on steroids
License:        ASL 2.0
Group:          Development/Languages/Python
Source:         https://files.pythonhosted.org/packages/source/k/kcli/kcli-%{version}.tar.gz
AutoReq:        no
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildRequires:  python3-devel rubygem-ronn gzip
Requires:       python3 python3-iptools libvirt-python3 genisoimage nmap-ncat python3-prettytable python3-PyYAML python3-flask python3-netaddr

%description
Kcli is meant to interact with a local/remote libvirt daemon and
to easily deploy from templates (optionally using cloud-init). It will
also report ips for any vm connected to a dhcp-enabled libvirt network
and generally for every vm deployed from this client.

%global debug_package %{nil}
%global __python /usr/bin/python3
%{!?python_sitelib: %global python_sitelib %(%{__python} -c "import sys; from distutils.sysconfig import get_python_lib; sys.stdout.write(get_python_lib())")}


%prep
%setup -q -n kcli-%{version}

%build
sed -i.bak '/pyvbox/d' setup.py
sed -i.bak '/docker/d' setup.py
sed -i.bak '/libvirt/d' setup.py
sed -i.bak '/kubernetes/d' setup.py
sed -i.bak '/google/d' setup.py
sed -i.bak '/boto3/d' setup.py
sed -i.bak '/ovirt-engine-sdk-python/d' setup.py
sed -i.bak '/python-keystoneclient/d' setup.py
sed -i.bak '/python-neutronclient/d' setup.py
sed -i.bak '/python-novaclient/d' setup.py
sed -i.bak '/python-glanceclient/d' setup.py
%{__python} setup.py build

%install
%{__python} setup.py install --prefix=%{_prefix} --root=%{buildroot}
mkdir -p %{buildroot}/%{_docdir}/kcli
mkdir -p %{buildroot}/%{_mandir}/man1
#cp doc/*md %{buildroot}/%{_docdir}/kcli
#cp doc/*rst %{buildroot}/%{_docdir}/kcli
cp -r extras %{buildroot}/%{_docdir}/kcli
cp -r plans %{buildroot}/%{_docdir}/kcli
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
* Wed Jul 11 2018 Karim Boumedhel <karimboumedhel@gmail.com> 12.1
- 12.1 Release switching to python3
* Tue Mar 20 2018 Karim Boumedhel <karimboumedhel@gmail.com> 11.0
- 11.0 Release
* Fri Jul 14 2017 Karim Boumedhel <karimboumedhel@gmail.com> 8.2
- Remove kcli ssh print
* Wed May 24 2017 Karim Boumedhel <karimboumedhel@gmail.com> 7.18-1
* Fri Jul 14 2017 Karim Boumedhel <karimboumedhel@gmail.com> 8.0
- 8.0 Release
* Wed May 24 2017 Karim Boumedhel <karimboumedhel@gmail.com> 7.18-1
- Fix dynamic inventory
* Thu May 11 2017 Karim Boumedhel <karimboumedhel@gmail.com> 7.13-2
- Doc, Sample, Plan and inventory files included
