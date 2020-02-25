# -*- coding: utf-8 -*-

__all__ = ['MiniCircuitsRCDAT', 'MiniCircuitsRC4DAT']

import ssmdevices.lib
import labbench as lb
import time,random

if __name__ == '__main__':
    from _minicircuits_usb import SwitchAttenuatorBase
else:
    from ._minicircuits_usb import SwitchAttenuatorBase


class MiniCircuitsRCDAT(SwitchAttenuatorBase):
    frequency: lb.Float(
        default=None, allow_none=True,
        min=10e6, max=6e9,
        help='frequency for calibration data, or None for no calibration'
    )

    output_power_offset: lb.Float(
        default=None, allow_none=True,
        help='output power at 0 dB attenuation'
    )
    
    calibration_path: lb.Unicode(
        default=None, allow_none=True,
        help='path to the calibration table, which is a csv with frequency '\
             '(columns) and attenuation setting (row), or None to search ssmdevices'
    )

    PID = 0x23

    def open(self):
        import pandas as pd
        from pathlib import Path
        
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
        CMD_GET_ATTENUATION = 18
        
        d = self._cmd(CMD_GET_ATTENUATION)
        full_part = d[1]
        frac_part = float(d[2]) / 4.0
        return full_part + frac_part

    @attenuation_setting # setter
    def attenuation_setting(self, value):
        CMD_SET_ATTENUATION = 19
        
        value1 = int(value)
        value2 = int((value - value1) * 4.0)
        self._cmd(CMD_SET_ATTENUATION, value1, value2, 1)
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
            # only log on changes
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


#class MiniCircuitsRC4DAT(SwitchAttenuatorBase):
#    PID = 0x23
#
#    CMD_GET_ATTENUATION = 18
#    CMD_SET_ATTENUATION = 19
#
#    attenuation1 = lb.Float(min=0, max=115, step=0.25, key=1)
#    attenuation2 = lb.Float(min=0, max=115, step=0.25, key=2)
#    attenuation3 = lb.Float(min=0, max=115, step=0.25, key=3)
#    attenuation4 = lb.Float(min=0, max=115, step=0.25, key=4)
#
#    def __get_by_key__(self, key, name):
#        d = self._cmd(self.CMD_GET_ATTENUATION)
#        offs = key * 2 - 1
#        full_part = d[offs]
#        frac_part = float(d[offs + 1]) / 4.0
#        return full_part + frac_part
#
#    def __set_by_key__(self, key, name, value):
#        value1 = int(value)
#        value2 = int((value - value1) * 4.0)
#        self._cmd(self.CMD_SET_ATTENUATION, value1, value2, key)


# TODO: Replace this with the above
class MiniCircuitsRC4DAT(lb.DotNetDevice):
    ''' Base class for MiniCircuits USB attenuators.
    
        This implementation calls the .NET drivers provided by the
        manufacturer instead of the recommended C DLL drivers in order to
        support 64-bit python.
    '''
    
    library  = ssmdevices.lib    # Must be a module
    dll_name = 'mcl_RUDAT64.dll'
    model_includes = ''
    
    resource: lb.Unicode(None,
                         help='Serial number of the USB device. Must be defined if more than one device is connected to the computer', allow_none=True)

    def open (self):
        ''' Open the device resource.
        '''
        @lb.retry(ConnectionError, 10, delay=0.25)
        def do_connect():
            self.backend = self.dll.USB_RUDAT()

            for retry in range(10):
                ret = self.backend.Connect(self.settings.resource)[0]
                if ret == 1:
                    time.sleep(random.uniform(0,0.2))
                    break
            else:
                time.sleep(0.25)
                raise ConnectionError('Cannot connect to attenuator resource {}'.format(self.settings.resource))
            
        if self.dll is None:
            raise Exception('Minicircuits attenuator support currently requires pythonnet and windows')
            
        # Validate the input resource
        valid = self.list_available_devices()
        if self.settings.resource is None:
            if len(valid) == 0:
                raise ValueError('no MiniCircuits attenuators were detected on USB')
            elif len(valid) > 1:
                raise ValueError('more than one MiniCircuits USB attenuators are connected, specify one of '+repr(valid))
        else:
            if self.settings.resource not in valid:
                raise ValueError('specified serial number {} but only found {} on USB'\
                                 .format(repr(self.settings.resource),repr(valid)))
                
        do_connect()
        if self.model_includes and self.model_includes not in self.model:
            raise lb.DeviceException('attenuator model {model} does not include the expected {model_has} string'\
                                     .format(model=self.model,
                                             model_has=self.model_includes))

        self.logger.debug('Connected to {model} attenuator, SN#{sn}'\
                          .format(model=self.model,
                                  sn=self.serial_number))

    def _validate_connection(self):
        if self.backend.GetUSBConnectionStatus() != 1:
            raise lb.DeviceStateError('USB device unexpectedly disconnected')

    def close(self):
        ''' Release the attenuator hardware resource via the driver DLL.
        '''
        self.backend.Disconnect()

    @classmethod
    def list_available_devices(cls, inst=None):
        ''' Return a list of valid resource strings of MiniCircuitsRCDAT and
            MiniCircuitsRC4DAT devices that are found on this computer.

            If inst is not None, it should be a MiniCircuitsRCBase instance.
            In this case its backend will be used instead of temporarily
            making a new one.
        '''

        # Force the dll to import if no devices have been imported yet
        if inst is None:
            if not hasattr(cls, 'dll'):
                cls.__imports__()
            backend = cls.dll.USB_RUDAT()
        else:
            backend = inst.backend

        count, response = backend.Get_Available_SN_List('')

        lb.console.debug('response was {}'.format(response))
        if count > 0:
            return response.split(' ')
        else:
            return []

    @lb.Unicode(settable=False, cache=True)
    def model(self):
        self._validate_connection()
        return 'MiniCircuits ' + self.backend.Read_ModelName('')[1]
    
    @lb.Unicode(settable=False, cache=True)
    def serial_number(self):
        self._validate_connection()
        return self.backend.Read_SN('')[1]

    attenuation1 = lb.Float(min=0, max=115, step=0.25, key=1)
    attenuation2 = lb.Float(min=0, max=115, step=0.25, key=2)
    attenuation3 = lb.Float(min=0, max=115, step=0.25, key=3)
    attenuation4 = lb.Float(min=0, max=115, step=0.25, key=4)

    def __get_by_key__ (self, key, name):
        self._validate_connection()
        ret = self.backend.ReadChannelAtt(key)
        self.logger.debug(f'got attenuation {key} {ret} dB')
        return ret    

    def __set_state_(self, key, name, value):
        self._validate_connection()
        self.logger.debug(f'set attenuation {key} {value} dB')
        self.backend.SetChannelAtt(key, value)

if __name__ == '__main__':
    import numpy as np
    lb.show_messages('info')
    
    for i in np.arange(0,110.25,0.25):
        atten = MiniCircuitsRCDAT('11604210014')
        atten2 = MiniCircuitsRCDAT('11604210008')
        with atten,atten2:
            atten.attenuation = i
            lb.console.info(str(atten.attenuation))