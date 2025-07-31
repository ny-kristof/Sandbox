import FreeCAD
import FreeCADGui
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

def add_selected_LCS_to_xml(xml_node):
    """
    Adds a new node 'SelectedCoordinateSystems' under xml_node,
    and writes all placements from the selected FreeCAD objects as subnodes.
    """
    placements = []
    doc = FreeCAD.ActiveDocument
    if doc is None:
        return
    selection = FreeCADGui.Selection.getSelection()
    if not selection:
        FreeCAD.Console.PrintError("No objects selected.\n")
        return
    print(f"Selected {len(selection)} objects for coordinate system export.")
    
    # Build kinematic chain: each sel's transformation is relative to the previous one (first is workspace center)
    prev_placement = None
    for idx, sel in enumerate(selection):
        if (sel.TypeId == "Part::LocalCoordinateSystem" or sel.TypeId == "App::Origin" or sel.TypeId == "App::Part") and hasattr(sel, "Placement"):
            pl = sel.getGlobalPlacement() if hasattr(sel, 'getGlobalPlacement') else sel.Placement
            if prev_placement is None:
                print(f"First selected object: {sel.Name}")
                # First: relative to workspace (global)
                rel_pl = pl
            else:
                print(f"Selected object {idx+1}: {sel.Name}, relative to previous: {selection[idx-1].Name}")
                # Relative to previous: rel = prev.inverse() * current
                rel_pl = prev_placement.inverse().multiply(pl)
            pos = rel_pl.Base
            rot = rel_pl.Rotation.toMatrix()
            placements.append({
                'name': sel.Label if hasattr(sel, 'Label') else sel.Name,
                'reference': getattr(selection[idx-1], 'Label', '') if idx > 0 else '0',
                'position': [pos.x, pos.y, pos.z],
                'rotation_matrix': [
                    [rot.A11, rot.A12, rot.A13],
                    [rot.A21, rot.A22, rot.A23],
                    [rot.A31, rot.A32, rot.A33]
                ]
            })
            prev_placement = pl
    print(f"Collected {len(placements)} placements from selected objects.")

    
    # Try to find existing "CoordinateSystems" node, else create it
    cs_node = None
    for child in xml_node:
        if child.tag == "CoordinateSystems":
            cs_node = child
            break
    if cs_node is None:
        cs_node = ET.SubElement(xml_node, "CoordinateSystems")

    print(f"Adding {len(placements)} placements to 'CoordinateSystems' node.")

    # Add each placement as a subnode
    for placement in placements:
        p_node = ET.SubElement(cs_node, "CoordinateSystem", name=placement.get('name', ''), reference=placement.get('reference', '0'))

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