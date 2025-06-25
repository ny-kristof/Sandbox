from PySide import QtGui, QtCore, QtWidgets
import FreeCADGui as Gui
import FreeCAD as App
import Part
import os
from SurfSense import SurfSense
import SelectionPlanner
import NewMeasure
import CSExporter
import xml.etree.ElementTree as ET


class SurfSensePanel(QtWidgets.QWidget):
    _measurement_count = 0
    def __init__(self, loc, parent=None):
        super().__init__(parent)
        # dlg =  os.path.join(loc, "SurfSenseHorizontal.ui")
        dlg =  os.path.join(loc, "UI\\SurfSenseVertical.ui")
        self.loc = loc
        self.form = Gui.PySideUic.loadUi(dlg)
        self.surf_sense = SurfSense(self)
        self.list_widget = self.form.MeasurementsListWidget
        self.new_measure = NewMeasure.NewMeasure(self, loc)
        self.selection_planner = SelectionPlanner.SelectionPlanner(self.new_measure.form)
        self.selObserver = SurfSenseSelObserver(self.new_measure.form)


    def setupUi(self):
        if App.ActiveDocument != None:
            if len(App.ActiveDocument.Objects) > 0:
                self.form.toolBox.setCurrentIndex(1)
            else:
                self.form.toolBox.setCurrentIndex(0)
        else:
            self.form.toolBox.setCurrentIndex(0)
        
        self.new_measure.handleMeasurementHistory(self.form.Measurements)
        icon = QtGui.QIcon(os.path.join(self.loc, "icons\\plus_sign.svg"))
        self.form.AddSensor.setIcon(icon)
        self.handleMeasurementSaveButtonState()
        
    
    def initConnections(self):
        self.form.ImportBtn.clicked.connect(self.importModel)
        self.form.NewMeasureBtn.clicked.connect(self.openNewMeasure)
        self.form.FinishMeasure.clicked.connect(self.saveMeasurementsToXML)
        self.list_widget.model().rowsInserted.connect(self.handleMeasurementSaveButtonState)
        self.list_widget.model().rowsRemoved.connect(self.handleMeasurementSaveButtonState)
        self.form.MatteButton.clicked.connect(self.handleProductDataReflectionAbilityButtons)
        self.form.GlossyButton.clicked.connect(self.handleProductDataReflectionAbilityButtons)
        self.form.RobotButton.clicked.connect(self.handleKinematicsButtons)
        self.form.ManipulatorButton.clicked.connect(self.handleKinematicsButtons)
        QtWidgets.QApplication.instance().installEventFilter(self)


    def importModel(self):
        Gui.runCommand('Std_Open')
        if Gui.ActiveDocument == None:
            return
        elif len(App.ActiveDocument.Objects) > 0:
            self.form.toolBox.setCurrentIndex(1)

    def openNewMeasure(self):
        measure_widget = self.new_measure.form
        self.form.ExtraLayout.addWidget(measure_widget)
        self.form.toolBox.hide()
        measure_widget.show()
        self.new_measure.setupMeasureTypeCombobox()
        self.new_measure.resetMeasurementWidget()
        self.new_measure.handleMeasurementHistory(measure_widget.Measurements)
                            
        Gui.Selection.addObserver(self.selObserver)
        self.selObserver.addSelectedItemToSelection()
       

    def closeMeasureWidget(self, measure_widget):
        self.form.ExtraLayout.removeWidget(measure_widget)
        measure_widget.hide()
        self.form.toolBox.show()
        Gui.Selection.removeObserver(self.selObserver)


    def handleMeasurementSaveButtonState(self):
        finish_button = self.form.FinishMeasure 
        if len(self.surf_sense.getMeasurements()) > 0:
            finish_button.setDisabled(False)
            finish_button.setToolTip("")
        else:
            finish_button.setDisabled(True)
            finish_button.setToolTip("There isn't any finished measurement")


    def handleProductDataReflectionAbilityButtons(self, checked):
        if checked == False:
            self.surf_sense.setReflectionAbility(None)
            return
        sender = self.sender()
        if sender is self.form.MatteButton:
            self.form.GlossyButton.setChecked(False)
            self.surf_sense.setReflectionAbility("Matte")

        elif sender is self.form.GlossyButton:
            self.form.MatteButton.setChecked(False)
            self.surf_sense.setReflectionAbility("Glossy")



    def handleKinematicsButtons(self, checked):
        if checked == False:
            self.surf_sense.setKinematics(None)
            return
        sender = self.sender()
        if sender is self.form.RobotButton:
            self.form.ManipulatorButton.setChecked(False)
            self.surf_sense.setReflectionAbility("Robot")

        elif sender is self.form.ManipulatorButton:
            self.form.RobotButton.setChecked(False)
            self.surf_sense.setReflectionAbility("Manipulator")
        

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
            pos = event.globalPosition().toPoint()  # For PySide6

            # Handle self.list_widget
            widget_pos = self.list_widget.mapFromGlobal(pos)
            item = self.list_widget.itemAt(widget_pos)
            if self.list_widget.rect().contains(widget_pos) and item is None:
                if self.list_widget.selectedItems():
                    self.list_widget.clearSelection()
                    Gui.Selection.clearSelection()

            # Handle new_measure.list_widget
            new_widget_pos = self.new_measure.list_widget.mapFromGlobal(pos)
            new_item = self.new_measure.list_widget.itemAt(new_widget_pos)
            if self.new_measure.list_widget.rect().contains(new_widget_pos) and new_item is None:
                if self.new_measure.list_widget.selectedItems():
                    self.new_measure.list_widget.clearSelection()
                    Gui.Selection.clearSelection()

        return super().eventFilter(obj, event)


    def saveMeasurementsToXML(self):
            try:
                CSExporter.add_coordinate_systems_to_xml(self.selection_planner.root_node)
                tree = ET.ElementTree(self.selection_planner.root_node)
                #App.Console.PrinteMessage(f"tree: {tree}")
                tree.write("C:\\Users\\KaszaZsolt\\Documents\\SurfSense\\measurements.xml", encoding="utf-8", xml_declaration=True)
                # for dim in self.dimensions:
                #     App.ActiveDocument.removeObject(dim.Name)
                App.Console.PrintMessage("File saved succesfully")
            except:
                App.Console.PrintError("Failed to save the measurements")


 
class SurfSenseSelObserver:
    """
    causes an action to the mouse click on an object
    This function remains resident (in memory) with the function "addObserver(s)"
    "removeObserver(s) # Uninstalls the resident function
    """
    def __init__(self, m_widget):
        measure_widget = m_widget
        self.list_view = measure_widget.SelectedObjects
        self.model = QtGui.QStandardItemModel()
        self.list_view.setModel(self.model)


    def setPreselection(self,doc,obj,sub):                                      # Preselection object
        pass
        # App.Console.PrintMessage("setPreselection" + str(sub)+ "\n")          # The part of the object name


    def addSelection(self,doc,obj,sub,pnt):                                   # Selection object
        # App.Console.PrintMessage("add"+ "\n")
        # App.Console.PrintMessage(str(doc)+ "\n")                              # Name of the document
        # App.Console.PrintMessage(str(obj)+ "\n")                              # Name of the object
        # App.Console.PrintMessage(str(sub)+ "\n")                              # The part of the object name
        # App.Console.PrintMessage(str(pnt)+ "\n")                              # Coordinates of the object
        # App.Console.PrintMessage("______"+ "\n")
        self.addSelectedItemToSelection()


    def removeSelection(self,doc,obj,sub):                                    # Remove the selection
        # App.Console.PrintMessage("remove"+ "\n")
        self.model.clear()
        self.addSelectedItemToSelection()


    def setSelection(self,doc):                                               # Set selection
        return
        App.Console.PrintMessage("set"+ "\n")


    def clearSelection(self,doc):
        #App.Console.PrintMessage("clear"+ "\n")                               # If click on another object, clear the previous object
        self.model.clear()


    def addSelectedItemToSelection(self, doc=None, obj1=None, sub=None):
        self.model.clear()
        sel = Gui.Selection.getSelectionEx()
        if len(sel):
            for i in range(len(sel)):
                for idx, obj in enumerate(sel[i].SubElementNames):
                    message = f"{idx + 1} - {obj}"
                    item = QtGui.QStandardItem(message)
                    self.model.appendRow(item) 
