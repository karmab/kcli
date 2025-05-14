from mcp.server.fastmcp import FastMCP
from kvirt.config import Kbaseconfig, Kconfig
from urllib.request import urlopen

mcp = FastMCP("kclimcp")


@mcp.prompt()
def prompt() -> str:
    """Indicates contexts of questions related to kcli"""
    return """You are a helpful assistant who knows everything about kcli, a powerful client and library written
    in Python and meant to interact with different virtualization providers, easily deploy and customize VMs or
    full kubernetes/OpenShift clusters. All information about kcli is available at
    https://github.com/karmab/kcli/blob/main/docs/index.md"""


@mcp.resource("resource://kcli-doc.md")
def get_doc() -> str:
    """Provides kcli documentation"""
    url = 'https://raw.githubusercontent.com/karmab/kcli/refs/heads/main/docs/index.md'
    return urlopen(url).read().decode('utf-8')


@mcp.tool()
def about_kcli() -> str:
    """What is kcli"""
    return open('about.txt').read()


@mcp.tool()
def list_clients() -> list:
    """List kcli clients/providers"""
    clientstable = ["Client", "Type", "Enabled", "Current"]
    baseconfig = Kbaseconfig()
    for client in sorted(baseconfig.clients):
        enabled = baseconfig.ini[client].get('enabled', True)
        _type = baseconfig.ini[client].get('type', 'kvm')
        if client == baseconfig.client:
            clientstable.append([client, _type, enabled, 'X'])
        else:
            clientstable.append([client, _type, enabled, ''])
    return clientstable


@mcp.tool()
def list_vms(client: str = None) -> list:
    """List kcli vms for specific client or for default one when unspecified"""
    return Kconfig(client).k.list()


@mcp.tool()
def info_vm(name: str, client: str = None) -> dict:
    """Get info of a kcli vm"""
    return Kconfig(client).k.info(name)


@mcp.tool()
def create_vm(name: str, profile: str, overrides: dict, client: str = None) -> dict:
    """Create a kcli vm"""
    return Kconfig(client).create_vm(name, profile, overrides=overrides)


@mcp.tool()
def delete_vm(vm: str, client: str = None) -> dict:
    """Delete a kcli vm"""
    return Kconfig(client).k.delete(vm)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
