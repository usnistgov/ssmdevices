# -*- coding: utf-8 -*-
"""
Basic control over the QXDM software.

Author: Paul Blanchard (paul.blanchard@nist.gov)
Edits by Dan Kuester (dkuester@nist.gov)
"""

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
__all__ = ['QXDM']

import labbench as lb
import time, os, psutil, datetime
from xml.etree import ElementTree as ET

class QPST(lb.Win32ComDevice):
    class state(lb.Win32ComDevice.state):
        com_object           = lb.LocalUnicode('QPSTAtmnServer.Application', is_metadata=True)
    
    def setup(self):
        self.backend._FlagAsMethod('AddPort')
        self.backend._FlagAsMethod('RemovePort')
        self.backend._FlagAsMethod('GetPort')
        self.backend.HideWindow()
        
    def disconnect(self):
        self.backend.Quit()
        
    def add_port(self, port):
        ''' Make sure that QPST is configured to enable the desired port
        '''
        state_to_qpst_api = {'phone_model_number': 'ModelNumber',
                             'phone_mode':         'PhoneMode',
                             'phone_imei':         'IMEI',
                             'phone_esn':          'ESN',
                             'phone_build_id':     'BuildId'}
    
        codes = {'phone_mode':   {0: 'No phone detected',
                                  2: 'Download',
                                  3: 'Diagnostic',
                                  4: 'Offline and diagnostic',
                                  5: 'Streaming download'}}
    

        self.backend.AddPort('COM{}'.format(port), 'Python generated port')
        
        t0 = time.time()
    
        while time.time()-t0 < 5:
            try:
                port_list = self.backend.GetPortList
                for i in range(port_list.PhoneCount):
                    if port_list.PortName(i).upper() == 'COM{}'.format(port):
                        if port_list.PhoneStatus(i) != 5:
                            raise ValueError('QXDM: no phone detected on COM{}'.format(port))
                        for key, api_name in state_to_qpst_api.items():
                            value = getattr(port_list,api_name)(i)
                            
                            # Remap integers to strings
                            value = codes.get(key,{}).get(value,value)
                            setattr(self.state, key, value)
                        break

                else:
                    raise Exception('QXDM: could not add port at COM{}'.format(port))
            except ValueError:
                time.sleep(0.1)
                continue
            break
        else:
            raise TimeoutError('QXDM: could not connect to port on COM{}'.format(port))
    
    def remove_port(self, port):
        ''' Remove the port from QPST for consistency
        '''
        self.backend.RemovePort('COM{}'.format(port))
        
        t0 = time.time()
        while time.time()-t0 < 5:
            try:
                port_list = self.backend.GetPortList
                for i in range(port_list.PhoneCount):
                    if port_list.PortName(i).upper() == 'COM{}'.format(port):
                        break
                else:
                    break
            except ValueError:
                time.sleep(0.1)
                continue
            break
        else:
            raise TimeoutError('QXDM: could not disconnect from port on COM{}'.format(port))
        

class QXDM(lb.Win32ComDevice):
    """
    Class to provide some basic control over the QXDM software.


    Required parameters:
            resource int; port number in QXDM to which UE is connected, e.g. 10 for COM10
            config_path str;

    """

    class state(lb.Win32ComDevice.state):
        com_object           = lb.LocalUnicode("QXDM.QXDMAutoApplication", is_metadata=True)
        cache_path           = lb.LocalUnicode("temp", is_metadata=True,
                                               help='folder path to contain auto-saved isf file(s)')
        connection_timeout   = lb.LocalFloat(2, min=0.5, help='connection timeout in seconds')
        version              = lb.Unicode(read_only=True, is_metadata=True, cache=True,
                                          help='QXDM application version')
        phone_model_number   = lb.LocalInt(-1, help='model number code')
        phone_mode           = lb.LocalUnicode(help='current state of the phone')
        phone_imei           = lb.LocalInt(-1,help='Phone IMEI')
        phone_esn            = lb.LocalInt(-1,help='Phone ESN')
        phone_build_id       = lb.LocalUnicode(help='Build ID of software on the phone')

    def connect(self):
        for pid in psutil.pids():
            try:
                proc = psutil.Process(pid)
                for target in 'qpst','qxdm','atmnserver':
                    if proc.name().lower().startswith(target.lower()):
                        self.logger.info('killing zombie process {}'.format(proc.name()))
                        proc.kill()
            except psutil.NoSuchProcess:
                pass
#
        self._qpst = QPST()
        self._qpst.connect()
        super(QXDM, self).connect()

    def setup(self):
        ''' Like all other Device subclasses, this setup method is run
            automatically right after .connect().
        '''
        self.__start_time = None
        self._window = self.backend.GetAutomationWindow()
        self.state.cache_path = os.path.abspath(self.state.cache_path)
        os.makedirs(self.state.cache_path, exist_ok=True)

        
        while not self._qpst.state.connected:
            time.sleep(0.1)

        # Disable to prevent undesired data streaming on startup
        try:
            self._set_com_port(None)
        except TimeoutError:
            raise Exception('could not disable UE; does QXDM work if you start it manually?')

    def disconnect (self):
        try:
            f1 = self._qpst.disconnect
        except AttributeError:
            self.logger.debug('QPST already quit')
        try:
            f2 = self._window.QuitApplication
        except AttributeError:
            self.logger.debug('QXDM already quit')
        
        lb.concurrently(f1,f2)

    def configure(self, config_path, min_acquisition_time=None):
        ''' Load the QXDM .dmc configuration file at the specified path,
            with adjustments that disable special file output modes like
            autosave, quicksave, and automatic segmenting based on time and
            file size.
        '''
        if not os.path.isfile(config_path):
            raise Exception("config_path {} does not exist.".format(repr(config_path)))
        self._min_acquisition_time = min_acquisition_time

        basename = os.path.splitext(os.path.basename(config_path))[0]+'-live.dmc'
        path_out = os.path.join(self.state.cache_path, basename)

        tree = ET.parse(config_path)
        root = tree.getroot()
        settings = root.find('Persistence').find('MainFrame').find('ISFSettings')

        # Disable automatic file saving and partitioning
        settings.find('AutoISFSave').text = '0'
        settings.find('QuickISFSave').text = '0'
        settings.find('QueryISFSave').text = '0'
        # These seem to be irrelevant now
#        settings.find('BaseISFName').text = self.state.save_base_name
#        settings.find('ISFFolder').text = self.state.cache_path
        settings.find('MaxISFSize').text = '0'#str(self.state.save_size_limit_MB)
        settings.find('MaxISFDuration').text = '0'
        settings.find('MaxISFDurationFraction').text = '0'#str(self.state.save_time_limit)
        settings.find('Advanced').text = '0'
        
        # Don't care about this any more?
#        isv_config = root.find('Persistence').find('LoggingView').find('ISVConfig')
#        isv_config.find('LogFilePath').text = self.state.cache_path
        
        tree.write(path_out)
        self._load_config(path_out)
        self.logger.debug('loaded modified configuration at {}'\
                          .format(repr(path_out)))

    def save(self, path=None, saveNm = None):
        ''' Stop the run and save the data in a file at the specified path.
            If path is None, autogenerate with self.state.cache_path and
            self.data_filename.
            
            This method is threadsafe.
            
            :returns: The absolute path to the data file
        '''
        if self.__start_time is None:
            raise Exception('call start() to acquire data before calling save()')
        if self._min_acquisition_time is not None:
            t_elapsed = time.time()-self.__start_time
            if t_elapsed < self._min_acquisition_time:
                time.sleep(self._min_acquisition_time-t_elapsed)
        # Munge path
        if path is None:
            now = datetime.datetime.now()
            fmt = lb.Host.time_format.replace(' ','_').replace(':','')
            timestamp = '{}.{}'.format(now.strftime(fmt),
                                       now.microsecond)
            if not saveNm == None:
                path = os.path.join(self.state.cache_path, '{}-{}.isf'\
                                .format(saveNm, timestamp))
            else:
                path = os.path.join(self.state.cache_path, 'qxdm-{}.isf'\
                                .format(timestamp))
        else:
            path = os.path.abspath(path)
        
        # Stop acquisition
        t0 = time.time()
        self._set_com_port(None)
        self._wait_for_stop()

        # Save the file
        self._window.SaveItemStore(path)
        self.logger.debug('stopped and saved to {} in {}s'\
                          .format(repr(path),time.time()-t0))

        self.__start_time = None
        return path

    def start(self, wait=True):
        ''' Start acquisition, optionally waiting to return until 
            new data enters the QXDM item store.
        '''
        t0 = time.time()
        self._clear()
        self._set_com_port(self.resource)
        if wait:
            self._wait_for_start()
        self.logger.debug('started run in {}s'.format(time.time()-t0))

        self.__start_time = time.time()

    # Bare wrapper methods for the low level QXDM COM API
    def _get_com_port (self):
        return self._window.getCOMPort()

    def _load_config (self, path):
        self._window.LoadConfig(path)

    @state.version.getter
    def __(self):
        _window = self.backend.GetAutomationWindow()
        if not self.state.connected:
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

    # Methods that support the higher-level functions above        
    def _set_com_port (self, com_port):
        ''' Set the com_port to the integer n for COMn, or 0 or None to disable
            acquisition. This includes logic to enable and disable the port
            in QPST.
            
            Return blocks until QXDM confirms the phone is connected,
            or raise a TimeoutError if it fails, or Exception on other
            rare error types that have not been observed.
        '''
        if com_port is None:
            com_port = 0
        if com_port > 0:
            self._qpst.add_port(self.resource)

        try:
            code = None
            t0 = time.time()
            while time.time()-t0 < self.state.connection_timeout:
                ret = int(self._window.setCOMPort(com_port))
                if ret == -1:
                    raise Exception('Connection error')
                actual = self._get_com_port()
                if actual == com_port:
                    break
                else:
                    code = self._window.GetServerState()
                    if code == 0xFFFFFFFF:
                        raise Exception('Connection error')
                    time.sleep(0.1)
            else:
                if com_port:
                    raise TimeoutError('QXDM timeout connecting to UE (connected to {})'.format(actual))
                else:
                    raise TimeoutError('QXDM timeout disconnecting to UE (return code {})'.format(actual))
            if com_port > 0:
                self.logger.debug('connected to COM{} in {}s'\
                                  .format(self.resource, time.time()-t0))
            else:
                self.logger.debug('disconnected from COM{} in {}s'\
                                  .format(self.resource, time.time()-t0))
                
        finally:
            if com_port == 0:
                self._qpst.remove_port(self.resource)

    def _clear(self):
        ''' Clear the buffer of data. 
        '''
        t0 = time.time()
        for item in 'Item view',:
            if not self._window.ClearViewItems(item):
                pass
#                raise Exception('failed to clear item {}'.format(repr(item)))

        start = self._get_item_count()

        # Block until the item store is clear
        while time.time()-t0 < 20:
            count = self._get_item_count()
            if count < start or count <= 5:
                break
            time.sleep(.05)
        else:
            raise Exception('timeout waiting for qxdm to clear, buffer still had {} items'.format(self._get_item_count()))

        self.logger.debug('cleared data buffer in {}s'.format(time.time()-t0))

    def _wait_for_stop (self):
        ''' Block until the reported number of data rows stops growing.
        '''
        t0 = time.time()
        prev = self._get_item_count()
        while time.time()-t0 < 10:
            time.sleep(.25)
            new = self._get_item_count()
            if new == prev:
                break
            else:
                prev = new
        else:
            raise Exception('timeout waiting for qxdm to buffer data')

    def _wait_for_start (self):
        ''' Block until the reported number of data rows starts growing
            or exceeds 10 rows.
        '''
        t0 = time.time()
        start = self._get_item_count()
        while time.time()-t0 < 10:
            time.sleep(.05)
            if self._get_item_count() != start:
                break
        else:
            raise Exception('timeout waiting for qxdm to start acquisition')
#        time.sleep(1)
        self.logger.debug('activity began after observing items after {}s'\
                          .format(self._get_item_count(), time.time()-t0))

    # Deprecated
#    def fetch(self):
#        time_elapsed = time.time() - self.__start_time
#        if time_elapsed < self.state.min_acquisition_time:
#            time.sleep(self.state.min_acquisition_time - time_elapsed)
#
#        self.stop()
##        time.sleep(1)
#
#        # Quitting the application should force QXDM to write a "temporary" .isf file containing
#        # whatever hasn't already been saved.  This needs to be renamed with the .isf base name.
#        path = self.renameLatestISF('99-Final', self.state.max_cleanup_tries)
##        self.clear_stale_isf(path)
#        return path
#    def _list_isf(self):
#        return [e for e in os.listdir(self.state.cache_path)\
#                if e.lower().endswith('.isf')]
#

#if __name__ == '__main__':
#    import labbench as lb
#
#    lb.show_messages('debug')
#
#    # Connect to application
#    with QXDM(8, cache_path=r'C:\Python Code\potato', concurrency_support=False) as qxdm:
##        mod = inspect.getmodule(qxdm.backend._FlagAsMethod).__name__
#        print(repr(qxdm.backend),dir(qxdm.backend))
#        qxdm.configure(r'C:\Python Code\potato\180201_QXDMConfig.dmc')
#        for i in range(1):
#            qxdm.start()
#            time.sleep(10)
#            qxdm.save(r'C:\python code\potato\junk-{}.isf'.format(i))
