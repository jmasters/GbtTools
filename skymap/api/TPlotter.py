# Copyright (C) 2004 Associated Universities, Inc. Washington DC, USA.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 675 Mass Ave Cambridge, MA 02139, USA.
#
# Correspondence concerning GBT software should be addressed as follows:
#     GBT Operations
#     National Radio Astronomy Observatory
#     P. O. Box 2
#     Green Bank, WV 24944-0002 USA

from   Antenna                      import Antenna
from   gbt.turtle.database          import ConfigScript
from   GbtConnection                import GbtConnection
from   Scan                         import Scan
from   Configure                    import Configure
from   Location                     import Location 
from   Loci                         import Loci
from   Telescope                    import *
from   gbt.project                  import Project
from   telescope.gbt.config         import gbtsetup
from   telescope.gbt.config.Balance import Balance
from   gbt.ygor.GrailClient         import Manager
from   gbt.ygor.GrailClient         import GrailClient
from   mx                           import DateTime
import sys
import wx

class FunctionPointer:
    def __init__(self, function):
        self.function = function

    def __call__(self, *args, **kwds):
        return True

class LocalGrailClient:
    def __init__(self):
        self.gc = GrailClient

    def __getattr__(self, name):
        return FunctionPointer(getattr(self.gc, name))

    def create_manager(self, device):
        return Manager(self, device)

    def get_value(self, device, path):
        if path == "nextScanNumber":
            retval = 1
        else:
            return True
        return retval

    def get_parameter(self, device, param):
        if param == "scanLength":
            retval = {param : {param : {"seconds" : {"value" : "30.0"}}}}
        else:
            return True
        return retval

class SimulateConfigure(Configure):

    def SendSetup(self):
        # Let's configure this bad boy!
        try:
            success = self.setup.setup(0)
        except:
            success  = False
            messages = traceback.format_exception(*sys.exc_info())
            for m in messages:
                self.pipe.write("self.telescope.Comment(%s, wx.RED)\n" % m)

        return success


class TPlotter(Telescope):
    """
    This class attempts to simulate the class Telescope and log the
    antenna positions for plotting
    """

    def __init__(self):
        gc               = LocalGrailClient()
        connection       = TelescopeConnection(GbtConnection(gc))
        self.antenna     = Antenna(connection)
        self.scan        = Scan(connection)
        self.configure   = SimulateConfigure(self)
        self.username    = None
        self.velocity    = None
        self.attributes  = {}
        self.positions   = []
        
        # Create a dictionary of GO FITS keywords.  The annotations
        # will be written to the primary header of a GO FITS file and
        # serve as meta-data for data-processing routines.
        self.InitAnnotations()

    def NeedToAbort(self):
        return False

    def NeedToStop(self):
        return False

    def NeedToPause(self):
        return False

    def NeedToWriteGOFITSFile(self):
        return False

    def Balance(self, devices = [], options = {}):
        """
        Balances the IF system based on the backend in use, unless expressly
        overridden.
        """

        # Figure out correct balancing strategy since none provided.
        if devices == (): devices = self.GetDefaultBalanceParameters()

        # Here for backward compatibility with old Balancing API.
        if type(devices) is str:
            theDevice = devices
            devices = []
            if theDevice == "IFRack": devices.append("ifrack")
            if theDevice in ("RcvrPF_1", "RcvrPF_2"): devices.append("pf")
            if theDevice == "Spectrometer": devices.append("acs")
            if theDevice == "SpectralProcessor": devices.append("spp")

        self.Comment("Balancing IF system.\n")
        self.Comment("    devices = %s\n" % str(devices))
        self.Comment("    options = %s\n" % str(options))

        ifSystem = Balance(devices)
        try:
            ifSystem.balance(options, sim = 1)
        except:
            self.Comment("*** Error: Balance failed!\n", wx.RED)
            self.QueryUserToTerminateBlock("Balance failed")

    def GetValue(self, manager, value, value_type = None):
        retval = None
        if manager == "ScanCoordinator":
            if value == "receiver":
                retval = "Rcvr1_2"
            elif value == "nextScanNumber":
                retval = "2"
            elif value == "startTime,MJD":
                gmt = DateTime.gmt()
                loci = Loci()
                mjd, _ = loci.DateTime2TimeStamp(gmt)
                retval = str(mjd)
            elif value == "startTime,seconds":
                gmt = DateTime.gmt()
                loci = Loci()
                _, secs = loci.DateTime2TimeStamp(gmt)
                retval = str(secs)
            elif value == "projectId":
                retval = 'TAPI_FRANK'
        elif manager == "DCR":
            if value.find("Channel,") == 0 or value.find("CH1_16,Tsys") == 0:
                retval = "1"
        elif manager == "Antenna":
            if value == "azWrapMode":
                retval = 'Auto'
        elif manager == "Antenna,AntennaManager":
            if value == "ccuData,Az,indicated":
                retval = "180.0"
        if retval is None:
            retval =  "%s's value" % value
        self.Comment("GetValue(%s, %s) returning %s\n" % (manager,
                                                          value,
                                                          retval))
        return retval

    def GetSamplerValue(self, manager, value):
        self.Comment("GetSamplerValue(%s, %s) returning \n" % (manager, value))
        retval = None
        if manager == "DCR":
            if value == "CH1_16":
                port_values = {}
                for i in range(16):
                    port_values["Tsys%d" % i] = { 'value' : "30.0" }
                retval =  { value : { value : port_values } }
        if retval is None:
            retval =  "%s's value" % value
        return retval

    def SetValues(self, manager, values, force = 0):
        Telescope.SetValues(self, manager, values, force)
        if values.has_key("state"):
            print "The state of the", manager, "is now", values["state"].lower()

        self.Comment("SetValues for %s\n" % manager)
        for key in values:
            self.Comment("    " + key + " = " + str(values[key]) + "\n")

    def SpigotAutoLevelerStart(self, time_constant, gain):
        self.Comment("SpigotAutoLevelerStart\n")

    def SpigotAutoLevelerStop(self):
        self.Comment("SpigotAutoLevelerStop\n")

    def SetupSpigot(self, mode, data_disk, freq):
        self.Comment("SetupSpigot\n")

    def CalibrateSpigot(self, calib_file):
        self.Comment("CalibrateSpigot\n")

    def CheckSpigotData(self):
        self.Comment("CheckSpigotData\n")

    def WaitFor(self, time):
        self.Comment("WaitFor(%s)\n" % time)

    def TakeSpigotData(self, duration, scan_num, power_file):
        self.Comment("TakeSpigotData\n")

    def SpigotChangeDataDirectory(self, data_directory):
        self.Comment("SpigotChangeDataDirectory(%s)\n" % data_directory)

    def SetSourceVelocity(self, velocity):
        Telescope.SetSourceVelocity(self, velocity)
        self.Comment("SetSourceVelocity(%s)\n" % velocity)

    def SetScanDuration(self, duration):
        Telescope.SetScanDuration(self, duration)
        self.Comment("SetScanDuration %f.\n" % duration)

    def SetProjectId(self, projectId):
        self.SetValues("ScanCoordinator", {"projectId" : projectId})
    
    def SetAntennaBeginPosition(self, position):
        Telescope.SetAntennaBeginPosition(self, position)
        self.positions.append(position)
        self.Comment("Initial Antenna position:" + str(position) + "\n")

    def SetAntennaEndPosition(self, position):
        Telescope.SetAntennaEndPosition(self, position)
        self.positions.append(position)
        self.Comment("Final Antenna position:" + str(position) + "\n")

    def SetAntennaYBeginPosition(self, position):
        Telescope.SetAntennaYBeginPosition(self, position)
        self.Comment("Initial subreflector position:" + str(position) + "\n")

    def SetAntennaYEndPosition(self, position):
        Telescope.SetAntennaYEndPosition(self, position)
        self.Comment("Final subreflector position:" + str(position) + "\n")

    def GetCurrentLocation(self, coordinateMode):
        self.Comment("GetCurrentLocation(%s): returning dummy location" % coordinateMode)
        return Location(coordinateMode, 0.0, 0.0)

    def UpdateCorrections(self):
        self.Comment("Updating corrections.\n")

    def Ask(self, message, style, default, timeout = 300.0, choices=None):
        msg = 'User queried: "%s".' % message
        self.Comment(msg)
        if choices:
            return choices[-1]  #last item in list is index of default choice
        else:
            return wx.OK

    def WaitForRunning(self, stopTime):
        self.Comment("Running ...\n")

    def WaitForReady(self):
        pass

    def AddAnnotation(self, key, value = None, comment = None):
        "Add or update a key/value pair."
        self.Comment("Adding FITS keyword: %s = %s    \\ %s\n" % (key, value, comment))

    def RemoveAnnotation(self, key):
        """
        Since annotations persist from scan to scan, the user may have
        reason to remove unnecessary annotations hanging around from
        an earlier scan.
        """
        self.Comment("Deleting FITS keyword %s\n" % key)

    def Comment(self, message, color = wx.BLACK):
        "Give any observers the opportunity to process Comment messages."
        print message

    def Trace(self, message):
        "Give any observers the opportunity to process Trace messages."
        print message


