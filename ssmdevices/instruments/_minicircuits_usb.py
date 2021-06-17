# -*- coding: utf-8 -*-

import time
import labbench as lb
import platform
import numpy as np
from threading import Lock
import ssmdevices.lib
from pathlib import Path

__all__ = ['MiniCircuitsUSBDevice', 'SwitchAttenuatorBase']

usb_enumerate_lock = Lock()
usb_command_lock = Lock()

class MiniCircuitsUSBDevice(lb.Device):
    """ General control over MiniCircuits USB devices
    """
    _VID = 0x20ce # USB HID Vendor ID

    resource = lb.value.str(
        default=None,
        help='serial number; must be set if more than one device is connected',
        allow_none=True
    )
    
    timeout = lb.value.float(
        default=1,
        min=0.5,
        label='s'
    )

    # overload these with properties
    model = "Unknown model"
    serial_number = "Unknown serial number"

    @classmethod
    def __imports__(cls):
        global hid
        import hid

    def open(self):
        found = self._enumerate()

        if len(found) == 0:
            raise ConnectionError( 
                f'found no USB HID devices connected that match vid={self._VID}, pid={self._PID}'
            )

        names = ', '.join([repr(k) for k in found.keys()])

        if self.resource is None:
            # check that exactly one device is connected, and use its HID path
            if len(found) == 1:
                usb_path = next(iter(found.values()))
            else:
                raise lb.ConnectionError(
                    f'specify resource when multiple devices are connected; currently connected: {names}'
                )
        else:
            # find the HID device path matching the MiniCircuits device
            try:
                usb_path = found[self.resource]
            except KeyError:
                raise lb.ConnectionError(
                    f'could not find USB HID at serial resource="{self.resource}"'
                )

        self.backend = self._hid_connect(usb_path)

        self._logger.info(
            f'opened USB HID path "{usb_path}" to "{self.model}" with serial "{self.serial_number}"'
        )

    def close(self):
        if self.backend:
            self.backend.close()

    @classmethod
    def _parse_str(cls, data):
        ''' Convert a command response to a string.
        '''
        b = np.array(data[1:], dtype='uint8').tobytes()
        return b.split(b'\x00', 1)[0].decode()

    def _cmd(self, *cmd):
        ''' Send up to 64 1-byte unsigned integers and return the response.
        '''
        with usb_command_lock:       
            if len(cmd) > 64:
                raise ValueError('command key data length is limited to 64')

            cmd = list(cmd) + (63 - len(cmd)) * [0]

            if platform.system().lower() == 'windows':
                self.backend.write([0] + cmd[:-1])
            else:
                self.backend.write(cmd)

            t0 = time.time()
            msg = None
            while time.time() - t0 < self.timeout:
                d = self.backend.read(64)
                if d:
                    if d[0] == cmd[0]:
                        break
                    else:
                        msg = "device responded to command code {}, but expected {} (full response {})" \
                            .format(d[0], cmd[0], repr(d))
            else:
                if msg is None:
                    raise TimeoutError('no response from device')
                else:
                    raise lb.DeviceException(msg)

        return d

    @classmethod
    def _hid_connect(cls, usb_path):
        """ must return a trial object to test connections when enumerating devices.
            the subclass must have serial_number and model traits.
        """
        hiddev = hid.device()
        hiddev.open_path(usb_path)

        try:
            hiddev.set_nonblocking(1)
        except:
            hiddev.close()
            raise

        return hiddev
        raise NotImplementedError("subclasses must implement this to return an instance for trial connection")

    @classmethod
    def list_available_devices(cls):
        return list(cls._enumerate())

    @classmethod
    def _enumerate(cls):
        with usb_enumerate_lock:        
            found = {}
    
            for hiddev in hid.enumerate(cls._VID, cls._PID):
                # Otherwise, connect to the device to learn its serial number
                try:
                    # bypass cls.open and directly test connection to the hid path
                    inst = cls()
                    inst._logger.logger.disabled = True
                    inst.backend = cls._hid_connect(hiddev['path'])
                except OSError as e:
                    # Device already open, skipping.
                    print(str(e))
                    pass
                else:
                    # success!
                    found[inst.serial_number] = hiddev['path']
                finally:
                    inst.close()

        return found

# class PowerSensor(MiniCircuitsUSBDevice):
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

    @lb.property.str(sets=False, cache=True)
    def model(self):
        d = self._cmd(self.CMD_GET_PART_NUMBER)
        return self._parse_str(d)

    @lb.property.str(sets=False, cache=True)
    def serial_number(self):
        d = self._cmd(self.CMD_GET_SERIAL_NUMBER)
        return self._parse_str(d)