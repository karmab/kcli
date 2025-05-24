from kvirt import common
from kvirt.config import Kconfig
from kvirt.nameutils import get_random_name
from mcp.server.fastmcp import FastMCP


def _parse_vms_list(_list, overrides={}):
    if isinstance(_list, str):
        print(_list)
        return
    field = overrides.get('field')
    if field is not None:
        vmstable = ["Name", field.capitalize()]
    else:
        vmstable = ["Name", "Status", "Ips", "Source", "Plan", "Profile"]
    for vm in _list:
        if field is not None:
            name = next(iter(vm))
            vminfo = [name, vm[name]]
            vmstable.append(vminfo)
            continue
        name = vm.get('name')
        status = vm.get('status')
        ip = vm.get('ip', '')
        source = vm.get('image', '')
        plan = vm.get('plan', '')
        profile = vm.get('profile', '')
        vminfo = [name, status, ip, source, plan, profile]
        vmstable.append(vminfo)
    return vmstable


mcp = FastMCP("kcli-cloud")


@mcp.tool()
def create_bucket(buckets: list = [], public: bool = False,
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None):
    """Create bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for bucket in buckets:
        k.create_bucket(bucket, public=public)


@mcp.tool()
def create_bucketfile(bucket: str, path: str, temp: str = None, public: bool = False,
                      client: str = None, debug: bool = False, region: str = None,
                      zone: str = None, namespace: str = None) -> str:
    """Create bucketfile in bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.upload_to_bucket(bucket, path, temp_url=temp, public=public)


@mcp.tool()
def create_dns(names: list, net: str, domain: str, ip: str, alias: str,
               client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None):
    """Create dns entry"""
    if alias is None:
        alias = []
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    name = names[0]
    if len(names) > 1:
        alias.extend(names[1:])
    k.reserve_dns(name=name, nets=[net], domain=domain, ip=ip, alias=alias, primary=True)


@mcp.tool()
def create_lb(name: str = None, checkpath: str = '/index.html', checkport: int = 80, ip: str = None,
              ports: list = [], domain: str = None, internal: bool = False, vms: list = [],
              client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None):
    """Create load balancer"""
    if name is None:
        name = get_random_name().replace('_', '-')
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.create_loadbalancer(name, ports=ports, checkpath=checkpath, vms=vms, domain=domain,
                                      checkport=checkport, internal=internal, ip=ip)


@mcp.tool()
def create_securitygroup(securitygroup: str,
                         client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None, overrides: dict = {}) -> dict:
    """Create security group"""
    securitygroup = securitygroup
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.create_security_group(securitygroup, overrides)


@mcp.tool()
def delete_bucket(buckets: list = [],
                  client: str = None, debug: bool = False, region: str = None,
                  zone: str = None, namespace: str = None):
    """Delete bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for bucket in buckets:
        k.delete_bucket(bucket)


@mcp.tool()
def delete_bucketfile(bucket: str, path: str,
                      client: str = None, debug: bool = False, region: str = None,
                      zone: str = None, namespace: str = None):
    """Delete bucketfile from bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    k.delete_from_bucket(bucket, path)


@mcp.tool()
def delete_dns(names: list, net: str, domain: str = None, allentries: bool = False,
               client: str = None, debug: bool = False, region: str = None,
               zone: str = None, namespace: str = None):
    """Delete dns entry"""
    domain = domain or net
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for name in names:
        k.delete_dns(name, domain, allentries=allentries)


@mcp.tool()
def delete_lb(names: list = [], client: str = None, debug: bool = False, region: str = None,
              zone: str = None, namespace: str = None):
    """Delete load balancer"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    for name in names:
        config.delete_loadbalancer(name)


@mcp.tool()
def delete_securitygroup(securitygroups: list = [],
                         client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None):
    """Delete security group"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    for securitygroup in securitygroups:
        k.delete_security_group(securitygroup)


@mcp.tool()
def download_bucketfile(bucket: str, path: str,
                        client: str = None, debug: bool = False, region: str = None,
                        zone: str = None, namespace: str = None):
    """Download bucketfile from bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    k.download_from_bucket(bucket, path)


@mcp.tool()
def list_bucketfiles(bucket: str,
                     client: str = None, debug: bool = False, region: str = None,
                     zone: str = None, namespace: str = None) -> list:
    """List bucketfiles of bucket"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.list_bucketfiles(bucket)


@mcp.tool()
def list_buckets(client: str = None, debug: bool = False, region: str = None,
                 zone: str = None, namespace: str = None) -> list:
    """List buckets"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.list_buckets()


@mcp.tool()
def list_dns_entries(domain: str = None,
                     client: str = None, debug: bool = False, region: str = None,
                     zone: str = None, namespace: str = None) -> list:
    """List dns entries"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    if domain is None:
        return config.k.list_dns_zones()
    else:
        return config.k.list_dns_(domain)


@mcp.tool()
def list_lbs(client: str = None, debug: bool = False, region: str = None,
             zone: str = None, namespace: str = None) -> list:
    """List load balancers"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    return config.list_loadbalancers()


@mcp.tool()
def list_securitygroups(network: str,
                        client: str = None, debug: bool = False, region: str = None,
                        zone: str = None, namespace: str = None) -> list:
    """List security groups"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    k = config.k
    return k.list_security_groups(network=network)


@mcp.tool()
def update_securitygroup(securitygroup: str,
                         client: str = None, debug: bool = False, region: str = None,
                         zone: str = None, namespace: str = None, overrides: dict = {}):
    """Update security group"""
    config = Kconfig(client=client, debug=debug, region=region, zone=zone, namespace=namespace)
    result = config.k.update_security_group(name=securitygroup, overrides=overrides)
    common.handle_response(result, securitygroup, element='SecurityGroup', action='updated')


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
