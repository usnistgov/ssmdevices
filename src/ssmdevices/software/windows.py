__all__ = ['WLANInfo', 'WLANClient']

import logging
import re
import subprocess as sp
import time

import labbench as lb
from labbench import paramattr as attr
import psutil

if __name__ == '__main__':
    from _networking import network_interface_info
else:
    from ._networking import network_interface_info


class WLANInfo(lb.ShellBackend):
    """parse calls to netsh to get information about WLAN interfaces on the host"""

    background_timeout = attr.value.float(5, inherit=True)
    binary_path = attr.value.Path(r'C:\Windows\System32\netsh.exe', must_exist=True)

    only_bssid: bool = attr.value.bool(False, key='mode=bsside', help='gather only BSSID information')
    interface: str = attr.value.str(None, key='interface', help='name of the interface to query')

    def wait(self):
        try:
            while self.running():
                pass
        except BaseException:
            pass

    @lb.retry(sp.TimeoutExpired, tries=5)
    def get_wlan_ssids(self, interface):
        def pairs_to_dict(lines):
            d = {}
            ssid = None

            for k, v in lines:
                k = k.lower().replace('(', '').replace(')', '').replace(' ', '_')
                if k.startswith('ssid'):
                    ssid = v
                    d[ssid] = {}
                elif ssid is not None:
                    d[ssid][k] = v
            return d

        # Execute the binary
        flags = lb.shell_options_from_keyed_values(self, hide_false=True, join_str='=')
        txt = self.run(
            self.binary_path, 'wlan', 'show', 'networks', *flags, check_return=True
        ).decode()

        # Parse into (key, value) pairs separated by whitespace and a colon
        lines = re.findall(r'^\s*(.*?)\s*:\s*(.*?)\s*$', txt, flags=re.MULTILINE)

        return pairs_to_dict(lines)

    @lb.retry(sp.TimeoutExpired, tries=5)
    def get_wlan_interfaces(self, name=None, param=None):
        def pairs_to_dict(lines):
            d = {}
            name = None

            for k, v in lines:
                k = k.lower().replace('(', '').replace(')', '').replace(' ', '_')
                if k.startswith('name'):
                    name = v
                    d[name] = {}
                elif name is not None:
                    if k == 'signal':
                        v = v.replace('%', '')
                    d[name][k] = v
            return d

        # Execute the binary
        flags = lb.shell_options_from_keyed_values(self, hide_false=True, join_str='=')
        txt = self.run(
            self.binary_path, 'wlan', 'show', 'interfaces', *flags, check_return=True
        ).decode()

        # Parse into (key, value) pairs separated by whitespace and a colon
        lines = re.findall(r'^\s*(\S+.*?)\s+:\s+(\S+.*?)\s*$', txt, flags=re.MULTILINE)

        return pairs_to_dict(lines)


class WLANClient(lb.Device):
    resource: str = attr.value.str(
        None,
        help='interface name (from the OS) or MAC address (nn:nn:nn:nn:nn)',
        cache=True,
    )
    ssid: str = attr.value.str(None, help='SSID of the AP for connection')
    timeout: float = attr.value.float(
        10,
        min=0,
        cache=True,
        help='attempt AP connection for this long before raising ConnectionError',
        label='s',
    )

    def open(self):
        self._import_pywifi()

        available = self.list_available_clients(by='physical_address')
        available_by_interface = {k: v['interface'] for k, v in available.items()}
        if (
            self.resource not in available_by_interface.keys()
            and self.resource not in available_by_interface.values()
        ):
            txt = (
                f"resource '{self.resource}' does not match any of the available "
                f'WLAN interface names {tuple(available_by_interface.keys())} '
                f'or corresponding MAC addresses {tuple(available_by_interface.values())}'
            )
            raise ConnectionError(txt)

        # Use netsh to identify the device guid from the network interface name
        info = network_interface_info(self.resource)
        mac = info['physical_address']

        if mac not in available:
            txt = (
                f"interface with MAC address '{self.resource}' is not one of the "
                f'WLAN interfaces {tuple(available)}'
            )
            print('raising connection error')
            raise ConnectionError(txt)

        guid = available[mac]['guid'].lower()

        ctrl = pywifi.wifi.wifiutil.WifiUtil()

        for iface_key in ctrl.interfaces():
            this_guid = str(iface_key['guid'])[1:-1].lower()
            if this_guid == guid:
                self.backend = pywifi.iface.Interface(iface_key)
                break
        else:
            # This really shouldn't happen
            raise ConnectionError('requested guid not present in pywifi')

        self._logger.debug(
            f"client network interface is '{info['interface']}' "
            f"at physical address '{info['physical_address']}'"
        )

    @classmethod
    def list_available_clients(cls, by='interface'):
        if by not in ('interface', 'guid', 'physical_address'):
            raise ValueError(
                f"argument 'by' must be one of ('interface', 'guid', 'physical_address'), not {by}"
            )

        netsh = WLANInfo()
        # netsh._logger.logger.disabled = True
        with netsh:
            # Check that this interface exists
            interfaces = netsh.get_wlan_interfaces()

        if by == 'interface':
            return interfaces

        ret = {}
        for if_name, if_map in interfaces.items():
            if_map['interface'] = if_name
            ret[if_map[by]] = if_map

        return ret

    @classmethod
    def _import_pywifi(cls):
        global pywifi

        # pywifi wants to clobber the global logging display settings with its own.
        # temporarily monkeypatch logging.basicConfig to bypass this
        try:
            logging.basicConfig, orig_config = lambda **kws: None, logging.basicConfig
            # level = lb.logger.logger.level
            import pywifi

        finally:
            logging.basicConfig = orig_config

        # reduce pywifi logging
        logger = logging.getLogger('pywifi')
        # logger.propagate = False
        # logger.disabled = True
        logger.setLevel(10000000000)

        cls._status_lookup = {
            pywifi.const.IFACE_CONNECTED: 'connected',
            pywifi.const.IFACE_CONNECTING: 'connecting',
            pywifi.const.IFACE_DISCONNECTED: 'disconnected',
            pywifi.const.IFACE_INACTIVE: 'inactive',
            pywifi.const.IFACE_SCANNING: 'scanning',
        }

    def interface_connect(self):
        if self.state == 'connected':
            return 0.0

        # Do the connect
        profile = pywifi.Profile()
        profile.ssid = self.ssid
        self.backend.connect(profile)

        t0 = time.perf_counter()
        while time.perf_counter() - t0 < self.timeout:
            if self.isup:
                break
            lb.sleep(0.02)
        else:
            raise TimeoutError(f'in connecting {repr(self)} to SSID {repr(self.ssid)}')

        t1 = time.perf_counter()
        while time.perf_counter() - t1 < self.timeout:
            s = self.state
            if s == 'connected':
                break
            lb.sleep(0.05)
        else:
            self._logger.debug(f'failed to connect to AP with SSID {repr(self.ssid)}')
            raise TimeoutError(
                'tried to connect but only achieved the {} state '.format(repr(s))
            )

        t2 = time.perf_counter()
        while time.perf_counter() - t2 < self.timeout:
            if self.channel is not None and self.signal is not None:
                break
            lb.sleep(0.02)
        else:
            raise TimeoutError('tried to connect, but got no AP scan information')

        time_elapsed = time.perf_counter() - t0
        self._logger.debug('connected WLAN interface to {}'.format(self.ssid))

        self.backend.scan()

        return time_elapsed

    def interface_disconnect(self):
        """Try to disconnect to the WLAN interface, or raise TimeoutError
        if there is no connection after the specified timeout.

        :param timeout: timeout to wait before raising TimeoutError
        :type timeout: float
        """
        if self.state == 'disconnected':
            return 0.0

        # Disconnect, if necessary
        self.backend.disconnect()

        # First, poll the faster state.isup
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < self.timeout:
            if not self.isup:
                break
            lb.sleep(0.02)
        else:
            raise TimeoutError('tried to disconnect but interface did not go down')

        # Then confirm with
        while time.perf_counter() - t0 < self.timeout:
            s = self.state
            if s == 'disconnected':
                break
            lb.sleep(0.05)
        else:
            raise TimeoutError(
                'tried to disconnect but only achieved the {} state '.format(repr(s))
            )

        self._logger.debug('disconnected WLAN interface')

    def interface_reconnect(self):
        """Reconnect to the network interface.

        :return: time elapsed to reconnect
        """
        self.interface_disconnect()
        return self.interface_connect()

    @attr.property.str(sets=False)
    def state(self):
        """`True` if psutil reports that the interface is up"""
        return self._status_lookup[self.backend.status()]

    @attr.property.bool(sets=False)
    def isup(self):
        """`True` if psutil reports that the interface is up"""
        stats = psutil.net_if_stats()
        iface_name = network_interface_info(self.resource)['interface']
        return stats[iface_name].isup

    @attr.property.int(sets=False, allow_none=True)
    def transmit_rate_mbps(self):
        stats = psutil.net_if_stats()
        iface_name = network_interface_info(self.resource)['interface']
        return stats[iface_name].speed

    @attr.property.int(allow_none=True, max=100, sets=False)
    def signal(self):
        def attempt():
            for result in self.backend.scan_results():
                if result.ssid == self.ssid:
                    return float(result.signal)
            else:
                lb.sleep(0.2)
                raise TimeoutError('interface reported no signal strength')

        t0 = time.perf_counter()
        while time.perf_counter() - t0 < 1.0:
            if self.state != 'scanning':
                break
            lb.sleep(0.02)
        else:
            raise TimeoutError('timeout while scanning for ssid signal strength')

        return lb.until_timeout(TimeoutError, 2 * self.timeout)(attempt)()

    @attr.property.str(sets=False, cache=True)
    def description(self):
        return self.backend.name()

    @attr.property.int(allow_none=True)
    def channel(self):
        def attempt():
            for result in self.backend.scan_results():
                if result.ssid == self.ssid:
                    return float(result.freq) * 1000
            else:
                lb.sleep(0.2)
                raise TimeoutError('interface reported no channel frequency')

        t0 = time.perf_counter()
        while time.perf_counter() - t0 < 1.0:
            if self.state != 'scanning':
                break
            lb.sleep(0.02)
        else:
            raise TimeoutError('ssid signal strength scan timeout')

        return lb.until_timeout(TimeoutError, 2 * self.timeout)(attempt)()

    def refresh(self):
        for attr_def in self._property_attrs:
            getattr(self, attr_def)


if __name__ == '__main__':
    client = WLANClient(
        resource='f8:ac:65:c8:72:bf',  # MAC address of the wireless client device on the host
        ssid='EnGenius1',  # SSID name to connect with
        timeout=5,  # (s) how long to continue attempts to connect the client and AP
    )

    with client:
        pass

    # with Netsh() as netsh:
    #     # Check that this interface exists
    #     available_interfaces = netsh.get_wlan_interfaces()
    #     print(available_interfaces)
    #
    #     print(netsh.get_wlan_ssids(list(available_interfaces)[0]))

    # with WLANStatus(resource='WLAN_Client_DUT', ssid='EnGenius1') as wlan:
    #     wlan.interface_reconnect()
    #     for attr in wlan._traits:
    #         print(attr, ':', getattr(wlan.state, attr))

#        while True:
#            print('isup: ', wlan.isup)
#            state = wlan.state
#            if state == 'connected':
#                try:
#                    print('RSSI "{}%"'.format(wlan.signal))
#                except:
#                    pass
#            else:
#                print(f'not connected - {state} instead')
#            lb.sleep(.25)
