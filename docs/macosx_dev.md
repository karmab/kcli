
PYTHON3="/usr/local/Cellar/python/3.7.4_1/bin/python3"
virtualenv --python=$PYTHON3 venv
source venv/bin/activate.fish
pip3 install libvirt-python PyYAML
export PYCURL_SSL_LIBRARY=openssl
export CPPFLAGS="-I/usr/local/opt/openssl/include"
export LDFLAGS="-L/usr/local/opt/openssl/lib"
git clone https://github.com/pycurl/pycurl
cd pycurl
pip3 install --no-cache-dir --compile --ignore-installed --install-option="--with-openssl" pycurl
cd ..
pip3 install -e .[all]
brew upgrade virt-viewer
