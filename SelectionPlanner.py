from PySide6 import QtWidgets
import FreeCADGui
import FreeCAD
import Part
import Draft
import DraftGeomUtils # type: ignore
import Sketcher
import xml.etree.ElementTree as ET
import SubSurfaceCreator
from BOPTools import SplitFeatures

class SelectionPlanner:

    def __init__(self, TaskPanel):
        self.Panel = TaskPanel
        self.normals_resolution = 0.5  # Default resolution for normals
        self.root_node = ET.Element("Part")
        self.measurements_node = ET.SubElement(self.root_node, "Measurements")
        self.measurements_node.set("spacing", str(self.normals_resolution))
        self.measurement_index = 0
        #root_node.set("spacing", str(resolution))

    def getElementsFromSelection(self):
            #selectedElements = []
            self.elementsToMeasure = []
            sel = FreeCADGui.Selection.getSelectionEx()[0]
            if len(sel.SubObjects) > 3:
                QtWidgets.QMessageBox.information(None, "Error", f"Please select maximum 3 elements (face, edge or point). {len(sel.SubObjects)} is currently selected") # type: ignore
            
            self.Panel.textbox.clear()

            #ONLY FOR TESTING, PLACE INTO SEPARATE FEATURE LATER
            if self.isObjectSketch(FreeCADGui.Selection.getSelection()[0]):
                print("Sketch selected")
                sel = FreeCADGui.Selection.getSelection()[0]
                self.handleSketchSelection(sel)
                return
            #END OF TESTING

            if len(sel.SubObjects) == 1:
                if(sel.SubObjects[0].ShapeType == "Edge"):
                    #self.createEdgeExtensionRectangles(sel, sel.SubObjects[0])
                    self.handle1EdgeSelection(sel)
                elif(sel.SubObjects[0].ShapeType == "Face"):
                    self.handle1FaceSelection(sel)
                else:
                    QtWidgets.QMessageBox.information(None, "Error","Only edge is allowed with single selection.") # type: ignore
            
            elif len(sel.SubObjects) == 2:
                if(sel.SubObjects[0].ShapeType == "Face" and sel.SubObjects[1].ShapeType == "Face"):
                    self.handle2FaceSelection(sel)
                elif self.edgeType(sel.SubObjects[0]) == "line" and self.edgeType(sel.SubObjects[1]) == "line":
                    self.handle2EdgeSelection(sel)
                elif self.edgeType(sel.SubObjects[0]) == "circle" and self.edgeType(sel.SubObjects[1]) == "circle":
                    self.handle2CircleSelection(sel)
                elif (self.edgeType(sel.SubObjects[0]) == "circle" and self.faceType(sel.SubObjects[1]) == "cylinder") or (self.edgeType(sel.SubObjects[1]) == "circle" and self.faceType(sel.SubObjects[0]) == "cylinder"):
                    self.handleCircleAndCylinderSelection(sel)
                elif (
                    (self.edgeType(sel.SubObjects[0]) in ["line", "circle"] and self.faceType(sel.SubObjects[1]) == "plane") or
                    (self.edgeType(sel.SubObjects[1]) in ["line", "circle"] and self.faceType(sel.SubObjects[0]) == "plane")):
                    self.handleEdgeAndPlaneSelection(sel)
                elif (self.edgeType(sel.SubObjects[0]) == "circle" and self.edgeType(sel.SubObjects[1]) == "line") or (self.edgeType(sel.SubObjects[1]) == "circle" and self.edgeType(sel.SubObjects[0]) == "line"):
                    self.handleCircleAndLineSelection(sel)
                else:
                    QtWidgets.QMessageBox.information(None, "Error","Invalid selection pair.") # type: ignore
                
            self.Panel.textbox.append("Elements to be measured: \n")
            self.displayFaceVertexInfo(self.elementsToMeasure)

    #region Selection handlers
    def handle1EdgeSelection(self, sel):
        if not sel.SubObjects[0]:
            return
        measurement_node = self.createMeasurementNode()
        measurement_group = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroup", "EdgeLengthMeasurement")

        SubSurfaceCreator.createNeighborSubsurfaces(sel.Object, sel.SubObjects[0], resolution= self.normals_resolution, aroundVertex=True , measurement_node = measurement_node, measurement_group = measurement_group)
        #TODO: Ez nagy hekk, használjuk mindenképpen, meg a discretise függvényt is, felosztja pl az élt
        
        #DEPRECATED
        facesofEdge = sel.Object.Shape.ancestorsOfType(sel.SubObjects[0].Vertexes[0], Part.Face)
        print(f"faces of edge: {len(facesofEdge)}")

        for v in sel.SubObjects[0].Vertexes:
            for i,face in enumerate(sel.Object.Shape.Faces):
                if any(v.Point.isEqual(fv.Point, 1e-07) for fv in face.Vertexes):
                    # elementsToMeasure.append((face, f"Face{i+1}"))
                    if not any(face.isSame(f) for f in self.elementsToMeasure):
                        self.elementsToMeasure.append(face)
                        FreeCADGui.Selection.addSelection(sel.Object, f"Face{i+1}")
        # QtWidgets.QMessageBox.information(None, "Hello",f"You selected one edge of length {sel0.SubObjects[0].Length}!")
        self.Panel.textbox.append(f"You selected one edge with length of {sel.SubObjects[0].Length}\n")

    def handle1FaceSelection(self, sel):
        if not sel.SubObjects[0]:
            return
        face = sel.SubObjects[0]
        self.elementsToMeasure.append(face)
        measurement_node = self.createMeasurementNode()
        measurement_group = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroup", "FaceMeasurement")
        points, normals = SubSurfaceCreator.sample_surface_by_spacing(face, spacing_mm = 1.0, measurement_group = measurement_group)
        if measurement_node is not None:
            SubSurfaceCreator.addFaceToMeasurementXML(face, points, normals, measurement_node)
        SubSurfaceCreator.createOffsetToFaces(face, measurement_group = measurement_group)

    def handle2FaceSelection(self, sel):
        face1 = sel.SubObjects[0]
        face2 = sel.SubObjects[1]
        self.elementsToMeasure.append(face1)
        self.elementsToMeasure.append(face2)
        if self.areFacesParallel(face1, face2):
            distance, pointsofdist, info = face1.distToShape(face2)
            print("Faces are parallel")
            print("len edges of face1: ", len(face1.Edges))
            print("len vertices of face1: ", len(face1.Vertexes))
            self.Panel.textbox.append(f"You selected two parallel faces with distance of {distance}\n")
            measurement_node = self.createMeasurementNode()
            measurement_group = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroup", "FaceDistanceMeasurement")
            faces = [face1, face2]
            for i, face in enumerate(faces):
                points, normals = SubSurfaceCreator.sample_surface_by_spacing(face, spacing_mm = 1.0, measurement_group = measurement_group)
                if measurement_node is not None:
                    SubSurfaceCreator.addFaceToMeasurementXML(face, points, normals, measurement_node, i)
                SubSurfaceCreator.createOffsetToFaces(face, measurement_group = measurement_group)
        else:
            QtWidgets.QMessageBox.information(None, "Error","Selected faces are not parallel") # type: ignore
            return
        self.makeDim(face1,face2)

    def handle2EdgeSelection(self, sel):
        if self.notParallelAndNotSkew(sel.SubObjects[0], sel.SubObjects[1]):
            QtWidgets.QMessageBox.information(None, "Error","The selected lines are not parallel and not skew (or collinear)") # type: ignore
            return
        if len(sel.SubObjects) != 2:
            QtWidgets.QMessageBox.information(None, "Error","Please select two edges") # type: ignore
        distance, points, info = sel.SubObjects[0].distToShape(sel.SubObjects[1])
        self.Panel.textbox.append(f"You selected two parallel lines with distance of {distance}\n")
        
        self.makeDim(sel.SubObjects[0],sel.SubObjects[1])
        # FreeCAD.ActiveDocument.recompute()
        # FreeCADGui.runCommand('Std_Measure',0)
        measurement_node = self.createMeasurementNode()
        measurement_group = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroup", "EdgeDistanceMeasurement")
        for i, edge in enumerate(sel.SubObjects):
            SubSurfaceCreator.createNeighborSubsurfaces(sel.Object, edge, resolution=self.normals_resolution, aroundVertex=False, measurement_node=measurement_node, measurement_group=measurement_group)

        for i, face in enumerate(sel.Object.Shape.Faces):
            for s in sel.SubObjects:
                contToNextLine = False
                for v in s.Vertexes:
                    if not any(v.Point.isEqual(fv.Point, 1e-07) for fv in face.Vertexes):
                        contToNextLine = True
                        break
                if not contToNextLine and not any(face.isSame(f) for f in self.elementsToMeasure):
                    self.elementsToMeasure.append(face)
                    FreeCADGui.Selection.addSelection(sel.Object, f"Face{i+1}")

    def handle2CircleSelection(self, sel):
        circle1 = sel.SubObjects[0]
        circle2 = sel.SubObjects[1]
        if not self.areCirclesCoplanar(circle1, circle2):
            QtWidgets.QMessageBox.information(None, "Error","The selected circles are not coplanar") # type: ignore
            return
        
        measurement_node = self.createMeasurementNode()
        measurement_group = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroup", "CircleDistanceMeasurement")
        for i, circle in enumerate(sel.SubObjects):
            SubSurfaceCreator.createNeighborSubsurfaces(sel.Object, circle, resolution=self.normals_resolution, aroundVertex=False, measurement_node=measurement_node, measurement_group=measurement_group)

    def handleCircleAndLineSelection(self, sel):
        circle: Part.Edge = None
        line: Part.Edge = None
        if self.edgeType(sel.SubObjects[0]) == "circle":
            circle = sel.SubObjects[0]
            line = sel.SubObjects[1]
        elif self.edgeType(sel.SubObjects[1]) == "circle":
            circle = sel.SubObjects[1]
            line = sel.SubObjects[0]
        else:
            QtWidgets.QMessageBox.information(None, "Error","Please select a circle and a line") # type: ignore
        
        if not circle or not line:
            QtWidgets.QMessageBox.information(None, "Error","Please select a circle and a line") # type: ignore

        if not self.isCircleAndLineCoplanar(circle, line):
            QtWidgets.QMessageBox.information(None, "Error","The circle and line are not coplanar") # type: ignore
        measurement_node = self.createMeasurementNode()
        measurement_group = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroup", "CircleAndLineMeasurement")
        SubSurfaceCreator.createNeighborSubsurfaces(sel.Object, circle, resolution=self.normals_resolution, aroundVertex=False, measurement_node=measurement_node, measurement_group=measurement_group)
        SubSurfaceCreator.createNeighborSubsurfaces(sel.Object, line, resolution=self.normals_resolution, aroundVertex=False, measurement_node=measurement_node, measurement_group=measurement_group)

    def handleCircleAndCylinderSelection(self, sel):
        doc = FreeCAD.ActiveDocument
        circle: Part.Edge = None
        cylinder: Part.Cylinder = None
        if self.edgeType(sel.SubObjects[0]) == "circle":
            circle = sel.SubObjects[0]
            cylinder = sel.SubObjects[1]
        elif self.edgeType(sel.SubObjects[1]) == "circle":
            circle = sel.SubObjects[1]
            cylinder = sel.SubObjects[0]
        else:
            QtWidgets.QMessageBox.information(None, "Error","Please select a circle and a cylinder") # type: ignore

        if not circle or not cylinder:
            QtWidgets.QMessageBox.information(None, "Error","Please select a circle and a cylinder") # type: ignore

        center = circle.Curve.Center
        normal = circle.Curve.Axis.normalize()

        bbox = sel.Object.Shape.BoundBox
        plane_size = 2 * max(bbox.XLength, bbox.YLength, bbox.ZLength)

        # Create a rectangular Part Plane
        plane = Part.makePlane(plane_size, plane_size, center, normal)
        # shift the plane to the center of the circle
        plane.translate(center.sub(plane.CenterOfMass))
        # Add the plane to the FreeCAD document
        plane_obj = doc.addObject("Part::Feature", "CirclePlane")
        plane_obj.Shape = plane
        doc.recompute()

        section = cylinder.section(plane)
        if not section:
            QtWidgets.QMessageBox.information(None, "Error","The circle and cylinder do not intersect") # type: ignore
            doc.removeObject(plane_obj.Label)
            return
            
        doc.removeObject(plane_obj.Label)

        section_obj = FreeCAD.ActiveDocument.addObject("Part::Feature", "CircleSection")
        section_obj.Shape = section

        bool_frag = SplitFeatures.makeBooleanFragments(name="CircleSectionFragments")
        bool_frag.Objects = [section_obj, sel.Object]
        bool_frag.Mode = 'Standard'
        bool_frag.Proxy.execute(bool_frag)
        doc.recompute()
        if not bool_frag.Shape:
            QtWidgets.QMessageBox.information(None, "Error","The boolean fragments could not be created") # type: ignore
            return
        measurement_node = self.createMeasurementNode()
        measurement_group = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroup", "CircleAndCylinderMeasurement")
        for edge in section_obj.Shape.Edges:
            frag_edge = SubSurfaceCreator.findEdgeOnObject(bool_frag.Shape, edge)
            if frag_edge:
                SubSurfaceCreator.createNeighborSubsurfaces(bool_frag, frag_edge, resolution=self.normals_resolution, aroundVertex=False, measurement_node=measurement_node, measurement_group=measurement_group)
            else:
                print(f"Edge {edge} not found in boolean fragments shape.")
        SubSurfaceCreator.createNeighborSubsurfaces(sel.Object, circle, resolution=self.normals_resolution, aroundVertex=False, measurement_node=measurement_node, measurement_group=measurement_group)

        doc.removeObject(bool_frag.Label)
        doc.removeObject(section_obj.Label)
        doc.recompute()

    def handleEdgeAndPlaneSelection(self, sel):
        edge: Part.Edge = None
        plane: Part.Plane = None
        if self.faceType(sel.SubObjects[0]) == "plane":
            plane = sel.SubObjects[0]
            edge = sel.SubObjects[1]
        elif self.faceType(sel.SubObjects[1]) == "plane":
            plane = sel.SubObjects[1]
            edge = sel.SubObjects[0]
        else:
            QtWidgets.QMessageBox.information(None, "Error","Please select a line and a plane") # type: ignore
            return

        if not edge or not plane:
            QtWidgets.QMessageBox.information(None, "Error","Please select a line and a plane") # type: ignore
            return

        if not self.isEdgeAndPlaneParallel(edge, plane):
            QtWidgets.QMessageBox.information(None, "Error","The selected edge and plane are not parallel") # type: ignore
            return
        measurement_node = self.createMeasurementNode()
        measurement_group = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroup", "EdgeAndPlaneMeasurement")
        SubSurfaceCreator.createNeighborSubsurfaces(sel.Object, edge, resolution=self.normals_resolution, aroundVertex=False, measurement_node=measurement_node, measurement_group=measurement_group)

        points, normals = SubSurfaceCreator.sample_surface_by_spacing(plane, spacing_mm=1.0, measurement_group=measurement_group)
        if measurement_node is not None:
            SubSurfaceCreator.addFaceToMeasurementXML(plane, points, normals, measurement_node)
        SubSurfaceCreator.createOffsetToFaces(plane, measurement_group=measurement_group)

    def handleSketchSelection(self, sel):
        sketch = sel
        if not self.isObjectSketch(sketch):
            QtWidgets.QMessageBox.information(None, "Error", "The provided object is not a Sketch.") # type: ignore

        # if not sketch.FullyConstrained or not self.isSketchClosed(sketch):
        if not self.isSketchClosed(sketch):
            QtWidgets.QMessageBox.information(None, "Info", "Sketch must be fully constrained and closed to create a face.") # type: ignore
            return
        measurement_node = self.createMeasurementNode()
        self.createMeasurementFromSketch(sketch, measurement_node)


    #endregion

    #region Helper functions

    def createMeasurementNode(self):
        measurement_node = ET.SubElement(self.measurements_node, "Measurement")
        measurement_node.set("index", str(self.measurement_index))
        self.measurement_index += 1
        return measurement_node

    def displayFaceVertexInfo(self, faces):
        for i, face in enumerate(faces):
            # face, name = faceTuple
            self.Panel.textbox.append(f"Face#{i}: ")
            for vertex in face.Vertexes:
                point = vertex.Point
                self.Panel.textbox.append(f"  ({point.x:.2f}, {point.y:.2f}, {point.z:.2f})")
            self.Panel.textbox.append("")  # Blank line between faces
    
    def areFacesParallel(self, face1, face2):
        tol = 1e-07
        normal1 = face1.normalAt(0.5, 0.5)
        normal2 = face2.normalAt(0.5, 0.5)
        # print(normal1)
        # print(normal2)
        # print(normal1.dot(normal2))
        # print(normal1.dot(normal2) / (normal1.Length * normal2.Length))
        # print(abs(normal1.dot(normal2) / (normal1.Length * normal2.Length)))
        # return abs(abs(normal1.dot(normal2) / (normal1.Length * normal2.Length))-1) < tol
        return normal1.cross(normal2).Length < tol
    
    def areCirclesCoplanar(self, circle1, circle2):
        tol = 1e-07
        normal1 = circle1.Curve.Axis.normalize()
        normal2 = circle2.Curve.Axis.normalize()
        centersVector = circle2.Curve.Center.sub(circle1.Curve.Center)
        return normal1.dot(centersVector) < tol and normal2.dot(centersVector) < tol
    
    def isCircleAndLineCoplanar(self, circle, line):
        tol = 1e-07
        if self.edgeType(circle) != "circle" or self.edgeType(line) != "line":
            QtWidgets.QMessageBox.information(None, "Error","Error during coplanarity check: received objects are not circle and line") # type: ignore
        circle_normal = circle.Curve.Axis.normalize()
        for v in line.Vertexes:
            vec_to_circle_center = circle.Curve.Center.sub(v.Point)
            if abs(circle_normal.dot(vec_to_circle_center)) > tol:
                return False
        return True

    def isEdgeAndPlaneParallel(self, edge, plane):
        if self.edgeType(edge) not in ["line", "circle"] or self.faceType(plane) != "plane":
            QtWidgets.QMessageBox.information(None, "Error","Error during parallael check: received objects are not line and plane") # type: ignore
        tol = 1e-07
        plane_normal = plane.normalAt(0, 0).normalize()
        if self.edgeType(edge) == "circle":
            axis = edge.Curve.Axis.normalize()
            return abs(axis.cross(plane_normal).Length) < tol
        elif self.edgeType(edge) == "line":
            line_direction = edge.tangentAt(0.5).normalize()
            return abs(line_direction.dot(plane_normal)) < tol
        else:
            QtWidgets.QMessageBox.information(None, "Error","Error during parallael check: received edge is neither line nor circle") # type: ignore

        
    def edgeType(self, subobj):
        if subobj.ShapeType == "Edge":
            if isinstance(subobj.Curve, Part.Line):
                return "line"
            elif isinstance(subobj.Curve, Part.Circle):
                return "circle"
        return ""
       # return subobj.ShapeType == "Edge" and isinstance(subobj.Curve, Part.Line)

    def faceType(self, subobj):
        if subobj.ShapeType == "Face":
            if isinstance(subobj.Surface, Part.Plane):
                return "plane"
            elif isinstance(subobj.Surface, Part.Cylinder):
                return "cylinder"
            elif isinstance(subobj.Surface, Part.Sphere):
                return "sphere"
        return ""
       # return subobj.ShapeType == "Face" and isinstance(subobj.Surface, Part.Plane)
    
    def notParallelAndNotSkew(self, line1, line2):
        tol = 1e-07
        dirVec1 = line1.tangentAt(0.5)
        dirVec2 = line2.tangentAt(0.5)
        parallel = dirVec1.cross(dirVec2).Length < tol
        skew = True
        for v1 in line1.Vertexes:
            for v2 in line2.Vertexes:
                if v1.isEqual(v2):
                    skew = False
        
        vec_between = line2.Vertexes[0].Point.sub(line1.Vertexes[0].Point)
        print(f"Collinearity: {vec_between.cross(dirVec1).Length}")
        collinear = vec_between.cross(dirVec1).Length < tol
        print(f"Collinear: {collinear}")
        print(f"Parallel: {parallel}")
        print(f"Return value: {not ((parallel or skew) and not collinear)}")
        return not parallel or collinear
        #return not ((parallel or skew) and not collinear)
        #not parallel and not skew or collinear
    
    #TODO: makeDim legyen univerzális két bármilyen tipusu subobj között
    def makeDim(self, subobj1, subobj2):
        return
        prev_selection = FreeCADGui.Selection.getSelectionEx()
        dim = Draft.make_dimension(subobj1.CenterOfMass, subobj2.CenterOfMass, subobj1.CenterOfMass.add(subobj2.CenterOfMass).multiply(0.5).add(FreeCAD.Vector(0, 0, 10))) # type: ignore
        FreeCADGui.Selection.clearSelection()
        for sel in prev_selection:
            obj = sel.Object
            for subname in sel.SubElementNames:
                FreeCADGui.Selection.addSelection(obj, subname)
        self.Panel.dimensions.append(dim)

    def createMeasurementFromSketch(self, sketch, measurement_node):
        if not self.isObjectSketch(sketch):
            QtWidgets.QMessageBox.information(None, "Error", "The provided object is not a Sketch.") # type: ignore
            return
        
        face_obj : Part.Face = None
        measurement_group = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroup", "FaceFragmentMeasurement")
        # Check if the sketch is fully constrained and closed
        # if sketch.FullyConstrained and self.isSketchClosed(sketch):
        if self.isSketchClosed(sketch):
            try:
                face = Part.Face(sketch.Shape)
                face_obj = FreeCAD.ActiveDocument.addObject("Part::Feature", "SketchFace")
                face_obj.Shape = face
                FreeCAD.ActiveDocument.recompute()
            except Exception as e:
                QtWidgets.QMessageBox.information(None, "Error", f"Could not create face from sketch: {e}") # type: ignore
        else:
            QtWidgets.QMessageBox.information(None, "Info", "Sketch must be fully constrained and closed to create a face.") # type: ignore
            return
        face = face_obj.Shape.Faces[0]
        # Create a measurement from the sketch
        points, normals = SubSurfaceCreator.sample_surface_by_spacing(face, spacing_mm = 1.0, measurement_group = measurement_group)
        if measurement_node is not None:
            SubSurfaceCreator.addFaceToMeasurementXML(face, points, normals, measurement_node)
        SubSurfaceCreator.createOffsetToFaces(face, measurement_group = measurement_group)
        FreeCAD.ActiveDocument.removeObject(face_obj.Name)

    def isObjectSketch(self, obj):
        """Check if the given object is a Sketcher sketch."""
        return hasattr(obj, "TypeId") and obj.TypeId.startswith("Sketcher::SketchObject")

    def isSketchClosed(self, sketch):
        """Check if the sketch is closed by verifying that all edges form a single closed wire."""
        try:
            wires = sketch.Shape.Wires
            return len(wires) == 1 and wires[0].isClosed()
        except Exception:
            return False
    
    #DEPRECATED
    def createEdgeExtensionRectangles(self,sel,edge):
        rectangles = []
        # adjacent_faces = [f for f in sel.Object.Shape.Faces if any(edge.isSame(e) for e in f.Edges)]
        # print(f"adjacent faces: {len(adjacent_faces)}")
        v1, v2 = None, None
        orientation = None
        for face in sel.Object.Shape.Faces:
            if not any(edge.isSame(f) for f in face.Edges):
                # Skip if the edge is not part of the face
                continue
            
            print(f"Edges len: {len(face.Edges)}")
            for e in face.Edges:
                print(f"edge points: {e.Vertexes[0].Point}; {e.Vertexes[1].Point}, direction of edge: {e.tangentAt(0.5)}, orientation: {e.Orientation}")
                if edge.isSame(e):
                    v1, v2 = e.Vertexes
                    orientation = e.Orientation
                    break
            if v1 is None or v2 is None:
                continue  # Skip if the edge is not found in the face edges

            # Get the edge's vertices
            #v1, v2 = edge.Vertexes
            # Get the edge's direction vector
            edge_vector = v2.Point.sub(v1.Point)
            edge_length = edge_vector.Length
            edge_vector.normalize()
            print(f"edge_vector: {edge_vector.normalize()}")
            #print(f"edge normal: {edge.normalAt(0)}")

            # Get the face's normal vector
            face_normal = face.normalAt(0.5, 0.5)
            face_normal.normalize()
            print(f"face_normal: {face_normal.normalize()}")

            # Calculate a perpendicular vector on the face
            perp_vector = face_normal.cross(edge_vector)
            print(f"original edge orientation: {edge.Orientation}")
            if orientation == "Reversed":
                print("edge orientation reversed")
                perp_vector = perp_vector.multiply(-1)
            perp_vector = perp_vector.normalize()
            # perp_vector = perp_vector.normalize() if edge.Orientation == "Reversed" else perp_vector.normalize().multiply(-1)
            print(f"perp_vector: {perp_vector}")

            # Define the rectangle's corners
            scanline_width = perp_vector.multiply(edge_length / 5)
            corner1 = v1.Point
            corner2 = v2.Point
            corner3 = v2.Point.add(scanline_width)
            corner4 = v1.Point.add(scanline_width)
            for corner in [corner1, corner2, corner3, corner4]:
                print(f"corner: {corner}")

            # Make a wire from the corners
            wire = Part.makePolygon([corner1, corner2, corner3, corner4, corner1])
            
            # Create a face from the wire
            facePart = Part.Face(wire)
            facePart.translate(face_normal.multiply(0.01))
            
            
            # Add the face to the FreeCAD document
            face_obj = FreeCAD.ActiveDocument.addObject("Part::Feature", "RectangleFace")
            face_obj.Shape = facePart
            
            # Set the face's color
            face_obj.ViewObject.ShapeColor = (1.0, 0.0, 0.0)  # Red color
            
            # Recompute the document to reflect changes
            FreeCAD.ActiveDocument.recompute()
        return rectangles
    #endregion