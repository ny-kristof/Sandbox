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
        from PySide import QtCore, QtGui
        import FreeCAD as App
        import os
        import SurfSensePanel
        # python file where the commands are:
        import SandboxGui
        # list of commands, only one (it is in the imported SandboxGui):
        # cmdlist = [ "Sandbox_MakeBox", "Sandbox_AddObserver", "Sandbox_RemoveObserver", "Sandbox_AddClippingPlaneToFaceCommand", "Sandbox_SelectDistanceCommand"]
        cmdlist = ["Sandbox_SelectDistanceCommand", "Sandbox_RestartFreeCADCommand", "Sandbox_MakeSectionCommand", "Sandbox_RunCreateSketchCommand", "Sandbox_SurfSenseCommand"]
        self.appendToolbar(
            str(QtCore.QT_TRANSLATE_NOOP("Sandbox", "Sandbox")), cmdlist)
        self.appendMenu(
            str(QtCore.QT_TRANSLATE_NOOP("Sandbox", "Sandbox")), cmdlist)

        vm = QtGui.QDockWidget()
        
        path = os.path.join(os.getenv('APPDATA'), "FreeCAD\\Mod\\Sandbox")
        surfsense_panel = SurfSensePanel.SurfSensePanel(path)
        vm.setWidget(surfsense_panel.form)

        surfsense_panel.setupUi()
        surfsense_panel.initConnections()

        vm.setObjectName("SurfSensePanel")
        vm.setWindowTitle("SurfSense")
        mw = Gui.getMainWindow()
        # vm.setFloating(True)
        # vm.setGeometry(vm.x(), vm.y(), 200, 300)
        mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, vm)
        tabs = App.ParamGet("User parameter:BaseApp/Preferences/Mod/BIM").GetString("BimViewTabs", "")
        # App.Console.PrintMessage(f"found: {App.ParamGet('User parameter:BaseApp/Preferences').GetGroups()} \n")
        # App.Console.PrintMessage(f"found: {App.ParamGet('User parameter:BaseApp/Preferences/MainWindow').IsEmpty()} \n")
        if tabs:
            tabs = tabs.split("+")
            for tab in tabs:
                dw = mw.findChild(QtGui.QDockWidget, tab)
                
                if dw:
                    mw.tabifyDockWidget(dw, vm)
                    break
        
        vm.show()
        vm.raise_()

        Log ('Loading Sandbox module... done\n') # type: ignore

    def GetClassName(self):
        return "Gui::PythonWorkbench"
        
    # def getIcon(self):
        # return __dir__ + '/icons/idm_systems_zrt_logo.svg'

# The workbench is added:
Gui.addWorkbench(SandboxWorkbench())