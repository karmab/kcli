---
name: kcli-testing
description: Guides testing and code quality for kcli. Use when writing tests, running linting, or validating changes before committing.
---

# kcli Testing and Code Quality

## Development Setup

```bash
# Create virtual environment
python3 -m venv venv
. venv/bin/activate

# Install in development mode
pip install -e .

# Install with all provider dependencies
pip install -e ".[all]"
```

## Linting

### pycodestyle (PEP8)
```bash
# Lint all Python files
pycodestyle --ignore=E402,W504,E721,E722,E741 --max-line-length=120 kvirt/

# Lint specific file
pycodestyle --ignore=E402,W504,E721,E722,E741 --max-line-length=120 kvirt/config.py
```

**Ignored codes:**
- `E402`: Module level import not at top of file
- `W504`: Line break after binary operator
- `E721`: Do not compare types, use isinstance()
- `E722`: Do not use bare except
- `E741`: Ambiguous variable name

**Max line length:** 120 characters

### codespell (Spelling)
```bash
# Check spelling
codespell kvirt/ -L "aks"

# The -L flag ignores specific words (aks is Azure Kubernetes Service)
```

### Combined Linting (CI Script)
```bash
# Run the same linting as CI
.github/linting.sh
```

**Note:** The linting script excludes `kvirt/bottle.py` (vendored web framework) from checks.

## Running Tests

### Prerequisites
Tests require:
- libvirt running locally
- Default storage pool configured
- SSH keypair in `~/.kcli/`

```bash
# Setup for testing
sudo mkdir -p /var/lib/libvirt/images
sudo setfacl -m u:$(id -un):rwx /var/lib/libvirt/images
mkdir -p ~/.kcli
ssh-keygen -t rsa -N '' -f ~/.kcli/id_rsa
kcli create pool -p /var/lib/libvirt/images default
```

### pytest Commands
```bash
# Run all tests
python -m pytest tests/test_kvirt.py -v

# Run specific test class
python -m pytest tests/test_kvirt.py::TestK -v

# Run specific test method
python -m pytest tests/test_kvirt.py::TestK::test_create_vm -v

# Run with output capture disabled
python -m pytest tests/test_kvirt.py -v -s
```

### Integration Test Script
```bash
# Full integration test (used in CI)
.github/testing.sh
```

## Test Structure

Tests are in `tests/test_kvirt.py`:

```python
class TestK:
    @classmethod
    def setup_class(self):
        # Initialize Kconfig and provider
        self.config = Kconfig()
        self.k = self.config.k
        
    def test_list(self):
        result = self.k.list()
        assert result is not None
        
    def test_create_vm(self):
        result = self.config.create_vm(...)
        assert result["result"] == "success"
        
    @classmethod
    def teardown_class(self):
        # Cleanup resources
        self.k.delete_network(...)
        self.k.delete_pool(...)
```

## Test Plan Example

The CI uses `.github/test_plan.yml` for integration testing:

```yaml
parameters:
  pool: default
  image: cirros
  network: mynetwork
  profile: myprofile

{{ image }}:
  type: image
  pool: {{ pool }}

{{ network }}:
  type: network
  cidr: 192.168.125.0/24
  dhcp: true

{{ profile }}:
  type: profile
  image: {{ image }}
  memory: 2048
  numcpus: 2

myvm:
  profile: {{ profile }}
  pool: {{ pool }}
```

Run it:
```bash
kcli create plan -f .github/test_plan.yml test_plan
kcli list plan | grep test_plan
kcli delete plan --yes test_plan
```

## Validating Changes

### Before Committing
```bash
# 1. Run linting
pycodestyle --ignore=E402,W504,E721,E722,E741 --max-line-length=120 kvirt/

# 2. Check spelling
codespell kvirt/ -L "aks"

# 3. Run tests (if libvirt available)
python -m pytest tests/test_kvirt.py -v

# 4. Test your specific change manually
kcli <your-command>
```

### Manual Testing Patterns

**Testing Provider Changes:**
```bash
# Test with debug output
kcli -d list vm
kcli -d create vm -i cirros testvm
kcli -d delete vm --yes testvm
```

**Testing Plan Changes:**
```bash
# Create minimal test plan
cat > /tmp/test.yml << 'EOF'
testvm:
  image: cirros
  memory: 512
EOF

kcli create plan -f /tmp/test.yml mytest
kcli info plan mytest
kcli delete plan --yes mytest
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs:

1. **Lint** - pycodestyle + codespell
2. **Test** - Integration tests with libvirt
3. **Release** (main branch only):
   - RPM via Copr
   - DEB via Cloudsmith
   - PyPI package
   - Container image to Quay.io

## Flake8 Configuration

Project uses `.flake8`:
```ini
[flake8]
max-line-length = 120
ignore = E722,E402,E741,W504,E721,E501
```

**Note:** Flake8 config also ignores `E501` (line too long) which is stricter than the CI linting script. The CI script uses pycodestyle directly without E501 ignore.

## Writing New Tests

When adding tests:

1. Use the `TestK` class pattern
2. Return `{'result': 'success'}` or `{'result': 'failure', 'reason': ...}`
3. Clean up resources in `teardown_class`
4. Use unique names to avoid conflicts

```python
def test_new_feature(self):
    # Setup
    result = self.k.create_something(name="test-unique-name")
    
    # Assert
    assert result["result"] == "success"
    
    # Cleanup (or use teardown_class)
    self.k.delete_something("test-unique-name")
```
