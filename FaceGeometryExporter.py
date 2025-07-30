import FreeCAD as App
import FreeCADGui as Gui
import Part
from FreeCAD import Vector
import xml.etree.ElementTree as ET
import math

def addDetailedFaceInfoToXML(xml_node, face, global_placement=None):
    """
    Extends XML node with detailed geometric information about a FreeCAD face.
    
    Args:
        xml_node: XML ElementTree node to add information to
        face: FreeCAD Part.Face object to analyze
    """
    if xml_node is None or face is None:
        print("XML node or face is None. Cannot add detailed face information.")
        return
    
    # Get global placement for coordinate transformation
    # selected_object = Gui.Selection.getSelection()[0] if Gui.Selection.getSelection() else None
    # global_placement = selected_object.getGlobalPlacement() if selected_object and selected_object.Placement != selected_object.getGlobalPlacement() else None
    
    # Add face type and basic properties
    # surface_type = type(face.Surface).__name__
    # xml_node.set("surfaceType", surface_type)
    xml_node.set("area", f"{face.Area:.6f}")
    xml_node.set("edgeCount", str(len(face.Edges)))
    
    # Add detailed surface parameters based on type
    _addSurfaceParameters(xml_node, face, global_placement)
    
    # Add edge information
    edges_node = ET.SubElement(xml_node, "Edges")
    for i, edge in enumerate(face.Edges):
        _addEdgeInfo(edges_node, edge, i, global_placement)

def _addSurfaceParameters(xml_node, face, global_placement=None):
    """Add surface-specific geometric parameters to XML node"""
    surface = face.Surface
    surface_type = type(surface).__name__
    
    if surface_type == "Plane":
        _addPlaneParameters(xml_node, surface, global_placement)
    elif surface_type == "Cylinder":
        _addCylinderParameters(xml_node, surface, face, global_placement)
    elif surface_type == "Sphere":
        _addSphereParameters(xml_node, surface, global_placement)
    elif surface_type == "Cone":
        _addConeParameters(xml_node, surface, global_placement)
    elif surface_type == "Torus":
        _addTorusParameters(xml_node, surface, global_placement)
    elif surface_type == "BSplineSurface":
        _addBSplineParameters(xml_node, surface, global_placement)
    else:
        pass # For unsupported types, we can skip or log a warning
        # For other surface types, add parameter range
        # umin, umax, vmin, vmax = face.ParameterRange
        # xml_node.set("uMin", f"{umin:.6f}")
        # xml_node.set("uMax", f"{umax:.6f}")
        # xml_node.set("vMin", f"{vmin:.6f}")
        # xml_node.set("vMax", f"{vmax:.6f}")

def _addPlaneParameters(xml_node, plane, global_placement=None):
    pass  # Placeholder for plane parameters
    """Add plane-specific parameters"""
    # Get plane position and normal
    # position = plane.Position
    # normal = plane.Axis
    
    # # Transform if global placement exists
    # if global_placement:
    #     position = global_placement.Matrix.multVec(position)
    #     normal = global_placement.Rotation.multVec(normal)
    
    # xml_node.set("positionX", f"{position.x:.6f}")
    # xml_node.set("positionY", f"{position.y:.6f}")
    # xml_node.set("positionZ", f"{position.z:.6f}")
    # xml_node.set("normalX", f"{normal.x:.6f}")
    # xml_node.set("normalY", f"{normal.y:.6f}")
    # xml_node.set("normalZ", f"{normal.z:.6f}")

def _addCylinderParameters(xml_node, cylinder, face, global_placement=None):
    """Add cylinder-specific parameters"""
    # Get cylinder axis, position, and radius
    axis = cylinder.Axis
    position = cylinder.Center
    radius = cylinder.Radius
    
    # Calculate cylinder height from face parameter range
    umin, umax, vmin, vmax = face.ParameterRange
    # For cylinders, one parameter (usually V) represents the height
    height = vmax - vmin
    
    # Transform if global placement exists
    if global_placement:
        position = global_placement.Matrix.multVec(position)
        axis = global_placement.Rotation.multVec(axis)
    
    xml_node.set("centerX", f"{position.x:.6f}")
    xml_node.set("centerY", f"{position.y:.6f}")
    xml_node.set("centerZ", f"{position.z:.6f}")
    xml_node.set("axisX", f"{axis.x:.6f}")
    xml_node.set("axisY", f"{axis.y:.6f}")
    xml_node.set("axisZ", f"{axis.z:.6f}")
    xml_node.set("radius", f"{radius:.6f}")
    xml_node.set("height", f"{height:.6f}")

def _addSphereParameters(xml_node, sphere, global_placement=None):
    """Add sphere-specific parameters"""
    # Get sphere center and radius
    center = sphere.Center
    radius = sphere.Radius
    
    # Transform if global placement exists
    if global_placement:
        center = global_placement.Matrix.multVec(center)
    
    xml_node.set("centerX", f"{center.x:.6f}")
    xml_node.set("centerY", f"{center.y:.6f}")
    xml_node.set("centerZ", f"{center.z:.6f}")
    xml_node.set("radius", f"{radius:.6f}")

def _addConeParameters(xml_node, cone, global_placement=None):
    """Add cone-specific parameters"""
    # Get cone parameters
    apex = cone.Apex
    center = cone.Center  # Center of the base circle
    axis = cone.Axis
    semi_angle = cone.SemiAngle
    radius = cone.Radius
    height = center.sub(apex).Length  # Height is the distance from apex to center
    
    # Transform if global placement exists
    if global_placement:
        apex = global_placement.Matrix.multVec(apex)
        center = global_placement.Matrix.multVec(center)
        axis = global_placement.Rotation.multVec(axis)
    
    xml_node.set("apexX", f"{apex.x:.6f}")
    xml_node.set("apexY", f"{apex.y:.6f}")
    xml_node.set("apexZ", f"{apex.z:.6f}")
    xml_node.set("centerX", f"{center.x:.6f}")
    xml_node.set("centerY", f"{center.y:.6f}")
    xml_node.set("centerZ", f"{center.z:.6f}")
    xml_node.set("axisX", f"{axis.x:.6f}")
    xml_node.set("axisY", f"{axis.y:.6f}")
    xml_node.set("axisZ", f"{axis.z:.6f}")
    xml_node.set("radius", f"{radius:.6f}")
    xml_node.set("height", f"{height:.6f}")
    xml_node.set("semiAngle", f"{math.degrees(semi_angle):.6f}")

def _addTorusParameters(xml_node, torus, global_placement=None):
    """Add torus-specific parameters"""
    # Get torus parameters
    center = torus.Center
    axis = torus.Axis
    major_radius = torus.MajorRadius
    minor_radius = torus.MinorRadius
    
    # Transform if global placement exists
    if global_placement:
        center = global_placement.Matrix.multVec(center)
        axis = global_placement.Rotation.multVec(axis)
    
    xml_node.set("centerX", f"{center.x:.6f}")
    xml_node.set("centerY", f"{center.y:.6f}")
    xml_node.set("centerZ", f"{center.z:.6f}")
    xml_node.set("axisX", f"{axis.x:.6f}")
    xml_node.set("axisY", f"{axis.y:.6f}")
    xml_node.set("axisZ", f"{axis.z:.6f}")
    xml_node.set("majorRadius", f"{major_radius:.6f}")
    xml_node.set("minorRadius", f"{minor_radius:.6f}")

def _addBSplineParameters(xml_node, bspline, global_placement=None):
    """Add B-spline surface parameters"""
    xml_node.set("uDegree", str(bspline.UDegree))
    xml_node.set("vDegree", str(bspline.VDegree))
    xml_node.set("uKnotCount", str(len(bspline.getUKnots())))
    xml_node.set("vKnotCount", str(len(bspline.getVKnots())))
    xml_node.set("controlPointsU", str(bspline.NbUPoles))
    xml_node.set("controlPointsV", str(bspline.NbVPoles))

def _addEdgeInfo(edges_node, edge, edge_index, global_placement=None):
    """Add detailed information about an edge to the XML"""
    edge_node = ET.SubElement(edges_node, "Edge")
    edge_node.set("index", str(edge_index))
    edge_node.set("length", f"{edge.Length:.6f}")
    
    # Determine edge type and add specific parameters
    curve = edge.Curve
    curve_type = type(curve).__name__
    edge_node.set("curveType", curve_type)
    
    if curve_type == "Line" or curve_type == "LineSegment":
        _addLineEdgeInfo(edge_node, edge, global_placement)
    elif curve_type == "Circle":
        _addCircleEdgeInfo(edge_node, edge, global_placement)
    elif curve_type == "Ellipse":
        _addEllipseEdgeInfo(edge_node, edge, global_placement)
    elif curve_type == "BSplineCurve":
        _addBSplineEdgeInfo(edge_node, edge, global_placement)
    else:
        # For other curve types, add start and end points
        _addGenericEdgeInfo(edge_node, edge, global_placement)

def _addLineEdgeInfo(edge_node, edge, global_placement=None):
    """Add line edge specific information"""
    start_point = edge.Vertexes[0].Point
    end_point = edge.Vertexes[1].Point
    
    # Transform points if global placement exists
    if global_placement:
        start_point = global_placement.Matrix.multVec(start_point)
        end_point = global_placement.Matrix.multVec(end_point)
    
    edge_node.set("startX", f"{start_point.x:.6f}")
    edge_node.set("startY", f"{start_point.y:.6f}")
    edge_node.set("startZ", f"{start_point.z:.6f}")
    edge_node.set("endX", f"{end_point.x:.6f}")
    edge_node.set("endY", f"{end_point.y:.6f}")
    edge_node.set("endZ", f"{end_point.z:.6f}")
    
    # # Add direction vector
    # direction = end_point.sub(start_point).normalize()
    # edge_node.set("directionX", f"{direction.x:.6f}")
    # edge_node.set("directionY", f"{direction.y:.6f}")
    # edge_node.set("directionZ", f"{direction.z:.6f}")

def _addCircleEdgeInfo(edge_node, edge, global_placement=None):
    """Add circle edge specific information"""
    circle = edge.Curve
    center = circle.Center
    radius = circle.Radius
    axis = circle.Axis
    
    # Transform if global placement exists
    if global_placement:
        center = global_placement.Matrix.multVec(center)
        axis = global_placement.Rotation.multVec(axis)
    
    edge_node.set("centerX", f"{center.x:.6f}")
    edge_node.set("centerY", f"{center.y:.6f}")
    edge_node.set("centerZ", f"{center.z:.6f}")
    edge_node.set("radius", f"{radius:.6f}")
    edge_node.set("axisX", f"{axis.x:.6f}")
    edge_node.set("axisY", f"{axis.y:.6f}")
    edge_node.set("axisZ", f"{axis.z:.6f}")
    
    # Add start and end points for arc segments
    if len(edge.Vertexes) >= 2:
        start_point = edge.Vertexes[0].Point
        end_point = edge.Vertexes[1].Point
        
        if global_placement:
            start_point = global_placement.Matrix.multVec(start_point)
            end_point = global_placement.Matrix.multVec(end_point)
        
        edge_node.set("startX", f"{start_point.x:.6f}")
        edge_node.set("startY", f"{start_point.y:.6f}")
        edge_node.set("startZ", f"{start_point.z:.6f}")
        edge_node.set("endX", f"{end_point.x:.6f}")
        edge_node.set("endY", f"{end_point.y:.6f}")
        edge_node.set("endZ", f"{end_point.z:.6f}")
        
        # Calculate arc angle
        start_param = circle.parameter(edge.Vertexes[0].Point)
        end_param = circle.parameter(edge.Vertexes[1].Point)
        arc_angle = abs(end_param - start_param)
        edge_node.set("arcAngle", f"{math.degrees(arc_angle):.6f}")

def _addEllipseEdgeInfo(edge_node, edge, global_placement=None):
    """Add ellipse edge specific information"""
    ellipse = edge.Curve
    center = ellipse.Center
    major_radius = ellipse.MajorRadius
    minor_radius = ellipse.MinorRadius
    axis = ellipse.Axis
    
    # Transform if global placement exists
    if global_placement:
        center = global_placement.Matrix.multVec(center)
        axis = global_placement.Rotation.multVec(axis)
    
    edge_node.set("centerX", f"{center.x:.6f}")
    edge_node.set("centerY", f"{center.y:.6f}")
    edge_node.set("centerZ", f"{center.z:.6f}")
    edge_node.set("majorRadius", f"{major_radius:.6f}")
    edge_node.set("minorRadius", f"{minor_radius:.6f}")
    edge_node.set("axisX", f"{axis.x:.6f}")
    edge_node.set("axisY", f"{axis.y:.6f}")
    edge_node.set("axisZ", f"{axis.z:.6f}")
    
    # Add start and end points for ellipse segments
    _addGenericEdgeInfo(edge_node, edge, global_placement)

def _addBSplineEdgeInfo(edge_node, edge, global_placement=None):
    """Add B-spline edge specific information"""
    bspline = edge.Curve
    edge_node.set("degree", str(bspline.Degree))
    edge_node.set("knotCount", str(len(bspline.getKnots())))
    edge_node.set("poleCount", str(bspline.NbPoles))
    edge_node.set("rational", str(bspline.isRational()))
    
    # Add start and end points
    _addGenericEdgeInfo(edge_node, edge, global_placement)

def _addGenericEdgeInfo(edge_node, edge, global_placement=None):
    """Add generic edge information (start/end points) for any edge type"""
    if len(edge.Vertexes) >= 1:
        start_point = edge.Vertexes[0].Point
        if global_placement:
            start_point = global_placement.Matrix.multVec(start_point)
        
        edge_node.set("startX", f"{start_point.x:.6f}")
        edge_node.set("startY", f"{start_point.y:.6f}")
        edge_node.set("startZ", f"{start_point.z:.6f}")
    
    if len(edge.Vertexes) >= 2:
        end_point = edge.Vertexes[1].Point
        if global_placement:
            end_point = global_placement.Matrix.multVec(end_point)
        
        edge_node.set("endX", f"{end_point.x:.6f}")
        edge_node.set("endY", f"{end_point.y:.6f}")
        edge_node.set("endZ", f"{end_point.z:.6f}")

# def extendFaceXMLWithGeometry(face, measurement_node):
#     """
#     Convenience function to extend existing face XML nodes with detailed geometry.
#     This can be used to update existing XML structures created by other parts of the system.
    
#     Args:
#         face: FreeCAD Part.Face object to analyze
#         measurement_node: XML node containing Face elements to extend
#     """
#     if measurement_node is None or face is None:
#         print("Measurement node or face is None. Cannot extend XML.")
#         return
    
#     # Find all Face nodes and extend the last one (assuming it corresponds to the current face)
#     face_nodes = measurement_node.findall("Face")
#     if face_nodes:
#         last_face_node = face_nodes[-1]
#         addDetailedFaceInfoToXML(last_face_node, face)
#     else:
#         print("No Face nodes found in measurement XML to extend.")
