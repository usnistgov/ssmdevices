import psutil
import socket
import re

INTERFACE_FIELDS = ('interface', 'ip_address', 'physical_address', 'ipv6_address')


def list_network_interfaces(by='interface'):
    f"""Try to look up the IP address corresponding to the network interface
    referred to by the OS with the name `iface`.

    If the interface does not exist, the medium is disconnected, or there
    is no IP address associated with the interface, raise `ConnectionError`.

    :param by: the field to use as the key in the return dictionary. one of {INTERFACE_FIELDS}

    """
    if by not in INTERFACE_FIELDS:
        raise ValueError(f"by '{by}' is not one of {INTERFACE_FIELDS}")

    ret = {}
    for name, if_structs in psutil.net_if_addrs().items():
        iface = dict(interface=name)
        for family_info in if_structs:
            if family_info.family is socket.AF_INET:
                iface['ip_address'] = family_info.address
                iface['ip_netmask'] = family_info.netmask
                iface['ip_broadcast'] = family_info.broadcast
            elif family_info.family is socket.AF_INET6:
                iface['ipv6_address'] = family_info.address
                iface['ipv6_netmask'] = family_info.netmask
                iface['ipv6_broadcast'] = family_info.broadcast
            elif family_info.family is psutil.AF_LINK:
                iface['physical_address'] = family_info.address.replace(
                    '-', ':'
                ).lower()

        if by in iface:
            ret[iface[by]] = iface

    return ret


def network_interface_info(resource):
    """Try to look up the IP address of a network interface by its name
    or MAC (physical) address.

    If the interface does not exist, the medium is disconnected, or there
    is no IP address associated with the interface, raise `ConnectionError`.
    """
    if re.match(
        r'([0-9a-f]{2}:){5}[0-9a-f]{2}',
        resource.lower().replace('-', ':'),
        re.IGNORECASE,
    ):
        # it's a physical address
        addrs = list_network_interfaces('physical_address')
        resource = resource.lower().replace('-', ':')
    else:
        addrs = list_network_interfaces('interface')

    # Check whether the interface exists
    if resource not in addrs:
        available = ', '.join(addrs.keys())
        msg = (
            f'requested interface for "{resource}" but only ({available}) are available'
        )
        raise ConnectionError(msg)

    return addrs[resource]


def get_ipv4_occupied_ports(ip):
    return {
        conn.laddr[1]
        for conn in psutil.net_connections(kind='inet4')
        if ip in conn.laddr
    }


def get_ipv4_address(resource):
    """Try to look up the IP address of a network interface by its name
    or MAC (physical) address.

    If the interface does not exist, the medium is disconnected, or there
    is no IP address associated with the interface, raise `ConnectionError`.
    """
    info = network_interface_info(resource)

    # Check whether it's up, which is necessary for a good IP address
    if not psutil.net_if_stats()[info['interface']].isup:
        raise ConnectionError(
            f"the network interface {info['interface']} ({info['physical_address']}) is disabled or disconnected"
        )

    # lookup and return the address
    if 'ip_address' not in info:
        raise ConnectionError(
            f"no ipv4 address associated with interface '{info['interface']}' ({info['physical_address']})"
        )

    return info['ip_address']


def find_free_port():
    from contextlib import closing

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


if __name__ == '__main__':
    print(list_network_interfaces('physical_address'))
