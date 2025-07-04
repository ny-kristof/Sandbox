import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector
from Part import BRepOffsetAPI
from BOPTools import BOPFeatures, SplitFeatures
# from Part import BOPTools
import xml.etree.ElementTree as ET

def createNeighborSubsurfaces(object, edge, resolution = 0.5, radius = 1, aroundVertex = False, measurement_node = None, measurement_group : App.DocumentObject = None):

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
    profile.Shape=circle_wire

    # Create the spine of the sweep that is the selected edge
    spine=doc.addObject("Part::Feature","Spine")
    spine.Shape=path_edge

    # Create the sweep object and the end spheres
    sweep = doc.addObject('Part::Sweep','Sweep')
    sweep.Sections=[profile]
    sweep.Spine=spine
    sweep.Solid=True
    sweep.Frenet=False
    sweep.Transition=2

    if aroundVertex:
        endSphere1 = doc.addObject("Part::Sphere","EndSphere1")
        endSphere1.Label = "EndSphere1"
        endSphere1.Radius = radius
        endSphere1.Placement = App.Placement(start_point, App.Rotation())
        print("Start point: ", start_point)
        
        endSphere2 = doc.addObject("Part::Sphere","EndSphere2")
        endSphere2.Label = "EndSphere2"
        endSphere2.Radius = radius
        endSphere2.Placement = App.Placement(end_point, App.Rotation())
        print("End point: ", end_point)

    # doc.recompute()

        # Create the union of the sweep and the spheres
        bp = BOPFeatures.BOPFeatures(App.activeDocument())
        sweepAndSpheres =  bp.make_multi_fuse(["EndSphere1", "Sweep", "EndSphere2", ])
    else:
        sweepAndSpheres = sweep
    
    print("Selection object: ", object.Name)
    print("Sweep object: ", sweepAndSpheres.Label)
    doc.recompute()
    bp = BOPFeatures.BOPFeatures(App.activeDocument())
    common = bp.make_multi_common([object.Name, sweepAndSpheres.Label])
    doc.recompute()
    mycommon = doc.addObject("Part::Feature", "MyCommon")
    mycommon.Shape = common.Shape

    doc.removeObject(common.Label)
    doc.removeObject(sweepAndSpheres.Label)
    if aroundVertex and endSphere1 and endSphere2: # type: ignore
        doc.removeObject(sweep.Label)
        doc.removeObject(endSphere1.Label) # type: ignore
        doc.removeObject(endSphere2.Label) # type: ignore
    doc.removeObject(profile.Label)
    doc.removeObject(spine.Label)
    object.Visibility = True
    doc.recompute()

    edgeOnCommon = findEdgeOnObject(mycommon.Shape, path_edge)
    edgeOnCommon_obj = doc.addObject("Part::Feature", "EdgeOnCommon")
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
                points, normals = sample_surface_by_spacing(face, resolution, measurement_group = measurement_group)
                if measurement_node is not None:
                    addFaceToMeasurementXML(face, points, normals, measurement_node)
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

def addFaceToMeasurementXML(face, points, normals, measurement_node, point_density = 0.1):
    if measurement_node is None:
        print("Measurement node is None. Cannot add face to XML.")
        return
    face_index = len(measurement_node.findall("Face"))
    face_node = ET.SubElement(measurement_node, "Face")
    face_node.set("type", type(face.Surface).__name__)
    face_node.set("index", str(face_index))
    face_node.set("minimumPointDensity", str(point_density))
    planar = type(face.Surface).__name__ == "Plane"
    if(planar):
        n = face.normalAt(0, 0)
        face_node.set("nx", str(round(n.x, 6)))
        face_node.set("ny", str(round(n.y, 6)))
        face_node.set("nz", str(round(n.z, 6)))
    addNormalsToFaceXML(points, normals, face_node, planar)

def createOffsetToFaces(faces, measurement_group : App.DocumentObject = None, color = (1.0, 0.0, 0.0), offset_value = 0.02):
    doc = App.ActiveDocument
    if doc is None:
        print("No active document. Please open a FreeCAD document.")
        return

    # Create the shell from the faces
    facesToMeasure = Part.makeShell(faces)
    facesToMeasure_obj = doc.addObject("Part::Feature", "FacesToMeasure")
    facesToMeasure_obj.Shape = facesToMeasure
    facesToMeasure_obj.ViewObject.ShapeColor = color  # red
    doc.recompute()

    # Create the offset object
    offset = doc.addObject("Part::Offset", "FacesToMeasureOffset")
    offset.Source = facesToMeasure_obj
    offset.Value = offset_value
    offset.ViewObject.ShapeColor = color
    if measurement_group is not None:
        measurement_group.addObject(offset)
    doc.recompute()






def addNormalsToFaceXML(points, normals, faceNode, planar=False):
    for row_pts, row_nrm in zip(points, normals):
        for p, n in zip(row_pts, row_nrm):
            if p and n:
                sample_node = ET.SubElement(faceNode, "Sample", {
                    "x": f"{p.x:.6f}",
                    "y": f"{p.y:.6f}",
                    "z": f"{p.z:.6f}",
                    # "nx": f"{n.x:.6f}",
                    # "ny": f"{n.y:.6f}",
                    # "nz": f"{n.z:.6f}"
                })
                if not planar:
                    sample_node.set("nx", f"{n.x:.6f}")
                    sample_node.set("ny", f"{n.y:.6f}")
                    sample_node.set("nz", f"{n.z:.6f}")
            # else:
            #     ET.SubElement(faceNode, "Sample")  # Empty sample

def sample_surface_by_spacing(face, spacing_mm = 1.0, measurement_group : App.DocumentObject = None):
    (umin, umax, vmin, vmax) = face.ParameterRange

    # Estimate arc lengths in U and V directions (rough approximation)
    def estimate_length_u(v_const, steps=100):
        points = [face.valueAt(umin + (umax - umin) * i / steps, v_const) for i in range(steps + 1)]
        return sum((points[i+1] - points[i]).Length for i in range(steps))

    def estimate_length_v(u_const, steps=100):
        points = [face.valueAt(u_const, vmin + (vmax - vmin) * i / steps) for i in range(steps + 1)]
        return sum((points[i+1] - points[i]).Length for i in range(steps))

    u_length = estimate_length_u((vmin + vmax) / 2)
    v_length = estimate_length_v((umin + umax) / 2)

    u_count = max(2, int(u_length / spacing_mm) + 1)
    v_count = max(2, int(v_length / spacing_mm) + 1)

    points = []
    normals = []
    lines = []
    #TODO: próbájluk ki, ha megcseréljük a két ciklust.
    for j in range(v_count):
        row_points = []
        row_normals = []
        v = vmin + (vmax - vmin) * j / (v_count - 1)
        for i in range(u_count):
            u = umin + (umax - umin) * i / (u_count - 1)

            if row_points:
                prev_point = next((p for p in reversed(row_points) if p is not None), None)
                # prev_point = row_points[-1]
                if prev_point is not None and (face.valueAt(u, v).sub(prev_point)).Length < spacing_mm:
                    row_points.append(None)
                    row_normals.append(None)
                    continue

            point = face.valueAt(u, v)
            if face.isInside(point, 1e-5, True):
                normal = face.normalAt(u, v)
                line = Part.makeLine(point, point.add(normal))
                lines.append(line)
                row_points.append(point)
                row_normals.append(normal)
            else:
                row_points.append(None)
                row_normals.append(None)
        points.append(row_points)
        normals.append(row_normals)
    normal_lines = Part.Compound(lines)
    normals_obj = App.ActiveDocument.addObject("Part::Feature", "NormalLines")
    normals_obj.Shape = normal_lines
    if measurement_group is not None:
        measurement_group.addObject(normals_obj)
    App.ActiveDocument.recompute()

    return points, normals