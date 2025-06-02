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

# import ptvsd
# print("Waiting for debugger attach")
# # 5678 is the default attach port in the VS Code debug configurations
# ptvsd.enable_attach(address=('localhost', 5678), redirect_output=True)
# ptvsd.wait_for_attach()

class SelectionPlanner:

    def __init__(self, TaskPanel):
        self.Panel = TaskPanel
        self.root_node = ET.Element("Measurements")
        self.measurement_index = 0
        #root_node.set("spacing", str(resolution))

    def getElementsFromSelection(self):
            #selectedElements = []
            self.elementsToMeasure = []
            sel = FreeCADGui.Selection.getSelectionEx()[0]
            if len(sel.SubObjects) > 3:
                QtWidgets.QMessageBox.information(None, "Error", f"Please select maximum 3 elements (face, edge or point). {len(sel.SubObjects)} is currently selected") # type: ignore
            # for sel in selection:
                # if len(sel.SubObjects) >1:
                    # QtWidgets.QMessageBox.information(None, "Error", f"Selected element called {sel.SubObjects[0]} has more than 1 element (face, edge or point)")
                    # print(f"len selection: {len(selection)}")
                    # print(f"len subobjects of sel: {len(sel.SubObjects)}") 
                    # return
            
            self.Panel.textbox.clear()

            if len(sel.SubObjects) == 1:
                if(sel.SubObjects[0].ShapeType == "Edge"):
                    #self.createEdgeExtensionRectangles(sel, sel.SubObjects[0])
                    self.handle1EdgeSelection(sel)
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
                else:
                    QtWidgets.QMessageBox.information(None, "Error","Invalid selection pair.") # type: ignore
                
            self.Panel.textbox.append("Elements to be measured: \n")
            self.displayFaceVertexInfo(self.elementsToMeasure)
            # firstSelection = None
            # for sel in selection:
                # for subobj in sel.SubObjects:
                    # if subobj.ShapeType == "Edge":
                        # if isinstance(curve, Part.Line):
                        # elif isinstance(curve, Part.Circle):
                    # elif subobj.ShapeType == "Vertex":
                    # elif subobj.ShapeType == "Face":

    #region Selection handlers
    def handle1EdgeSelection(self, sel):
        if not sel.SubObjects[0]:
            return
        measurement_node = self.createMeasurementNode()

        SubSurfaceCreator.createNeighborSubsurfaces(sel.Object, sel.SubObjects[0], aroundVertex=True , measurement_node = measurement_node)
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
            faces = [face1, face2]
            for i, face in enumerate(faces):
                points, normals = SubSurfaceCreator.sample_surface_by_spacing(face)
                SubSurfaceCreator.addFaceToMeasurementXML(face, points, normals, measurement_node, i)
                SubSurfaceCreator.createOffsetToFaces(face)
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
        for i, edge in enumerate(sel.SubObjects):
            SubSurfaceCreator.createNeighborSubsurfaces(sel.Object, edge, aroundVertex=False, measurement_node = measurement_node)

        
        for i,face in enumerate(sel.Object.Shape.Faces):
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
        for i, circle in enumerate(sel.SubObjects):
            SubSurfaceCreator.createNeighborSubsurfaces(sel.Object, circle, aroundVertex=False, measurement_node = measurement_node)

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
        for edge in section_obj.Shape.Edges:
            frag_edge = SubSurfaceCreator.findEdgeOnObject(bool_frag.Shape, edge)
            if frag_edge:
                SubSurfaceCreator.createNeighborSubsurfaces(bool_frag, frag_edge, aroundVertex=False, measurement_node = measurement_node)
            else:
                print(f"Edge {edge} not found in boolean fragments shape.")
        SubSurfaceCreator.createNeighborSubsurfaces(sel.Object, circle, aroundVertex=False, measurement_node = measurement_node)
        
        doc.removeObject(bool_frag.Label)
        doc.removeObject(section_obj.Label)
        doc.recompute()




        


    #endregion
    
    #region Helper functions

    def createMeasurementNode(self):
        measurement_node = ET.SubElement(self.root_node, "Measurement")
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

            # rectangle = Draft.make_rectangle(
            #     length=edge_length, 
            #     height=edge_length / 2, 
            #     placement=FreeCAD.Placement(
            #         corner1,#.add(face_normal.normalize().multiply(1/10)), 
            #         FreeCAD.Rotation(FreeCAD.Vector(1,0,0), edge_vector),
            #         #FreeCAD.Rotation(face_normal, edge_vector),
            #         #FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 0.0), # rotation around the edge
            #     )
            # )
            # FreeCAD.ActiveDocument.recompute()
            # rectangle.ViewObject.ShapeColor = (1.0, 0.75, 0.8)  # Pink fill
            # rectangle.ViewObject.LineColor = (1.0, 0.0, 0.0)    # Red outline
            # rectangle.ViewObject.LineWidth = 2.0                # Line width
            # sketch = Draft.make_sketch(rectangle, delete=False, name = "MySketch", tol = 1)
            # FreeCAD.ActiveDocument.recompute()            
            # return


            # sketch = Draft.make_sketch(face)

            # sketch = FreeCAD.ActiveDocument.addObject('Sketcher::SketchObject', 'Sketch')
            # sketch.Placement = FreeCAD.Placement(corner1, FreeCAD.Rotation(face_normal, 0))


            # #sketch_plane = DraftGeomUtils.getPlaneFromFace(face)
            # face_name = None
            # for i, f in enumerate(sel.Object.Shape.Faces):
            #     if f.isSame(face):
            #         face_name = f"Face{i+1}"
            #         print(f"Face name: {face_name}")
            #         break
            # sketch = FreeCAD.ActiveDocument.addObject('Sketcher::SketchObject', 'RectangleSketch')
            # sketch.AttachmentSupport = (sel.Object, face_name)
            # sketch.MapMode = 'FlatFace'

            # # Add the rectangle's corners to the sketch
            # l1 = sketch.addGeometry(Part.LineSegment(corner1, corner2), False)
            # # l2 = sketch.addGeometry(Part.LineSegment(corner2, corner3), False)
            # # l3 = sketch.addGeometry(Part.LineSegment(corner3, corner4), False)
            # # l4 = sketch.addGeometry(Part.LineSegment(corner4, corner1), False)
            # return


            # Add constraints for closed rectangle
            # sketch.addConstraint(Sketcher.Constraint('Coincident', l1, 2, l2, 1))
            # sketch.addConstraint(Sketcher.Constraint('Coincident', l2, 2, l3, 1))
            # sketch.addConstraint(Sketcher.Constraint('Coincident', l3, 2, l4, 1))
            # sketch.addConstraint(Sketcher.Constraint('Coincident', l4, 2, l1, 1))

            # # Set the color of the lines to red
            # for line in [l1, l2, l3, l4]:
            #     sketch.ViewObject.setElementColors(line, (1.0, 0.0, 0.0))  # RGB for red

            # Recompute the document to update the sketch
            #FreeCAD.ActiveDocument.recompute()
            # rectangles.append(rectangle)
            #print(f"created {len(rectangles)} rectangles")

        return rectangles
    
    # def createCircleNeighboringFaces(self, sel, edge):
    #     if isinstance(edge.Curve, Part.Circle):
    #         # Get the circle's center and radius
    #         center = edge.Curve.Center
    #         radius = edge.Curve.Radius
            
    #         # Create a circle face
    #         circle_face = Part.makeCircle(radius, center)
            
    #         # Add the circle face to the FreeCAD document
    #         circle_obj = FreeCAD.ActiveDocument.addObject("Part::Feature", "CircleFace")
    #         circle_obj.Shape = circle_face
            
    #         # Set the face's color
    #         circle_obj.ViewObject.ShapeColor = (0.0, 1.0, 0.0)
    #endregion