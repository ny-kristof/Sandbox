from PySide import QtWidgets
from enum import Enum
import FreeCADGui as Gui
import FreeCAD as App
import Part
import SectionSelObserver

class SectionPanel:
    def __init__(self):
        Gui.Selection.clearSelection()
        Gui.Selection.removeSelectionGate()
        self.form = QtWidgets.QWidget()
        self.sel_observer = SectionSelObserver.SectionSelObserver(self)
        Gui.Selection.addObserver(self.sel_observer)
        Gui.Selection.addSelectionGate("SELECT Part::Feature SUBELEMENT Face")
        self.basePlane = None
        self.toSection = None
        self.state = self.TaskState.SELECT_BASE_PLANE
        self.isFaceSelected = False



        #self.instructionLabel = QtWidgets.QLabel("Select a base plane.")
        # sel = Gui.Selection.getSelectionEx()[0]
        # self.object = sel.Object
        # selectedFace = sel.SubObjects[0]
        # self.base_color = sel.Object.ViewObject.DiffuseColor[0] if sel.Object.ViewObject.DiffuseColor else (0.5, 0.5, 0.5)
        # self.setColorOfSelectedFaces(sel, (1.0, 0.0, 0.0), self.base_color)

        layout = self.createSelectBaseLayout()
        self.form.setLayout(layout)

        
    

    def accept(self):
        Gui.Selection.removeObserver(self.sel_observer)
        Gui.Selection.removeSelectionGate()
        self.sel_observer.includeSectionsInObject()
        self.sel_observer.removePlaneAndSections(False)
        return True

    def reject(self):
        Gui.Selection.removeObserver(self.sel_observer)
        Gui.Selection.removeSelectionGate()
        # for obj in self.sel_observer.sections:
        #     App.ActiveDocument.removeObject(obj.Label)
        # if self.sel_observer.sectionPlane:
        #     App.ActiveDocument.removeObject(self.sel_observer.sectionPlane.Label)
        # if self.sel_observer.base_color and self.sel_observer.root_object:
        #     self.sel_observer.setColorOfAllFaces(self.sel_observer.root_object , self.sel_observer.base_color)
        self.sel_observer.removePlaneAndSections()
        return True
        # self.setColorOfAllFaces(self.object, self.base_color)
    
    # def setColorOfSelectedFaces(self, sel, colorSelected, colorBase, ignoreSelection=False):
    #     if not sel or not sel.SubObjects:
    #         App.Console.PrintMessage("No face selected.\n")
    #         return
    #     # faces can be selected with mouse
    #     obj = sel.Object
    #     colorArray = obj.ViewObject.DiffuseColor
    #     # got all faces indexes
    #     faceIdx = []
    #     if not ignoreSelection:
    #         for item in sel.SubElementNames:
    #             if item.startswith('Face'):
    #                 faceIdx.append(int(item[4:])-1)
    #         print('[*] Object %s contains %d faces'%(obj.Name, len(faceIdx)))
    #     # Loop over whole object faces, make list of colors
    #     setColor = []
    #     for idx in range(len(obj.Shape.Faces)):
    #         if idx in faceIdx:
    #             setColor.append(colorSelected)
    #         else:
    #             setColor.append(colorArray[idx] if idx < len(colorArray) else colorBase)
    #     obj.ViewObject.DiffuseColor = setColor
    #     print('[*] ... colored %d faces'%(len(setColor),))

    # def setColorOfAllFaces(self, obj, color):
    #     if not obj or not hasattr(obj, 'Shape'):
    #         App.Console.PrintMessage("No valid object selected.\n")
    #         return
    #     setColor = [color] * len(obj.Shape.Faces)
    #     obj.ViewObject.DiffuseColor = setColor
    #     print('[*] ... colored %d faces'%(len(setColor),))

    def nextState(self):
        if self.state == self.TaskState.SELECT_BASE_PLANE:
            print("nextState of SELECT_BASE_PLANE")
            old_layout = self.form.layout()
            if old_layout:
                QtWidgets.QWidget().setLayout(old_layout)
            layout = self.createSelectObjectLayout()
            self.form.setLayout(layout)
            self.form.repaint()
            self.state = self.TaskState.SELECT_OBJECT_TO_SECTION
        elif self.state == self.TaskState.SELECT_OBJECT_TO_SECTION:
            #self.instructionLabel.setText("Done. Click 'OK' to finish.")
            self.state = self.TaskState.DONE
        elif self.state == self.TaskState.DONE:
            App.Console.PrintMessage("Sectioning completed.\n")
            Gui.Selection.removeObserver(self)
            return True
        return False

    class TaskState(Enum):
        SELECT_BASE_PLANE = 1
        SELECT_OBJECT_TO_SECTION = 2
        DONE = 3


    def createSelectBaseLayout(self):
        layout = QtWidgets.QVBoxLayout()
        label = QtWidgets.QLabel("Select a base plane.")
        layout.addWidget(label)
        return layout
    
    def createSelectObjectLayout(self):
        layout = QtWidgets.QVBoxLayout()

        label = QtWidgets.QLabel("Select an object to section.")

        rowLayout = QtWidgets.QHBoxLayout()
        labelDistance = QtWidgets.QLabel("Distance from base plane:")
        distanceInput = QtWidgets.QDoubleSpinBox()
        distanceInput.setDecimals(2)
        distanceInput.setSingleStep(0.1)
        distanceInput.setValue(0.0)
        distanceInput.setSuffix(" mm")
        distanceInput.setRange(-100.0, 100.0)
        distanceInput.valueChanged.connect(self.sel_observer.positionSectionPlaneAlongNormal)
        # TODO: Make the plane non selectable
        rowLayout.addWidget(labelDistance)
        rowLayout.addStretch()
        rowLayout.addWidget(distanceInput)

        self.makeSectionButton = QtWidgets.QPushButton("Make Section")
        self.makeSectionButton.setVisible(False)
        self.makeSectionButton.clicked.connect(self.sel_observer.makeSection)
        
        layout.addWidget(label)
        layout.addLayout(rowLayout)
        layout.addWidget(self.makeSectionButton)
        return layout
    
    def updateButtonVisibility(self, visible):
        self.makeSectionButton.setVisible(visible)
        self.form.repaint()

    
        
    
