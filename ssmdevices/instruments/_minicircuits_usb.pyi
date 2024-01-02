import time
import labbench as lb
from labbench import paramattr as attr
import platform
import numpy as np
from threading import Lock
__all__ = ['MiniCircuitsUSBDevice', 'SwitchAttenuatorBase']
usb_enumerate_lock = Lock()
usb_command_lock = Lock()
usb_registry = {}


@attr.adjust(
    'resource',
    default=None,
    help='serial number; must be set if more than one device is connected',
    allow_none=True,
    cache=True
)
class MiniCircuitsUSBDevice(lb.Device):

    def __init__(self, resource: str='NoneType', usb_path: str='NoneType', timeout: str='int'):
        ...
    """General control over MiniCircuits USB devices"""
    _VID = 8398
    usb_path: bytes = attr.value.bytes(
        default=None,
        allow_none=True,
        help='override `resource` to connect to a specific USB path',
        cache=True
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
            self._logger.info('connected to {self.model} with serial {self.serial_number}')

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
                            d[0],
                            cmd[0],
                            repr(d)
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
        with usb_enumerate_lock:
            found = {}
            for dev in hid.enumerate(cls._VID, cls._PID):
                try:
                    this_serial = usb_registry[dev['path']]
                    found[this_serial] = dev['path']
                    continue
                except KeyError:
                    pass
                try:
                    with cls._test_instance(dev['path']) as inst:
                        this_serial = inst.serial_number
                        usb_registry[dev['path']] = this_serial
                        found[this_serial] = dev['path']
                except OSError as e:
                    print(str(e))
                    pass
        if len(found) == 0:
            raise ConnectionError(
                f'found no {cls.__name__} connected with vid={cls._VID}, pid={cls._PID}'
            )
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


class SwitchAttenuatorBase(MiniCircuitsUSBDevice):

    def __init__(self, resource: str='NoneType', usb_path: str='NoneType', timeout: str='int'):
        ...
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
