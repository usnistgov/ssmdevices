# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
__all__ = ['Netsh','WLANStatus','WLANException','WLANAPException']

import labbench as lb
import traitlets as tl
import re,time

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
                         timeout=3)
    
    def wait (self):
        try:
            while self.running():
                pass
        except:
            pass
    
    def get_wlan_ssids (self):
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
        txt = self.foreground('show', 'networks', 'mode=bssid').decode()

        # Parse into (key, value) pairs separated by whitespace and a colon
        lines = re.findall(r'^\s*(.*?)\s*:\s*(.*?)\s*$',txt,flags=re.MULTILINE)

        return pairs_to_dict(lines)
    
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

    def set_interface_connected (self, interface, profile):
        ret = self.foreground('connect',
                              'name="{}"'.format(profile),
                              'interface="{}"'.format(interface)).decode()
        
        if 'success' in ret:
            return
        elif 'there is no profile' in ret.lower():
            raise WLANAPException(ret)
        elif 'no such wireless interface' in ret.lower():
            raise WLANInterfaceException(ret)
        else:
            raise ValueError('unknown netsh return {}'.format(repr(ret)))
            
    def set_interface_disconnected (self, interface):
        ret = self.foreground('disconnect',
                              'interface="{}"'.format(interface)).decode()
        
        if 'success' in ret:
            return
        elif 'no such wireless interface' in ret.lower():
            raise WLANInterfaceException(ret)
        else:
            raise ValueError('unknown netsh return {}'.format(repr(ret)))
        


class WLANStatus(lb.Device):
    class settings(lb.Device.settings):
        resource           = lb.Unicode(allow_none=True)
        ssid               = lb.Unicode(allow_none=True)

    class state(lb.Device.state):
        # SSID info
        bssid              = lb.Unicode(read_only=True,allow_none=True,command='ssid')
        bssid_1            = lb.Unicode(read_only=True,allow_none=True,command='ssid')
        bssid_2            = lb.Unicode(read_only=True,allow_none=True,command='ssid')
        bssid_3            = lb.Unicode(read_only=True,allow_none=True,command='ssid')
        bssid_4            = lb.Unicode(read_only=True,allow_none=True,command='ssid')
        channel            = lb.Int(min=0,allow_none=True,read_only=True,command='ssid')
        signal             = lb.Int(min=0,allow_none=True,max=100,read_only=True,command='ssid')
        ssid               = lb.Unicode(read_only=True,allow_none=True,command='ssid')
        transmit_rate_mbps = lb.Int(min=0,read_only=True,allow_none=True,command='ssid')
        radio_type         = lb.Unicode(read_only=True,allow_none=True,command='ssid')
        encryption         = lb.Unicode(read_only=True,allow_none=True,command='ssid')

        # Interface info
        description        = lb.Unicode(read_only=True,command='interface')
        state              = lb.Unicode(read_only=True,command='interface')
        radio_status       = lb.Unicode(read_only=True,command='interface')

    def connect (self):
        self.backend = Netsh()
        self.backend.connect()

        # Check that this interface exists
        available_interfaces = list(self.backend.get_wlan_interfaces().keys())
        if self.settings.resource not in available_interfaces:
            raise WLANInterfaceException('requested WLAN interface {}, but only {} are available'\
                                         .format(repr(self.settings.resource),
                                                 repr(available_interfaces)))

    def disconnect (self):
        self.backend.disconnect()

    def reconnect_interface(self, timeout=2):
        ''' Disconnect from the WLAN interface, and reconnect.
        '''
        
        # Disconnect, if necessary
        if self.state.state != 'disconnected':
            self.backend.set_interface_disconnected(self.settings.resource)

            t0 = time.time()
            while time.time()-t0 < timeout:
                s = self.state.state
                if s == 'disconnected':
                    break
                lb.sleep(.05)
            else:
                raise TimeoutError('tried to connect but only achieved the state '+s)

        # Connect
        self.backend.set_interface_connected(self.settings.resource,
                                             self.settings.ssid)

        t0 = time.time()
        while time.time()-t0 < timeout:
            s = self.state.state
            if s == 'connected':
                break
            lb.sleep(.05)
        else:
            self.logger.debug('failed to reconnect to WLAN AP with SSID {}'\
                              .format(self.settings.ssid))
            raise TimeoutError('tried to connect but only achieved the {} state '\
                               .format(repr(s)))
            
        self.logger.debug('reconnected')

    @state.getter
    def __(self, trait):
        ret = lb.concurrently(self.backend.get_wlan_interfaces,
                              self.backend.get_wlan_ssids,flatten=False)
        interfaces = ret.pop('get_wlan_interfaces')
        ssids = ret.pop('get_wlan_ssids')
        
        resource = self.settings.resource

        # When resource is None, try to automatically pick one
        if self.settings.resource is None:
            if len(interfaces) == 0:
                raise OSError('no WLAN interfaces available')
            elif len(interfaces) != 1:
                available = ' ,'.join(interfaces.keys())
                raise Exception('resource needs to be specified to specify one of the available WLAN interfaces ({})'\
                                .format())
            elif len(interfaces) == 1:
                resource = list(interfaces.keys())[0]
        
        if resource not in interfaces:
            self.logger.warn('windows reports no WLAN interface named "{}"'\
                             .format(self.settings.resource))
            
            if len(interfaces) == 0:
                msg = 'requested WLAN interface "{}" does not exist, and no other interfaces are available'\
                      .format(resource)
            else:
                available = ' ,'.join(interfaces.keys())
                msg = 'requested WLAN interface "{}" does not exist. windows reports only {}'\
                              .format(resource, available)
            #raise Exception('windows reports no WLAN interface named "{}"'.format(self.settings.resource['interface']))
            raise OSError(msg)
            
            self.logger.warn('OS reports no WLAN interface named {}'\
                             .format(repr(resource)))
            return None
        interface = interfaces[resource]

        # Look for info
        ssid = ssids.get(self.settings.ssid, {})
        if ssid is {}:
            self.logger.debug('OS does not report requested ssid {} on {}'\
                              .format(self.settings.ssid,self.settings.resource))

        # Set the other traits with the other dictionary values
        for name,other_trait in self.state.traits().items():
            # set the other traits directly with traitlets, bypassing the labbench
            # remote get/set
            if other_trait.command == 'ssid':
                if name == 'signal' and name in ssid:
                    ssid['signal'] = ssid['signal'].replace('%','')
                other_trait._parent.set(other_trait, self.state,
                                        ssid.get(name,None))
            elif other_trait.command == 'interface':
                other_trait._parent.set(other_trait, self.state,
                                        interface.get(name,None))
                
            if other_trait is trait:
                if name in interface:
                    ret = interface[name]
                else:
                    ret = ssid.get(name, None)

        return ret

if __name__ == '__main__':
    import time
        
    with WLANStatus(ssid='EnGenius1') as wlan:
        while True:
            if wlan.state.state == 'connected':
                try:
                    print('{}%'.format(wlan.state.signal))
                except:
                    pass
            else:
                print('not connected')
            lb.sleep(.25)