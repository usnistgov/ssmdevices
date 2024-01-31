"""
Made by Michael Voecks
"""

import labbench as lb
from labbench import paramattr as attr
import ssmdevices.lib


class AndroidDebugBridge(lb.ShellBackend):
    binary_path = attr.value.Path(ssmdevices.lib.path('adb.exe'), inherit=True)
    timeout = attr.value.float(6, inherit=True)

    def devices(self):
        """This function checks ADB to see if any devices are connected, if
        none are, it raises an exception, if there is at least one device
        connected:
        This function returns a list of tuples, each tuple contains the
        device id and device type. i.e. [['f0593056', 'device']] represents
        one connected device with id f0593056.
        """
        # with self.no_state_arguments:
        devices = (
            self.run('devices', pipe=True, check_stderr=True, check_return=True)
            .strip()
            .rstrip()
            .splitlines()[1:]
        )
        if len(devices) > 0:
            # At least one device found, lets return it in a nice way
            for index in range(len(devices)):
                devices[index] = devices[index].decode('utf-8').split('\t')
            return devices
        else:
            raise Exception('No devices found. Is the UE properly connected?')

    def is_device_connected(self, serialNum):
        """Uses the devices function to check if a device (sepecified by the
        serialNum argument) is connected to the ADB server, return true/false
        """
        # Get list of devices
        devices = self.devices()

        # Test to see if serialNum is one of the first elements in the list of tuples
        if serialNum not in [i[0] for i in devices]:
            return False
        return True

    def reboot(self, deviceId):
        """This function takes in a UE's Id, (from self.devices), and reboots
        the specified device.
        """
        # with self.no_state_arguments:
        if self.is_device_connected(deviceId):
            # Device is connected and ready to reboot, lets do
            self.run('-s', str(deviceId), 'reboot', check_return=True)
        else:
            # Devices isn't connected, lets raise an error saying so
            raise Exception('The specified device is not connected to the ADB server')

    def check_airplane_mode(self, deviceId):
        """Returns the status of airplane mode of device deviceId,
        returns 0 if deviceId's airplane_mode is OFF
        returns 1 if deviceId's airplane_mode is ON
        raises exception if it cannot find the device
        """
        if self.is_device_connected(deviceId):
            res = self.run(
                '-s',
                str(deviceId),
                'shell',
                'settings',
                'get',
                'global',
                'airplane_mode_on',
                pipe=True,
            )
            return res.strip().rstrip().decode('utf-8')
        else:
            raise Exception('The specified device is not connected to the ADB server')

    def set_airplane_mode(self, deviceId, status):
        """Sets the airplane_mode feature on the device specified by deviceId
        to the value of the 'status' argumentself.
        status should be set to either 0 or 1, 0 indicating that the airplane_mode
        should be turned off, 1 indicating it should be turned on
        """
        if self.is_device_connected(deviceId):
            if status not in [0, 1]:
                # invalid status argument
                raise Exception(
                    'The Airplane Mode feature can only be set to a value of 0 or 1'
                )
            else:
                self.foreground(
                    '-s',
                    str(deviceId),
                    'shell',
                    'settings',
                    'put',
                    'global',
                    'airplane_mode_on',
                    str(status),
                    pipe=True,
                    check_return=True,
                )
                self.foreground(
                    '-s',
                    str(deviceId),
                    'shell',
                    'am',
                    'broadcast',
                    '-a',
                    'android.intent.action.AIRPLANE_MODE',
                    pipe=True,
                    check_return=True,
                )
        else:
            raise Exception('The specified device is not connected to the ADB server')

    def push_file(self, deviceId, local_filepath, device_filepath):
        """Takes a file at the location specified by local_filepath and copys
        it into the directory specified by device_filepath on the device that
        is specified by deviceId.
        """
        if self.is_device_connected(deviceId):
            res = self.run(
                '-s',
                str(deviceId),
                'push',
                local_filepath,
                device_filepath,
                pipe=True,
                check_return=True,
            )
            res = res.strip().rstrip().splitlines()
            for val in res:
                print(val.decode('utf-8'))
        else:
            raise Exception('The specified device is not connected to the ADB server')


if __name__ == '__main__':
    with AndroidDebugBridge() as adb:
        devices = adb.devices()[0][0]  # Returns a list of tuples containing device Ids
        #  adb.reboot(devices[0][0])
        print(adb.check_airplane_mode(devices))
        adb.set_airplane_mode(devices, 0)
        print(adb.check_airplane_mode(devices))
        adb.push_file(
            devices,
            ssmdevices.lib.path('android', 'iperf'),
            '/data/local/tmp/iperf',
        )
