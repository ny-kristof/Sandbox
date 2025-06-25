import os
import FreeCADGui as Gui
import FreeCAD as App
from PySide import QtGui, QtCore, QtWidgets
from SurfSense import MeasurementData

class NewMeasure:
    def __init__(self, parent, loc):
        self.parent = parent
        self.loc = loc
        path =  os.path.join(self.loc, "UI\\NewMeasure.ui")
        self.form = Gui.PySideUic.loadUi(path)
        self.list_widget = self.form.MeasurementsList

        self.form.MeasureCancelBtn.clicked.connect(lambda: self.parent.closeMeasureWidget(self.form))
        self.form.MeasureBtn.clicked.connect(self.runMeasurement)
        self.form.MeasureDetailsWidget.hide()
        self.form.MeasureBtn.setEnabled(False)
        self.form.unitLineEdit.editingFinished.connect(lambda: self.handleToleranceChange(self.form.unitLineEdit.text()))
        self.form.MeasureTypeCombobox.currentIndexChanged.connect(lambda: self.handleMeasureTypeChange())
        self.list_widget.clicked.connect(self.onListItemClicked)
        self.parent.list_widget.clicked.connect(self.onParentListItemClicked)
        self.form.SamplingRate.valueChanged.connect(self.handleSamplingRateChange)
        

    def handleSamplingRateChange(self, value):
        self.form.SliderLabel.setText(str(value))
        self.parent.surf_sense.setSamplingRate(value)
    

    def setupMeasureTypeCombobox(self):
        combo_box = self.form.MeasureTypeCombobox
        if combo_box.count() != 0:
            return
        
        import json
        json_path = os.path.join(self.loc, "Data\\measurements.json")
        if not os.path.exists(json_path):
            App.Console.PrintError(f"File not found: {json_path}")
            return

        with open(json_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                App.Console.PrintError(f"Error parsing JSON: {e}")
                return
            
        measurements = data.get("measurement_types", [])
        if not isinstance(measurements, list):
            App.Console.PrintError("Invalid format: 'measurement_types' should be a list.")
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
        combo_box = self.form.MeasureTypeCombobox
        index = combo_box.currentIndex()
        data = combo_box.itemData(index)
  
        if combo_box.currentIndex() != -1:
            unit_label = self.form.unitLabel
            unit_label.setText(data.get('unit'))
            tolerance_edit = self.form.unitLineEdit
            tolerance_edit.setText(str(self.parent.surf_sense.getBaseTolerance()))

            self.form.MeasureDetailsWidget.show()
            self.form.MeasureBtn.setEnabled(True)


    def runMeasurement(self):
        sel = Gui.Selection.getSelectionEx()
        if(len(sel) < 1):
            App.Console.PrintWarning("Selection is empty")
            return
        combo_box = self.form.MeasureTypeCombobox
        
        for current_sel in sel:
            selected_value = combo_box.itemData(combo_box.currentIndex())
            m_type = selected_value.get('name')
            m_tolerance = self.parent.surf_sense.getBaseTolerance()
            m_unit = self.form.unitLabel.text()
            m_document_name = App.ActiveDocument.Label
            m_object_list = current_sel.SubElementNames
            m_object_name = current_sel.ObjectName
                        
            data = MeasurementData(m_type, m_tolerance, m_unit, m_object_list, 0, m_document_name, m_object_name)
            measurement = self.parent.selection_planner.getElementsFromSelection()
            data.measurement = measurement
            self.parent.surf_sense.addMeasurementToList(data)

            self.addMeasurementToHistory(data)
            self.handleMeasurementUIItems()       


    def addMeasurementToHistory(self, data):
        list_count = self.list_widget.count()
        text = f"Measurement-{list_count + 1}: {data.measure_type} | {data.measurement} {data.unit}"
        self.addListItemWithToListWidget(self.list_widget, text, data.id)
        self.addListItemWithToListWidget(self.parent.list_widget, text, data.id)


    def refreshMeasurementHistory(self):
        self.list_widget.clear()
        self.parent.list_widget.clear()

        measurements = self.parent.surf_sense.getMeasurements()
        for i, obj in enumerate(measurements):
            text = f"Measurement-{i + 1}: {obj.measure_type} | {obj.measurement} {obj.unit}"
            self.addListItemWithToListWidget(self.list_widget, text, obj.id)
            self.addListItemWithToListWidget(self.parent.list_widget, text, obj.id)        


    def onListItemClicked(self, index):
        item = self.list_widget.itemFromIndex(index)
        widget = self.list_widget.itemWidget(item)
        if widget:
            measurement = self.parent.surf_sense.getMeasurementByID(widget.measurement_id)
            if(measurement):
                Gui.Selection.clearSelection()
                for obj in measurement.object_list:
                    Gui.Selection.addSelection(measurement.doc_name, measurement.object_name, obj)
                print("Clicked in self.list_widget:", vars(measurement))


    def onParentListItemClicked(self, index):
        item = self.parent.list_widget.itemFromIndex(index)
        widget = self.parent.list_widget.itemWidget(item)
        if widget:
            measurement = self.parent.surf_sense.getMeasurementByID(widget.measurement_id)
            if(measurement):
                Gui.Selection.clearSelection()
                for obj in measurement.object_list:
                    Gui.Selection.addSelection(measurement.doc_name, measurement.object_name, obj)
                print("Clicked in self.list_widget:", vars(measurement))

        
    def addListItemWithToListWidget(self, target_list_widget, text, measurement_id):
        item = QtWidgets.QListWidgetItem()
        widget = ListItemWidget(text, target_list_widget, self.loc, measurement_id)

        # TODO handle clearselection if a selected item is deleted (if it's needed)
        widget.itemRemoved.connect(self.parent.surf_sense.removeMeasurement)
        widget.itemRemoved.connect(self.handleMeasurementDeletion)

        item.setSizeHint(widget.sizeHint())
        target_list_widget.addItem(item)
        target_list_widget.setItemWidget(item, widget)
                

    def handleMeasurementDeletion(self):
        self.handleMeasurementUIItems()
        self.refreshMeasurementHistory()


    def handleMeasurementUIItems(self, id=0):
        self.handleMeasurementHistory(self.form.Measurements)
        self.handleMeasurementHistory(self.parent.form.Measurements)
        self.parent.handleMeasurementSaveButtonState()

    
    def resetMeasurementWidget(self):
        self.form.MeasureTypeCombobox.setCurrentIndex(-1)
        self.form.unitLabel.setText("")
        self.form.textbox.clear()
        base_tolerance = self.parent.surf_sense.getBaseTolerance()
        sampling_rate = self.parent.surf_sense.getSamplingRate()

        if sampling_rate is not None:
            self.form.SamplingRate.setValue(sampling_rate)
        
        if base_tolerance is not None:
            self.form.unitLineEdit.setText(str(base_tolerance))

        self.form.MeasureDetailsWidget.hide()
        self.form.MeasureBtn.setEnabled(False)


class ListItemWidget(QtWidgets.QWidget):
    from PySide6.QtCore import Signal
    itemRemoved = Signal(object)


    def __init__(self, text, list_widget, loc, measurement_id):
        super().__init__()
        self.list_widget = list_widget
        self.measurement_id = measurement_id

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        self.label = QtWidgets.QLabel(text)
        self.button = QtWidgets.QToolButton()
        icon = QtGui.QIcon(os.path.join(loc, "icons\\close_sign.svg"))
        self.button.setIcon(icon)
        self.button.setFixedSize(20, 20)
        self.button.clicked.connect(self.remove_self)

        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.button)


    def remove_self(self):
        for i in range(self.list_widget.count()):
            if self.list_widget.itemWidget(self.list_widget.item(i)) == self:
                self.list_widget.takeItem(i)
                break
        
        self.itemRemoved.emit(self.measurement_id)
