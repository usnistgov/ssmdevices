# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

from builtins import super
from future import standard_library
standard_library.install_aliases()
__all__ = ['Netsh','WLANStatus']

import labbench as lb
import traitlets as tl
import re,threading,time
import subprocess as sp

class Netsh(lb.CommandLineWrapper):
    ''' Parse calls to netsh to get information about available WLAN access
        points.
    '''
    
    settings = lb.CommandLineWrapper\
                 .settings\
                 .define(binary_path=r'C:\Windows\System32\netsh.exe',
                         arguments=['wlan'])
    
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
#        self.wait()
        super(Netsh,self).foreground('show', 'networks', 'mode=bssid')
        
        # Block until the call finishes, then fetch the output text
#        self.wait()
        txt = self.read_stdout()
        
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
#        self.wait()
        super(Netsh,self).foreground('show', 'interfaces')
        
        # Block until the call finishes, then fetch the output text
#        self.wait()
        txt = self.read_stdout()
        
        # Parse into (key, value) pairs separated by whitespace and a colon
        lines = re.findall(r'^\s*(\S+.*?)\s+:\s+(\S+.*?)\s*$',txt,flags=re.MULTILINE)

        return pairs_to_dict(lines)

    def set_interface_connected (self, interface, profile):
        args = ['wlan', 'connect', 'name="{}"'.format(profile),'interface="{}"'.format(interface)]
        self.wait()
        si = sp.STARTUPINFO()
        si.dwFlags |= sp.STARTF_USESHOWWINDOW
        proc = sp.Popen(args, stdout=sp.PIPE, startupinfo=si,
                        bufsize=1, universal_newlines=True,
                        creationflags=sp.CREATE_NEW_PROCESS_GROUP,
                        stderr=sp.PIPE)
        proc.wait()


class WLANStatus(lb.Device):
    class settings(lb.Device.settings):
        resource           = lb.Unicode(allow_none=True)
        ssid               = lb.Unicode(allow_none=True)
        force_reconnect    = tl.Bool(True)        

    class state(lb.Device.state):
        bssid              = lb.Bytes(read_only=True,)
        channel            = lb.Int(min=0,read_only=True)
        signal             = lb.Int(min=0,max=100,read_only=True)
        ssid               = lb.Bytes(read_only=True,)
        transmit_rate_mbps = lb.Int(min=0,read_only=True)
        radio_type         = lb.Bytes(read_only=True)
        state              = lb.Bytes(read_only=True)

    def connect (self):
        self.backend = Netsh()
        self.backend.connect()
        
        def reconnect():
            states = {}
            def onchange (args):
                states[args['name']] = args['new']
            self.state.observe(onchange)
            
            self.logger.debug('starting WLAN reconnect watchdog')
            iface = self.settings.resource
            target_ssid = self.settings.ssid
            time.sleep(0.1)
            
            while True:
                if not self.state.connected:
                    return
#                self.state.state
                if states.get('state',None) != 'disconnected':
                    if target_ssid is None:
                        target_ssid = states.get('ssid', None)
                elif self.settings.force_reconnect:
                    if target_ssid is None:
                        self.logger.warn("{}, but don't know SSID for reconnection".format(iface))
                    else:
                        self.logger.warn("{}, reconnecting to {}".format(iface,target_ssid))
                        self.backend.set_interface_connected(self.settings.resource,
                                                             target_ssid)
                        
                time.sleep(.1)
        
        threading.Thread(target=reconnect).start()

    def disconnect (self):
        self.backend.disconnect()
    
    def command_get (self, command, trait):
        d = self.backend.get_wlan_interfaces()
        resource = self.settings.resource
        
        if self.settings.resource is None:
            if len(d) == 0:
                raise OSError('no WLAN interfaces available')
            if len(d) != 1:
                available = ' ,'.join(d.keys())
                raise Exception('resource needs to be specified to specify one of the available WLAN interfaces ({})'\
                                .format())
            resource = list(d.keys())[0]
        
        if resource not in d:
            self.logger.warn('windows reports no WLAN interface named "{}"'\
                             .format(self.settings.resource))
            
            if len(d) == 0:
                msg = 'requested WLAN interface "{}" does not exist, and no other interfaces are available'\
                      .format(resource)
            else:
                available = ' ,'.join(d.keys())
                msg = 'requested WLAN interface "{}" does not exist. windows reports only {}'\
                              .format(resource, available)
            #raise Exception('windows reports no WLAN interface named "{}"'.format(self.settings.resource['interface']))
            raise OSError(msg)
            
            self.logger.warn('windows reports no WLAN interface named "{}"'\
                             .format(resource))
            return None
        d = d[resource]
        
        # Set the other traits with the other dictionary values
        for other in list(self.state.traits().values()):
            if other.name in d and other.name != trait.name:
                # sneak in under the hood and set the other traits directly 
                # with traitlets
                other._parent.set(other, self.state, d[other.name])
            
        return d[trait.name]

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
            time.sleep(.25)