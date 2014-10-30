# Copyright (C) 2005 Associated Universities, Inc. Washington DC, USA.
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

from gbt.turtle.database                    import TurtleConnection
from gbt.turtle.database                    import SchedulingBlock
from gbt.turtle.database.SchedulingBlock    import VALID
from gbt.turtle.database                    import Project
from gbt.turtle.proc                        import Validator
from gbt.turtle.proc                        import Observation
from gbt.turtle.user                        import Telescope as uTelescope
from gbt.turtle.user                        import Catalog
from gbt.turtle.ygor                        import TSimulator as yTelescope
from gbt.turtle.ygor                        import TPlotter as yPlotTelescope
from TurtleDocument                         import TurtleDocument
from ServerEvent                            import *

import traceback
import os
import sys

class EditDocument(TurtleDocument):
    """
    Holds the state relevant to the "Edit" panel in the Turtle UI.
    """
    
    def __init__(self):
        TurtleDocument.__init__(self)

        db = Project(TurtleConnection())

        self.script           = ""
        self.fileName         = ""
        self.outputFileName   = ""
        self.project          = None
        self.activeSB         = None
        self.isScriptModified = True
        self.projects         = db.GetName2IdDictionary()

    def Run(self, script):
        if self.GetServer() is not None:
            self.GetServer().Run(script)

    def SBSort(self, a, b):
        if a.lower() == b.lower():
            return 0
        elif a.lower() > b.lower():
            return 1
        elif a.lower() < b.lower():
            return -1

    def GetSBs(self):
        project = self.GetProject()
        if project is None:
            return []

        db           = SchedulingBlock(TurtleConnection())
        self.blocks  = db.GetName2IdStatusDictionary(self.GetProjectId())
        names        = self.blocks.keys()
        names.sort(self.SBSort)

        return names

    def GetProjectId(self):
        return self.projects[self.GetProject()]

    def GetProjects(self):
        projects = self.projects.keys()
        projects.sort()
        return projects

    def GetProject(self):
        return self.project

    def SetProject(self, project):
        self.project = project 
        self.GetSBs()

    def NotifyProjectNameChange(self, project):
        for observer in self.observers:
            wxPostEvent(observer, ServerEvent(ID_PROJECT_NAME_CHANGE_EVENT, project))

    def IsSBValid(self, name):
        return self.blocks.has_key(name) and self.blocks[name][1] == VALID

    def GetActiveSBId(self):
        return self.blocks[self.GetActiveSB()][0]

    def GetActiveSBStatus(self):
        return self.blocks[self.GetActiveSB()][1]

    def GetActiveSB(self):
        return self.activeSB

    def SetActiveSB(self, name):
        self.activeSB = name

    def SetScriptModified(self, flag):
        self.isScriptModified = flag

    def IsScriptModified(self):
        return self.isScriptModified

    def Simulate(self, script, textctrl):
        # Always leave things the way you found them
        oldstdout = sys.stdout
        oldstderr = sys.stderr

        # Redirect messages to TextCtrl
        self.write = textctrl.AppendText
        sys.stdout = self
        sys.stderr = self

        # Don't forget to actually do the simulation
        ygorTelescope = yTelescope()
        userTelescope = uTelescope(ygorTelescope)
        observation   = Observation(script, globals())

        Catalog.SetUp()

        try:
            observation.Execute(userTelescope)
        except:
            print "\n"
            msgs = apply(traceback.format_exception, sys.exc_info())
            for m in msgs:
                print m

        # Resume our regularly scheduled messaging.
        sys.stdout = oldstdout
        sys.stderr = oldstderr

    def PlotBeam(self, script, textctrl):
        # Always leave things the way you found them
        oldstdout = sys.stdout
        oldstderr = sys.stderr

        # Redirect messages to TextCtrl
        self.write = textctrl.AppendText
        sys.stdout = self
        sys.stderr = self

        # Don't forget to actually do the simulation
        ygorTelescope = yPlotTelescope()
        userTelescope = uTelescope(ygorTelescope)
        observation   = Observation(script, globals())

        Catalog.SetUp()

        try:
            observation.Execute(userTelescope)
        except:
            print "\n"
            msgs = apply(traceback.format_exception, sys.exc_info())
            for m in msgs:
                print m

        # Resume our regularly scheduled messaging.
        sys.stdout = oldstdout
        sys.stderr = oldstderr
        return ygorTelescope.positions

    def IsScriptValid(self, script, textctrl):
        # Always leave things the way you found them
        oldstdout = sys.stdout
        oldstderr = sys.stderr

        # Redirect messages to TextCtrl
        self.write = textctrl.AppendText
        sys.stdout = self
        sys.stderr = self

        # Collect configuration tool info.
        validator = Validator(script)

        # Resume our regularly scheduled messaging.
        sys.stdout = oldstdout
        sys.stderr = oldstderr

        return validator.IsValid(), validator.GetError()

    def GetFileName(self):
        return self.fileName

    def GetOutputFileName(self):
        return self.outputFileName

    def SetOutputFileName(self, fileName):
        self.outputFileName = fileName

    def AddSB(self, status):
        db = SchedulingBlock(TurtleConnection())
        db.Add(self.GetActiveSB(), self.GetScript(), self.GetProject(), status)

        self.SetScriptModified(False)
        self.DatabaseChanged()

    def CopySB(self):
        db = SchedulingBlock(TurtleConnection())
        db.Copy(self.GetActiveSBId())

        self.DatabaseChanged()

    def DeleteSB(self):
        db = SchedulingBlock(TurtleConnection())
        db.Remove(self.GetActiveSBId())

        self.SetActiveSB(None)
        self.SetScriptModified(False)
        self.DatabaseChanged()

    def OpenSB(self):
        db     = SchedulingBlock(TurtleConnection())
        script = db.GetScript(self.GetActiveSBId())
        script = script[0].replace("\r", "")

        self.SetScript(script)
        self.SetScriptModified(False)

    def RenameSB(self, name):
        db = SchedulingBlock(TurtleConnection())
        db.SetName(self.GetActiveSBId(), name)

        self.SetActiveSB(name)
        self.DatabaseChanged()

    def UpdateScript(self, script, status):
        db = SchedulingBlock(TurtleConnection())
        db.SetScript(self.GetActiveSBId(), script, status)

        self.SetScript(script)
        self.SetScriptModified(False)
        self.DatabaseChanged()

    def HasScriptChanged(self, script, status):
        db = SchedulingBlock(TurtleConnection())
        id = self.GetActiveSBId()
        if script == db.GetScript(id)[0] and status == db.GetStatus(id)[0]:
            return False
        else:
            return True

    def ScriptExists(self):
        if self.GetActiveSB() in self.GetSBs():
            return True
        else:
            return False

    def OpenFile(self, fileName):
        # Remember the file name for future saves.
        self.fileName = fileName

        # Read the entire contents of the file into the script.
        f = file(self.fileName, "r")
        self.script = f.read()
        self.script = self.script.replace("\x0D", "") # strip any Ctrl-M's
        f.close()

        self.SetScriptModified(False)
        self.OnOpen()

    def SaveFile(self, fileName):
        # Remember the file name for future saves.
        self.fileName = fileName

        # Save the entire contents of the script to the named file.
        f = file(fileName, "w")
        f.write(self.script)
        f.close()

    def GetScript(self):
        return self.script

    def SetScript(self, script):
        self.script = script

        for observer in self.observers:
            wxPostEvent(observer, ServerEvent(ID_SAVE_SCRIPT_EVENT))

    def OnDatabaseChange(self):
        self.GetSBs()

        for observer in self.observers:
            wxPostEvent(observer, ServerEvent(ID_DATABASE_CHANGE_EVENT))
        
    def DatabaseChanged(self):
        if self.server:
            self.server.DatabaseChanged()
