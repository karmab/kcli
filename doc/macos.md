virtualenv --python=python3.6 venv
source venv/bin/activate.fish
pip install libvirt-python
env PYCURL_SSL_LIBRARY=openssl LDFLAGS="-L/usr/local/opt/openssl/lib" CPPFLAGS="-I/usr/local/opt/openssl/include" pip install --no-cache-dir pycurl
python setup.py build
python setup.py install
pip install kubernetes google-api-python-client google-auth-httplib2 google-auth-httplib2 ovirt-engine-sdk-python ovirt-engine-sdk-python ovirt-engine-sdk-python python-cinderclient python-neutronclient python-glanceclient python-glanceclient python-novaclient boto3 google-cloud-dns
