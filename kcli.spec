#
# spec file for kcli package
#
# Copyright (c) 2017 Karim Boumedhel
#

Name:           kcli
Version:        99.${GIT_CUSTOM_VERSION}
Release:        0%{?dist}
Url:            http://github.com/karmab/kcli
Summary:        Wrapper for libvirt, kubevirt, vsphere, openstack, proxmox, ovirt, aws, azure, gcp, ibmcloud, packet and hcloud
License:        ASL 2.0
Group:          Development/Languages/Python
VCS:            ${GIT_DIR_VCS}
Source:         kcli.tar.gz
AutoReq:        no
BuildRoot:      %{_tmppath}/%{name}-%{version}-build
BuildRequires:  python3-devel rubygem-ronn gzip python3-setuptools git
Requires:       python3 libvirt-python3 genisoimage nmap-ncat python3-prettytable python3-jinja2 python3-PyYAML python3-argcomplete

%description
Kcli is a wrapper for local/remote libvirt, kubevirt, vsphere, openstack, proxmox, ovirt, aws, azure, gcp, ibmcloud, packet and hcloud
It allows to easily deploy and manage single vms from cloud images or several using plans or kubernetes clusters

%global debug_package %{nil}

%prep
%setup -T -b 0 -q -n kcli

%build
sed -i "s/, 'libvirt.*/\]/" setup.py
echo "$(git ls-remote https://github.com/karmab/kcli | head -1 | cut -c1-7) $(date +%Y/%m/%d)" > kvirt/version/git
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
%attr(0755,root,root) %{_bindir}/ksushy-isoremover
%attr(0755,root,root) %{_bindir}/ignitionmerger
%attr(0755,root,root) %{_bindir}/ekstoken
%attr(0755,root,root) %{_bindir}/gketoken

%post
! systemctl is-active --quiet ksushy.service || (systemctl daemon-reload && systemctl restart ksushy.service)

%changelog
