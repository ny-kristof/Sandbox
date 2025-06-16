from PySide import QtGui, QtCore, QtWidgets
import FreeCADGui as Gui
import FreeCAD as App
import Part
import os
from SurfSense import SurfSense, MeasurementData
import SelectionPlanner
import NewMeasure


# class ImportPanel:
#     def __init__(self):
#         self.form = []
#         form = QtWidgets.QWidget()
#         form.setWindowTitle("Import file")

#         self.ProductDataPanel = Panels.ProductDataPanel.ProductDataPanel(self)
#         # Layout
#         layout = QtWidgets.QVBoxLayout()

#         # Button and Label
#         row_layout1 = QtWidgets.QVBoxLayout()
#         button1 = QtWidgets.QPushButton("Import")

#         # button1.setGeometry(200,150,100,40)
#         button1.clicked.connect(self.importFile)
#         # row_layout1.addStretch()
#         row_layout1.addWidget(button1)
#         #row_layout1.
#         layout.addLayout(row_layout1)

#         form.setLayout(layout)
#         self.form.append(form)
#         if App.ActiveDocument != None:
#             if len(App.ActiveDocument.Objects) > 0:
#                 dataform = self.ProductDataPanel.form
#                 self.form = [form, dataform]
#                 App.Console.PrintError(self.form)

#     # def accept(self):
#     #     return True

#     # def reject(self):
#     #     return True

#     # def open(filename):
#     #     doc = FreeCAD.newDocument()
#     #     doc.recompute()

#     # TODO: open a step file (Gui.runCommand('Std_Open'))
#     def importFile(self):
#         Gui.runCommand('Std_Open')
#         if Gui.ActiveDocument == None:
#             return
#         elif len(App.ActiveDocument.Objects) > 0:
#             self.ProductDataPanel.form.show()
#             # Gui.Control.closeDialog()
#             # Gui.runCommand('Sandbox_SelectDistanceCommand',0)
#             # dataform = self.ProductDataPanel.form

#             # self.update()
#             # Gui.Control.closeDialog()
#             # Gui.Control.showDialog(self.form)
#         # App.Console.PrintError(self.form)
#         # Gui.updateGui()
#         # return self.form


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
        #self.measure_model = QtGui.QStandardItemModel()
        #self.list_view.setModel(self.model)
        
        # mw = self.getMainWindow()
        # App.Console.PrintMessage(dlg)
        #form = mw.findChild(QtGui.QWidget, "TaskPanel")
        # App.Console.PrintMessage(form)
        # tool_box = form.findChild(QtGui.QToolBox, "toolbox")
        # tool_box.setCurrentIndex(0)
        
        #self.measures = []
        # form = mw.findChild(QtGui.QWidget, "TaskPanel")
        # App.Console.PrintMessage(form)
        # tool_box = form.findChild(QtGui.QToolBox, "toolbox")
        # tool_box.setCurrentIndex(0)
        # self.dialog.show()    

    def setupUi(self):
        # mw = self.getMainWindow() 
        # form = mw.findChild(QtGui.QWidget, "TaskPanel")
        # import_button = form.findChild(QtGui.QPushButton, "ImportBtn")
        #App.Console.PrintMessage(f"with findchild: {self.form.ImportBtn}")
        
        #tool_box = self.form.toolBox
        #App.Console.PrintMessage(f"self.form.ObjectName: {self.form.ImportBtn}")
        if App.ActiveDocument != None:
            if len(App.ActiveDocument.Objects) > 0:
                self.form.toolBox.setCurrentIndex(1)
            else:
                self.form.toolBox.setCurrentIndex(0)
        else:
            self.form.toolBox.setCurrentIndex(0)
        # self.form.toolBox.currentChanged.connect(lambda: App.Console.PrintMessage(tool_box.currentIndex()))

        self.new_measure.handleMeasurementHistory(self.form.Measurements)        
        # self.hideIrrelevantWidgets()


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
        #self.measures.append(1)
        #App.Console.PrintMessage(f"Mérések: {self.measures}")
        #path =  os.path.join(self.loc, "UI\\NewMeasure.ui")
        # measure_widget = Gui.PySideUic.loadUi(path)
        # Layout
        measure_widget = self.new_measure.form
        self.form.ExtraLayout.addWidget(measure_widget)
        self.form.toolBox.hide()
        measure_widget.show()
        # Button and Label
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


# -*- coding: utf-8 -*-
# causes an action to the mouse click on an object
# This function remains resident (in memory) with the function "addObserver(s)"
# "removeObserver(s) # Uninstalls the resident function
class SurfSenseSelObserver:
    def __init__(self, m_widget):
        measure_widget = m_widget
        self.list_view = measure_widget.SelectedObjects
        self.model = QtGui.QStandardItemModel()
        self.list_view.setModel(self.model)
        #self.addSelectedItemToSelection()

    def setPreselection(self,doc,obj,sub):                # Preselection object
        
        App.Console.PrintMessage("setPreselection" + str(sub)+ "\n")          # The part of the object name

    def addSelection(self,doc,obj,sub,pnt):               # Selection object
        App.Console.PrintMessage("add"+ "\n")
        App.Console.PrintMessage(str(doc)+ "\n")          # Name of the document
        App.Console.PrintMessage(str(obj)+ "\n")          # Name of the object
        App.Console.PrintMessage(str(sub)+ "\n")          # The part of the object name
        App.Console.PrintMessage(str(pnt)+ "\n")          # Coordinates of the object
        App.Console.PrintMessage("______"+ "\n")
        self.model.clear()
        self.addSelectedItemToSelection()



    def removeSelection(self,doc,obj,sub):                # Remove the selection
        App.Console.PrintMessage("remove"+ "\n")
        self.model.clear()
        self.addSelectedItemToSelection()

    def setSelection(self,doc):                           # Set selection
        App.Console.PrintMessage("set"+ "\n")

    def clearSelection(self,doc):                         # If click on the screen, clear the selection
        App.Console.PrintMessage("clear"+ "\n")           # If click on another object, clear the previous object
        self.model.clear()


    def addSelectedItemToSelection(self):
        self.model.clear()
        sel = Gui.Selection.getSelectionEx()
        if len(sel):
            for idx, obj in enumerate(sel[0].SubElementNames):
                message = f"{idx + 1} - {obj}"
                item = QtGui.QStandardItem(message)
                self.model.appendRow(item)


# s = SelObserver()
# Gui.Selection.addObserver(s)                       # install the function mode resident
#FreeCADGui.Selection.removeObserver(s)                   # Uninstall the resident function

