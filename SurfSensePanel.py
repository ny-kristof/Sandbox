from PySide import QtGui, QtCore, QtWidgets
import FreeCADGui as Gui
import FreeCAD as App
import Part
import os
from SurfSense import SurfSense, MeasurementData
import SelectionPlanner
import NewMeasure


class SurfSensePanel:
    def __init__(self, loc):
        # dlg =  os.path.join(loc, "SurfSenseHorizontal.ui")
        dlg =  os.path.join(loc, "UI\\SurfSenseVertical.ui")
        self.loc = loc
        self.form = Gui.PySideUic.loadUi(dlg)
        self.surf_sense = SurfSense(self)
        self.new_measure = NewMeasure.NewMeasure(self, loc)
        self.selection_planner = SelectionPlanner.SelectionPlanner(self.new_measure.form)
        self.selObserver = SurfSenseSelObserver(self.new_measure.form)
        self.list_view = self.form.MeasurementsListView


    def setupUi(self):
        if App.ActiveDocument != None:
            if len(App.ActiveDocument.Objects) > 0:
                self.form.toolBox.setCurrentIndex(1)
            else:
                self.form.toolBox.setCurrentIndex(0)
        else:
            self.form.toolBox.setCurrentIndex(0)
        
        self.new_measure.handleMeasurementHistory(self.form.Measurements)        
        


    def initConnections(self):
        self.form.ImportBtn.clicked.connect(self.importModel)
        self.form.NewMeasureBtn.clicked.connect(self.openNewMeasure)
        #TODO add eventslisteners to radio buttons


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
        self.new_measure.setupFormalityComboBox()
        self.new_measure.handleMeasurementHistory(measure_widget.Measurements)
                    
        Gui.Selection.addObserver(self.selObserver)
        self.selObserver.addSelectedItemToSelection()
       

    def closeMeasureWidget(self, measure_widget):
        self.form.ExtraLayout.removeWidget(measure_widget)
        measure_widget.hide()
        self.form.toolBox.show()
        Gui.Selection.removeObserver(self.selObserver)

    def hideIrrelevantWidgets(self):
        pass


    def resetMeasurementWidget(self, combo_box):
        pass


 
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

    def setPreselection(self,doc,obj,sub):                                    # Preselection object
        App.Console.PrintMessage("setPreselection" + str(sub)+ "\n")          # The part of the object name

    def addSelection(self,doc,obj,sub,pnt):                                   # Selection object
        App.Console.PrintMessage("add"+ "\n")
        App.Console.PrintMessage(str(doc)+ "\n")                              # Name of the document
        App.Console.PrintMessage(str(obj)+ "\n")                              # Name of the object
        App.Console.PrintMessage(str(sub)+ "\n")                              # The part of the object name
        App.Console.PrintMessage(str(pnt)+ "\n")                              # Coordinates of the object
        App.Console.PrintMessage("______"+ "\n")
        self.addSelectedItemToSelection()



    def removeSelection(self,doc,obj,sub):                                    # Remove the selection
        App.Console.PrintMessage("remove"+ "\n")
        self.model.clear()
        self.addSelectedItemToSelection()

    def setSelection(self,doc):                                               # Set selection
        App.Console.PrintMessage("set"+ "\n")

    def clearSelection(self,doc):                                             # If click on the screen, clear the selection
        App.Console.PrintMessage("clear"+ "\n")                               # If click on another object, clear the previous object
        self.model.clear()


    def addSelectedItemToSelection(self):
        self.model.clear()
        sel = Gui.Selection.getSelectionEx()
        if len(sel):
            for idx, obj in enumerate(sel[0].SubElementNames):
                message = f"{idx + 1} - {obj}"
                item = QtGui.QStandardItem(message)
                self.model.appendRow(item) 
