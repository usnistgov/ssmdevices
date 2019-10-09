# -*- coding: utf-8 -*-
__all__ = ['Netsh','WLANStatus','WLANException','WLANAPException']

import labbench as lb
import re,time
import subprocess as sp
import psutil
import logging

class WLANException(lb.DeviceException):
    pass

class WLANInterfaceException(WLANException):
    pass

class WLANAPException(WLANException):
    pass

class Netsh(lb.CommandLineWrapper):
    ''' Parse calls to netsh to get information about available WLAN access
        points.
    '''
    
    settings = lb.CommandLineWrapper\
                 .settings\
                 .define(binary_path=r'C:\Windows\System32\netsh.exe',
                         arguments=['wlan'],
                         timeout=5)
    
    def wait (self):
        try:
            while self.running():
                pass
        except:
            pass
    
    @lb.retry(sp.TimeoutExpired, tries=5)
    def get_wlan_ssids (self, interface):
        def pairs_to_dict(lines):
            d = {}
            ssid = None
                       
            for k,v in lines:
                k = k.lower().replace('(','').replace(')','').replace(' ','_')                
                if k.startswith('ssid'):
                    ssid = v
                    d[ssid] = {}
                elif ssid is not None:
                    d[ssid][k] = v
            return d

        # Execute the binary
        txt = self.foreground('show', 'networks', 'mode=bssid', interface).decode()

        # Parse into (key, value) pairs separated by whitespace and a colon
        lines = re.findall(r'^\s*(.*?)\s*:\s*(.*?)\s*$',txt,flags=re.MULTILINE)

        return pairs_to_dict(lines)

    @lb.retry(sp.TimeoutExpired, tries=5)
    def get_wlan_interfaces (self, name=None, param=None):
        def pairs_to_dict(lines):
            d = {}
            name = None
            
            for k,v in lines:
                k = k.lower().replace('(','').replace(')','').replace(' ','_')               
                if k.startswith('name'):
                    name = v
                    d[name] = {}
                elif name is not None:
                    if k == 'signal':
                        v = v.replace('%','')
                    d[name][k] = v
            return d

        # Execute the binary
        txt = self.foreground('show', 'interfaces').decode()       
        
        # Parse into (key, value) pairs separated by whitespace and a colon
        lines = re.findall(r'^\s*(\S+.*?)\s+:\s+(\S+.*?)\s*$',txt,flags=re.MULTILINE)

        return pairs_to_dict(lines)
    

class WLANStatus(lb.Device):    
    class settings(lb.Device.settings):
        resource           = lb.Unicode(allow_none=True)
        ssid               = lb.Unicode(allow_none=True)
        timeout            = lb.Float(10, min=0)

    class state(lb.Device.state):
        # SSID info
        channel            = lb.Int(allow_none=True,read_only=True,command='ssid')
        signal             = lb.Int(allow_none=True,max=100,read_only=True,command='ssid')

        # Interface info
        description        = lb.Unicode(read_only=True,command='interface')
        state              = lb.Unicode(read_only=True,command='interface')
        isup               = lb.Bool(help='whether the interface is up as reported by psutil')
        transmit_rate_mbps = lb.Int(read_only=True,allow_none=True,command='ssid')

    def connect (self):
        # Use netsh to identify the device guid from the network interface name
        with Netsh() as netsh:
            # Check that this interface exists
            available_interfaces = netsh.get_wlan_interfaces()
            
            if not self.settings.resource:
                raise WLANInterfaceException('must set resource to the name of a WLAN network interface (currently one of {})'\
                                             .format(repr(available_interfaces)))
            elif self.settings.resource not in available_interfaces:
                raise WLANInterfaceException('requested WLAN interface {}, but only {} are available'\
                                             .format(repr(self.settings.resource),
                                                     repr(available_interfaces)))
                
            guid = available_interfaces[self.settings.resource]['guid'].lower()

        ctrl = pywifi.wifi.wifiutil.WifiUtil()
        global outguid
        for iface_key in ctrl.interfaces():
            this_guid = str(iface_key['guid'])[1:-1].lower()
            if this_guid == guid:
                self.backend = pywifi.iface.Interface(iface_key)
                break
        else:
            # This really shouldn't happen
            raise WLANInterfaceException('requested guid not present in pywifi')

    @classmethod
    def __imports__(cls):
        global pywifi
        level = lb.logger.level
        try:
            import pywifi
        except ImportError:
            raise ImportError('install pywifi to use WLANStatus: pip install pywifi')
        
        logger = logging.getLogger('pywifi')
        logger.propagate = False

        # Reset the level that has been changed by pywifi
        lb.logger.setLevel(level)
        
        cls._status_lookup = {pywifi.const.IFACE_CONNECTED: 'connected',
                              pywifi.const.IFACE_CONNECTING: 'connecting',
                              pywifi.const.IFACE_DISCONNECTED: 'disconnected',
                              pywifi.const.IFACE_INACTIVE: 'inactive',
                              pywifi.const.IFACE_SCANNING: 'scanning'}

    def interface_connect(self):
        if self.state.state == 'connected':
            return 0.
        
        # Do the connect
        profile = pywifi.Profile()
        profile.ssid = self.settings.ssid
        self.backend.connect(profile)
    
        t0 = time.perf_counter()
        while time.perf_counter()-t0 < self.settings.timeout:
            if self.state.isup:
                break
            lb.sleep(.02)
        else:
            raise TimeoutError(f'tried to connect but interface {repr(self)} did not go up')

        t1 = time.perf_counter()
        while time.perf_counter()-t1 < self.settings.timeout:
            s = self.state.state
            if s == 'connected':                
                break
            lb.sleep(.05)
        else:
            self.logger.debug('failed to reconnect to WLAN AP with SSID {}'\
                              .format(self.settings.ssid))
            raise TimeoutError('tried to connect but only achieved the {} state '\
                               .format(repr(s)))

        t2 = time.perf_counter()
        while time.perf_counter()-t2 < self.settings.timeout:
            if self.state.channel is not None and self.state.signal is not None:
                break
            lb.sleep(.02)
        else:
            raise TimeoutError('tried to connect, but got no AP scan information')            
            
        time_elapsed = time.perf_counter()-t0
        self.logger.debug('connected WLAN interface to {}'.format(self.settings.ssid))
        
        self.backend.scan()

        return time_elapsed

    def interface_disconnect(self):
        ''' Try to disconnect to the WLAN interface, or raise TimeoutError
            if there is no connection after the specified timeout.
            
            :param timeout: timeout to wait before raising TimeoutError
            :type timeout: float
        '''
        if self.state.state == 'disconnected':
            return 0.
        
        # Disconnect, if necessary
        self.backend.disconnect()

        # First, poll the faster state.isup
        t0 = time.perf_counter()
        while time.perf_counter()-t0 < self.settings.timeout:
            if not self.state.isup:
                break
            lb.sleep(.02)
        else:
            raise TimeoutError('tried to disconnect but interface did not go down')
            
        # Then confirm with 
        while time.perf_counter()-t0 < self.settings.timeout:
            s = self.state.state
            if s == 'disconnected':
                break
            lb.sleep(.05)
        else:
            raise TimeoutError('tried to disconnect but only achieved the {} state '\
                               .format(repr(s)))            

        self.logger.debug('disconnected WLAN interface')

    def interface_reconnect(self):
        ''' Reconnect to the network interface.
        
            :return: time elapsed to reconnect
        '''        
        self.interface_disconnect()            
        return self.interface_connect()

    @state.state.getter
    def __(self):        
        return self._status_lookup[self.backend.status()]
    
    @state.isup.getter
    def __(self):
        stats = psutil.net_if_stats()
        return stats[self.settings.resource].isup
    
    @state.transmit_rate_mbps.getter
    def __(self):
        stats = psutil.net_if_stats()
        return stats[self.settings.resource].speed
    
    @state.signal.getter
    def __(self):
        def attempt():            
            for result in self.backend.scan_results():
                if result.ssid == self.settings.ssid:
                    return float(result.signal)
            else:
                lb.sleep(.2)
                raise TimeoutError('interface reported no signal strength')

        t0 = time.perf_counter()
        while time.perf_counter()-t0 < 1.:
            if self.state.state != 'scanning':
                break
            lb.sleep(.02)
        else:
            raise TimeoutError('timeout while scanning for ssid signal strength')
                
        return lb.until_timeout(TimeoutError, 2*self.settings.timeout)(attempt)()

    @state.description.getter
    def __(self):
        return self.backend.name()
        
    @state.channel.getter
    def __(self):
        def attempt(): 
            for result in self.backend.scan_results():
                if result.ssid == self.settings.ssid:
                    return float(result.freq)*1000
            else:
                lb.sleep(0.2)
                raise TimeoutError('interface reported no channel frequency')

        t0 = time.perf_counter()
        while time.perf_counter()-t0 < 1.:
            if self.state.state != 'scanning':
                break
            lb.sleep(.02)
        else:
            raise TimeoutError('timeout while scanning for ssid signal strength')
                
        return lb.until_timeout(TimeoutError, 2*self.settings.timeout)(attempt)()

    def refresh(self):
        for attr in self.state.traits().keys():
            getattr(self.state, attr)

if __name__ == '__main__':
    with WLANStatus(resource='WLAN_Client_DUT', ssid='EnGenius1') as wlan:
        wlan.interface_reconnect()
        for attr in wlan.state.traits().keys():
            print(attr, ':', getattr(wlan.state, attr))
#        while True:
#            print('isup: ', wlan.state.isup)
#            state = wlan.state.state
#            if state == 'connected':
#                try:
#                    print('RSSI "{}%"'.format(wlan.state.signal))
#                except:
#                    pass
#            else:
#                print(f'not connected - {state} instead')
#            lb.sleep(.25)