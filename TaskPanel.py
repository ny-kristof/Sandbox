from PySide6 import QtWidgets
import FreeCADGui
import FreeCAD
import Part
import SelectionPlanner
import xml.etree.ElementTree as ET

class TaskPanel:
    def __init__(self):
        self.form = QtWidgets.QWidget()
        self.Planner = SelectionPlanner.SelectionPlanner(self)

        # Layout
        layout = QtWidgets.QVBoxLayout()

        # Button and Label
        row_layout1 = QtWidgets.QHBoxLayout()
        label1 = QtWidgets.QLabel("Measure one edge: ")
        button1 = QtWidgets.QPushButton("Get measurement")
        button1.clicked.connect(self.Planner.getElementsFromSelection)
        row_layout1.addWidget(label1)
        row_layout1.addStretch()
        row_layout1.addWidget(button1)
        layout.addLayout(row_layout1)
        
        # Button and Label
        row_layout2 = QtWidgets.QHBoxLayout()
        label2 = QtWidgets.QLabel("Measure two parallel planes: ")
        button2 = QtWidgets.QPushButton("Get measurement")
        button2.clicked.connect(self.Planner.getElementsFromSelection)
        row_layout2.addWidget(label2)
        row_layout2.addStretch()
        row_layout2.addWidget(button2)
        layout.addLayout(row_layout2)
        
        # Button and Label
        row_layout3 = QtWidgets.QHBoxLayout()
        label3 = QtWidgets.QLabel("Measure two parallel edges: ")
        button3 = QtWidgets.QPushButton("Get measurement")
        button3.clicked.connect(self.Planner.getElementsFromSelection)
        row_layout3.addWidget(label3)
        row_layout3.addStretch()
        row_layout3.addWidget(button3)
        layout.addLayout(row_layout3)
        
        
        #Textbox do display information
        self.textbox = QtWidgets.QTextEdit()
        self.textbox.setReadOnly(True)
        layout.addWidget(self.textbox)
        
        
        self.form.setLayout(layout)
        
        self.dimensions = []

    

    def accept(self):
        tree = ET.ElementTree(self.Planner.root_node)
        tree.write("C:\\Users\\nyomarkay.kristof\\Documents\\SurfSense\\measurements.xml", encoding="utf-8", xml_declaration=True)
        for dim in self.dimensions:
            FreeCAD.ActiveDocument.removeObject(dim.Name)
        return True

    def reject(self):
        for dim in self.dimensions:
            FreeCAD.ActiveDocument.removeObject(dim.Name)
        return True
        
    
