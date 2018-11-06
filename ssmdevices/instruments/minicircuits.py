# -*- coding: utf-8 -*-

import time
import labbench as lb
import hid, platform
import numpy as np

class MiniCircuitsUSBDevice(lb.Device):
    VID = 0x20ce
    
    class settings(lb.Device.settings):
        resource = lb.Unicode(None, help='Serial number of the USB device. Must be defined if more than one device is connected to the computer', allow_none=True)        
        path = lb.Bytes(None, allow_none=True,
                        help='override `resource` to connect to a specific USB path')
        timeout = lb.Int(5, min=0.5)
    
    class state(lb.Device.state):
        model         = lb.Unicode(read_only=True, cache=True, is_metadata=True)
        serial_number = lb.Unicode(read_only=True, cache=True, is_metadata=True)

    def __imports__(self):
        global hid
        import hid

    def connect(self):
        if self.settings.path is None:
            self.settings.path = self._find_path(self.settings.resource)

        self.backend = hid.device()
        self.backend.open_path(self.settings.path)
        self.backend.set_nonblocking(0)

    def disconnect(self):
        if self.backend is not None:
            self.backend.close()

    @classmethod
    def _parse_str(cls, data):
        ''' Convert a command response to a string.
        '''
        b = np.array(data[1:],dtype='uint8').tobytes()
        return b.split(b'\x00',1)[0].decode()

    def _cmd(self, *cmd):
        ''' Send up to 64 1-byte unsigned integers and return the response.
        '''
        if len(cmd) > 64:
            raise ValueError('command data length is limited to 64')
            
        cmd = list(cmd) + (63-len(cmd))*[0]
            
        if platform.system().lower() == 'windows':
            self.backend.write([0]+cmd[:-1])
        else:
            self.backend.write(cmd)

        t0 = time.time()
        while time.time()-t0 < self.settings.timeout:
            d = self.backend.read(64)
            if d:
                break
        else:
            raise TimeoutError('no response from device')
            
        if d[0] != cmd[0]:
            raise RuntimeError("Invalid response from device: %s" % d)
        return d

    @classmethod
    def _find_path(cls, serial):
        ''' Find a USB HID device path matching the MiniCircuits device with
            the specified serial number. If serial is None, then check that
            exactly one MiniCircuits device is connected, and return its path.
            Raise an exception if no devices are connected.
        '''
        ret = {}
        
        dev_list = hid.enumerate()
        for dev in dev_list:
            if (dev['vendor_id'] == cls.VID) and (dev['product_id'] == cls.PID):
                # Note: we have to do this dance where we try to open every
                # device, since Mini-Circuits is inconsistent about
                # returning HID-compliant serial numbers, so we have to use
                # the actual Mini-Circuits API for it.
                try:
                    inst = cls(path=dev['path'])
                    inst.connect()
                    ret[inst.state.serial_number] = dev['path']
                except OSError as e:
                    # Device already open, skipping.
                    print(str(e))
                    pass
                finally:
                    inst.disconnect()
        
        if len(ret) == 0:
            raise lb.ConnectionError('found no {} connected that match vid={vid},pid={pid}'\
                                     .format(cls.__name__, cls.VID, cls.PID))
            
        names = ', '.join([repr(k) for k in ret.keys()])
            
        if serial is None:
            if len(ret) == 1:
                return next(iter(ret.values()))
            else:
                raise lb.ConnectionError('specify one of the available {} resources: {}'\
                                         .format(cls.__name__, names))
                
        try:
            return ret[serial]
        except KeyError:
            raise lb.ConnectionError('specified resource {}, but only {} are available'\
                                     .format(repr(serial), names))

#class PowerSensor(MiniCircuitsUSBDevice):
#    """
#    Class for interfacing with Mini-Circuits USB Power Sensors.
#    Verified working:
#        - PWR-6GHS
#    """
#
#    # Mini-Circuits PWR-6GHS USB Power Sensor
#    PID = 0x11
#
#    # Not sure if any of these command codes are also shared.
#    CMD_GET_MODEL_NAME = 104
#    CMD_GET_SERIAL = 105
#    CMD_SET_MEASUREMENT_MODE = 15
#    CMD_READ_POWER = 102
#    CMD_GET_TEMPERATURE = 103
#    CMD_GET_FIRMWARE_VERSION = 99
#
#    def get_model_name(self):
#        d = self._cmd(self.CMD_GET_MODEL_NAME)
#        return self._parse_str(d)
#
#    def get_serial(self):
#        d = self._cmd(self.CMD_GET_SERIAL)
#        return self._parse_str(d)
#
#    def set_measurement_mode(self, mode='low-noise'):
#        mode_num = {
#            'low-noise': 0,
#            'fast-sampling': 1,
#            'fastest-sampling': 2,
#        }[mode]
#        self._cmd(self.CMD_SET_MEASUREMENT_MODE, mode_num)
#
#    def get_power(self, freq):
#        if freq > 65.535e6:
#            scale = 1e6
#            units = 'M'
#        else:
#            scale = 1e3
#            units = 'k'
#        freq = int(round(freq / scale))
#        freq1 = freq >> 8
#        freq2 = freq - (freq1 << 8)
#        d = self._cmd(self.CMD_READ_POWER, freq1, freq2, ord(units))
#        s = ''.join(chr(c) for c in d[1:7])
#        return float(s)
#
#    def get_temperature(self):
#        d = self._cmd(self.CMD_GET_TEMPERATURE)
#        s = ''.join(chr(c) for c in d[1:7])
#        return float(s)
#
#    def get_firmware_version(self):
#        d = self._cmd(self.CMD_GET_FIRMWARE_VERSION)
#        return chr(d[5]) + chr(d[6])


class SwitchAttenuatorBase(MiniCircuitsUSBDevice):    
    CMD_GET_PART_NUMBER = 40
    CMD_GET_SERIAL_NUMBER = 41

    class state(MiniCircuitsUSBDevice.state):
        pass

    @state.model.getter
    def __(self):
        d = self._cmd(self.CMD_GET_PART_NUMBER)
        return self._parse_str(d)

    @state.serial_number.getter
    def __(self):
        d = self._cmd(self.CMD_GET_SERIAL_NUMBER)
        return self._parse_str(d)


class Attenuator(SwitchAttenuatorBase):
    PID = 0x23
    
    CMD_GET_ATTENUATION = 18
    CMD_SET_ATTENUATION = 19

    class state(SwitchAttenuatorBase.state):
        attenuation   = lb.Float(min=0, max=115, step=0.25)

    @state.attenuation.getter
    def __(self):
        d = self._cmd(self.CMD_GET_ATTENUATION)
        full_part = d[1]
        frac_part = float(d[2]) / 4.0
        return full_part + frac_part

    @state.attenuation.setter
    def set_attenuation(self, value):
        value1 = int(value)
        value2 = int((value - value1) * 4.0)
        self._cmd(self.CMD_SET_ATTENUATION, value1, value2)


class Switch(SwitchAttenuatorBase):
    # Mini-Circuits USB-SP4T-63
    PID = 0x22
    CMD_GET_SWITCH_PORT = 15
    
    class state(SwitchAttenuatorBase.state):
        port   = lb.Int(min=1, max=4)

    @state.port.setter
    def __(self, port):
        """
        Set which port is connected to the COM port: 1-indexed.
        """
        if port not in (1, 2, 3, 4):
            raise ValueError("Invalid switch port: %s" % port)
        self._cmd(port)

    @state.port.getter
    def __(self):
        """
        Return which port is connected to the COM port: 1-indexed.
        """
        d = self._cmd(self.CMD_GET_SWITCH_PORT)
        port = d[1]
        return port


if __name__ == '__main__':
    atten = Attenuator('11604210014')
    with atten:
        print(atten.state.serial_number)
        atten.state.attenuation = 101
        print(atten.state.attenuation)
        