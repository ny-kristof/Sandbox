import FreeCADGui as Gui

class SandboxWorkbench (Workbench): #type: ignore
    """Basic 1 workbench object"""
    # this is the icon in XPM format 16x16 pixels
    Icon = """
    /* XPM */
    static char * basic1_xpm[] = {
    "16 16 5 1",
    " 	c None",
    ".	c #FFFFFF",
    "+	c #000000",
    "@	c #7F4F00",
    "#	c #FFBF00",
    "................",
    "...++++++++++++.",
    "..+@#########++.",
    ".+@#########+@+.",
    ".+++++++++++@#+.",
    ".+#########+##+.",
    ".+###++####+##+.",
    ".+####+####+##+.",
    ".+####+####+##+.",
    ".+####+####+##+.",
    ".+####+####+##+.",
    ".+####+####+##+.",
    ".+###+++###+#@+.",
    ".+#########+@+..",
    ".++++++++++++...",
    "................"};
    """
    # Icon = __dir__ + '/icons/idm_systems_zrt_logo.svg'

    MenuText = "Sandbox"
    ToolTip = "Sandbox workbench"

    def Initialize(self) :
        "This function is executed when FreeCAD starts"
        from PySide6 import QtCore, QtGui
        # python file where the commands are:
        import SandboxGui
        # list of commands, only one (it is in the imported SandboxGui):
        # cmdlist = [ "Sandbox_MakeBox", "Sandbox_AddObserver", "Sandbox_RemoveObserver", "Sandbox_AddClippingPlaneToFaceCommand", "Sandbox_SelectDistanceCommand"]
        cmdlist = ["Sandbox_SelectDistanceCommand", "Sandbox_RestartFreeCADCommand", "Sandbox_MakeSectionCommand", "Sandbox_RunCreateSketchCommand"]
        self.appendToolbar(
            str(QtCore.QT_TRANSLATE_NOOP("Sandbox", "Sandbox")), cmdlist)
        self.appendMenu(
            str(QtCore.QT_TRANSLATE_NOOP("Sandbox", "Sandbox")), cmdlist)

        Log ('Loading Sandbox module... done\n') # type: ignore

    def GetClassName(self):
        return "Gui::PythonWorkbench"
        
    # def getIcon(self):
        # return __dir__ + '/icons/idm_systems_zrt_logo.svg'

# The workbench is added:
Gui.addWorkbench(SandboxWorkbench())