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
#
# $Id: EditPanel.py,v 1.86 2010/11/30 15:36:42 ashelton Exp $

# DEAP imports
from   gui.framework                       import *

# Other imports
from   editor.PythonStyledTextCtrl         import PythonStyledTextCtrl
from   gbt.turtle.proc.Observation         import OBSERVING_DIRECTIVES
from   gbt.turtle.proc.Observation         import SCANTYPES
from   gbt.turtle.database.SchedulingBlock import ILLICIT
from   gbt.turtle.database.SchedulingBlock import UNKNOWN
from   gbt.turtle.database.SchedulingBlock import VALID
from   EditDocument                        import EditDocument
from   ServerEvent                         import *
from   mx                                  import DateTime
import wx.stc                              as     stc
import wx.lib.masked                       as     masked
import keyword
import os
import string
import wx
import sys

from BeamMap    import BeamMap

# Define identifiers for UI controls.
[
  # Pop-up items for sb list.
    ID_POPUP_SAVE
  , ID_POPUP_DELETE
  , ID_POPUP_RENAME
  , ID_POPUP_COPY
] = [wx.NewId() for i in range(4)]

# Add items to File menu.
[
    ID_FILE_DELETE
  , ID_FILE_EXPORT
  , ID_FILE_IMPORT
  , ID_FILE_SIMULATE
  , ID_FILE_VALIDATE
  , ID_FILE_REDO
  , ID_FILE_UNDO
] = [wx.NewId() for i in range(7)]

CONFIG_PATH = [
    os.path.expanduser("~/.sparrow")
  , os.path.join(os.environ["SPARROW_DIR"], "sparrow.conf")
]

SIMULATE_ALPHA_TESTERS = (
    "ashelton", "bgarwood", "cbignell", "dbalser", "dpisano", "fghigo",
    "jbrandt", "jharnett", "karen", "koneil", "lmorgan", "mclark", "mmccarty",
    "nradziwi", "pruffle", "rcreager", "pbrandt", "rmaddale", "mwhitehe",
    "thunter", "tminter", "monctrl", "jlockman", "pford", "mmello",
    "glangsto", "aroshi", "dfrayer", "sransom", "rrosen", "pdemores",
    "bmason", "emcnany")

class EditPanel(Panel):

    def __del__(self):
        self.GetDocument().RemoveObserver(self)

    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.access = 0

        self.InitDocument()
        self.InitUI()

    def ActivateSite(self, site):
        Panel.ActivateSite(self, site)
        self.ActivateMenus()
        self.ActivateToolbar()

    def ActivateMenus(self):
        self.ActivateFileMenu()
        self.ActivateEditMenu()

    def ActivateFileMenu(self):
        fileMnu = self.GetMenu(ID_FILE_MENU)

        fileMnu.InsertSeparator(fileMnu.GetMenuItemCount() - 2)
        fileMnu.Insert(fileMnu.GetMenuItemCount() - 2, ID_FILE_IMPORT, "&Import from File...",  "Imports a file from a directory into the editor.")
        fileMnu.Insert(fileMnu.GetMenuItemCount() - 2, ID_FILE_EXPORT, "&Export to File...",  "Exports the contents of the editor into a file.")

        fileMnu.InsertSeparator(fileMnu.GetMenuItemCount() - 2)
        # TBF: Temporarily being snobby.
        if os.environ['USER'] in SIMULATE_ALPHA_TESTERS:
            fileMnu.Insert(fileMnu.GetMenuItemCount() - 2, ID_FILE_SIMULATE, "&Simulate",  "Simulates the execution of the contents of the editor.")
        fileMnu.Insert(fileMnu.GetMenuItemCount() - 2, ID_FILE_VALIDATE, "&Validate",  "Validates the contents of the editor.")

        fileMnu.InsertSeparator(fileMnu.GetMenuItemCount() - 2)
        fileMnu.Insert(fileMnu.GetMenuItemCount() - 2, ID_FILE_DELETE, "&Delete",  "Deletes the selected scheduling block from the database.")

        wx.EVT_MENU(self.GetFrame(), ID_FILE_SAVE,     self.OnSave)
        wx.EVT_MENU(self.GetFrame(), ID_FILE_SAVE_AS,  self.OnSave)
        wx.EVT_MENU(self.GetFrame(), ID_FILE_DELETE,   self.OnDelete)
        wx.EVT_MENU(self.GetFrame(), ID_FILE_IMPORT,   self.OnImport)
        wx.EVT_MENU(self.GetFrame(), ID_FILE_EXPORT,   self.OnExport)

        # TBF: Temporarily being snobby.
        if os.environ['USER'] in SIMULATE_ALPHA_TESTERS:
            wx.EVT_MENU(self.GetFrame(), ID_FILE_SIMULATE, self.OnSimulate)
        wx.EVT_MENU(self.GetFrame(), ID_FILE_VALIDATE, self.OnValidate)

    def ActivateEditMenu(self):
        wx.EVT_MENU(
            self.GetFrame(), ID_EDIT_UNDO,   lambda e: self.editor.Undo())
        wx.EVT_MENU(
            self.GetFrame(), ID_EDIT_REDO,   lambda e: self.editor.Redo())
        wx.EVT_MENU(
            self.GetFrame(), ID_EDIT_CUT,    lambda e: self.editor.Cut())
        wx.EVT_MENU(
            self.GetFrame(), ID_EDIT_COPY,   lambda e: self.editor.Copy())
        wx.EVT_MENU(
            self.GetFrame(), ID_EDIT_PASTE,  lambda e: self.editor.Paste())
        wx.EVT_MENU(
            self.GetFrame(), ID_EDIT_DELETE, lambda e: self.editor.Cut())
        wx.EVT_MENU(
            self.GetFrame(), ID_EDIT_SELECT_ALL, lambda e: self.editor.SetSelection(0,-1))
        wx.EVT_MENU(
            self.GetFrame(), ID_EDIT_CLEAR,  lambda e: self.editor.ClearAll())

    def ActivateToolbar(self):
        toolBar = self.GetToolBar()
   
        toolBar.RemoveTool(ID_FILE_OPEN)

        toolBar.AddTool(bitmap=wx.Bitmap(self.GetImagePath('delete.bmp')),
              id=ID_FILE_DELETE, isToggle=false,
              longHelpString='', pushedBitmap=wx.Bitmap(self.GetImagePath('delete.bmp')),
              shortHelpString='Delete from database')
        toolBar.AddTool(bitmap=wx.Bitmap(self.GetImagePath('import.bmp')),
              id=ID_FILE_IMPORT, isToggle=false,
              longHelpString='', pushedBitmap=wx.Bitmap(self.GetImagePath('import.bmp')),
              shortHelpString='Import from file')
        toolBar.AddTool(bitmap=wx.Bitmap(self.GetImagePath('Export.bmp')),
              id=ID_FILE_EXPORT, isToggle=false,
              longHelpString='', pushedBitmap=wx.Bitmap(self.GetImagePath('Export.bmp')),
              shortHelpString='Export to file')
        toolBar.AddTool(bitmap=wx.Bitmap(self.GetImagePath('Undo.bmp')),
              id=ID_FILE_UNDO, isToggle=false,
              longHelpString='', pushedBitmap=wx.Bitmap(self.GetImagePath('Undo.bmp')),
              shortHelpString='Undo')
        toolBar.AddTool(bitmap=wx.Bitmap(self.GetImagePath('Redo.bmp')),
              id=ID_FILE_REDO, isToggle=false,
              longHelpString='', pushedBitmap=wx.Bitmap(self.GetImagePath('Redo.bmp')),
              shortHelpString='Redo')
        toolBar.AddTool(bitmap=wx.Bitmap(self.GetImagePath('trafficlight.bmp')),
              id=ID_FILE_VALIDATE, isToggle=false,
              longHelpString='', pushedBitmap=wx.Bitmap(self.GetImagePath('trafficlight.bmp')),
              shortHelpString='Validate')

        wx.EVT_TOOL(self.GetFrame(), ID_FILE_SAVE,     self.OnSave)
        wx.EVT_TOOL(self.GetFrame(), ID_FILE_DELETE,   self.OnDelete)
        wx.EVT_TOOL(self.GetFrame(), ID_FILE_IMPORT,   self.OnImport)
        wx.EVT_TOOL(self.GetFrame(), ID_FILE_EXPORT,   self.OnExport)
        wx.EVT_TOOL(self.GetFrame(), ID_FILE_UNDO, lambda e: self.editor.Undo())
        wx.EVT_TOOL(self.GetFrame(), ID_FILE_REDO, lambda e: self.editor.Redo())
        wx.EVT_TOOL(self.GetFrame(), ID_FILE_VALIDATE, self.OnValidate)

    def UpdateMenus(self):
        Panel.UpdateMenus(self)
        self.UpdateFileMenu()
        self.UpdateEditMenu()

    def UpdateFileMenu(self):
        self.GetMenuBar().Enable(ID_FILE_OPEN,     0)
        self.GetMenuBar().Enable(ID_FILE_SAVE,     self.access)
        self.GetMenuBar().Enable(ID_FILE_SAVE_AS,  self.access)
        self.GetMenuBar().Enable(ID_FILE_IMPORT,   1)
        self.GetMenuBar().Enable(ID_FILE_EXPORT,   1)
        self.GetMenuBar().Enable(ID_FILE_SAVE,     self.access)
        self.GetMenuBar().Enable(ID_FILE_DELETE,   self.access)

        # TBF: Temporarily being snobby.
        if os.environ['USER'] in SIMULATE_ALPHA_TESTERS:
            self.GetMenuBar().Enable(ID_FILE_SIMULATE, self.access)

        self.GetMenuBar().Enable(ID_FILE_VALIDATE, self.access)

    def UpdateEditMenu(self):
        self.GetMenuBar().Enable(ID_EDIT_UNDO,       self.editor.CanUndo())
        self.GetMenuBar().Enable(ID_EDIT_REDO,       self.editor.CanRedo())
        self.GetMenuBar().Enable(ID_EDIT_CUT,        1)
        self.GetMenuBar().Enable(ID_EDIT_COPY,       1)
        self.GetMenuBar().Enable(ID_EDIT_PASTE,      self.editor.CanPaste())
        self.GetMenuBar().Enable(ID_EDIT_DELETE,     1)
        self.GetMenuBar().Enable(ID_EDIT_SELECT_ALL, 1)
        self.GetMenuBar().Enable(ID_EDIT_CLEAR,      1)

    def InitDocument(self):
        self.document = EditDocument()
        self.document.AddObserver(self)

    def InitUI(self):
        self.splitter = wx.SplitterWindow(self, -1, style = wx.SP_3D)

        sbList = self.InitSBList(self.splitter)
        eArea  = self.InitEditorArea(self.splitter)
        sbSize = sbList.GetAdjustedBestSize()

        # Split the frame with the SB list on the left and editor on the right.
        self.splitter.SplitVertically(sbList, eArea, sbSize.width)
        self.splitter.SetMinimumPaneSize(20)
        self.splitter.Fit()

        # Hack to fix sash position of editor area splitter.
        eArea.SetSashPosition(eArea.GetWindow1().GetAdjustedBestSize().width)

        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(self.splitter, 1, wx.ALL | wx.EXPAND)

        self.SetSizer(box)
        self.SetAutoLayout(1)
        self.Fit()

    def InitEditorArea(self, parent):
        splitter = wx.SplitterWindow(parent, -1, style = wx.SP_3D)

        # The editor has the edit window and the output window.
        editorPanel = self.InitEditor(splitter)
        outputPanel = self.InitOutput(splitter)
        eWindowSize = editorPanel.GetAdjustedBestSize()
        oWindowSize = outputPanel.GetAdjustedBestSize()

        splitter.SplitVertically(editorPanel
                               , outputPanel
                               , -oWindowSize.width)
        splitter.SetMinimumPaneSize(50)

        splitter.SetSize(eWindowSize + oWindowSize)
        splitter.Fit()

        return splitter

    def InitEditor(self, parent):
        panel = wx.Panel(parent, -1)
        id    = wx.NewId()

        self.sbName = wx.StaticText(panel, -1, "")
        self.editor = PythonStyledTextCtrl(panel, id)
        self.editor.Colourise(0, -1)
        self.editor.SetMarginType(1, stc.STC_MARGIN_NUMBER)
        self.editor.SetMarginWidth(1, 25)
        self.AddTurtleKeywordsToEditor()

        self.SetText(self.GetDocument().GetScript())

        self.editor.SetModEventMask(stc.STC_MOD_INSERTTEXT | stc.STC_MOD_DELETETEXT | stc.STC_PERFORMED_USER)

        stc.EVT_STC_CHANGE(parent, id, self.OnTextChange)

        editorBox   = wx.StaticBox(panel, -1, "Editor:")
        editorSizer = wx.StaticBoxSizer(editorBox, wx.VERTICAL)
        editorSizer.Add(self.editor, 1, wx.EXPAND)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(editorSizer, 1, wx.ALL | wx.EXPAND)
        sizer.Add(self.sbName, 0, wx.ALL | wx.EXPAND)
        sizer.AddSizer(self.InitEditorButtons(panel), 0, wx.ALL | wx.EXPAND, 2)

        panel.SetSizer(sizer)
        panel.SetAutoLayout(1)
        panel.Fit()

        return panel

    def InitOutput(self, parent):
        panel       = wx.Panel(parent, -1)
        self.output = wx.TextCtrl(panel, -1,
                                  style = wx.TE_READONLY | wx.TE_MULTILINE | 
                                          wx.SUNKEN_BORDER | wx.TE_DONTWRAP)
        text        = wx.StaticText(panel, -1, "")

        box   = wx.StaticBox(panel, -1, "Validation Output:")
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        sizer.AddSizer(self.output,                   1, wx.EXPAND)
        sizer.Add(text,                               0, wx.EXPAND | wx.ALL)
        sizer.AddSizer(self.InitOutputButtons(panel), 0, wx.EXPAND | wx.ALL)

        panel.SetSizer(sizer)
        panel.SetAutoLayout(1)
        panel.Fit()

        return panel

    def AddTurtleKeywordsToEditor(self):
        kw = keyword.kwlist[:]
        for k in OBSERVING_DIRECTIVES + SCANTYPES:
            kw.append(k)
        kw.append("execfile")
        kw.append("Catalog")
        kw.append("DefineScan")
        kw.append("Location")
        kw.append("Offset")
        kw.sort()
        self.editor.SetKeyWords(0, " ".join(kw))

    def InitSBList(self, parent):
        self.sbPanel = wx.Panel(parent, -1)
        id           = wx.NewId()

        wx.EVT_MENU(self, ID_POPUP_SAVE,   self.OnSave)
        wx.EVT_MENU(self, ID_POPUP_DELETE, self.OnDelete)
        wx.EVT_MENU(self, ID_POPUP_RENAME, self.OnEditSBName)
        wx.EVT_MENU(self, ID_POPUP_COPY,   self.OnCopySB)

        self.sbList = wx.ListView(self.sbPanel, id, style = wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER | wx.LC_EDIT_LABELS)
        self.sbList.InsertColumn(0, "Scheduling Block")
        self.sbList.SetColumnWidth(0, wx.LIST_AUTOSIZE)

        wx.EVT_LIST_ITEM_SELECTED(parent,    id, self.OnSBItemActivated)
        wx.EVT_LIST_ITEM_RIGHT_CLICK(parent, id, self.OnRightClick)
        wx.EVT_LIST_END_LABEL_EDIT(parent,   id, self.OnEndLabelEdit)
        wx.EVT_RIGHT_DOWN(self.sbList, self.OnRightDown)

        vBox  = wx.StaticBox(self.sbPanel, -1, "Scheduling Blocks:")
        sizer = wx.StaticBoxSizer(vBox, wx.VERTICAL)
        sizer.Add(self.sbList, 1, wx.EXPAND)

        v2Box = wx.BoxSizer(wx.VERTICAL)
        v2Box.AddSizer(self.InitMetaFields(self.sbPanel), 0, wx.EXPAND)
        v2Box.AddSizer(sizer,                             1, wx.EXPAND)

        self.sbPanel.SetSizer(v2Box)
        self.sbPanel.SetAutoLayout(1)
        self.sbPanel.Fit()

        return self.sbPanel

    def InitMetaFields(self, parent):
        "Fields for specifying/describing the script."

        projects = self.GetProjects()
        for p in projects:
            if len(p) > 11:
                projects.remove(p)

        id = wx.NewId()
        self.projectName = \
            masked.ComboBox(parent,
                            id,
                            formatcodes = "F!V",
                            choices     = projects,
                            choiceRequired = True,
                            invalidBackgroundColour = "Red",
                            validRegex  = "(%s)" % string.join(projects,'|'),
                            autoSelect  = True)

        # Little hack to force the first autosuggestion to be alphabetized.
        self.projectName.SetSelection(0)
        self.projectName._SetValue(" ")
        # End hack

        wx.EVT_COMBOBOX(parent, id, self.OnProjectName)

        projectBox      = wx.StaticBox(parent, -1, "Project:")
        projectBoxSizer = wx.StaticBoxSizer(projectBox, wx.HORIZONTAL)
        projectBoxSizer.Add(self.projectName, 1, wx.EXPAND)

        return projectBoxSizer

    def InitEditorButtons(self, parent):
        id           = wx.NewId()
        self.saveBtn = wx.Button(parent, id, "Save to Database")
        wx.EVT_BUTTON(parent, id, self.OnSave)

        id             = wx.NewId()
        self.deleteBtn = wx.Button(parent, id, "Delete from Database")
        wx.EVT_BUTTON(parent, id, self.OnDelete)

        id             = wx.NewId()
        self.importBtn = wx.Button(parent, id, "Import from File")
        wx.EVT_BUTTON(parent, id, self.OnImport)

        id             = wx.NewId()
        self.exportBtn = wx.Button(parent, id, "Export to File")
        wx.EVT_BUTTON(parent, id, self.OnExport)

        # Disable some buttons initially.
        self.saveBtn.Enable(0)
        self.deleteBtn.Enable(0)

        # Help strings
        self.saveBtn.SetToolTipString("Saves the scheduling block to the database.")
        self.deleteBtn.SetToolTipString("Deletes the scheduling block from the database.")
        self.importBtn.SetToolTipString("Opens a text file and places contents in the editor.")
        self.exportBtn.SetToolTipString("Save contents of editor to a text file.")

        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(self.saveBtn,   0, wx.ALL, 2)
        box.Add(self.deleteBtn, 0, wx.ALL, 2)
        box.Add(self.importBtn, 0, wx.ALL, 2)
        box.Add(self.exportBtn, 0, wx.ALL, 2)

        return box

    def InitOutputButtons(self, parent):
        self.status = UNKNOWN
        trafficLight      = wx.Bitmap(os.environ["SPARROW_DIR"] + \
                                "/app/turtle/images/trafficlight-yellow.bmp")
        self.trafficLight = wx.StaticBitmap(parent, -1, trafficLight)

        id               = wx.NewId()
        self.validateBtn = wx.Button(parent, id, "Validate")
        wx.EVT_BUTTON(parent, id, self.OnValidate)

        id               = wx.NewId()
        self.simulateBtn = wx.Button(parent, id, "Simulate")
        wx.EVT_BUTTON(parent, id, self.OnPlotBeam)#OnSimulate)

        id = wx.NewId()
        self.exportOutputBtn = wx.Button(parent, id, "Export")
        wx.EVT_BUTTON(parent, id, self.OnExportOutput)

        # Disable some buttons initially.
        self.simulateBtn.Enable(0)
        self.validateBtn.Enable(0)

        # TBF: Temporarily being snobby.
        if os.environ['USER'] in SIMULATE_ALPHA_TESTERS:
            self.simulateBtn.Show(1)
        else:
            self.simulateBtn.Show(0)

        # Help strings
        self.simulateBtn.SetToolTipString("Simulates the execution of the scheduling block.")
        self.validateBtn.SetToolTipString("Checks contents of scheduling block for errors.")

        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(self.trafficLight,    0, wx.ALL | wx.ALIGN_CENTER)
        box.AddSpacer((10, 10),       0, wx.ALL)
        box.Add(self.validateBtn,     0, wx.ALL | wx.ALIGN_RIGHT, 2)
        box.Add(self.simulateBtn,     0, wx.ALL, 2)
        box.AddSpacer((10, 10),       1, wx.ALL)
        box.Add(self.exportOutputBtn, 0, wx.ALL | wx.ALIGN_CENTER, 2)

        return box

    ##############################################################
    # Event Handlers
    ##############################################################

    def OnFocus(self, event):
        pass

    def OnDefocus(self, event):
        pass

    def OnCopySB(self, event):
        if self.GetActiveSB() is None:
            msg = "There is no active scheduling block to copy."
            dlg = self.CreateMessageDialog(msg, "Copy Failed")
            dlg.ShowModal()
            dlg.Destroy()
            return

        self.GetDocument().CopySB()
        self.PopulateSBList()

    def OnDelete(self, event):
        # Remove SB from database.
        if self.GetActiveSB() is None:
            msg = "There is no active scheduling block to delete."
            dlg = self.CreateMessageDialog(msg, "Delete Failed")
            dlg.ShowModal()
            dlg.Destroy()
            return

        # Make darn sure.
        msg   = "This will permanently delete this scheduling\nblock from the database. Continue?"
        flags = wx.YES_NO | wx.NO_DEFAULT
        dlg   = self.CreateMessageDialog(msg, "Confirm Delete", flags)
        if wx.ID_NO == dlg.ShowModal():
            return # guess not.

        self.GetDocument().DeleteSB()

        # Start over.
        self.PopulateSBList()
        self.editor.ClearAll()

    def OnDocumentEvent(self, event):
        if event.GetId() == ID_DATABASE_CHANGE_EVENT:
            self.PopulateSBList()
            self.sbName.SetLabel("You are currently editing %s" % self.GetActiveSB())
        elif event.GetId() == ID_PROJECT_NAME_CHANGE_EVENT:
            self.SetActiveSB(None)
            self.UpdateProjectName(event.GetMessage())
 
    def OnEditSBName(self, event):
        self.sbList.EditLabel(self.sbList.FindItem(0, self.GetActiveSB()))

    def OnEndLabelEdit(self, event):
        self.GetDocument().RenameSB(event.GetText())

    def OnExport(self, event):
        "Ask the user for a script file to export."

        # Ensure document is up-to-date with UI.
        self.GetDocument().SetScript(self.editor.GetText())

        # Does the document already have an associated file name?
        fileName = self.GetDocument().GetFileName()

        # If so, use it for a default in the dialog.
        if fileName <> "":
            fileName = wx.FileSelector(
                "Export a Turtle file"
              , default_path     = os.path.dirname(fileName)
              , default_filename = os.path.basename(fileName)
              , flags = wx.SAVE)
        else:
            fileName = wx.FileSelector("Export a Turtle file", flags = wx.SAVE)

        if fileName <> "":
            self.GetDocument().SaveFile(fileName)

    def OnExportOutput(self, event):
        "Ask the user for a output file to export."

        # Does the document already have an associated file name?
        fileName = self.GetDocument().GetOutputFileName()

        # If so, use it for a default in the dialog.
        if fileName <> "":
            fileName = wx.FileSelector(
                "Export an output file"
              , default_path     = os.path.dirname(fileName)
              , default_filename = os.path.basename(fileName)
              , flags = wx.SAVE)
        else:
            fileName = wx.FileSelector("Export an output file", flags = wx.SAVE)

        if fileName <> "":
            self.GetDocument().SetOutputFileName(fileName)
            self.output.SaveFile(fileName)

    def OnImport(self, event):
        "Ask the user for a script file to import."
        fileName = self.GetDocument().GetFileName()
  
        # If so, use it for a default in the dialog.
        if fileName <> "":
            fileName = wx.FileSelector(
                "Open file"
              , default_path     = os.path.dirname(fileName)
              , default_filename = os.path.basename(fileName)
              , flags = wx.OPEN | wx.FILE_MUST_EXIST)
        else:
            fileName = wx.FileSelector(
                "Open file"
              , default_path = os.curdir
              , flags        = wx.OPEN | wx.FILE_MUST_EXIST)

        if fileName <> "":
            try:
                self.GetDocument().OpenFile(fileName)
            except:
                import sys
                msg = str(sys.exc_value)
                dlg = self.CreateMessageDialog(msg, "File open failed")
                dlg.ShowModal()
                dlg.Destroy()
                return

            self.SetText(self.GetDocument().GetScript())
            self.SetActiveSB(fileName.split("/")[-1].split(".")[0])
            self.SetScriptModified(True)
            self.SetStatus(UNKNOWN)

    def OnOpen(self):
        self.sbName.SetLabel("You are currently editing %s" % self.GetActiveSB())
        self.SetText(self.GetDocument().GetScript())

    def OnProjectName(self, event):
        self.SetActiveSB(None)
        project = self.projectName.GetValue().rstrip()
        self.GetDocument().NotifyProjectNameChange(project)
        if not self.IsOnline():
            self.UpdateProjectName(project)

    def UpdateProjectName(self, project):
        for i in range(self.projectName.GetCount()):
            if project == self.projectName.GetString(i).strip():
                self.projectName._SetValue(self.projectName.GetString(i))
                break

        if project in self.GetProjects():
            self.GetDocument().SetProject(project)
            self.PopulateSBList()
            self.SetAccessToFunctionality(1)
        else:
            self.sbList.DeleteAllItems()
            self.SetAccessToFunctionality(0)

    def OnRightClick(self, event):
        "Right-click menu for sb list."

        location = wx.Point(self.x, self.y) + self.sbList.GetPosition()

        menu = wx.Menu()

        menu.Append(ID_POPUP_RENAME, "Rename")
        menu.Append(ID_POPUP_COPY,   "Create Copy")
        menu.Append(ID_POPUP_SAVE,   "Save")
        menu.Append(ID_POPUP_DELETE, "Delete")

        self.PopupMenu(menu, location)

        menu.Destroy()

    def OnRightDown(self, event):
        "Catches when user presses the right-click."

        self.x = event.GetX()
        self.y = event.GetY()

        item, flags = self.sbList.HitTest((self.x, self.y))
        if flags & wx.LIST_HITTEST_ONITEM:
            self.sbList.Select(item)

        event.Skip()

    def OnSave(self, event):
        "Save script to the database."

        script = self.GetScript(event)

        if not self.CanSaveSB():
            return
        if self.status != VALID and not self.IsScriptValid(script):
            msg = "Invalid script, save anyway?"
            dlg = self.CreateMessageDialog(msg, "Question",
                                           wx.YES_NO|wx.YES_DEFAULT)
            if wx.ID_YES != dlg.ShowModal():
                dlg.Destroy()
                return
            dlg.Destroy()

        name = self.GetActiveSB() or "New Scheduling Block"
        dlg  = wx.TextEntryDialog(self,
                                 "Enter a name for your scheduling block.",
                                 "Save",
                                 name)

        if wx.ID_OK == dlg.ShowModal():
            self.SetActiveSB(dlg.GetValue())
            self.SaveScriptToDatabase(script)
            self.PopulateSBList()

        dlg.Destroy()

    def OnSBItemActivated(self, event):
        "Pulls scheduling block into editor."

        # Check to see if anything has changed. If not, move on.
        if self.GetActiveSB() == event.GetText():
            return


        # Save current scheduling block if necessary.
        if self.GetActiveSB() is not None and self.IsScriptModified():
            msg = "Save scheduling block to database?"
            dlg = self.CreateMessageDialog(msg, "Question",
                                           wx.YES_NO|wx.YES_DEFAULT)
            response = dlg.ShowModal()
            dlg.Destroy()
            if response == wx.ID_YES:
                script = self.GetScript(event)
                # TBF why does the validity have to be checked again?
                if self.status != VALID and not self.IsScriptValid(script):
                    msg = "Invalid script, save anyway?"
                    dlg = self.CreateMessageDialog(msg, "Question",
                                                   wx.YES_NO|wx.YES_DEFAULT)
                    response = dlg.ShowModal()
                    dlg.Destroy()
                    if response != wx.ID_YES:
                        return

                self.SaveScriptToDatabase(script)

        # Open new scheduling block.
        self.SetActiveSB(event.GetText())
        self.GetDocument().OpenSB()
        self.SetText(self.GetDocument().GetScript())
        self.GetDocument().SetScriptModified(False)
        if self.IsSBValid(event.GetText()):
            self.SetStatus(VALID)
        else:
            self.SetStatus(ILLICIT)

    def OnSimulate(self, event):
        self.output.AppendText("*** Begin Simulation - %s ***\n" % str(DateTime.now()))
        self.GetDocument().Simulate(self.editor.GetText(), self.output)
        self.output.AppendText("*** End Simulation - %s ***\n" % str(DateTime.now()))
        self.output.AppendText("\n\n")

    def OnPlotBeam(self, event):
        try:
            self.output.AppendText("*** Begin Plot Beam - %s ***\n" % str(DateTime.now()))
            pts = self.GetDocument().PlotBeam(self.editor.GetText(), self.output)
            # This will fail, currently, because of incompatible versions of matplotlib
            # but *should* work in theory once that is fixed
            mapper = BeamMap(pts)
            mapper.main()
            self.output.AppendText("\n\n*** End Plot Beam - %s ***\n" % str(DateTime.now()))
            self.output.AppendText("\n\n")
        except:
            exc = sys.exc_info()
            print "WHOOPS %s, %s, %s"%(exc[0],exc[1],exc[2].tb_lineno)

    def OnTextChange(self, event):
        self.SetScriptModified(True)

    def OnValidate(self, event):
        self.IsScriptValid(self.editor.GetText())

    #####################################################
    # Helper Methods
    #####################################################

    def GetDocument(self):
        return self.document

    def SetStatus(self, status):
        if status == UNKNOWN:
            bitmap = wx.Bitmap(os.environ["SPARROW_DIR"] + \
                              "/app/turtle/images/trafficlight-yellow.bmp")
        elif status == VALID:
            bitmap = wx.Bitmap(os.environ["SPARROW_DIR"] + \
                              "/app/turtle/images/trafficlight-green.bmp")
        elif status == ILLICIT:
            bitmap = wx.Bitmap(os.environ["SPARROW_DIR"] + \
                              "/app/turtle/images/trafficlight-red.bmp")
        if self.trafficLight is not None:
            self.trafficLight.SetBitmap(bitmap)
        self.status = status

    def SetActiveSB(self, name):
        self.GetDocument().SetActiveSB(name)

        if name is None:
            descrip = "nothing"
        else:
            descrip = name
        self.sbName.SetLabel("You are currently editing %s" % descrip)

    def GetActiveSB(self):
        return self.GetDocument().GetActiveSB()

    def GetProject(self):
        return self.GetDocument().GetProject()

    def GetProjectId(self):
        return self.GetDocument().GetProjectId()

    def GetProjects(self):
        return self.GetDocument().GetProjects()

    def GetSBs(self):
        return self.GetDocument().GetSBs()

    def IsSBValid(self, name):
        return self.GetDocument().IsSBValid(name)

    def GetImagePath(self, image):
        # First, check Turtle
        path = os.environ["SPARROW_DIR"] + "/app/turtle/images/" + image
        if os.path.exists(path):
            return path
        else:
            # If it isn't in turtle, must be in DEAP.
            return self.GetFrame().GetImagePath(image)

    def PopulateSBList(self):
        self.sbList.DeleteAllItems()

        i     = 0
        names = self.GetSBs()
        for s in names:
            index = self.sbList.InsertStringItem(i, s)
            if not self.IsSBValid(s):
                self.sbList.SetItemTextColour(i, wx.LIGHT_GREY)
            i += 1

        self.sbList.SetColumnWidth(0, wx.LIST_AUTOSIZE)

        if self.GetActiveSB() is not None:
            self.sbList.SetItemState(self.sbList.FindItem(0, self.GetActiveSB())
                                   , wx.LIST_STATE_SELECTED
                                   , wx.LIST_STATE_SELECTED)
            self.sbList.SetItemState(self.sbList.FindItem(0, self.GetActiveSB())
                                   , wx.LIST_STATE_FOCUSED
                                   , wx.LIST_STATE_FOCUSED)

    def GetScript(self, event):
        return self.editor.GetText()

    def SaveScriptToDatabase(self, script):
        # Is the user adding a new script?
        if not self.GetDocument().ScriptExists():
            self.GetDocument().SetScript(script)
            self.GetDocument().AddSB(self.status)
            return

        # Does the user want to overwrite a script if it has changed?
        if self.GetDocument().HasScriptChanged(script, self.status):
            self.GetDocument().UpdateScript(script, self.status)

    def SetText(self, text):
        self.editor.Clear()
        self.editor.SetText(text)
        self.editor.EmptyUndoBuffer()

    def SetAccessToFunctionality(self, enable):
        self.access = enable
        self.saveBtn.Enable(enable)
        self.deleteBtn.Enable(enable)
        self.validateBtn.Enable(enable)
        self.simulateBtn.Enable(enable)

    def SetScriptModified(self, flag):
        self.GetDocument().SetScriptModified(flag)
        if flag:
            self.SetStatus(UNKNOWN)

    def IsScriptModified(self):
        return self.GetDocument().IsScriptModified()

    def CreateMessageDialog(self, msg, title, flags = wx.OK):
        return wx.MessageDialog(self, msg, title, flags)

    def IsScriptValid(self, script):
        hasAccess = self.access
        if hasAccess:
            self.SetAccessToFunctionality(0)

        self.output.AppendText("*** Begin Validation - %s ***\n" % str(DateTime.now()))
        isValid, error = self.GetDocument().IsScriptValid(script, self.output)

        if not isValid:
            self.SetStatus(ILLICIT)
            for e in error[-4:]:
                self.output.AppendText(e + "\n")
        else:
            self.SetStatus(VALID)

        if isValid:
            self.output.AppendText("\nYour observing script is syntactically correct!\n\n")

        self.output.AppendText("*** End Validation - %s ***\n" % str(DateTime.now()))
        self.output.AppendText("\n\n")

        if hasAccess:
            self.SetAccessToFunctionality(1)

        return isValid

    def CanSaveSB(self):
        if self.GetProject() not in self.GetProjects():
            msg = "Illegal project ID. Cannot save scheduling block."
            dlg = self.CreateMessageDialog(msg, "Error")
            dlg.ShowModal()
            dlg.Destroy()
            return False
        return True

    def GoOnline(self, server):
        # Setup to receive PyRO event notifications.
        self.GetDocument().SetServer(server)
        self.Connect(
            ID_STATE_CHANGE_EVENT
          , ID_STARTBLOCK_EVENT
          , EVT_TURTLE_SERVER
          , self.OnDocumentEvent)

    def GoOffline(self):
        self.GetDocument().SetServer(None)
        self.Disconnect(
            ID_STATE_CHANGE_EVENT
          , ID_STARTBLOCK_EVENT
          , EVT_TURTLE_SERVER)
