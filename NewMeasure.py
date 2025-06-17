import os
import FreeCADGui as Gui
import FreeCAD as App
from PySide import QtGui, QtCore
from SurfSense import MeasurementData

class NewMeasure:
    def __init__(self, parent, loc):
        self.parent = parent
        self.loc = loc
        path =  os.path.join(self.loc, "UI\\NewMeasure.ui")
        self.form = Gui.PySideUic.loadUi(path)
        self.list_view = self.form.MeasurementsList

        self.form.MeasureCancelBtn.clicked.connect(lambda: self.parent.closeMeasureWidget(self.form))
        self.form.MeasureBtn.clicked.connect(self.runMeasurement)
        self.form.MeasureDetailsWidget.hide()
        self.form.ConrolButtons.hide()
        self.form.unitLineEdit.editingFinished.connect(lambda: self.handleToleranceChange(self.form.unitLineEdit.text()))
        self.form.FormalityComboBox.currentIndexChanged.connect(lambda: self.handleMeasureTypeChange())
    

    def setupFormalityComboBox(self):
        combo_box = self.form.FormalityComboBox
        if combo_box.count() != 0:
            return
        
        import json
        json_path = os.path.join(self.loc, "Data\\measurements.json")
        if not os.path.exists(json_path):
            App.Console.PrintMessage(f"File not found: {json_path}")
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                App.Console.PrintMessage(f"Error parsing JSON: {e}")
                return
            
        measurements = data.get("measurement_types", [])
        if not isinstance(measurements, list):
            App.Console.PrintMessage("Invalid format: 'measurement_types' should be a list.")
            return

        
        for entry in measurements:
            name = entry.get('name', 'Unknown')
            icon_path = entry.get('icon', '')
            item_type = entry.get('type', '')
            unit = entry.get('unit', '')

            # Resolve relative paths based on the JSON file's directory
            if not os.path.isabs(icon_path):
                icon_path = os.path.join(os.path.dirname(json_path), icon_path)

            icon = QtGui.QIcon(icon_path) if os.path.exists(icon_path) else QtGui.QIcon()
            combo_box.addItem(icon, name)

            index = combo_box.count() - 1
            combo_box.setItemData(index, {'type': item_type, 'unit': unit, 'name': name})
        
        
    def handleMeasurementHistory(self, measurement_widget):
        measurements = self.parent.surf_sense.getMeasurements()
        if len(measurements) == 0:
            measurement_widget.hide()
        else:
            measurement_widget.show()


    def handleToleranceChange(self, value):
        line_edit = self.form.unitLineEdit
        try:
            val = float(value)
            line_edit.setText(str(val))
            self.parent.surf_sense.setBaseTolerance(value)
        except ValueError:
            line_edit.setText(str(self.parent.surf_sense.getBaseTolerance()))

    #TODO App.Gui.getLocale() to get the app language and update measurements.json
    def handleMeasureTypeChange(self):
        combo_box = self.form.FormalityComboBox
        index = combo_box.currentIndex()
        data = combo_box.itemData(index)
  
        unit_label = self.form.unitLabel
        unit_label.setText(data.get('unit'))
        tolerance_edit = self.form.unitLineEdit
        tolerance_edit.setText(str(self.parent.surf_sense.getBaseTolerance()))

        if combo_box.currentIndex() != -1:
            self.form.MeasureDetailsWidget.show()
            self.form.ConrolButtons.show()


    def runMeasurement(self):
        m = self.parent.selection_planner.getElementsFromSelection()

        combo_box = self.form.FormalityComboBox
        selected_value = combo_box.itemData(combo_box.currentIndex())
        m_type = selected_value.get('name')
        m_tolerance = self.parent.surf_sense.getBaseTolerance()
        m_unit = self.form.unitLabel.text()
        m_object_list = Gui.Selection.getSelectionEx()[0].SubElementNames
        data = MeasurementData(m_type, m_tolerance, m_unit, m_object_list, m)
        self.parent.surf_sense.addMeasurementToList(data)
        self.addMeasurementToHistory()
        self.handleMeasurementHistory(self.form.Measurements)
        self.handleMeasurementHistory(self.parent.form.Measurements)

    
    def addMeasurementToHistory(self):
        measurements = self.parent.surf_sense.getMeasurements()
        
        model1 = QtGui.QStandardItemModel()
        model2 = QtGui.QStandardItemModel()
        for i, obj in enumerate(measurements):
            to_show = f"Mérés-{(i + 1)}: {obj.measure_type} | {obj.measure} {obj.unit}"
            item1 = QtGui.QStandardItem(to_show)
            item2 = QtGui.QStandardItem(to_show)
            model1.appendRow(item1)
            model2.appendRow(item2)
            
        self.list_view.setModel(model1)
        self.parent.list_view.setModel(model2)
