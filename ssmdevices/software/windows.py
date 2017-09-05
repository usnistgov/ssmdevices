# -*- coding: utf-8 -*-
"""
Created on Thu Aug 31 10:19:14 2017

@author: dkuester
"""

# -*- coding: utf-8 -*-
"""
Created on Thu May 11 09:39:43 2017

@author: dkuester
"""

__all__ = ['Netsh','WLANStatus']

import labbench as lb
import traitlets as tl
import re,threading,time,logging
import subprocess as sp

logger = logging.getLogger('labbench')

class Netsh(lb.CommandLineWrapper):
    ''' Parse calls to netsh to get information about available WLAN access
        points.
    '''
    binary_path = r'C:\Windows\System32\netsh.exe'
    
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
        args = ['wlan','show','networks','mode=bssid']
        self.wait()
        super(Netsh,self).execute([self.binary_path]+args)
        
        # Block until the call finishes, then fetch the output text
        self.wait()
        txt = self.fetch()
        
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
        args = ['wlan','show','interfaces']
        self.wait()
        super(Netsh,self).execute([self.binary_path]+args)
        
        # Block until the call finishes, then fetch the output text
        self.wait()
        txt = self.fetch()
        
        # Parse into (key, value) pairs separated by whitespace and a colon
        lines = re.findall(r'^\s*(\S+.*?)\s+:\s+(\S+.*?)\s*$',txt,flags=re.MULTILINE)

        return pairs_to_dict(lines)

    def set_interface_connected (self, interface, profile):
        args = ['wlan', 'connect', 'name="{}"'.format(profile),'interface="{}"'.format(interface)]
        self.wait()
        si = sp.STARTUPINFO()
        si.dwFlags |= sp.STARTF_USESHOWWINDOW
        args = [self.binary_path]+args
        proc = sp.Popen(args, stdout=sp.PIPE, startupinfo=si,
                        bufsize=1, universal_newlines=True,
                        creationflags=sp.CREATE_NEW_PROCESS_GROUP,
                        stderr=sp.PIPE)
        proc.wait()

class WLANStatus(lb.Device):
    resource = {'interface': 'Wi-Fi',
                'ssid': None}

    class state(lb.Device.state):
        bssid              = lb.Bytes(readonly=True)
        channel            = lb.Int(min=0,readonly=True)
        signal             = lb.Int(min=0,max=100,readonly=True)
        ssid               = lb.Bytes(readonly=True)
        transmit_rate_mbps = lb.Int(min=0,readonly=True)
        radio_type         = lb.Bytes(readonly=True)
        state              = lb.Bytes(readonly=True)
        force_reconnect    = tl.Bool(True)

    def connect (self):
        self.backend = Netsh()
        self.backend.connect()
        
        def reconnect():
            states = {}
            def onchange (args):
                states[args['name']] = args['new']
            self.state.observe(onchange)
            
            logger.debug('starting WLAN reconnect watchdog')
            iface,target_ssid = self.resource['interface'],self.resource['ssid']
            time.sleep(0.1)
            
            while True:
                if not self.state.connected:
                    return
#                self.state.state
                if states.get('state',None) != 'disconnected':
                    if target_ssid is None:
                        target_ssid = states.get('ssid', None)
                elif self.state.force_reconnect:
                    if target_ssid is None:
                        logger.warn("{}, but don't know SSID for reconnection".format(iface))
                    else:
                        logger.warn("{}, reconnecting to {}".format(iface,target_ssid))
                        self.backend.set_interface_connected(self.resource['interface'],
                                                             target_ssid)
                        
                time.sleep(.1)
        
        threading.Thread(target=reconnect).start()

    def disconnect (self):
        pass
    
    def command_get (self, command, trait):
        d = self.backend.get_wlan_interfaces()
        if self.resource['interface'] not in d:
            #raise Exception('windows reports no WLAN interface named "{}"'.format(self.resource['interface']))
            logger.warn('windows reports no WLAN interface named "{}"'.format(self.resource['interface']))
            return None
        d = d[self.resource['interface']]
        
        # Set the other traits with the other dictionary values
        for other in self.state.traits().values():
            if other.name in d and other.name != trait.name:
                # sneak in under the hood and set the other traits directly 
                # with traitlets
                other._trait_cls().set(other, self.state, d[other.name])
            
        return d[trait.name]

if __name__ == '__main__':
    import time
        
    with WLANStatus({'interface': 'Wi-Fi', 'ssid': 'EnGenius1'}) as wlan:
        while True:
            if wlan.state.state == 'connected':
                try:
                    print '{}%'.format(wlan.state.signal)
                except:
                    pass
            else:
                print 'not connected'
            time.sleep(.25)