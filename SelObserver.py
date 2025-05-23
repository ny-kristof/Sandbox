# -*- coding: utf-8 -*-
# causes an action to the mouse click on an object
# This function remains resident (in memory) with the function "addObserver(s)"
# "removeObserver(s) # Uninstalls the resident function
import FreeCAD as App
import FreeCADGui

class SelObserver:
#    def setPreselection(self,doc,obj,sub):                # Preselection object
#        App.Console.PrintMessage(str(sub)+ "\n")          # The part of the object name

    def addSelection(self,doc,obj,sub,pnt):               # Selection object
        App.Console.PrintMessage("addSelection"+ "\n")
        App.Console.PrintMessage("Document name: " + str(doc)+ "\n")          # Name of the document
        App.Console.PrintMessage("Object name: " + str(obj)+ "\n")          # Name of the object
        App.Console.PrintMessage("Object part name: " + str(sub)+ "\n")          # The part of the object name
#        App.Console.PrintMessage("Object Coordinates: " + str(pnt)+ "\n")          # Coordinates of the object
#        App.Console.PrintMessage("Subelements: " + str(Gui.Selection.getSelectionEx()[0].Object) + "\n")
#        App.Console.PrintMessage("Subelements: " + str(Gui.Selection.getSelectionEx()[0].SubElementNames[0]) + "\n")
#        App.Console.PrintMessage("______"+ "\n")
        selection = FreeCADGui.Selection.getSelectionEx()
#        for sub in sel[0].SubObjects:
#            if hasattr(sub, 'Point'):
#                # Print coordinates of a vertex
#                App.Console.PrintMessage("Vertex coordinates:", sub.Point)
#            elif hasattr(sub, 'Shape'):
#                # Check if the shape is a line
#                if sub.Shape.ShapeType == 'Edge':
#                    edge = sub.Shape
#                    start_point = edge.Vertexes[0].Point
#                    end_point = edge.Vertexes[1].Point
#                    print("Edge start point:", start_point)
#                    print("Edge end point:", end_point)
#            elif hasattr(sub, 'CenterOfMass'):
#                # Print coordinates of the center of mass of a face
#                App.Console.PrintMessage("Face center of mass:", sub.CenterOfMass)
        for sel in selection:
#            print(f"Selected an Object in {sel.Object.Name} of type {sel.__class__.__name__}")
            print(f"Number of selections: {len(selection)}")
            print(f"Selected an Object in {sel.Object.Name} of type {sel.Object.TypeId}")
            if sel.Object.TypeId == 'Sketcher::SketchObject':
                print(f"Selected Sketch: {sel.Object.Name}")
                
                # Iterate through the geometry of the sketch
                for i, geo in enumerate(sel.Object.Geometry):
                    if isinstance(geo, Part.LineSegment):
                        start_point = geo.StartPoint
                        end_point = geo.EndPoint
                        print(f"  Line {i + 1}:")
                        print(f"    Start Point: ({start_point.x}, {start_point.y}, {start_point.z})")
                        print(f"    End Point: ({end_point.x}, {end_point.y}, {end_point.z})")
                
                # Collect all unique vertices
                vertices = set()
                for geo in sel.Object.Geometry:
                    if hasattr(geo, 'StartPoint'):
                        vertices.add((geo.StartPoint.x, geo.StartPoint.y, geo.StartPoint.z))
                    if hasattr(geo, 'EndPoint'):
                        vertices.add((geo.EndPoint.x, geo.EndPoint.y, geo.EndPoint.z))
                
                print("  Vertices:")
                for j, vertex in enumerate(vertices, start=1):
                    print(f"    Vertex {j}: ({vertex[0]}, {vertex[1]}, {vertex[2]})")
            else:
                for subobj in sel.SubObjects:
                    if subobj.ShapeType == "Edge":
                        curve = subobj.Curve
                        # Check if the edge is a line segment
                        if isinstance(curve, Part.Line):
                            start_point = subobj.Vertexes[0].Point
                            end_point = subobj.Vertexes[-1].Point
                            print(f"Selected a Line Edge in {sel.Object.Name}")
                            print(f"  Start Point: ({start_point.x}, {start_point.y}, {start_point.z})")
                            print(f"  End Point: ({end_point.x}, {end_point.y}, {end_point.z})")
                        
                        # Detect if the edge is a circle or arc
                        elif isinstance(curve, Part.Circle):
                            center = curve.Location
                            radius = curve.Radius
                            print(f"Selected a Circular Edge in {sel.Object.Name}")
                            print(f"  Center: ({center.x}, {center.y}, {center.z})")
                            print(f"  Radius: {radius}")
                        else:
                            print(f"Selected an Edge in {sel.Object.Name} of type {curve.__class__.__name__}")
        
                    elif subobj.ShapeType == "Vertex":
                        # Get vertex coordinates
                        point = subobj.Point
                        print(f"Selected a Vertex (Point) in {sel.Object.Name}")
                        print(f"  Coordinates: ({point.x}, {point.y}, {point.z})")
        
                    elif subobj.ShapeType == "Face":
                        # Get bounding box corners
                        bounding_box = subobj.BoundBox
                        print(f"Selected a Face in {sel.Object.Name}")
                        print("  Bounding Box Corners:")
                        print(f"    Min: ({bounding_box.XMin}, {bounding_box.YMin}, {bounding_box.ZMin})")
                        print(f"    Max: ({bounding_box.XMax}, {bounding_box.YMax}, {bounding_box.ZMax})")
                        print(f"Area: {subobj.Area}")
                        print("  Surrounding Edges:")
                        for i, edge in enumerate(subobj.Edges, start=1):
                            print(f"    Edge {i}:")
                            # Get edge endpoints
                            start_point = edge.Vertexes[0].Point
                            end_point = edge.Vertexes[-1].Point
                            print(f"      Start Point: ({start_point.x}, {start_point.y}, {start_point.z})")
                            print(f"      End Point: ({end_point.x}, {end_point.y}, {end_point.z})")
        App.Console.PrintMessage("______"+ "\n")



    def removeSelection(self,doc,obj,sub):                # Remove the selection
        App.Console.PrintMessage("removeSelection"+ "\n")

    def setSelection(self,doc):                           # Set selection
        App.Console.PrintMessage("setSelection"+ "\n")

    def clearSelection(self,doc):                         # If click on the screen, clear the selection
        App.Console.PrintMessage("clearSelection"+ "\n")  # If click on another object, clear the previous object