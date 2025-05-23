import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector
from Part import BRepOffsetAPI
from BOPTools import BOPFeatures
import xml.etree.ElementTree as ET

def createNeighborSubsurfaces(sel, edge, resolution = 0.5, radius = 1, aroundVertex = False, measurement_node = None):

    doc = App.ActiveDocument
    if doc is None:
        print("No active document. Please open a FreeCAD document.")
        return
    if not sel or not sel.SubObjects:
        print("No subobject selected. Please select a subobject.")
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
        sweepAndSpheres =  bp.make_multi_fuse(["Sweep", "EndSphere1", "EndSphere2", ])
    else:
        sweepAndSpheres = sweep

    print("Selection object: ", sel.Object.Name)
    print("Sweep object: ", sweepAndSpheres.Label)
    doc.recompute()
    bp = BOPFeatures.BOPFeatures(App.activeDocument())
    common = bp.make_multi_common([sel.Object.Name, sweepAndSpheres.Label])
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
    sel.Object.Visibility = True
    doc.recompute()

    def midpoint(edge):
        return edge.Curve.value((edge.FirstParameter + edge.LastParameter) / 2)
    edgeOnCommon = None
    for edge in mycommon.Shape.Edges:
        #if edge.isSame(path_edge):
        #Bro ezt én írtam, de nem értem elsőre, hogy miért működik. 
        # A felső sor helyett van, ami azért nem működik, mert a path_edge nem egyenlő a közös shape edgjeivel, mivel a common művelet nem tökéletesen ugyanazt az élet adja.
        if all(any(v.Point.isEqual(ev.Point, 1e-07) for ev in edge.Vertexes) for v in path_edge.Vertexes) and midpoint(edge).isEqual(midpoint(path_edge), 1e-07):  #<-- Ez azért kell, mert a path_edge nem pontosan egyenlő a common shape edgjeivel. Nincs látható lassulás
            print("Edge found in common shape!")
            edgeOnCommon = edge
            break
    elementsToMeasure = []
    print("is edgeOnCommon None: ", edgeOnCommon is None)
    if edgeOnCommon is not None:
        face_index = 0
        for v in edgeOnCommon.Vertexes:
            facesOfVertex = mycommon.Shape.ancestorsOfType(v, Part.Face)
            print(f"number of faces of vertex {v}: ", len(facesOfVertex))
            for face in facesOfVertex:
                if not any(face.isSame(f) for f in elementsToMeasure) and (aroundVertex or any(edgeOnCommon.isSame(e) for e in face.Edges)):
                    elementsToMeasure.append(face)
                    print("class of face: ", type(face.Surface).__name__)
                    points, normals = sample_surface_by_spacing(face, resolution)
                    addFaceToMeasurementXML(face, points, normals, measurement_node, face_index)
                    face_index += 1
    print("Number of elements to measure: ", len(elementsToMeasure))
    createOffsetToFaces(elementsToMeasure)
    doc.removeObject(mycommon.Label)
    doc.recompute()

def addFaceToMeasurementXML(face, points, normals, measurement_node, face_index, point_density = 0.1):
    if measurement_node is None:
        print("Measurement node is None. Cannot add face to XML.")
        return
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

def createOffsetToFaces(faces, color = (1.0, 0.0, 0.0), offset_value = 0.02):
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

def sample_surface_by_spacing(face, spacing_mm = 1.0):
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

    for i in range(u_count):
        u = umin + (umax - umin) * i / (u_count - 1)
        row_points = []
        row_normals = []
        for j in range(v_count):
            v = vmin + (vmax - vmin) * j / (v_count - 1)
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
    App.ActiveDocument.recompute()

    return points, normals