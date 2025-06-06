import FreeCAD
import xml.etree.ElementTree as ET

def collect_placements_from_active_doc():
    """
    Collects placement data from all coordinate system objects in the active FreeCAD document.
    Returns a list of dicts with keys: 'name', 'position', 'rotation_matrix'.
    """
    placements = []
    doc = FreeCAD.ActiveDocument
    if doc is None:
        return placements
    for obj in doc.Objects:
        # Only collect objects of type 'Part::CoordinateSystem'
        if obj.TypeId == "Part::LocalCoordinateSystem" and hasattr(obj, "Placement"):
            pl = obj.Placement
            pos = pl.Base
            rot = pl.Rotation.toMatrix()
            placements.append({
                'name': obj.Name,
                'position': [pos.x, pos.y, pos.z],
                'rotation_matrix': [
                    [rot.A11, rot.A12, rot.A13],
                    [rot.A21, rot.A22, rot.A23],
                    [rot.A31, rot.A32, rot.A33]
                ]
            })
    return placements

def add_coordinate_systems_to_xml(xml_node):
    """
    Adds a new node 'CoordinateSystems' under xml_node,
    and writes all placements from the active FreeCAD document as subnodes.
    """
    placements = collect_placements_from_active_doc()
    cs_node = ET.SubElement(xml_node, "CoordinateSystems")
    for placement in placements:
        p_node = ET.SubElement(cs_node, "CoordinateSystem", name=placement.get('name', ''))
        
        # Replace -0.0 with 0.0 in position and rotation_matrix
        placement['position'] = [0.0 if round(coord,1) == -0.0 else coord for coord in placement['position']]
        placement['rotation_matrix'] = [
            [0.0 if round(val,1) == -0.0 else val for val in row]
            for row in placement['rotation_matrix']
        ]

        ET.SubElement(p_node, "Position").text = "[" + ",".join(str(round(coord, 2)) for coord in placement.get('position', [0, 0, 0])) + "]"
        ET.SubElement(
            p_node, "Rotation"
        ).text = ",".join(
            "[" + ",".join(str(round(val, 2)) for val in row) + "]"
            for row in placement.get('rotation_matrix', [[0, 0, 0], [0, 0, 0], [0, 0, 0]])
        )