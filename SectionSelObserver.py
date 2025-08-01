import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector
from BOPTools import SplitFeatures
import SurfSensePanel


class SectionSelObserver:

    #Selection gate already initialised for faces
    def __init__(self, sectionPanel) -> None:
        self.sectionPanel = sectionPanel
        App.Console.PrintMessage("SectionSelObserver initialized" + "\n")
        self.sections = []
        self.sectionPlane = None
        self.base_color = None

    def addSelection(self, doc, obj, sub, pnt):
        self.sel = Gui.Selection.getSelectionEx()[0]
        colorArray = self.sel.Object.ViewObject.DiffuseColor
        self.base_color = colorArray[0] if colorArray and len(colorArray) > 1 and colorArray[0] == colorArray[1] else (0.5, 0.5, 0.5)
        self.root_object = self.sel.Object
        if self.sectionPanel.state == self.sectionPanel.TaskState.SELECT_BASE_PLANE:
            self.handleBasePlateSelection(self.sel.Object, self.sel.SubObjects[-1])
        elif self.sectionPanel.state == self.sectionPanel.TaskState.SELECT_OBJECT_TO_SECTION:
            self.handleObjectToSectionSelection(self.sel.Object, self.sel.SubObjects[-1])
        elif self.sectionPanel.state == self.sectionPanel.TaskState.Done:
            App.Console.PrintMessage("Selection is done, no further action needed.\n")
        else:
            App.Console.PrintMessage("Unknown state, cannot handle selection.\n")
        


    def removeSelection(self,doc,obj,sub):                # Remove the selection
        App.Console.PrintMessage("removeSelection"+ "\n")
        sel = Gui.Selection.getSelectionEx()
        if sel and sel[0].SubObjects and self.sectionPanel.state == self.sectionPanel.TaskState.SELECT_OBJECT_TO_SECTION:
            if len(sel[0].SubObjects) == 0:
                self.sectionPanel.updateButtonVisibility(False)

    def setSelection(self,doc):                           # Set selection
        App.Console.PrintMessage("setSelection"+ "\n")

    def clearSelection(self,doc):                         # If click on the screen, clear the selection
        App.Console.PrintMessage("clearSelection"+ "\n")
        if self.sectionPanel.state == self.sectionPanel.TaskState.SELECT_OBJECT_TO_SECTION:
            self.sectionPanel.updateButtonVisibility(False)

    def handleBasePlateSelection(self, obj, sub):
        if not isinstance(sub.Surface, Part.Plane):
            App.Console.PrintMessage("Selected object is not a planar.\n")
            return
        center = sub.CenterOfMass
        self.normal = sub.normalAt(0,0)

        # Get the bounding box of the object
        bbox = obj.Shape.BoundBox
        plane_size = 2 * max(bbox.XLength, bbox.YLength, bbox.ZLength)

        plane = Part.makePlane(plane_size, plane_size, center, self.normal)
        plane.translate(center.sub(plane.CenterOfMass))
        self.sectionPlane = App.ActiveDocument.addObject("Part::Feature", "ParallelPlane")
        self.sectionPlane.addProperty("App::PropertyInteger", "SurfSenseID", "Base", "", True)
        self.sectionPlane.SurfSenseID = SurfSensePanel.SurfSensePanel._measurement_count
        self.sectionPlane.Shape = plane
        self.placement = self.sectionPlane.Placement.copy()

        # # Create a rectangular Part Plane
        # doc = App.ActiveDocument
        # self.sectionPlane = doc.addObject("Part::Plane", "ParallelPlane")
        # self.sectionPlane.Length = plane_size
        # self.sectionPlane.Width = plane_size

        # # Create rotation to align plane normal to face normal
        # rotation = App.Rotation(Vector(0, 0, 1), self.normal)

        # # Compute the vector from corner (0,0) to center in local plane coords
        # local_offset = Vector(plane_size / 2, plane_size / 2, 0)

        # # Rotate that offset into global coords
        # world_offset = rotation.multVec(local_offset)

        # # Final placement
        # self.placement = App.Placement()
        # self.placement.Base = center - world_offset
        # self.placement.Rotation = rotation
        # self.sectionPlane.Placement = self.placement

        planeColor = (1.0, 0.5, 0.0)
        self.sectionPlane.ViewObject.DiffuseColor = [planeColor]
        self.sectionPlane.ViewObject.LineColor = planeColor
        self.sectionPlane.ViewObject.LineWidth = 2.0
        self.sectionPlane.ViewObject.Transparency = 60
        self.sectionPlane.ViewObject.Selectable = False

        Gui.Selection.clearSelection()
        App.ActiveDocument.recompute()

        self.sectionPanel.basePlane = self.sectionPlane
        self.setColorOfSelectedFaces(self.sel, planeColor, self.base_color)
        self.sectionPanel.nextState()
    
    def handleObjectToSectionSelection(self, obj, sub):
        self.sectionPanel.updateButtonVisibility(True)

    def makeSection(self):
        if not self.sectionPlane or not self.sectionPlane.isDerivedFrom("Part::Feature"):
            App.Console.PrintMessage("No valid section plane defined.\n")
            return
        # the currently selected objects should be faces
        sel = Gui.Selection.getSelectionEx()
        if not sel or not sel[0].SubObjects:
            App.Console.PrintMessage("No valid object selected for sectioning.\n")
            return
        for face in sel[0].SubObjects:
            if isinstance(face, Part.Face):
                # if face.common(self.sectionPlane.Shape).Volume == 0:
                #     print("Face does not intersect with the section plane, skipping.")
                #     continue
                section = face.section(self.sectionPlane.Shape)
                if section:
                    section_obj = App.ActiveDocument.addObject("Part::Feature", "Section")
                    section_obj.addProperty("App::PropertyInteger", "SurfSenseID", "Base", "", True)
                    section_obj.SurfSenseID = SurfSensePanel.SurfSensePanel._measurement_count
                    section_obj.Shape = section
                    self.sections.append(section_obj)
        if not self.sections:
            App.Console.PrintMessage("No valid sections created from the selected faces.\n")
            return

    def positionSectionPlaneAlongNormal(self, value):
        if self.sectionPlane:
            value = round(value, 2)
            placement = self.sectionPlane.Placement
            # offset = self.normal.multiply(value) <-- azért ez nem szép dolog, mert a multiply függvény változtatja a hívó objektumot és önreferenciát ad vissza
            offset = self.normal * value
            placement.Base = self.placement.Base + offset
            self.sectionPlane.Placement = placement
            App.ActiveDocument.recompute()
    
    def setColorOfSelectedFaces(self, sel, colorSelected, colorBase, ignoreSelection=False):
        if not sel or not sel.SubObjects:
            App.Console.PrintMessage("No face selected.\n")
            return
        # faces can be selected with mouse
        obj = sel.Object
        colorArray = obj.ViewObject.DiffuseColor
        # got all faces indexes
        faceIdx = []
        if not ignoreSelection:
            for item in sel.SubElementNames:
                if item.startswith('Face'):
                    faceIdx.append(int(item[4:])-1)
            print('[*] Object %s contains %d faces'%(obj.Name, len(faceIdx)))
        # Loop over whole object faces, make list of colors
        setColor = []
        for idx in range(len(obj.Shape.Faces)):
            if idx in faceIdx:
                setColor.append(colorSelected)
            else:
                setColor.append(colorArray[idx] if idx < len(colorArray) else colorBase)
        obj.ViewObject.DiffuseColor = setColor
        print('[*] ... colored %d faces'%(len(setColor),))

    def setColorOfAllFaces(self, obj, color):
        if not obj or not hasattr(obj, 'Shape'):
            App.Console.PrintMessage("No valid object selected.\n")
            return
        setColor = [color] * len(obj.Shape.Faces)
        obj.ViewObject.DiffuseColor = setColor
        print('[*] ... colored %d faces'%(len(setColor),))
    
    def removePlaneAndSections(self, sectionsToo=True):
        if self.sectionPlane:
            App.ActiveDocument.removeObject(self.sectionPlane.Label)
            self.sectionPlane = None
        if sectionsToo:
            for section in self.sections:
                App.ActiveDocument.removeObject(section.Label)
        self.sections.clear()
        if self.base_color and self.root_object:
            self.setColorOfAllFaces(self.root_object , self.base_color)
        if App.ActiveDocument:
            App.ActiveDocument.recompute()
        Gui.Selection.clearSelection()
        App.Console.PrintMessage("Removed section plane and sections.\n")

    def includeSectionsInObject(self):
        if not self.sections:
            App.Console.PrintMessage("No sections to include in the object.\n")
            return
        if not self.root_object:
            App.Console.PrintMessage("No root object to include sections in.\n")
            return
        bool_frag = SplitFeatures.makeBooleanFragments(name="ObjectWithSections")
        bool_frag.Objects = self.sections + [self.root_object]
        # bool_frag.Objects = [self.sections, self.root_object]
        bool_frag.Mode = "Standard"
        bool_frag.Proxy.execute(bool_frag)
        # TODO
        # bool_frag.purgeTouched() #<-- jó lenne tudni mit jelent és kell-e nekünk
        # TODO: egy metszésnél ne egymásba ágyazott boolfragmenteket csináljunk, hanem inkább ahhoz adjunk hozzá ami megvan már
        for obj in bool_frag.ViewObject.Proxy.claimChildren():
            obj.ViewObject.hide()
        App.ActiveDocument.recompute()