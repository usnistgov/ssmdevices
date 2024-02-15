import time
import labbench as lb
from labbench import paramattr as attr
import platform
import numpy as np
from threading import Lock

__all__ = ['MiniCircuitsUSBDevice', 'SwitchAttenuatorBase']

usb_enumerate_lock = Lock()
usb_command_lock = Lock()
usb_registry = {}  # serial number: USB path


class MiniCircuitsUSBDevice(lb.Device):
    """General control over MiniCircuits USB devices"""

    _VID = 0x20CE  # USB HID Vendor ID

    resource: str = attr.value.str(
        default=None,
        help='serial number; must be set if more than one device is connected',
        cache=True,
    )

    # annotated values can be passed as constructor arguments
    usb_path: bytes = attr.value.bytes(
        default=None,
        help='if not None, override `resource` to connect to a specific USB path',
        cache=True,
    )

    timeout: float = attr.value.float(default=1, min=0.5, label='s', cache=True)

    def open(self):
        import hid

        if self.usb_path is None:
            self.usb_path = self._find_path(self.resource)

        self.backend = hid.device()
        self.backend.open_path(self.usb_path)
        self.backend.set_nonblocking(1)

        usb_registry[self.usb_path] = self.serial_number

        if self.usb_path is None:
            self._logger.info(
                'connected to {self.model} with serial {self.serial_number}'
            )

    def close(self):
        if self.backend:
            self.backend.close()

    @classmethod
    def _parse_str(cls, data):
        """Convert a command response to a string."""
        b = np.array(data[1:], dtype='uint8').tobytes()
        return b.split(b'\x00', 1)[0].decode()

    def _cmd(self, *cmd):
        """Send up to 64 1-byte unsigned integers and return the response."""
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
                        msg = 'device responded to command code {}, but expected {} (full response {})'.format(
                            d[0], cmd[0], repr(d)
                        )
            else:
                if msg is None:
                    raise TimeoutError('no response from device')
                else:
                    raise lb.DeviceException(msg)

        return d

    @classmethod
    def _test_instance(cls, usb_path):
        """must return a trial object to test connections when enumerating devices.
        the subclass must have serial_number and model traits.
        """
        raise NotImplementedError(
            'subclasses must implement this to return an instance for trial connection'
        )

    @classmethod
    def _find_path(cls, serial):
        """Find a USB HID device path matching the MiniCircuits device with
        the specified serial number. If serial is None, then check that
        exactly one MiniCircuits device is connected, and return its path.
        Raise an exception if no devices are connected.
        """
        import hid
        unknown_match = []

        with usb_enumerate_lock:
            found = {}

            for dev in hid.enumerate(cls._VID, cls._PID):
                # Check for a cached serial number first
                try:
                    this_serial = usb_registry[dev['path']]
                    found[this_serial] = dev['path']
                    continue
                except KeyError:
                    pass

                try:
                    # serial number is unfamiliar - probe the device
                    with cls._test_instance(dev['path']) as inst:
                        this_serial = inst.serial_number
                        usb_registry[dev['path']] = this_serial
                        found[this_serial] = dev['path']

                except OSError:
                    # potentially open in another process
                    unknown_match.append(dev)
                    continue

        if len(found) == 0:
            ex = ConnectionError(
                f'found no USB HID devices matching the vendor and product of {cls.__qualname__}'
            )

            if len(unknown_match) > 0 and hasattr(ex, 'add_note'):
                # python>=3.10
                ex.add_note(f'hid failed to open these matches to vid={hex(cls._VID)} pid={hex(cls._PID)}:')
                for dev in unknown_match:
                    ex.add_note(f'\t{dev["path"]}')

            raise ex

        names = ', '.join([repr(k) for k in found.keys()])

        if serial is None:
            if len(found) == 1:
                ret = list(found.values())[0]
                return ret
            else:
                raise ConnectionError(
                    f'specify one of the available {cls.__name__} resources: {names}'
                )

        try:
            ret = found[serial]
        except KeyError:
            raise ConnectionError(
                f'specified resource {repr(serial)}, but only {names} are available'
            )
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

    @classmethod
    def _test_instance(cls, usb_path):
        device = SwitchAttenuatorBase(usb_path=usb_path)
        device._logger.logger.disabled = True
        return device

    @attr.property.str(sets=False, cache=True)
    def model(self):
        d = self._cmd(self.CMD_GET_PART_NUMBER)
        return self._parse_str(d)

    @attr.property.str(sets=False, cache=True)
    def serial_number(self):
        d = self._cmd(self.CMD_GET_SERIAL_NUMBER)
        return self._parse_str(d)
