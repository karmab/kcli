#
# spec file for package kcli
#
# Copyright (c) 2017 Karim Boumedhel/ Miguel P.C
#

Name:           kcli
Version:        12.0
Release:        2
Url:            http://github.com/karmab/kcli
Summary:        Libvirt/VirtualBox wrapper on steroids
License:        ASL 2.0
Group:          Development/Languages/Python
Source:         https://files.pythonhosted.org/packages/source/k/kcli/kcli-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildRequires:  python2-devel rubygem-ronn gzip
#Requires:       python2 python-iptools libvirt-python genisoimage nmap-ncat python-prettytable PyYAML python-flask python-netaddr python2-docker python2-kubernetes
Requires:       python2 python-iptools libvirt-python genisoimage nmap-ncat python-prettytable PyYAML python-flask python-netaddr

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
sed -i.bak '/kubernetes/d' setup.py
sed -i.bak '/google/d' setup.py
python setup.py build

%install
python setup.py install --prefix=%{_prefix} --root=%{buildroot}
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
