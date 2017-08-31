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
import re

class Netsh(lb.CommandLineWrapper):
    ''' Parse calls to netsh to get information about available WLAN access
        points.
    '''
    binary_path = r'C:\Windows\System32\netsh.exe'
    
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
        super(Netsh,self).execute([self.binary_path]+args)
        
        # Block until the call finishes, then fetch the output text
        try:
            while self.running():
                pass
        except:
            pass
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
        super(Netsh,self).execute([self.binary_path]+args)
        
        # Block until the call finishes, then fetch the output text
        try:
            while self.running():
                pass
        except:
            pass
        txt = self.fetch()
        
        # Parse into (key, value) pairs separated by whitespace and a colon
        lines = re.findall(r'^\s*(\S+.*?)\s+:\s+(\S+.*?)\s*$',txt,flags=re.MULTILINE)

        return pairs_to_dict(lines)

class WLANStatus(lb.Device):
    resource = 'Wi-Fi'

    class state(lb.Device.state):
        bssid              = lb.Bytes(readonly=True)
        channel            = lb.Int(min=1,readonly=True)
        signal             = lb.Int(min=0,max=100,readonly=True)
        ssid               = lb.Bytes(readonly=True)
        transmit_rate_mbps = lb.Int(min=0,readonly=True)
        radio_type         = lb.Bytes(readonly=True)
        state              = lb.Bytes(readonly=True)
    
    def connect (self):
        self.backend = Netsh()
        self.backend.connect()
        
    def disconnect (self):
        pass
    
    def command_get (self, command, trait):
        d = self.backend.get_wlan_interfaces()
        if self.resource not in d:
            raise Exception('windows reports no WLAN interface named "{}"'.format(self.resource))
        d = d[self.resource]
        
        # Set the other traits with the other dictionary values
        for other in self.state.traits().values():
            if other.name in d and other.name != trait.name:
                # sneak in under the hood and set the other traits directly 
                # with traitlets
                other._trait_cls().set(other, self.state, d[other.name])
            
        return d[trait.name]

if __name__ == '__main__':
    with WLANStatus() as wlan:
        wlan.state.observe(notify)
        print 'hello there ssid! ', wlan.state.ssid