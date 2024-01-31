"""
Drivers for USB peripherals

:author: Dan Kuester <daniel.kuester@nist.gov>, Andre Rosete <andre.rosete@nist.gov>
"""

import collections
import labbench as lb
from labbench import paramattr as attr


class AcronamePropertyAdapter(attr.KeyAdapterBase):
    def set(self, device, key: tuple, value, trait=None):
        """Apply an instrument setting to the instrument. The value ``value''
        will be applied to the trait attriute ``attr'' in type(self).
        """
        op, channel = key

        if op == 'data':
            device._set_data_enabled(channel, value)
        elif op == 'power':
            device._set_power_enabled(channel, value)
        else:
            raise ValueError(
                'first element in command key must be one of "data" or "power"'
            )

    def get(self, device, key: tuple, trait=None):
        """Apply an instrument setting to the instrument. The value ``value''
        will be applied to the trait attriute ``attr'' in type(self).
        """
        op, channel = key

        if op == 'data':
            device._get_data_enabled(channel)
        elif op == 'power':
            device._get_power_enabled(channel)
        else:
            raise ValueError(
                'first element in command key must be one of "data" or "power"'
            )


@AcronamePropertyAdapter()
class AcronameUSBHub2x4(lb.Device):
    """A USB hub with control over each port."""

    MODEL = 17

    def _set_power_enable(self, port: int, enabled: bool):
        if enabled:
            self._hub.usb.setPortEnable(port)
        else:
            self._hub.usb.setPortDisable(port)

    def _set_data_enable(self, port: int, enabled: bool):
        if enabled:
            self._hub.usb.setDataEnable(port)
        else:
            self._hub.usb.setDataDisable(port)

    def _get_power_enable(self, port: int):
        self._hub.usb.getPortEnable(port)

    def _get_data_enable(self, port: int):
        return self._hub.usb.getDataEnable(port)

    data0_enabled = attr.property.bool(key=('data', 0))
    data1_enabled = attr.property.bool(key=('data', 1))
    data2_enabled = attr.property.bool(key=('data', 2))
    data3_enabled = attr.property.bool(key=('data', 3))

    power0_enabled = attr.property.bool(key=('power', 0))
    power1_enabled = attr.property.bool(key=('power', 1))
    power2_enabled = attr.property.bool(key=('power', 2))
    power3_enabled = attr.property.bool(key=('power', 3))

    resource: str = attr.value.str(
        allow_none=True,
        cache=True,
        help='None to autodetect, or a serial number string',
    )

    def open(self):
        import brainstem

        specs = self._bs.discover.findAllModules(brainstem.link.Spec.USB)

        specs = [s for s in specs if s.model == self.MODEL]
        if self.resource is not None:
            specs = [s for s in specs if s.serial_number == self.resource]

        if len(specs) > 1:
            if self.resource is None:
                raise Exception(
                    'More than one connected USB device matches model '
                    + str(self.MODEL)
                    + ' - provide serial number?'
                )
            else:
                raise Exception(
                    'More than one connected USB device match model '
                    + str(self.MODEL)
                    + ' and serial '
                    + str(self.resource)
                )
        elif len(specs) == 0:
            raise Exception(
                'No USB devices connected that match model '
                + str(self.MODEL)
                + ' and serial '
                + str(self.resource)
            )

        self.backend = brainstem.stem.USBHub2x4()
        self.backend.connectFromSpec(specs[0])

    def close(self):
        """Release control over the device."""
        self.backend.disconnect()

    def _set_power_enabled(self, channel, enabled):
        """Enable or disable of USB port features at one or all hub ports.

        :param data:  Enables data on the port (if evaluates to true)

        :param power: Enables power on the port (if evaluates to true)

        :param channel: An integer port number specifies the port to act on,
         otherwise 'all' (the default) applies the port settings to all
         ports on the hub.
        """
        if channel == 'all':
            channels = list(range(4))
        elif isinstance(channel, collections.Iterable):
            channels = channel
        else:
            channels = [channel]

        for chan in channels:
            if enabled:
                self._hub.usb.setPortEnable(chan)
            else:
                self._hub.usb.setPortDisable(chan)

    def _set_data_enabled(self, channel, enabled):
        """Enable or disable of USB port features at one or all hub ports.

        :param data:  Enables data on the port (if evaluates to true)

        :param power: Enables power on the port (if evaluates to true)

        :param channel: An integer port number specifies the port to act on,
         otherwise 'all' (the default) applies the port settings to all
         ports on the hub.
        """
        if channel == 'all':
            channels = list(range(4))
        elif isinstance(channel, collections.Iterable):
            channels = channel
        else:
            channels = [channel]

        for chan in channels:
            if enabled:
                self._hub.usb.setDataEnable(chan)
            else:
                self._hub.usb.setDataDisable(chan)
