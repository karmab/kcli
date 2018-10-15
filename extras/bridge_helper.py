#!/usr/bin/env python
# coding=utf-8

import logging
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import Ether, ARP, srp
import argparse
import yaml


def get_ip_from_mac(interface, cidr, mac):
    """

    """
    if interface is None or cidr is None:
        return None
    if mac is None:
        results = {}
        packet = Ether(dst='ff:ff:ff:ff:ff:ff') / ARP(pdst=cidr)
    else:
        packet = Ether(dst=mac) / ARP(pdst=cidr)
    ans, unans = srp(packet, timeout=2, iface=interface, verbose=False)
    for s, r in ans:
            currentmac = r.sprintf("%Ether.src%")
            if mac is None:
                results[currentmac] = r.sprintf("%ARP.psrc%")
            elif currentmac == mac:
                return r.sprintf("%ARP.psrc%")
    if mac is None:
        return yaml.dump(results)
    else:
        return None


def cli():
    """

    """

    parser = argparse.ArgumentParser(description='Helper client gathering ip from mac')
    parser.add_argument('-i', '--interface')
    parser.add_argument('-c', '--cidr')
    parser.add_argument('-m', '--mac')
    args = parser.parse_args()
    mac = get_ip_from_mac(args.interface, args.cidr, args.mac)
    if mac is not None:
        print(mac)


if __name__ == '__main__':
    cli()
