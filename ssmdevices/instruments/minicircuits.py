# -*- coding: utf-8 -*-

import time
import labbench as lb
import platform
import numpy as np
from threading import Lock
import ssmdevices.lib
from pathlib import Path

__all__ = ['MiniCircuitsUSBDevice', 'SingleChannelAttenuator',
           'FourChannelAttenuator']

usb_enumerate_lock = Lock()
usb_command_lock = Lock()
usb_registry = {} # serial number: USB path

class MiniCircuitsUSBDevice(lb.Device):
    """ General control over MiniCircuits USB devices
    """
    VID = 0x20ce # USB HID Vendor ID

    resource: lb.Unicode(
        default=None,
        help='serial number; must be set if more than one device is connected',
        allow_none=True
    )
    
    path: lb.Bytes(
        None,
        allow_none=True,
        help='override `resource` to connect to a specific USB path'
    )
    
    timeout: lb.Float(
        default=1,
        min=0.5,
        label='s'
    )

    @classmethod
    def __imports__(cls):
        global hid,pd
        import hid
        import pandas as pd

    def open(self):
        notify = self.settings.path is None
        if self.settings.path is None:
            self.settings.path = self._find_path(self.settings.resource)


        self.backend = hid.device()
        self.backend.open_path(self.settings.path)
        self.backend.set_nonblocking(1)
    
        usb_registry[self.settings.path] = self.serial_number

        if notify:
            self._console.info('connected to {} with serial {}'
                             .format(self.model, self.serial_number))

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
            while time.time() - t0 < self.settings.timeout:
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
    def _find_path(cls, serial):
        ''' Find a USB HID device path matching the MiniCircuits device with
            the specified serial number. If serial is None, then check that
            exactly one MiniCircuits device is connected, and return its path.
            Raise an exception if no devices are connected.
        '''
        with usb_enumerate_lock:        
            found = {}
    
            for dev in hid.enumerate(cls.VID, cls.PID):
                # Check for a cached serial number first
                try:
                    this_serial = usb_registry[dev['path']]
                    found[this_serial] = dev['path']
                    continue
                except KeyError:
                    pass
    
                # Otherwise, connect to the device to learn its serial number
                try:
                    print('trial connect to ', dev['path'])
                    with cls(path=dev['path']) as inst:
                        print('trial connected')
                        this_serial = inst.serial_number
                        usb_registry[dev['path']] = this_serial
                        found[this_serial] = dev['path']
                except OSError as e:
                    # Device already open, skipping.
                    print(str(e))
                    pass

        if len(found) == 0:
            raise lb.ConnectionError('found no {} connected that match vid={vid},pid={pid}' \
                                     .format(cls.__name__, cls.VID, cls.PID))

        names = ', '.join([repr(k) for k in found.keys()])

        if serial is None:
            if len(found) == 1:
                ret = next(iter(found.values()))
            else:
                raise lb.ConnectionError('specify one of the available {} resources: {}' \
                                         .format(cls.__name__, names))

        try:
            ret = found[serial]
        except KeyError:
            raise lb.ConnectionError('specified resource {}, but only {} are available' \
                                     .format(repr(serial), names))
        return ret


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

    @lb.Unicode(settable=False, cache=True)
    def model(self):
        d = self._cmd(self.CMD_GET_PART_NUMBER)
        return self._parse_str(d)

    @lb.Unicode(settable=False, cache=True)
    def serial_number(self):
        d = self._cmd(self.CMD_GET_SERIAL_NUMBER)
        return self._parse_str(d)


class SingleChannelAttenuator(SwitchAttenuatorBase):
    frequency: lb.Float(
        default=None,
        allow_none=True,
        max=6e9,
        help='frequency for calibration data, or None for no calibration'
    )

    output_power_offset: lb.Float(
        default=None,
        allow_none=True,
        help='output power at 0 dB attenuation'
    )
    
    calibration_path: lb.Unicode(
        default=None,
        allow_none=True,
        help='path to the calibration table, which is a csv with frequency '\
             '(columns) and attenuation setting (row), or None to search ssmdevices'
    )
    
    PID = 0x23

    CMD_GET_ATTENUATION = 18
    CMD_SET_ATTENUATION = 19

    def open(self):
        def read(path):
            # quick read
            self._cal = pd.read_csv(str(path),
                                    index_col='Frequency(Hz)',
                                    dtype=float)
            self._cal.columns = self._cal.columns.astype(float)
            if self.settings['frequency'].max in self._cal.index:
                self._cal.drop(self.settings['frequency'].max, axis=0, inplace=True)
            #    self._cal_offset.values[:] = self._cal_offset.values-self._cal_offset.columns.values[np.newaxis,:]

            self._console.debug(f'calibration data read from {path}')

        if self.settings.calibration_path is None:
            cal_path = Path(ssmdevices.lib.path('cal'))
            cal_filenames = f"MiniCircuitsRCDAT_{self.settings.resource}.csv.xz", \
                            f"MiniCircuitsRCDAT_default.csv.xz"
                            
            for f in cal_filenames:
                if (cal_path / f).exists():
                    read(str(cal_path/f))
                    self.settings.calibration_path = str(cal_path/f)
                    break
            else:
                self._cal_data = None
                self._console.debug(f'found no calibration data in {str(cal_path)}')
        else:
            read(self.settings.calibration_path)

        lb.observe(self.settings, self._update_frequency,
                   name='frequency', type_='set')
        lb.observe(self, self._console_debug, type_='set',
                   name=('attenuation', 'attenuation_setting', 'output_power'))
        
        # trigger cal update
        self.settings.frequency = self.settings.frequency 

    # the requested attenuation is the only state that directly interacts
    # with the device
    attenuation_setting = lb.Float(min=0, max=115, step=0.25, label='dB')

    @attenuation_setting # getter
    def attenuation_setting(self):
        '''attenuation setting sent to the attenuator (dB), which is different from the calibrated attenuation value an attenuation has been applied'''
        d = self._cmd(self.CMD_GET_ATTENUATION)
        full_part = d[1]
        frac_part = float(d[2]) / 4.0
        return full_part + frac_part

    @attenuation_setting # setter
    def attenuation_setting(self, value):
        value1 = int(value)
        value2 = int((value - value1) * 4.0)
        self._cmd(self.CMD_SET_ATTENUATION, value1, value2, 1)
        self._console.debug(f'applied {value:0.2f} dB attenuation setting')

    # the remaining traits are transformations to calibrate attenuation_Setting
    attenuation = attenuation_setting.calibrate(
        lookup=None, help='calibrated attenuation level'
    )

    _transmission = -attenuation

    output_power = _transmission.calibrate(
        offset_name='output_power_offset',
        help='power level at attenuator output'
    )

    def _update_frequency(self, msg):
        """ match the calibration table to the frequency """
        if self._cal is None:
            return

        frequency = msg['new']
        if frequency is None:
            cal = None
            txt = f"attenuation calibration is disabled"
        else:
            # pull in the calibration table specific at this frequency
            i_freq = self._cal.index.get_loc(frequency, 'nearest')
            cal = self._cal.iloc[i_freq]
            txt = f"applied calibration table at {frequency/1e6:0.3f} MHz"
        
        self['attenuation'].set_table(cal)
        self._console.debug(txt)

    def _console_debug(self, msg):
        """ debug messages """
        
        if msg['new'] == msg['old']:
            # only for changes
            return

        name = msg['name']
        if name == 'attenuation' and self.settings.frequency is not None:
            cal = msg['new']
            uncal = self['attenuation'].find_uncal(cal)
            txt = f'calibrated attenuation set to {cal:0.2f} dB (device setting {uncal:0.2f} dB)'
            self._console.debug(txt)
        elif name == 'attenuation_setting' and self.settings.frequency is None:
            uncal = msg['new']
            self._console.debug(f'applied attenuation setting {uncal:0.2f} dB')


class FourChannelAttenuator(SwitchAttenuatorBase):
    PID = 0x23

    CMD_GET_ATTENUATION = 18
    CMD_SET_ATTENUATION = 19

    attenuation1 = lb.Float(min=0, max=115, step=0.25, key=1)
    attenuation2 = lb.Float(min=0, max=115, step=0.25, key=2)
    attenuation3 = lb.Float(min=0, max=115, step=0.25, key=3)
    attenuation4 = lb.Float(min=0, max=115, step=0.25, key=4)

    def __get_by_key__(self, key, name):
        d = self._cmd(self.CMD_GET_ATTENUATION)
        offs = key * 2 - 1
        full_part = d[offs]
        frac_part = float(d[offs + 1]) / 4.0
        return full_part + frac_part

    def __set_by_key__(self, key, name, value):
        value1 = int(value)
        value2 = int((value - value1) * 4.0)
        self._cmd(self.CMD_SET_ATTENUATION, value1, value2, key)


class Switch(SwitchAttenuatorBase):
    # Mini-Circuits USB-SP4T-63
    PID = 0x22
    CMD_GET_SWITCH_PORT = 15

    @lb.Int(min=1, max=4)
    def port(self, port):
        """ the RF port connected to COM port indexed from 1 """
        if port not in (1, 2, 3, 4):
            raise ValueError("Invalid switch port: %s" % port)
        self._cmd(port)

    @port
    def port(self):
        d = self._cmd(self.CMD_GET_SWITCH_PORT)
        port = d[1]
        return port

if __name__ == '__main__':
#    lb.util._force_full_traceback(True)

    def show(event):
        print(event['name'], event['new'])

    lb.show_messages('debug')
    atten = SingleChannelAttenuator(
        '11604210008',
        output_power_offset=-20,
        frequency=5.3e9,
#        calibration_path=r'C:\Users\dkuester\AppData\Local\Continuum\anaconda3\lib\site-packages\ssmdevices\lib\cal\MiniCircuitsRCDAT_11604210008.csv.xz'
    )

    with atten:
        print(atten.settings.frequency)
        atten.attenuation = 100
        print(atten.attenuation_setting)
        print(atten.attenuation)
        atten.attenuation = 80
        print(atten.output_power, atten.attenuation)
