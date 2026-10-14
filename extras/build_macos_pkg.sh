#!/bin/bash
set -eo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
MACOS_DIR="$SCRIPT_DIR/macos"
VERSION="${GIT_CUSTOM_VERSION:-99.0.$(date +%Y%m%d%H%M).$(git -C "$REPO_DIR" rev-parse --short HEAD | python3 -c "import sys; print(int(sys.stdin.read().strip(), 16))")}"
STAGING=$(mktemp -d)
# Python resolves macOS aliases such as /var to /private/var in shebangs.
# Use the same physical path when creating and relocating the virtualenv.
STAGING=$(cd "$STAGING" && pwd -P)
PKG_ROOT="$STAGING/payload"
INSTALL_DIR="$PKG_ROOT/kcli"
BIN_DIR="$PKG_ROOT/bin"

trap "rm -rf $STAGING" EXIT

echo -e "${BLUE}Building kcli macOS package...${NC}"

if [ "$(uname -s)" != "Darwin" ]; then
    echo -e "${RED}This script must be run on macOS${NC}"
    exit 1
fi

if ! which python3 >/dev/null 2>&1; then
    echo -e "${RED}python3 not found. Install Xcode Command Line Tools: xcode-select --install${NC}"
    exit 1
fi

echo -e "${BLUE}Creating virtualenv...${NC}"
python3 -m venv "$INSTALL_DIR"

echo -e "${BLUE}Installing kcli...${NC}"
SRC_DIR="$STAGING/src"
mkdir -p "$PKG_ROOT"
cp -a "$REPO_DIR" "$SRC_DIR"
/usr/bin/sed -i "" "s/, 'libvirt-python>=2.0.0'//" "${SRC_DIR}/setup.py"
"$INSTALL_DIR/bin/pip" install --no-cache-dir "$SRC_DIR" 2>&1 | tail -1
rm -rf "$SRC_DIR"

# Fix shebangs to point to the installed path instead of the temp build dir
find "$INSTALL_DIR/bin" -type f -exec grep -Il "$INSTALL_DIR" {} \; | while read f; do
    sed -i "" "s|$INSTALL_DIR|/usr/local/kcli|g" "$f"
done
sed -i "" "s|$INSTALL_DIR|/usr/local/kcli|" "$INSTALL_DIR/pyvenv.cfg" 2>/dev/null || true

mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/kcli" << 'WRAPPER'
#!/bin/bash
exec /usr/local/kcli/bin/kcli "$@"
WRAPPER
chmod +x "$BIN_DIR/kcli"

echo -e "${BLUE}Building .pkg...${NC}"
CORE_PKG="$STAGING/kcli-core.pkg"
pkgbuild --root "$PKG_ROOT" \
         --identifier com.karmab.kcli \
         --version "$VERSION" \
         --install-location /usr/local \
         "$CORE_PKG"

RESOURCES="$STAGING/resources"
mkdir -p "$RESOURCES"
sed "s/@@VERSION@@/$VERSION/" "$MACOS_DIR/resources/welcome.html" > "$RESOURCES/welcome.html"
cp "$REPO_DIR/kcli.png" "$RESOURCES/background.png"

productbuild --distribution "$MACOS_DIR/Distribution" \
             --resources "$RESOURCES" \
             --package-path "$STAGING" \
             "$REPO_DIR/kcli.pkg"

echo -e "${GREEN}Built kcli.pkg${NC}"
echo -e "${BLUE}Install with: open kcli.pkg${NC}"
