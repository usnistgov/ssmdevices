# -*- coding: utf-8 -*-
"""
Basic control over the QXDM software.

Author: Paul Blanchard (paul.blanchard@nist.gov)
"""

from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
__all__ = ['QXDM']

import labbench as lb
import time,logging,os
from shutil import copyfile

logger = logging.getLogger('labbench')


class QXDM(lb.Win32ComDevice):
    """
    Class to provide some basic control over the QXDM software.

    Before running, you must launch QXDM manually and connect to the UE. QXDM can then be closed
    before executing the code, provided that QPST remains active (check for the globe icon in the
    Windows system tray--it should indicate 1 active port if QPST is running and the UE is
    connected).  Try launching QPST separately if it disappears when QXDM closes.

    Required parameters:
            resource int; port number in QXDM to which UE is connected, e.g. 10 for COM10
            self.state.config_directory_in str;

    """

    class state(lb.Win32ComDevice.state):
        com_object           = lb.LocalUnicode("QXDM.QXDMAutoApplication", is_metadata=True)
        config_directory_in  = lb.LocalUnicode(".", is_metadata=True,
                                           help=''' full file path to the input QXDM *.dmc config file,
                                                    e.g. 'C:\MyFolder\180131QXDMConfig.dmc
                                                ''')
        config_directory_out = lb.LocalUnicode("", is_metadata=True,
                                           help=''' full file path to which new, modified QXDM *.dmc config file will be written.
                                                    Required if any of the other optional __init__ parameters are used ''')
        save_directory       = lb.LocalUnicode("", is_metadata=True,
                                           help='folder path to contain auto-saved isf file(s)')
        save_base_name       = lb.LocalUnicode("", is_metadata=True,
                                           help=''' base file name for QXDM auto-save feature. QXDM will
                                                    append a non-optional date/time string to each isf file.''')
        save_size_limit_MB   = lb.LocalInt(0, min=0, is_metadata=True,
                                           help='.isf file will be auto-saved and a new one started if size exceeds this limit')
        save_time_limit      = lb.LocalInt(0, min=0, is_metadata=True,
                                           help='.isf file will be auto-saved and a new one started if duration exceeds this limit')

    def setup(self):
        ''' This is run automatically immediately after .connect(), or before the with block
            starts executing, if the with statement is used.
        '''
        self.initISFList = []

        self.qxdmObj = self.backend.GetAutomationWindow()

        for aFileName in os.listdir(self.state.save_directory):
            if '.isf' in aFileName:
                self.initISFList += [aFileName]
                if self.state.save_base_name in aFileName:
                    msgStr = 'isfBaseName = "{}" is contained in existing file name {}.\n'.format(self.state.save_base_name,
                                                                                                  aFileName)
                    msgStr += 'You must provide a different base file name or a different isf save folder path.'
                    raise Exception(msgStr)

        if not os.path.isfile(self.state.config_directory_in):
            raise Exception("self.state.config_directory_in {} does not exist.".format(self.state.config_directory_in))
        # If necessary, edit qxdm .dmc config file
        if self.state.outConfigFilePath == '':
            self.configFilePath = self.state.config_directory_in
            logger.info('Using config file at {}'.format(self.configFilePath))
            if self.state.save_base_name != '' or self.state.save_directory != '' or (self.state.save_size_limit_MB != 0) or (
                self.state.save_time_limit != 0):
                raise Exception('outConfigFilePath must be provided if using any non-default optional input values')
        else:  # i.e. outConfigFilePath != ''
            copyfile(self.state.config_directory_in, self.state.outConfigFilePath)
            self.configFilePath = self.state.outConfigFilePath
            # make sure auto-saving and quick saving options are enabled, with no user prompt/query
            self.configFileEdit(self.configFilePath, '<QuickISFSave>', '</QuickISFSave>', '1')
            self.configFileEdit(self.configFilePath, '<QueryISFSave>', '</QueryISFSave>', '0')

            logger.info('Writing options to new config file at {}...'.format(self.configFilePath))
            if self.state.save_base_name != '':
                self.state.save_base_name = os.path.splitext(self.state.save_base_name)[0]  # remove any file extension
                self.configFileEdit(self.configFilePath, '<BaseISFName>', '</BaseISFName>', self.state.save_base_name)
            if self.state.save_directory != '':
                self.configFileEdit(self.configFilePath, '<ISFFolder>', '</ISFFolder>', self.state.save_directory)
                if not os.path.isdir(self.state.save_directory):
                    raise Exception("self.state.save_directory {} is not an existing directory.".format(self.state.save_directory))
            if self.state.save_size_limit_MB != 0:
                if type(self.state.save_size_limit_MB) != int:
                    raise Exception('self.state.save_size_limit_MB must be an integer value.')
                self.configFileEdit(self.configFilePath, '<Advanced>', '</Advanced>', '1')
                self.configFileEdit(self.configFilePath, '<MaxISFSize>', '</MaxISFSize>', str(self.state.save_size_limit_MB))
            if self.state.save_time_limit != 0:
                if type(self.state.save_time_limit) != int:
                    raise Exception('self.state.save_time_limit must be an integer value.')
                self.configFileEdit(self.configFilePath, '<Advanced>', '</Advanced>', '1')
                self.configFileEdit(self.configFilePath, '<MaxISFDuration>', '</MaxISFDuration>', str(0))
                self.configFileEdit(self.configFilePath, '<MaxISFDurationFraction>', '</MaxISFDurationFraction>',
                                    str(self.state.save_time_limit))
            logger.info('...done with config file write.')

            # Ensure that auto-save is enabled so that the log will be saved in the proper location
        # when QXDM exits
        self.configFileEdit(self.configFilePath, '<AutoISFSave>', '</AutoISFSave>', '1')
        self.configFileEdit(self.configFilePath, '<LogFilePath>', '</LogFilePath>', self.state.save_directory,
                            sectionStartStr='<LoggingView>', sectionEndStr='</LoggingView>')

    def start(self):
        # Load in desired configuration file
        self.qxdmObj.LoadConfig(self.configFilePath)
        logger.info('Loaded QXDM config file: {}'.format(self.configFilePath))
        time.sleep(1)
        # Loading a new config should force QXDM to write a "temporary" .isf file containing
        # whatever hasn't already been saved.  To be safe, this needs to be renamed with the
        # .isf base name, even though there shouldn't be much data in it
        if self.renameLatestISF(5, '00-Initial') is False:
            logger.warn('No new auto-save .isf detected upon loading config file. Hopefully everything is working okay...')
        # Make sure UE is connected; try to connect if it's not
        nIter = 0
        nIterMax = 5
        ueConnectedFlag = self.qxdmObj.IsPhoneConnected
        time.sleep(1)
        while ueConnectedFlag == False and nIter <= nIterMax:
            self.qxdmObj.COMPort = self.resource
            time.sleep(1)
            ueConnectedFlag = self.qxdmObj.IsPhoneConnected
            time.sleep(1)
            nIter += 1
        logger.info('After {} attempt(s), self.qxdmObj.IsPhoneConnected = {}'\
                    .format(nIter, self.qxdmObj.IsPhoneConnected))
        if self.qxdmObj.IsPhoneConnected is False:
            raise Exception("UE not connected to QXDM.")

        logger.info('QXDM acquisition started.')
        if self.state.save_size_limit_MB != 0 and self.state.save_size_limit_MB != 0:
            logger.info('New .isf will be saved whenever file size exceeds {} MB.'.format(self.state.save_size_limit_MB))
        if self.state.save_time_limit != 0 and self.state.save_time_limit != 0:
            logger.info('New .isf will be saved every {} minutes.'.format(self.state.save_time_limit))

    def stop(self):
        logger.info('Terminating QXDM acquisition...')
        self.qxdmObj.QuitApplication()
        time.sleep(1)
        # Quitting the application should force QXDM to write a "temporary" .isf file containing
        # whatever hasn't already been saved.  This needs to be renamed with the .isf base name.
        renameISFFlag = self.renameLatestISF(60, '99-Final')
        logger.info('...finished terminating QXDM application')
        if renameISFFlag == False:
            logger.warn(''' Did not detect QXDM auto-save file upon QXDM exit.
                            Data since previous .isf save (if any) may not be in directory {}''' \
                        .format(self.state.save_directory))

    def disconnect (self):
        try:
            self.stop()
        except:
            pass

    def renameLatestISF(self, maxTries, endStr):
        """
        The "temporary" .isf log that QXDM creates uses a default naming convention.
        To be safe, it should be renamed with the base file name corresponding to the experiment.
        This function looks for the most recent file in the self.state.save_directory directory and
        renames it if it doesn't already have the base file name.  Because it might take a while
        for QXDM to write this file for a large data set, the function will try up to maxTries times
        to do this, waiting 1 second between attempts.
        """
        nTries = 0
        printRenameAttemptFlag = True
        printWrongLatestFileFlag = True
        doneFlag = False
        while doneFlag == False and nTries <= maxTries:
            nTries += 1
            tmpFileNameList = os.listdir(self.state.save_directory)
            tmpFilePathList = []
            for aName in tmpFileNameList:
                if '.isf' in aName and aName not in self.initISFList:
                    tmpFilePathList += [os.path.join(self.state.save_directory, aName)]
            # Get the most recently-created file
            if len(tmpFilePathList) > 0:
                latestFilePath = max(tmpFilePathList, key=os.path.getctime)
                # If it's the QXDM temporary log file, the file name won't contain self.state.save_base_name
                if self.state.save_base_name not in latestFilePath:
                    try:
                        newName = os.path.join(self.state.save_directory,
                                               self.state.save_base_name + endStr + '.isf')
                        os.rename(latestFilePath, newName)
                        doneFlag = True
                    except:
                        doneFlag = False
                        if printRenameAttemptFlag:
                            logger.warn('Exception occurred during first attempt to rename file {}'.format(latestFilePath))
                            logger.warn('Will wait and reattempt up to {} times.'.format(maxTries - nTries))
                            printRenameAttemptFlag = False
                            time.sleep(1)
                else:  # i.e., self.state.save_base_name in latestFilePath
                    if printWrongLatestFileFlag == True:
                        logger.warn('Latest file {} already contains basename {}.'\
                                    .format(latestFilePath, self.state.save_base_name))
                        logger.warn('Will wait and recheck up to {} times for final QXDM auto-save file.'\
                                    .format(maxTries - nTries))
                        printWrongLatestFileFlag = False
                        time.sleep(1)
            else:  # i.e. len(tmpFilePathList) == 0, no .isf files in folder
                if nTries == 1:
                    self.info('No new .isf files detected yet.')
                    self.info('Will wait and recheck up to {} times.'.format(maxTries))
        return doneFlag

    def configFileEdit(self, configFilePath, itemStartStr, itemEndStr, newItemStr,
                       sectionStartStr='<ISFSettings>', sectionEndStr='</ISFSettings>'):
        """
        Function to alter the text in the QXDM .dmc config file.  This allows the options such as quick-save
        file base name, file size and duration limits, and save directories to be changed.
        """
        with open(configFilePath, 'r') as configFile:
            allInLines = configFile.readlines()

        with open(configFilePath, 'w') as outConfigFile:
            sectionStartFlag = False
            sectionEndFlag = False
            for aLine in allInLines:
                newLine = aLine
                if sectionStartFlag == False:
                    if sectionStartStr in aLine:
                        sectionStartFlag = True
                else:
                    if sectionEndStr in aLine:
                        sectionEndFlag = True
                if sectionStartFlag == True and sectionEndFlag == False:
                    if itemStartStr in aLine:
                        if itemEndStr not in aLine:
                            raise Exception('itemStartStr and itemEndStr must be in the same line in the file')
                        newLine = aLine.split(itemStartStr)[0] + itemStartStr + newItemStr
                        newLine += itemEndStr + aLine.split(itemEndStr)[-1]
                outConfigFile.write(newLine)


if __name__ == '__main__':
    resource = 10
    base_path = r'C:\Python Code'
    name = 'ZZVXF_'
    config = {  # unique label for the experiment. QXDM will append a simple time/date string to
                # this for quick-save files
                'save_base_name': name,

                # folder in which .isf files will be placed
                'save_directory': base_path,

                # input config file, has all the views defined, etc.
                'config_directory_in': os.path.join(base_path, '180201_QXDMConfig.dmc'),

                # config file to be set up for this experiment with timing options, base file name, etc.
                'config_directory_out': os.path.join(base_path, name + 'Config.dmc'),

                # .isf file will be saved/restarted when size exceeds this (set to 0 for unlimited file size)
                'save_size_limit_MB': 10000,

                # .isf file will be saved/restarted when duration exceeds this (set to 0 for unlimited duration)
                'save_time_limit': 0
             }

    # Connect to application
    with QXDM(resource, **config) as qxdm:

        # Start acquisition
        qxdm.start()

        # Let QXDM run for however long
        time.sleep(220 * 60)

        # Close QXDM and make sure that the last of the unsaved .isf data is saved and named properly.
        qxdm.stop()
