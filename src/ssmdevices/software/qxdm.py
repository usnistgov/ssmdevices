"""
Basic control over the QXDM software.

Author: Paul Blanchard (paul.blanchard@nist.gov)
Edits by Dan Kuester (dkuester@nist.gov)
"""

__all__ = ['QXDM']

import datetime
import os
import time
from xml.etree import ElementTree as ET

import labbench as lb
from labbench import paramattr as attr
import psutil


class QPST(lb.Win32ComDevice):
    PORT_LIST_CODES = dict(
        ue_mode={
            0: 'No phone detected',
            2: 'Download',
            3: 'Diagnostic',
            4: 'Offline and diagnostic',
            5: 'Streaming download',
        }
    )

    API_ATTR_MAP = dict(
        ue_model_number='ModelNumber',
        ue_mode='PhoneMode',
        ue_imei='IMEI',
        ue_esn='ESN',
        ue_build_id='BuildId',
    )

    com_object = attr.value.str('QPSTAtmnServer.Application', inherit=True)

    def open(self):
        # have to do this for every method we want to call
        self.backend._FlagAsMethod('AddPort')
        self.backend._FlagAsMethod('RemovePort')
        self.backend._FlagAsMethod('GetPort')
        self.backend.HideWindow()

    def close(self):
        self.backend.Quit()

    def add_port(self, port):
        """enables the specified port in QPST"""

        self.backend.AddPort(f'COM{port}', 'Python generated port')

        for elapsed in lb.timeout_iter(5):
            try:
                port_list = self.backend.GetPortList
                for i in range(port_list.PhoneCount):
                    if port_list.PortName(i).upper() == f'COM{port}':
                        if port_list.PhoneStatus(i) != 5:
                            raise ValueError(f'qpst detected no phone on COM{port}')
                        ret = {}
                        for key, api_name in self.API_ATTR_MAP.items():
                            func = getattr(port_list, api_name)
                            port_code = func(i)

                            # Remap codes into strings
                            label = self.PORT_LIST_CODES.get(key, {}).get(
                                port_code, port_code
                            )
                            ret[key] = label
                        break

                else:
                    raise TimeoutError(f'qpst timeout adding port COM{port}')
            except ValueError:
                lb.sleep(0.1)
                continue
            else:
                break
        else:
            raise IOError(f'qpst connection failure on COM{port}')

        return ret

    def remove_port(self, port):
        """removes the port from QPST for consistency"""
        self.backend.RemovePort(f'COM{port}')

        for elapsed in lb.timeout_iter(5):
            try:
                port_list = self.backend.GetPortList
                for i in range(port_list.PhoneCount):
                    if port_list.PortName(i).upper() == f'COM{port}':
                        break
                else:
                    break
            except ValueError:
                lb.sleep(0.1)
                continue
            else:
                break
        else:
            raise TimeoutError(f'QXDM disconnect timeout on COM{port}')


class QXDM(lb.Win32ComDevice):
    """QXDM software wrapper"""

    com_object = attr.value.str('QXDM.QXDMAutoApplication', inherit=True)

    resource: int = attr.value.int(
        0, min=0, help='serial port number for the handset connection'
    )
    cache_path: str = attr.value.str(
        default='temp', help='directory for auto-saved isf files'
    )
    connection_timeout: float = attr.value.float(
        default=2, min=0.5, help='connection timeout (s)'
    )

    def open(self):
        #
        self._killall()

        self._connection_info = {}
        self._qpst = QPST()
        self._qpst.open()
        self._connection_info = self._qpst.add_port(self.resource)

        self._start_time = None
        self._window = self.backend.GetAutomationWindow()
        self.cache_path = os.path.abspath(self.cache_path)
        os.makedirs(self.cache_path, exist_ok=True)

        while not self._qpst.isopen:
            lb.sleep(0.1)

        # Disable to prevent undesired data streaming on startup
        try:
            self._set_com_port(None)
        except TimeoutError:
            raise Exception(
                'could not disable UE; does QXDM work if you start it manually?'
            )

    # State traits implemented by command key
    ue_model_number = attr.property.str(help='model number code', key='ue_model_number')
    ue_mode = attr.property.str(help='current state of the phone', key='ue_mode')
    ue_imei = attr.property.str(help='Phone IMEI', key='ue_imei')
    ue_esn = attr.property.str(help='Phone ESN', key='ue_esn')
    ue_build_id = attr.property.str(
        help='Build ID of software on the phone', key='ue_build_id'
    )

    def get_key(self, key, trait_name=None):
        try:
            return self._connection_info[key]
        except KeyError:
            raise lb.DeviceStateError(f"no state information for key '{key}'")

    def close(self):
        def none_func():
            pass

        try:
            f1 = self._qpst.disconnect
        except AttributeError:
            f1 = none_func
            self._logger.debug('QPST already quit')
        try:
            f2 = self._window.QuitApplication
        except AttributeError:
            f2 = none_func
            self._logger.debug('QXDM already quit')

        lb.concurrently(f1, f2)

    def configure(self, config_path, min_acquisition_time=None):
        """Load the QXDM .dmc configuration file at the specified path,
        with adjustments that disable special file output modes like
        autosave, quicksave, and automatic segmenting based on time and
        file size.
        """
        if not os.path.isfile(config_path):
            raise Exception('config_path {} does not exist.'.format(repr(config_path)))
        self._min_acquisition_time = min_acquisition_time

        basename = os.path.splitext(os.path.basename(config_path))[0] + '-live.dmc'
        path_out = os.path.join(self.cache_path, basename)

        tree = ET.parse(config_path)
        root = tree.getroot()
        settings = root.find('Persistence').find('MainFrame').find('ISFSettings')

        # Disable automatic file saving and partitioning
        settings.find('AutoISFSave').text = '0'
        settings.find('QuickISFSave').text = '0'
        settings.find('QueryISFSave').text = '0'
        # These seem to be irrelevant now
        #        settings.find('BaseISFName').text = self.save_base_name
        #        settings.find('ISFFolder').text = self.cache_path
        settings.find('MaxISFSize').text = '0'  # str(self.save_size_limit_MB)
        settings.find('MaxISFDuration').text = '0'
        settings.find('MaxISFDurationFraction').text = '0'  # str(self.save_time_limit)
        settings.find('Advanced').text = '0'

        # Don't care about this any more?
        #        isv_config = root.find('Persistence').find('LoggingView').find('ISVConfig')
        #        isv_config.find('LogFilePath').text = self.cache_path

        tree.write(path_out)
        self._load_config(path_out)
        self._logger.debug('loaded modified configuration at {}'.format(repr(path_out)))

    def save(self, path=None, saveNm=None):
        """Stop the run and save the data in a file at the specified path.
        If path is None, autogenerate with self.cache_path and
        self.data_filename.

        This method is threadsafe.

        :returns: The absolute path to the data file
        """
        if self._start_time is None:
            raise Exception('call start() to acquire data before calling save()')
        if self._min_acquisition_time is not None:
            t_elapsed = time.time() - self._start_time
            if t_elapsed < self._min_acquisition_time:
                lb.sleep(self._min_acquisition_time - t_elapsed)
        # Munge path
        if path is None:
            now = datetime.datetime.now()
            fmt = lb.Host.time_format.replace(' ', '_').replace(':', '')
            timestamp = '{}.{}'.format(now.strftime(fmt), now.microsecond)
            if saveNm is not None:
                path = os.path.join(
                    self.cache_path, '{}-{}.isf'.format(saveNm, timestamp)
                )
            else:
                path = os.path.join(self.cache_path, 'qxdm-{}.isf'.format(timestamp))
        else:
            path = os.path.abspath(path)

        # Stop acquisition
        with lb.stopwatch('saving data'):
            self._set_com_port(None)
            self._wait_for_stop()

            # Save the file
            self._window.SaveItemStore(path)
            self._logger.debug(f'saved to {path}')

        self._start_time = None
        return path

    def start(self, wait=True):
        """Start acquisition, optionally waiting to return until
        new data enters the QXDM item store.
        """
        t0 = time.time()
        self._clear()
        self._set_com_port(self.resource)
        if wait:
            self._wait_for_start()
        self._logger.debug('running after setup for {}s'.format(time.time() - t0))

        self._start_time = time.time()

    # Bare wrapper methods for the low level QXDM COM API
    def _get_com_port(self):
        return self._window.getCOMPort()

    def _load_config(self, path):
        self._window.LoadConfig(path)

    @attr.property.str(sets=False, cache=True)
    def version(self):
        """QXDM application version"""
        _window = self.backend.GetAutomationWindow()
        if not self.isopen:
            raise lb.DeviceNotReady('need to connect to get application version')
        version = _window.AppVersion
        return version

    def _get_server_state(self):
        state = self._window.GetServerState()
        if state == 0xFFFFFFFF:
            raise Exception('server state is in error')
        return state

    def _get_item_count(self):
        return self._window.GetItemCount()

    def _killall(self):
        """kills all instances of qpst, qxdm, and atmnserver"""
        for pid in psutil.pids():
            try:
                proc = psutil.Process(pid)
                for target in 'qpst', 'qxdm', 'atmnserver':
                    if proc.name().lower().startswith(target.lower()):
                        self._logger.debug(
                            'killing zombie process {}'.format(proc.name())
                        )
                        proc.kill()
            except psutil.NoSuchProcess:
                pass

    def _set_com_port(self, com_port: int):
        """connects to the handset at the specified serial port.

        Blocks until QXDM confirms the phone is connected.

        Arguments:
            com_port (int): serial port number, COMn; 0 or None to disable

        Raises:
            TimeoutError: after waiting `self.connection_timeout` for connection
            IOError: when the QXDM COM API returns code -1

        """
        if com_port is None:
            com_port = 0
        if int(com_port) > 0:
            self._connection_info = self._qpst.add_port(self.resource)

        try:
            code = None

            for elapsed in lb.timeout_iter(self.connection_timeout):
                # try it
                ret = int(self._window.setCOMPort(com_port))

                # validate
                if ret == -1:
                    raise IOError('Connection error')
                actual = self._get_com_port()
                if str(actual) == str(com_port):
                    break
                else:
                    code = self._window.GetServerState()
                    if code == 0xFFFFFFFF:
                        raise Exception('Connection error')
                    lb.sleep(0.1)
            else:
                if com_port:
                    raise TimeoutError(f'handset connect to port {actual} timed out')
                else:
                    raise TimeoutError(f'handset disconnect to port {actual} timed out')

            if int(com_port) > 0:
                self._logger.debug(f'connect to port {actual} took {elapsed:0.2f}s')
            else:
                self._logger.debug(
                    f'disconnect from port {actual} took {elapsed:0.2f}s'
                )

        finally:
            if int(com_port) == 0:
                self._qpst.remove_port(self.resource)

    def reconnect(self):
        self._logger.info('reinitializing')
        self.close()
        self.open()

    def _clear(self, timeout=20):
        """clears the buffer of data.

        TODO: Depending on if QXDM is already running, wait for the item
        count store to start increasing again?
        """
        start = self._get_item_count()
        for item in 'Item view', 'Filtered view':
            if not self._window.ClearViewItems(item):
                if item == 'Item view':
                    self._logger.error('failed to clear view ' + repr(item))

        # Block until the item store is clear or timeout
        for elapsed in lb.timeout_iter(timeout):
            count = self._get_item_count()
            if count < start or count < 10:
                break
            lb.sleep(0.05)
        else:
            remaining = self._get_item_count()
            raise TimeoutError(
                f'QXDM item store clear timed out with {remaining} items'
            )

        self._logger.debug(f'cleared item store buffer in {elapsed:0.2f}s')

    def _wait_for_stop(self, timeout=10):
        """blocks until the QXDM item store stops growing"""
        prev = self._get_item_count()
        for elapsed in lb.timeout_iter(timeout):
            lb.sleep(0.25)
            new = self._get_item_count()
            if new == prev:
                break
            else:
                prev = new
        else:
            raise TimeoutError('timeout waiting for qxdm to buffer data')

    def _wait_for_start(self, timeout=10, min_rows=10):
        """blocks until the item store has grown by at least `min_rows`"""

        start = self._get_item_count()
        for elapsed in lb.timeout_iter(timeout):
            lb.sleep(0.05)
            if self._get_item_count() != start:
                break
        else:
            raise Exception('timeout waiting for qxdm to start acquisition')
        #        lb.sleep(1)
        self._logger.debug(f'item store grew after {elapsed:0.2f}s')

if __name__ == '__main__':
   import labbench as lb
   import inspect

   lb.show_messages('debug')

   # Connect to application
   with QXDM(8, cache_path=r'C:\Python Code\potato', concurrency=False) as qxdm:
       mod = inspect.getmodule(qxdm.backend._FlagAsMethod).__name__
       print(repr(qxdm.backend),dir(qxdm.backend))
       qxdm.configure(r'180201_QXDMConfig.dmc')
       for i in range(1):
           qxdm.start()
           lb.sleep(10)
           qxdm.save(r'junk-{}.isf'.format(i))