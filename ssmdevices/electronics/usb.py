'''
Drivers for USB peripherals

:author: Dan Kuester <daniel.kuester@nist.gov>, Andre Rosete <andre.rosete@nist.gov>
'''
import labbench as lb

import logging
logger = logging.getLogger('labbench')

class AcronameUSBHub2x4(lb.Device):
    ''' This class wraps brainstem drivers to simplify control over USB hubs
        via the brainstem package.
        
        The only functionality exposed by method of this class is the ability
        to dynamically enable and disable USB 3.0 ports.
    
        :param resource: Serial number string specifying the device to connect to.
        If None (default), the brainstem driver will try to automatically choose
        a connected device.
        
    '''
    model = 17
    resource = None

    class state (lb.Device.state):
        data0_enabled  = lb.Bool()
        data1_enabled  = lb.Bool()
        data2_enabled  = lb.Bool()
        data3_enabled  = lb.Bool()

        power0_enabled = lb.Bool()
        power1_enabled = lb.Bool()
        power2_enabled = lb.Bool()
        power3_enabled = lb.Bool()
    
    def __init__ (self, resource=None):
        super(type(self), self).__init__(resource)
        
        try:
            import brainstem
        except Exception,e:
            logger.error('Could not import the brainstem package, a prerequisite for {} control'\
                         .format(type(self).__name__))
            raise e
            
    def connect (self):
        import brainstem
        
        specs = self._bs.discover.findAllModules(brainstem.link.Spec.USB)

        specs = [s for s in specs if s.model == self.model]        
        if self.resource is not None:
            specs = [s for s in specs if s.serial_number == self.resource]
    
        if len(specs)>1:
            if self.resource is None:
                raise Exception("More than one connected USB device matches model " + str(self.model) + " - provide serial number?")
            else:
                raise Exception("More than one connected USB device match model " + str(self.model) + " and serial " + str(self.serial))
        elif len(specs)==0:
            raise Exception("No USB devices connected that match model " + str(self.model) + " and serial " + str(serial))
            
        self.backend = brainstem.stem.USBHub2x4()
        self.backend.connectFromSpec(specs[0])
        
    def disconnect (self):
        ''' Release control over the device.
        '''
        self.backend.disconnect()
        
    def command_set (self, command, trait, value):
        ''' Apply an instrument setting to the instrument. The value ``value''
            will be applied to the trait attriute ``attr'' in type(self).
        '''
        raise NotImplementedError('state "{attr}" is defined but not implemented! implement {cls}.command_get, or implement a getter for {cls}.state.{attr}'\
                                  .format(cls=type(self).__name__, attr=attr))
        
    def enable (self, data = True, power = True, channel= "all"):
        ''' Enable or disable of USB port features at one or all hub ports.
            
            :param data:  Enables data on the port (if evaluates to true)
            
            :param power: Enables power on the port (if evaluates to true)
            
            :param channel: An integer port number specifies the port to act on,
             otherwise 'all' (the default) applies the port settings to all
             ports on the hub.
        '''
        if channel == "all":
            channels = range(4)
        elif isinstance(channel, collections.Iterable):
            channels = channel
        else:
            channels = [channel]
        
        for chan in channels:
            if power:
                self._hub.usb.setPortEnable(chan)
            else:
                self._hub.usb.setPortDisable(chan)
            if data:
                self._hub.usb.setDataEnable(chan)
            else:
                self._hub.usb.setDataDisable(chan)
                        
