# -*- coding: utf-8 -*-

import time
import labbench as lb
import platform
import numpy as np
from threading import Lock
from traitlets import TraitError
import ssmdevices.lib
from pathlib import Path


class MiniCircuitsUSBDevice(lb.Device):
    VID = 0x20ce
    __find_lock = Lock()
    __all_found = {}  # keyed on serial number

    resource: lb.Unicode(None,
                          help='Serial number of the USB device. Must be defined if more than one device is connected to the computer',
                          allow_none=True)
    path: lb.Bytes(None, allow_none=True,
                    help='override `resource` to connect to a specific USB path')
    timeout: lb.Int(1, min=0.5)

    # Will need to be r
    model = lb.Unicode(settable=False, cache=True)
    serial_number = lb.Unicode(settable=False, cache=True)

    @classmethod
    def __imports__(cls):
        global hid,pd
        import hid
        import pandas as pd
        super().__imports__()

    def open(self):
        notify = self.settings.path is None
        if self.settings.path is None:
            self.settings.path = self._find_path(self.settings.resource)

        #        if not self._lock().acquire(timeout=self.settings.timeout):
        #            raise lb.ConnectionError('there is already a connection with serial number ')

        self.backend = hid.device()
        self.backend.open_path(self.settings.path)
        self.backend.set_nonblocking(1)

        MiniCircuitsUSBDevice.__all_found[self.settings.path] = self.serial_number

        if notify:
            self.logger.info('connected to {} with serial {}'
                             .format(self.model, self.serial_number))

    def close(self):
        if self.backend:
            self.backend.close()

    #        try:
    #            self._lock().release()
    #        except RuntimeError:
    #            pass

    @classmethod
    def _parse_str(cls, data):
        ''' Convert a command response to a string.
        '''
        b = np.array(data[1:], dtype='uint8').tobytes()
        return b.split(b'\x00', 1)[0].decode()

    def _cmd(self, *cmd):
        ''' Send up to 64 1-byte unsigned integers and return the response.
        '''
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
        found = {}

        MiniCircuitsUSBDevice.__find_lock.acquire()

        for dev in hid.enumerate(cls.VID, cls.PID):
            # Check for a cached serial number first
            try:
                this_serial = MiniCircuitsUSBDevice.__all_found[dev['path']]
                found[this_serial] = dev['path']
                continue
            except KeyError:
                pass

            # Otherwise, connect to the device to learn its serial number
            try:
                with cls(path=dev['path']) as inst:
                    this_serial = inst.serial_number
                    MiniCircuitsUSBDevice.__all_found[dev['path']] = this_serial
                    found[this_serial] = dev['path']
            except OSError as e:
                # Device already open, skipping.
                print(str(e))
                pass

        MiniCircuitsUSBDevice.__find_lock.release()

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
    PID = 0x23

    CMD_GET_ATTENUATION = 18
    CMD_SET_ATTENUATION = 19

    frequency: lb.Float(None, allow_none=True, max=6e9,
                        help='calibration frequency, or None to disable level calibration')
    output_power_offset: lb.Float(None, allow_none=True,
                                  help='offset calibration such that state.output_power = settings.output_power_offset - state.attenuation')

    def open(self):
        def _validate_attenuation(trait, proposal):
            ''' Nudge the trait value to the nearest attenuation level from
                the cal data.
            '''
            if isinstance(proposal, dict):
                proposal = proposal['value']
            return self._lookup_cal(self._apply_cal(proposal))

        def _validate_output_power(trait, proposal):
            ''' Make sure that the trait knows the correct value with the
                discretized output power, and that the output power puts the
                attenuator in the specified range.
            '''

            # Require an offset to assign output power
            offset = self.settings.output_power_offset
            if offset is None:
                raise TraitError('set settings.output_power_offset before assigning to state.output_power')

            # Check bounds
            power = proposal['value']
            atten = self.traits()['attenuation']
            lo = offset - atten.max
            hi = offset - atten.min
            if power < lo or power > hi:
                msg = f'requested input power {power} is outside of the valid range ({lo},{hi})'
                raise TraitError(msg)

            # Compute the nearest available attenuation value, and return
            # the corresponding "true" output power value
            atten_true = _validate_attenuation(atten, offset - proposal['value'])
            return offset - atten_true

        self._register_validator(_validate_output_power, ('output_power',))
        self._register_validator(_validate_attenuation, ('attenuation',))

        cal_path = Path(ssmdevices.lib.path('cal'))

        cal_filenames = f"MiniCircuitsRCDAT_{self.settings.resource}.csv.xz", \
                        f"MiniCircuitsRCDAT_default.csv.xz"
        for f in cal_filenames:
            if (cal_path / f).exists():
                self._cal = pd.read_csv(str(cal_path / f),
                                        index_col='Frequency(Hz)',
                                        dtype=float)
                self._cal.columns = self._cal.columns.astype(float)
                if 6e9 in self._cal.index:
                    self._cal.drop(6e9, axis=0, inplace=True)
                #                self._cal_offset.values[:] = self._cal_offset.values-self._cal_offset.columns.values[np.newaxis,:]

                self.logger.debug(f'loaded calibration data from {str(cal_path / f)}')

                if self.settings.frequency is None:
                    self.logger.warning('set an operating frequency in settings.frequency to enable calibration')

                break
        else:
            self._cal_data = None
            self.logger.debug(f'found no calibration data in {str(cal_path)}')

    @lb.Float(min=0, max=115)
    def attenuation(self):
        '''attenuation level (dB), automatically calibrated if settings.frequency is not None'''
        return self._lookup_cal(self.attenuation_setting)

    @attenuation
    def attenuation(self, value):
        setting = self._apply_cal(value)
        self.attenuation_setting = setting
        if self.settings.frequency:
            self.logger.debug(
                f'calibrated attenuation level nearest {value:0.2f} dB at {self.settings.frequency / 1e6} MHz -> {setting:0.2f} dB setting')

    @lb.Float(min=0, max=115, step=0.25)
    def attenuation_setting(self):
        '''attenuation setting sent to the attenuator (dB), which is different from the calibrated attenuation value an attenuation has been applied'''
        d = self._cmd(self.CMD_GET_ATTENUATION)
        full_part = d[1]
        frac_part = float(d[2]) / 4.0
        return full_part + frac_part

    @attenuation_setting
    def __(self, value):
        value1 = int(value)
        value2 = int((value - value1) * 4.0)
        self._cmd(self.CMD_SET_ATTENUATION, value1, value2, 1)
        self.logger.debug(f'applied {value:0.2f} dB attenuation setting')

    @lb.Float()
    def output_power(self):
        '''output power, in dB units the same as output_power_offset (settings.output_power_offset - state.attenuation)'''
        offset = self.settings.output_power_offset
        if offset is None:
            raise ValueError('output power offset is undefined, cannot determine output power')
        return offset - self.attenuation

    @output_power
    def output_power(self, output_power):
        offset = self.settings.output_power_offset
        if offset is None:
            raise ValueError('output power offset is undefined, cannot determine attenuation settings for output power')
        self.attenuation = offset - output_power

    def _apply_cal(self, proposed_atten):
        ''' Find the setting that achieves the attenuation level closest to the
            proposed level. Returns a dictionary containing this attenuation
            setting, and the actual attenuation at this setting.
        '''
        if self._cal is None:
            return proposed_atten

        if self.settings.frequency is None:
            i = self._cal.columns.get_loc(proposed_atten, method='nearest')
            atten = self._cal.columns[i]
            return atten

        i_freq = self._cal.index.get_loc(self.settings.frequency, 'nearest')
        cal = self._cal.iloc[i_freq]
        cal.name = 'cal'
        cal = cal.reset_index().set_index('cal').sort_index()

        i_atten = cal.index.get_loc(proposed_atten, method='nearest')

        return cal.iloc[i_atten].values[0]

    def _lookup_cal(self, attenuation_setting):
        if self._cal is None:
            return attenuation_setting
        if self.settings.frequency is None:
            return attenuation_setting

        i_freq = self._cal.index.get_loc(self.settings.frequency, 'nearest')
        return self._cal.iloc[i_freq].loc[attenuation_setting]


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
    #    atten = SingleChannelAttenuator('11604210014')
    def show(event):
        print(event['name'], event['new'])


    lb.show_messages('debug')
    atten = SingleChannelAttenuator('11604210008',
                                    output_power_offset=0.1,
                                    frequency=5.3e9)
    atten.observe(show)

    with atten:
        print(atten.settings.frequency)
        atten.attenuation = 100
        print(atten.attenuation_setting)
        print(atten.attenuation)
        atten.attenuation = 80
