import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector
from Part import BRepOffsetAPI
from BOPTools import BOPFeatures, SplitFeatures
# from Part import BOPTools
import xml.etree.ElementTree as ET
from FaceGeometryExporter import addDetailedFaceInfoToXML
import SurfSensePanel

def createNeighborSubsurfaces(object, edge, resolution = 0.5, radius = 1.0, aroundVertex = False, measurement_node = None, measurement_group : App.DocumentObject = None):

    doc = App.ActiveDocument
    if doc is None:
        print("No active document. Please open a FreeCAD document.")
        return
    if not object or not edge:
        print("No object or edge selected. Please select an object and an edge.")
        return

    path_edge = edge
    start_point = path_edge.Vertexes[0].Point
    end_point = None
    if len(path_edge.Vertexes) > 1:
        end_point = path_edge.Vertexes[1].Point
    else:
        aroundVertex = False


    # Create tangent vector at the start of the edge
    uv = path_edge.Curve.parameter(start_point)
    tangentLong = path_edge.tangentAt(uv)
    tangent = tangentLong.normalize()

    # Create the circle as a wire
    circle_edge = Part.makeCircle(radius)#, Vector(0, 0, 0), Vector(0, 0, 1))
    circle_wire = Part.Wire([circle_edge])
    circle_wire.Placement = App.Placement(start_point, App.Rotation(App.Vector(0,0,1), tangent))
    profile = doc.addObject("Part::Feature","MyCircle")
    profile.addProperty("App::PropertyInteger", "SurfSenseID", "Base", "", True)
    profile.SurfSenseID = SurfSensePanel.SurfSensePanel._measurement_count
    profile.Shape=circle_wire

    # Create the spine of the sweep that is the selected edge
    spine=doc.addObject("Part::Feature","Spine")
    spine.addProperty("App::PropertyInteger", "SurfSenseID", "Base", "", True)
    spine.SurfSenseID = SurfSensePanel.SurfSensePanel._measurement_count
    spine.Shape=path_edge

    # Create the sweep object and the end spheres
    sweep = doc.addObject('Part::Sweep','Sweep')
    sweep.addProperty("App::PropertyInteger", "SurfSenseID", "Base", "", True)
    sweep.SurfSenseID = SurfSensePanel.SurfSensePanel._measurement_count
    sweep.Sections=[profile]
    sweep.Spine=spine
    sweep.Solid=True
    sweep.Frenet=False
    sweep.Transition=2

    if aroundVertex and end_point is not None:
    #     endSphere1 = doc.addObject("Part::Sphere","EndSphere1")
    #     endSphere1.addProperty("App::PropertyInteger", "SurfSenseID", "Base", "", True)
    #     endSphere1.SurfSenseID = SurfSensePanel.SurfSensePanel._measurement_count
    #     endSphere1.Label = "EndSphere1"
    #     endSphere1.Radius = radius
    #     endSphere1.Placement = App.Placement(start_point, App.Rotation())
    #     print("Start point: ", start_point)
        
    #     endSphere2 = doc.addObject("Part::Sphere","EndSphere2")
    #     endSphere2.addProperty("App::PropertyInteger", "SurfSenseID", "Base", "", True)
    #     endSphere2.SurfSenseID = SurfSensePanel.SurfSensePanel._measurement_count
    #     endSphere2.Label = "EndSphere2"
    #     endSphere2.Radius = radius
    #     endSphere2.Placement = App.Placement(end_point, App.Rotation())
    #     print("End point: ", end_point)

    # # doc.recompute()

    #     # Create the union of the sweep and the spheres
    #     bp = BOPFeatures.BOPFeatures(App.activeDocument())
    #     try:
    #         sweepAndSpheres =  bp.make_multi_fuse(["EndSphere1", "Sweep", "EndSphere2", ])
    #         doc.recompute()
    #             # Filter out tiny edges before using the shape
    #         if sweepAndSpheres and sweepAndSpheres.Shape:
    #             # Get faces and rebuild
    #             faces = [f for f in sweepAndSpheres.Shape.Faces]
    #             print(f"Number of faces in fused shape: {len(faces)}")
    #             print("faces: ", faces)
    #             try:
    #                 shell = Part.makeShell(faces)
    #                 print("Shell is valid: ", shell.isValid())
    #                 if shell.isValid():
    #                     print("Rebuilding solid from shell.")
    #                     solid = Part.makeSolid(shell)
    #                     sweepAndSpheres.Shape = solid
    #             except Exception as e:
    #                 print(f"Could not rebuild solid: {e}")
    #     except Exception as e:
    #         print("Error occurred while creating union: ", e)
    #         doc.removeObject("EndSphere1")
    #         doc.removeObject("EndSphere2")
    #         sweepAndSpheres = sweep
    #         return
        # Extend the edge by a factor of the radius at both ends
        extension_length = radius  # Extend by the radius amount
        
        # Get direction vectors at both ends
        start_param = path_edge.FirstParameter
        end_param = path_edge.LastParameter
        
        # Get tangent at start (pointing away from edge)
        tangent_start = path_edge.tangentAt(start_param).normalize()
        # Get tangent at end (pointing away from edge)
        tangent_end = path_edge.tangentAt(end_param).normalize()
        
        # Calculate extended points
        extended_start = start_point.add(tangent_start.multiply(-extension_length))
        extended_end = end_point.add(tangent_end.multiply(extension_length))
        
        # Create extended edge by making lines from extended points
        edge_start = Part.makeLine(extended_start, start_point)
        edge_end = Part.makeLine(end_point, extended_end)
        
        # Create extended spine as a wire
        extended_spine_wire = Part.Wire([edge_start, path_edge, edge_end])
        spine.Shape = extended_spine_wire
        
        print("Extended start point: ", extended_start)
        print("Extended end point: ", extended_end)

        # Create the sweep with extended spine
        try:
            doc.recompute()
            sweepAndSpheres = sweep
            
            if not sweepAndSpheres.Shape.isValid():
                print("Extended sweep shape is invalid")
                sweepAndSpheres = sweep
                return
                
        except Exception as e:
            print("Error occurred while creating extended sweep: ", e)
            sweepAndSpheres = sweep
            return
    else:
        sweepAndSpheres = sweep

    doc.recompute()
    
    try:
        # common = bp.make_multi_common([object.Name, sweepAndSpheres.Label])
        common = object.Shape.common(sweepAndSpheres.Shape)
    except Exception as e:
        print("Error occurred while creating common shape: ", e)
        doc.removeObject(sweepAndSpheres.Label)
        return

    doc.recompute()
    mycommon = doc.addObject("Part::Feature", "MyCommon")
    mycommon.addProperty("App::PropertyInteger", "SurfSenseID", "Base", "", True)
    mycommon.SurfSenseID = SurfSensePanel.SurfSensePanel._measurement_count
    mycommon.Shape = common # common.Shape
    doc.recompute()

    doc.removeObject(sweepAndSpheres.Label)
    # if aroundVertex and endSphere1 and endSphere2: # type: ignore
    #     doc.removeObject(sweep.Label)
    #     doc.removeObject(endSphere1.Label) # type: ignore
    #     doc.removeObject(endSphere2.Label) # type: ignore
    doc.removeObject(profile.Label)
    doc.removeObject(spine.Label)
    object.Visibility = True
    doc.recompute()

    edgeOnCommon = findEdgeOnObject(mycommon.Shape, path_edge)
    if edgeOnCommon is None:
        print("No matching edge found on the common shape. The edge might not be part of the common shape.")
        doc.removeObject(mycommon.Label)
        doc.recompute()
        return
    edgeOnCommon_obj = doc.addObject("Part::Feature", "EdgeOnCommon")
    edgeOnCommon_obj.addProperty("App::PropertyInteger", "SurfSenseID", "Base", "", True)
    edgeOnCommon_obj.SurfSenseID = SurfSensePanel.SurfSensePanel._measurement_count
    edgeOnCommon_obj.Shape = edgeOnCommon
    bool_frag = createBoolFragment([edgeOnCommon_obj, mycommon])
    doc.recompute()
    edgeOnCommon = findEdgeOnObject(bool_frag.Shape, path_edge)
    # # for face in mycommon.Shape.Faces:
    # #     print(f"Face {face} isInside selection object: {face.isInside(sel.Object.Shape, 1e-5, True)}")
    # for edge in mycommon.Shape.Edges:
    #     #if edge.isSame(path_edge):
    #     #Bro ezt én írtam, de nem értem elsőre, hogy miért működik. 
    #     # A felső sor helyett van, ami azért nem működik, mert a path_edge nem egyenlő a közös shape edgjeivel, mivel a common művelet nem tökéletesen ugyanazt az élet adja.
    #     if all(any(v.Point.isEqual(ev.Point, 1e-07) for ev in edge.Vertexes) for v in path_edge.Vertexes) and midpoint(edge).isEqual(midpoint(path_edge), 1e-07):  #<-- Ez azért kell, mert a path_edge nem pontosan egyenlő a common shape edgjeivel. Nincs látható lassulás
    #         print("Edge found in common shape!")
    #         edgeOnCommon = edge
    #         break
    elementsToMeasure = []
    print("is edgeOnCommon None: ", edgeOnCommon is None)
    if edgeOnCommon is not None:
        facesOfVertex = []
        if aroundVertex:
            print("Around vertex is True, finding faces of vertexes.")
            for v in edgeOnCommon.Vertexes:
                facesOfVertex.extend(bool_frag.Shape.ancestorsOfType(v, Part.Face))
        else:
            for face in bool_frag.Shape.Faces:
                if any(edgeOnCommon.isPartner(e) for e in face.Edges):
                    facesOfVertex.append(face)
        if not facesOfVertex:
            print("No faces found for the edge on common shape. This might be because the edge is not part of the common shape.")
            return
        for face in facesOfVertex:
            if not any(face.isSame(f) for f in elementsToMeasure):
                elementsToMeasure.append(face)
                result = sample_surface_by_spacing(face, resolution, measurement_group = measurement_group, detailOutline=True)
                if measurement_node is not None:
                    addFaceToMeasurementXML(face, result, measurement_node)
    if not elementsToMeasure:
        print("No faces found for the edge on common shape. This might be because the edge is not part of the common shape.")
        return
    print("Number of elements to measure: ", len(elementsToMeasure))
    createOffsetToFaces(elementsToMeasure, measurement_group=measurement_group)
    doc.removeObject(bool_frag.Label)
    doc.removeObject(mycommon.Label)
    doc.removeObject(edgeOnCommon_obj.Label)
    doc.recompute()

def findEdgeOnObject(shape, edge):
    """
    Finds an edge in a shape that matches the given edge.
    This function checks if the edge is present in the shape's edges.
    """
    for e in shape.Edges:
        if all(any(v.Point.isEqual(ev.Point, 1e-07) for ev in e.Vertexes) for v in edge.Vertexes) and midpoint(e).isEqual(midpoint(edge), 1e-07):
            return e
    return None

def createBoolFragment(objectlist = []):
    bool_frag = SplitFeatures.makeBooleanFragments(name="BooleanFragments")
    bool_frag.Objects = objectlist
    bool_frag.Mode = 'CompSolid'
    bool_frag.Proxy.execute(bool_frag)
    return bool_frag
    
    


def midpoint(edge):
    return edge.Curve.value((edge.FirstParameter + edge.LastParameter) / 2)

def addFaceToMeasurementXML(face, result, measurement_node, point_density = 0.1, addGeometry = True):
    if measurement_node is None:
        print("Measurement node is None. Cannot add face to XML.")
        return
    global_placement = Gui.Selection.getSelection()[0].getGlobalPlacement() if Gui.Selection.getSelection() else None
    face_index = len(measurement_node.findall("Face"))
    face_node = ET.SubElement(measurement_node, "Face")
    face_node.set("type", type(face.Surface).__name__)
    face_node.set("index", str(face_index))
    face_node.set("minimumPointDensity", str(point_density))
    planar = type(face.Surface).__name__ == "Plane"
    if(planar):
        n = global_placement.Rotation.Matrix.multVec(face.normalAt(0, 0)) if global_placement else face.normalAt(0, 0)
        face_node.set("nx", str(round(n.x, 6)))
        face_node.set("ny", str(round(n.y, 6)))
        face_node.set("nz", str(round(n.z, 6)))
    
    if addGeometry:
        # Add geometry information
        geometry_node = ET.SubElement(face_node, "Geometry")
        try:
            addDetailedFaceInfoToXML(geometry_node, face, global_placement)
        except Exception as e:
            print(f"Error in addDetailedFaceInfoToXML: {e}")
    
    # If there are only inside points, add them directly under face_node
    if result['inside_points'] and not result['outline_points']:
        addNormalsToFaceXML(result['inside_points'], result['inside_normals'], face_node, planar)
    else:
        # Create separate nodes for outline and shape points
        outline_node = ET.SubElement(face_node, "Outline")
        shape_node = ET.SubElement(face_node, "Shape")
        
        # Add outline points
        if result['outline_points']:
            addNormalsToFaceXML(result['outline_points'], result['outline_normals'], outline_node, planar)
        
        # Add shape points
        if result['inside_points']:
            addNormalsToFaceXML(result['inside_points'], result['inside_normals'], shape_node, planar)

def createOffsetToFaces(faces, measurement_group : App.DocumentObject = None, color = (1.0, 0.0, 0.0), offset_value = 0.02):
    doc = App.ActiveDocument
    if doc is None:
        print("No active document. Please open a FreeCAD document.")
        return
    selection = Gui.Selection.getSelection()[0] if Gui.Selection.getSelection() else None
    global_placement = selection.getGlobalPlacement() if selection and selection.Placement != selection.getGlobalPlacement() else None

    # Create the shell from the faces
    facesToMeasure = Part.makeShell(faces)
    facesToMeasure_obj = doc.addObject("Part::Feature", "FacesToMeasure")
    facesToMeasure_obj.addProperty("App::PropertyInteger", "SurfSenseID", "Base", "", True)
    facesToMeasure_obj.SurfSenseID = SurfSensePanel.SurfSensePanel._measurement_count
    facesToMeasure_obj.Shape = facesToMeasure
    facesToMeasure_obj.ViewObject.ShapeColor = color  # red
    if global_placement is not None:
        facesToMeasure_obj.Placement = facesToMeasure_obj.Placement.multiply(global_placement)
    if measurement_group is not None:
        measurement_group.addObject(facesToMeasure_obj)
    doc.recompute()
    try:
        # Create the offset object
        doc.openTransaction("Create Offset Object")
        offset = doc.addObject("Part::Offset", "FacesToMeasureOffset")
        offset.addProperty("App::PropertyInteger", "SurfSenseID", "Base", "", True)
        offset.SurfSenseID = SurfSensePanel.SurfSensePanel._measurement_count
        offset.Source = facesToMeasure_obj
        offset.Value = offset_value
        # offset_shape = facesToMeasure_obj.Shape.makeOffsetShape(offset_value, 0.01)
        # offset.Shape = offset_shape
        offset.ViewObject.ShapeColor = color
        if not offset.isValid():
            print("Offset object is not valid. Please check the input faces and offset value.")
            doc.removeObject(offset.Label)
            doc.abortTransaction()
            return
        if measurement_group is not None:
            measurement_group.addObject(offset)
        
        doc.commitTransaction()
        doc.recompute()
    except Exception as e:
        print("Error occurred while creating offset object:", e)
        doc.abortTransaction()
        return

def addNormalsToFaceXML(points, normals, faceNode, planar=False):
    """Add samples to a given XML node (either Outline or Shape)"""
    for p, n in zip(points, normals):
        if p and n:
            sample_node = ET.SubElement(faceNode, "Sample", {
                "x": f"{p.x:.6f}",
                "y": f"{p.y:.6f}",
                "z": f"{p.z:.6f}",
            })
            if not planar:
                sample_node.set("nx", f"{n.x:.6f}")
                sample_node.set("ny", f"{n.y:.6f}")
                sample_node.set("nz", f"{n.z:.6f}")

# def addNormalsToFaceXML(points, normals, faceNode, planar=False):
#     # Legacy function - kept for compatibility but functionality moved to addFaceToMeasurementXML
#     # This function is now deprecated and should not be used
#     pass

def sample_surface_by_spacing(face, spacing_mm = 1.0, measurement_group : App.DocumentObject = None, displayNormals : bool = True, detailOutline : bool = False):
    (umin, umax, vmin, vmax) = face.ParameterRange
    selected_object = Gui.Selection.getSelection()[0] if Gui.Selection.getSelection() else None
    global_placement = selected_object.getGlobalPlacement() if selected_object and selected_object.Placement != selected_object.getGlobalPlacement() else None
    print(f"global_placement: {global_placement}")

    outline_points = []
    outline_normals = []
    inside_points = []
    inside_normals = []
    lines = []
    
    if detailOutline:
        # Sample edges using discretise function
        for edge in face.Edges:
            # Discretise the edge based on spacing_mm
            edge_length = edge.Length
            if edge_length < 1e-3:
                print(f"Edge {edge} is too short to discretize. Skipping.")
                continue
            num_points = max(2, int(edge_length / spacing_mm) + 1)
            discretized_points = edge.discretize(num_points)
            
            for point in discretized_points:
                # Transform point if global placement exists
                transformed_point = global_placement.Matrix.multVec(point) if global_placement else point
                
                # Find UV parameters for the point on the face surface
                try:
                    # Project the point onto the face to get UV parameters
                    u, v = face.Surface.parameter(point)
                    normal = face.normalAt(u, v)
                except:
                    # Fallback: find closest point on face
                    closest_point, u, v = face.Surface.projectPoint(point)
                    normal = face.normalAt(u, v)
                
                transformed_normal = global_placement.Rotation.multVec(normal) if global_placement else normal
                
                outline_points.append(transformed_point)
                outline_normals.append(transformed_normal)
                
                if displayNormals:
                    line = Part.makeLine(transformed_point, transformed_point.add(transformed_normal))
                    lines.append(line)
        
        # Sample inside the face with 10x lower resolution (higher spacing)
        inside_spacing = spacing_mm * 5.0
    else:
        # Original implementation - treat all points as inside points
        inside_spacing = spacing_mm

    # Estimate arc lengths in U and V directions (rough approximation)
    def estimate_length_u(v_const, steps=100):
        points = [face.valueAt(umin + (umax - umin) * i / steps, v_const) for i in range(steps + 1)]
        return sum((points[i+1] - points[i]).Length for i in range(steps))

    def estimate_length_v(u_const, steps=100):
        points = [face.valueAt(u_const, vmin + (vmax - vmin) * i / steps) for i in range(steps + 1)]
        return sum((points[i+1] - points[i]).Length for i in range(steps))

    u_length = estimate_length_u((vmin + vmax) / 2)
    v_length = estimate_length_v((umin + umax) / 2)

    u_count = max(2, int(u_length / inside_spacing) + 1)
    v_count = max(2, int(v_length / inside_spacing) + 1)
    
    # Sample inside points
    for j in range(v_count):
        v = vmin + (vmax - vmin) * j / (v_count - 1)
        for i in range(u_count):
            u = umin + (umax - umin) * i / (u_count - 1)

            point = face.valueAt(u, v)
            
            # Check if point is inside the face
            if face.isInside(point, 1e-5, True):
                # For detailOutline mode, check distance from edges to avoid duplication
                if detailOutline:
                    min_edge_distance = float('inf')
                    for edge in face.Edges:
                        edge_distance = edge.distToShape(Part.Vertex(point))[0]
                        min_edge_distance = min(min_edge_distance, edge_distance)
                    
                    # Only include if sufficiently far from edges
                    if min_edge_distance > spacing_mm * 0.5:
                        transformed_point = global_placement.Matrix.multVec(point) if global_placement else point
                        normal = face.normalAt(u, v)
                        transformed_normal = global_placement.Rotation.multVec(normal) if global_placement else normal
                        
                        inside_points.append(transformed_point)
                        inside_normals.append(transformed_normal)
                        
                        if displayNormals:
                            line = Part.makeLine(transformed_point, transformed_point.add(transformed_normal))
                            lines.append(line)
                else:
                    # Original behavior for non-detailOutline mode
                    transformed_point = global_placement.Matrix.multVec(point) if global_placement else point
                    normal = face.normalAt(u, v)
                    transformed_normal = global_placement.Rotation.multVec(normal) if global_placement else normal
                    
                    # Apply spacing check for original behavior
                    should_add = True
                    if inside_points:
                        # Check distance to previous points
                        for prev_point in reversed(inside_points):
                            if (transformed_point.sub(prev_point)).Length < inside_spacing:
                                should_add = False
                                break
                    
                    if should_add:
                        inside_points.append(transformed_point)
                        inside_normals.append(transformed_normal)
                        
                        if displayNormals:
                            line = Part.makeLine(transformed_point, transformed_point.add(transformed_normal))
                            lines.append(line)
    
    if displayNormals and lines:
        normal_lines = Part.Compound(lines)
        normals_obj = App.ActiveDocument.addObject("Part::Feature", "NormalLines")
        normals_obj.addProperty("App::PropertyInteger", "SurfSenseID", "Base", "", True)
        normals_obj.SurfSenseID = SurfSensePanel.SurfSensePanel._measurement_count
        normals_obj.Shape = normal_lines
        if measurement_group is not None:
            measurement_group.addObject(normals_obj)
        App.ActiveDocument.recompute()

    return {
        'outline_points': outline_points,
        'outline_normals': outline_normals,
        'inside_points': inside_points,
        'inside_normals': inside_normals
    }