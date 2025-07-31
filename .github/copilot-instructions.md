# Copilot Instructions for the Sandbox FreeCAD Workbench

## Project Overview
This project is a FreeCAD workbench module, primarily written in Python, that extends FreeCAD with custom selection, measurement, and geometry sampling tools. The codebase is organized as a set of scripts loaded by FreeCAD, with UI integration via PySide6 and FreeCADGui.

## Key Components
- `SelectionPlanner.py`: Core logic for selection handling, measurement planning, and geometry sampling. Contains the main class `SelectionPlanner` with methods for handling different selection types (edges, faces, circles, sketches, etc.).
- `SubSurfaceCreator.py`: Provides geometry sampling and XML export utilities, used by `SelectionPlanner` for surface/edge sampling and measurement data output.
- `TaskPanel.py`, `SectionPanel.py`: UI panels for user interaction, typically referenced as `self.Panel` in logic classes.
- `Init.py`, `InitGui.py`: FreeCAD module entry points for registration and GUI integration.
- `icons/`: SVG icons for custom commands and UI elements.

## Patterns & Conventions
- **Selection Handling**: All selection logic is routed through `SelectionPlanner.getElementsFromSelection()`, which dispatches to handler methods based on the type and count of selected subobjects.
- **Measurement Nodes**: XML measurement data is built using `xml.etree.ElementTree`, with a root node per session and measurement nodes per operation. Use `self.createMeasurementNode()` to add new measurements.
- **UI Updates**: All user feedback and measurement results are appended to `self.Panel.textbox`.
- **Error Reporting**: Use `QtWidgets.QMessageBox.information` for user-facing errors and info.
- **Geometry Types**: Use helper methods like `edgeType`, `faceType`, `areFacesParallel` to classify and compare geometry.
- **Sketch Handling**: Sketches are checked for closure and type before face creation and measurement.

## Developer Workflows
- **Reloading**: After code changes, reload the workbench in FreeCAD or restart FreeCAD to pick up changes.
- **Debugging**: Use `print()` for console output; errors are surfaced via message boxes.
- **Dependencies**: Requires FreeCAD, PySide6, and any modules imported at the top of each script. Some modules (e.g., `BOPTools`, `SplitFeatures`) are FreeCAD add-ons.

## Integration Points
- **FreeCAD API**: Heavy use of `FreeCAD`, `FreeCADGui`, `Part`, `Draft`, and `Sketcher` modules.
- **XML Export**: Measurement data is exported as XML using `ElementTree`.
- **UI**: Panels and dialogs are built with PySide6 and connected to FreeCAD's GUI.

## Examples
- To add a new selection handler, implement a method in `SelectionPlanner` and dispatch to it from `getElementsFromSelection()`.
- To sample all faces of an object and export to XML, use `sampleEveryFaceOnObject()`.

## File References
- Main logic: `SelectionPlanner.py`
- Geometry sampling: `SubSurfaceCreator.py`
- UI: `TaskPanel.py`, `SectionPanel.py`
- Entry points: `Init.py`, `InitGui.py`

---

If any section is unclear or missing important project-specific details, please provide feedback for further refinement.
