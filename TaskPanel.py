from PySide6 import QtWidgets
import FreeCADGui
import FreeCAD
import Part
import SelectionPlanner
import CSExporter
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

        # Button and Label
        row_layout4 = QtWidgets.QHBoxLayout()
        label4 = QtWidgets.QLabel("Measure two parallel circles: ")
        button4 = QtWidgets.QPushButton("Get measurement")
        button4.clicked.connect(self.Planner.getElementsFromSelection)
        row_layout4.addWidget(label4)
        row_layout4.addStretch()
        row_layout4.addWidget(button4)
        layout.addLayout(row_layout4)

        # Button and Label for Plane and Line measurement
        row_layout5 = QtWidgets.QHBoxLayout()
        label5 = QtWidgets.QLabel("Measure Plane and Line: ")
        button5 = QtWidgets.QPushButton("Get measurement")
        button5.clicked.connect(self.Planner.getElementsFromSelection)
        row_layout5.addWidget(label5)
        row_layout5.addStretch()
        row_layout5.addWidget(button5)
        layout.addLayout(row_layout5)

        # Button and Label for extracting all faces to XML
        row_layout6 = QtWidgets.QHBoxLayout()
        label6 = QtWidgets.QLabel("Export whole Part to XML: ")
        button6 = QtWidgets.QPushButton("Export")
        button6.clicked.connect(lambda: self.Planner.sampleEveryFaceOnObject(FreeCADGui.Selection.getSelection()[0]))
        row_layout6.addWidget(label6)
        row_layout6.addStretch()
        row_layout6.addWidget(button6)
        layout.addLayout(row_layout6)

        #Button and Label for exporting selected coordinate systems to XML
        row_layout7 = QtWidgets.QHBoxLayout()
        label7 = QtWidgets.QLabel("Export selected coordinate systems to XML: ")
        button7 = QtWidgets.QPushButton("Export")
        button7.clicked.connect(lambda: CSExporter.add_selected_LCS_to_xml(self.Planner.root_node))
        row_layout7.addWidget(label7)
        row_layout7.addStretch()
        row_layout7.addWidget(button7)
        layout.addLayout(row_layout7)

        #Textbox do display information
        self.textbox = QtWidgets.QTextEdit()
        self.textbox.setReadOnly(True)
        layout.addWidget(self.textbox)
        
        
        self.form.setLayout(layout)
        
        self.dimensions = []

    

    def accept(self):
        # CSExporter.add_coordinate_systems_to_xml(self.Planner.root_node)
        tree = ET.ElementTree(self.Planner.root_node)
        tree.write("C:\\Users\\nyomarkay.kristof\\Documents\\SurfSense\\measurements.xml", encoding="utf-8", xml_declaration=True)
        for dim in self.dimensions:
            FreeCAD.ActiveDocument.removeObject(dim.Name)
        return True

    def reject(self):
        for dim in self.dimensions:
            FreeCAD.ActiveDocument.removeObject(dim.Name)
        return True
        
    
