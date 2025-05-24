from kvirt import common
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("kcli-baremetal")


@mcp.tool()
def info_baremetal_host(url: str, user: str, password: str, full: bool = False,
                        debug: bool = False) -> dict:
    """Provide information on baremetal host"""
    return common.info_baremetal_host(url, user, password, debug=debug, full=full)


@mcp.tool()
def reset_baremetal_host(url: str, user: str, password: str,
                         debug: bool = False) -> dict:
    """Reset baremetal host"""
    return common.reset_baremetal_host(url, user, password, debug=debug)


@mcp.tool()
def start_baremetal_host(url: str, user: str, password: str,
                         debug: bool = False, overrides: dict = {}) -> dict:
    """Start baremetal host"""
    return common.start_baremetal_host(url, user, password, overrides, debug=debug)


@mcp.tool()
def stop_baremetal_host(url: str, user: str, password: str,
                        debug: bool = False) -> dict:
    """Stop baremetal host"""
    return common.stop_baremetal_host(url, user, password, debug=debug)


@mcp.tool()
def update_baremetal_host(url: str, user: str, password: str,
                          debug: bool = False, overrides: dict = {}) -> dict:
    """update baremetal host"""
    return common.update_baremetal_host(url, user, password, overrides, debug=debug)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
