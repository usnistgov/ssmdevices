"""
Drivers for USB peripherals

:author: Dan Kuester <daniel.kuester@nist.gov>, Andre Rosete <andre.rosete@nist.gov>
"""
import labbench as lb
import collections


class AcronameUSBHub2x4(lb.Device, resource=None):
    """A USB hub with control over each port."""

    model = 17

    data0_enabled = lb.property.bool()
    data1_enabled = lb.property.bool()
    data2_enabled = lb.property.bool()
    data3_enabled = lb.property.bool()

    power0_enabled = lb.property.bool()
    power1_enabled = lb.property.bool()
    power2_enabled = lb.property.bool()
    power3_enabled = lb.property.bool()

    resource = lb.value.str(
        allow_none=True,
        cache=True,
        help="None to autodetect, or a serial number string",
    )

    def open(self):
        import brainstem

        specs = self._bs.discover.findAllModules(brainstem.link.Spec.USB)

        specs = [s for s in specs if s.model == self.model]
        if self.resource is not None:
            specs = [s for s in specs if s.serial_number == self.resource]

        if len(specs) > 1:
            if self.resource is None:
                raise Exception(
                    "More than one connected USB device matches model "
                    + str(self.model)
                    + " - provide serial number?"
                )
            else:
                raise Exception(
                    "More than one connected USB device match model "
                    + str(self.model)
                    + " and serial "
                    + str(self.resource)
                )
        elif len(specs) == 0:
            raise Exception(
                "No USB devices connected that match model "
                + str(self.model)
                + " and serial "
                + str(self.resource)
            )

        self.backend = brainstem.stem.USBHub2x4()
        self.backend.connectFromSpec(specs[0])

    def close(self):
        """Release control over the device."""
        self.backend.disconnect()

    def set_key(self, key, value, name=None):
        """Apply an instrument setting to the instrument. The value ``value''
        will be applied to the trait attriute ``attr'' in type(self).
        """
        cls = type(self).__name__
        raise NotImplementedError(
            f'property trait "{name}" is defined but not implemented! implement '
            f"{cls}.get_key, or a getter for {cls}.{name}"
        )

    def enable(self, data=True, power=True, channel="all"):
        """Enable or disable of USB port features at one or all hub ports.

        :param data:  Enables data on the port (if evaluates to true)

        :param power: Enables power on the port (if evaluates to true)

        :param channel: An integer port number specifies the port to act on,
         otherwise 'all' (the default) applies the port settings to all
         ports on the hub.
        """
        if channel == "all":
            channels = list(range(4))
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
