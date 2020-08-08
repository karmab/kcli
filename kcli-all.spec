Name:           kcli-all
Version:        99.0
Release:        1

License:        ASL 2.0
URL:            http://github.com/karmab/kcli

Summary:        Metapackage for dependencies of kcli additional providers
Group:          Development/Languages/Python

Requires:       python3-boto3
#Requires:      python3-google-api-client python3-google-auth-httplib2
Requires:       python3-kubernetes
Requires:       python3-ovirt-engine-sdk4
Requires:       python3-keystoneclient python3-glanceclient python3-cinderclient python3-neutronclient python3-novaclient
Requires:       python3-pyvmomi python3-requests

BuildArch:       noarch

%description
Kcli dependencies metapackage.

%prep

%build

%install

%files

%changelog

* Sat Aug 08 2020 karmab
- Initial Release
