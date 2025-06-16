import PySide6
from PySide6 import QtCore, QtGui, QtWidgets
import FreeCAD as App
import FreeCADGui
import os
import SelObserver
import SelectDistanceTaskPanel
import SectionPanel
import SurfSensePanel

__dir__ = os.path.dirname(__file__)
observer = None

# FreeCAD Command made with a Python script
def MakeBox():
    doc = App.ActiveDocument
    box =  doc.addObject("Part::Box",'box')
    box.Length = 1
    box.Width  = 1
    box.Height = 1

# GUI command that links the Python script
class _MakeBoxCmd:
    """Command to create a box"""
    
    def Activated(self):
        # what is done when the command is clicked
        MakeBox()

    def GetResources(self):
        # icon and command information
        MenuText = QtCore.QT_TRANSLATE_NOOP(
            'Sandbox_Box',
            'Box')
        ToolTip = QtCore.QT_TRANSLATE_NOOP(
            'Sandbox_Box',
            'Creates a new box')
        return {
            'Pixmap': __dir__ + '/icons/sandbox_makebox_cmd.svg',
            'MenuText': MenuText,
            'ToolTip': ToolTip}

    def IsActive(self):
        # The command will be active if there is an active document
        return not App.ActiveDocument is None

FreeCADGui.addCommand('Sandbox_MakeBox', _MakeBoxCmd())

class AddObserverCommand: 
    def Activated(self):
        global observer
        if observer is None:
            observer = SelObserver.SelObserver()
            FreeCADGui.Selection.addObserver(observer)
            print("Selection observer added.")
        else:
            print("Observer already added.")

    def IsActive(self):
        global observer
        return observer is None

    def GetResources(self):
        # icon and command information
        MenuText = QtCore.QT_TRANSLATE_NOOP(
            'Sandbox_Box',
            'Add Observer')
        ToolTip = QtCore.QT_TRANSLATE_NOOP(
            'Sandbox_Box',
            'Adds a selection observer')
        return {
            'Pixmap': __dir__ + '/icons/play.svg',
            'MenuText': MenuText,
            'ToolTip': ToolTip}

FreeCADGui.addCommand('Sandbox_AddObserver', AddObserverCommand())

class RemoveObserverCommand:
    def Activated(self):
        global observer
        if observer is not None:
            FreeCADGui.Selection.removeObserver(observer)
            observer = None
            print("Selection observer removed.")
        else:
            print("Observer already removed.")

    def IsActive(self):
        global observer
        return observer is not None

    def GetResources(self):
        # icon and command information
        MenuText = QtCore.QT_TRANSLATE_NOOP(
            'Sandbox_Box',
            'Remove Observer')
        ToolTip = QtCore.QT_TRANSLATE_NOOP(
            'Sandbox_Box',
            'Removes a selection observer')
        return {
            'Pixmap': __dir__ + '/icons/stop.svg',
            'MenuText': MenuText,
            'ToolTip': ToolTip}

FreeCADGui.addCommand('Sandbox_RemoveObserver', RemoveObserverCommand())

class AddClippingPlaneToFaceCommand:
    def GetResources(self):
        return {
            'MenuText': "Add Clipping Plane to Face",
            'ToolTip': "Adds a clipping plane aligned to the selected face",
            'Pixmap': __dir__ + '/icons/CrossSections.svg'  # Optional: add an icon path
        }

    def IsActive(self):
        return FreeCADGui.ActiveDocument is not None

    def Activated(self):
        sel = FreeCADGui.Selection.getSelectionEx()
        if not sel or not sel[0].SubObjects:
            App.Console.PrintMessage("No face selected.\n")
            return

        face = None
        for sub in sel[0].SubObjects:
            if sub.ShapeType == "Face":
                face = sub
                break

        if face is None:
            App.Console.PrintMessage("Please select a face.\n")
            return

        # Compute the center of the face and normal
        center = face.CenterOfMass
        try:
            normal = face.normalAt(0.5, 0.5)
        except:
            App.Console.PrintMessage("Could not compute face normal.\n")
            return

        # Add the clipping plane
        view = FreeCADGui.ActiveDocument.ActiveView
        view.addClippingPlane(center, normal)

        App.Console.PrintMessage(f"Clipping plane added at {center} with normal {normal}\n")
        
FreeCADGui.addCommand('Sandbox_AddClippingPlaneToFaceCommand', AddClippingPlaneToFaceCommand())

class SelectDistanceCommand:
    def GetResources(self):
        return {'Pixmap':  __dir__ + '/icons/idm_systems_zrt_logo.svg',
                'MenuText': 'Select Distance',
                'ToolTip': 'Select 2 entities to highlight the features to measure'}

    def Activated(self):
        task_panel = SelectDistanceTaskPanel.SelectDistanceTaskPanel()
        FreeCADGui.Control.showDialog(task_panel)

    def IsActive(self):
        return True
        
FreeCADGui.addCommand('Sandbox_SelectDistanceCommand', SelectDistanceCommand())


class SurfSenseCommand:
    def GetResources(self):
        return {'Pixmap': ':/icons/Std_ToggleVisibility.svg',
                'MenuText': 'SurfSense',
                'ToolTip': 'General command for Surface scan'}

    def Activated(self):
        surfsense_panel = SurfSensePanel.SurfSensePanel(__dir__)
        FreeCADGui.Control.showDialog(surfsense_panel)
        surfsense_panel.setupUi()
        surfsense_panel.initConnections()

    def IsActive(self):
        return True
        
FreeCADGui.addCommand('Sandbox_SurfSenseCommand', SurfSenseCommand())

class RestartFreeCADCommand:
    def GetResources(self):
        return {'Pixmap':  __dir__ + '/icons/stop.svg',
                'MenuText': 'Restart FreeCAD',
                'ToolTip': 'Restart FreeCAD'}

    def Activated(self):
        """Shuts down and restarts FreeCAD"""
        args = QtWidgets.QApplication.arguments()[1:]
        if FreeCADGui.getMainWindow().close():
            QtCore.QProcess.startDetached(
                QtWidgets.QApplication.applicationFilePath(), args
            )

    def IsActive(self):
        return True

FreeCADGui.addCommand('Sandbox_RestartFreeCADCommand', RestartFreeCADCommand())

class MakeSectionCommand:
    def GetResources(self):
        return {
            'Pixmap': __dir__ + '/icons/CrossSections.svg',
            'MenuText': 'Make Section',
            'ToolTip': 'Creates a section of the selected object'
        }

    def Activated(self):
        # sel = FreeCADGui.Selection.getSelectionEx()
        # if not sel:
        #     App.Console.PrintMessage("No object selected.\n")
        #     return

        # obj = sel[0]
        # subObjects = obj.SubObjects
        # if not subObjects:
        #     App.Console.PrintMessage("Selected object has no sub-objects.\n")
        #     return
        # for sub in subObjects:
        #     if not (sub.ShapeType == "Face" and type(sub.Surface).__name__ == "Cylinder"):
        #         QtWidgets.QMessageBox.information(None, "Error", "Please select cylinders to section") # type: ignore
        #         return
        # axis = subObjects[0].Surface.Axis
        # if not axis:
        #     App.Console.PrintMessage("Selected object does not have a valid axis.\n")
        #     return
        # for sub in subObjects:
        #     if not sub.Surface.Axis.cross(axis).Length < 1e-7:
        #         QtWidgets.QMessageBox.information(None, "Error", "Please select cylinders that has the same axis") # type: ignore
        #         return
            
        task_panel = SectionPanel.SectionPanel()
        FreeCADGui.Control.showDialog(task_panel)
        

        
        # if not hasattr(obj, 'Shape'):
        #     App.Console.PrintMessage("Selected object does not have a shape.\n")
        #     return

    def IsActive(self):
        return True
    
FreeCADGui.addCommand('Sandbox_MakeSectionCommand', MakeSectionCommand())

class RunCreateSketchCommand:
    def GetResources(self):
        return {
            'Pixmap': __dir__ + '/icons/SketcherWorkbench.svg',
            'MenuText': 'Run Create Sketch',
            'ToolTip': 'Runs the Create Sketch command'
        }

    def Activated(self):
        FreeCADGui.runCommand('Sketcher_NewSketch')

    def IsActive(self):
        return True

FreeCADGui.addCommand('Sandbox_RunCreateSketchCommand', RunCreateSketchCommand())