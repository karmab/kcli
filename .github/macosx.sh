bash extras/build_macos_pkg.sh

echo pushing kcli.pkg
pip install --break-system-packages cloudsmith-cli
cloudsmith push raw karmab/kcli kcli.pkg
