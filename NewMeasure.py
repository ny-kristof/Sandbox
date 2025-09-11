import os
from pathlib import Path
import FreeCADGui as Gui
import FreeCAD as App
from PySide import QtGui, QtCore, QtWidgets
from SurfSense import MeasurementData
import CSExporter
import xml.etree.ElementTree as ET

class NewMeasure:
    #TODO separate connections and ui setup
    def __init__(self, parent, loc):
        self.parent = parent
        self.loc = loc
        path =  os.path.join(self.loc, "UI\\NewMeasure.ui")
        self.form = Gui.PySideUic.loadUi(path)
        self.list_widget = self.form.MeasurementsList
        self.current_tolerance = {}

        self.form.MeasureCancelBtn.clicked.connect(lambda: self.parent.closeMeasureWidget(self.form))
        self.form.MeasureBtn.clicked.connect(self.runMeasurement)
        self.form.ToleranceLabel.hide()
        self.form.MeasureDetailsWidget.hide()
        self.form.MeasureBtn.setEnabled(False)
        self.form.unitLineEdit.editingFinished.connect(lambda: self.handleToleranceChange(self.form.unitLineEdit.text(), self.form.unitLineEdit))
        self.form.UpperToleranceLimit.editingFinished.connect(lambda: self.handleToleranceChange(self.form.UpperToleranceLimit.text(), self.form.UpperToleranceLimit))
        self.form.LowerToleranceLimit.editingFinished.connect(lambda: self.handleToleranceChange(self.form.LowerToleranceLimit.text(), self.form.LowerToleranceLimit))
        self.form.MeasureTypeCombobox.currentIndexChanged.connect(lambda: self.handleMeasureTypeChange())
        self.list_widget.clicked.connect(self.onListItemClicked)
        self.parent.list_widget.clicked.connect(self.onParentListItemClicked)
        self.form.SamplingRate.valueChanged.connect(self.handleSamplingRateChange)
        icon = QtGui.QIcon(os.path.join(self.loc, "icons\\gear.svg"))
        self.form.MeasurementSettingsBtn.setIcon(icon)
        self.form.MeasurementSettingsBtn.clicked.connect(self.showMeasurementExtraSettings)
        self.form.ExtraSettingsFrame.hide()
        self.form.textbox.hide()
        plus_less_icon = QtGui.QIcon(os.path.join(self.loc, "icons\\plus_less.svg")).pixmap(QtCore.QSize(20,20))
        self.form.PlusLessLabel.setPixmap(plus_less_icon)
        info_icon = QtGui.QIcon(os.path.join(self.loc, "icons\\info.svg")).pixmap(QtCore.QSize(20,20))
        self.form.InfoLabel1.setPixmap(info_icon)
        self.form.InfoLabel2.setPixmap(info_icon)
        self.form.InfoLabel1.setToolTip("tooltip here...")
        self.form.InfoLabel2.setToolTip("tooltip here...")
        self.form.ExportWholePartBtn.clicked.connect(self.handleWholePartBtnClick)
        self.form.ExportCoordinateSystemBtn.clicked.connect(lambda: CSExporter.add_selected_LCS_to_xml(self.parent.selection_planner.root_node))
        self.initializeGeneralTolerancesCombobox()
        

    def initializeGeneralTolerancesCombobox(self):
        path = os.path.join(self.loc, "Data", "tolerances")
        folder_path = Path(path)

        # Build mapping: {filename_stem: fullpath}
        self.tolerance_filemap = {f.stem: str(f) for f in folder_path.rglob("*.xml")}
        items = sorted(self.tolerance_filemap.keys())  # sorted list of names

        self.form.SearchBox = self.makeSearchBox(self.form.GeneralTolerancesframe.layout(), items)
        

    def makeSearchBox(self, parent_layout, items):
        """Create a search box with autocompletion and add it to a layout."""
        line = QtWidgets.QLineEdit()
        line.setObjectName("GeneralToleranceSearchBox")
        line.setPlaceholderText("Start typing tolerance class...")
        completer = QtWidgets.QCompleter(items, line)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)   # case-insensitive search
        line.setCompleter(completer)
        
        line.textChanged.connect(self.onTextChanged)
        completer.activated.connect(self.onOptionSelected)

        parent_layout.addWidget(line)
        return line


    def onTextChanged(self, text):
        if len(text) > 0:
            self.form.LowerToleranceLimit.setReadOnly(True)
            self.form.LowerToleranceLimit.setStyleSheet("QLineEdit{background-color:rgba(192,192,192,0.3);}")
            self.form.UpperToleranceLimit.setReadOnly(True)
            self.form.UpperToleranceLimit.setStyleSheet("QLineEdit{background-color:rgba(192,192,192,0.3);}")
        else:
            self.form.LowerToleranceLimit.setReadOnly(False)
            self.form.LowerToleranceLimit.setStyleSheet("")
            self.form.UpperToleranceLimit.setReadOnly(False)
            self.form.UpperToleranceLimit.setStyleSheet("")
            if self.form.UpperToleranceLimit.text() == "-" or self.form.LowerToleranceLimit.text() == "-":
                (lower_tolerance, upper_tolerance) = self.parent.surf_sense.getBaseTolerance()
                self.setGeneralToleranceInputFields(lower_tolerance, upper_tolerance)
            

    def onOptionSelected(self, text):
        # print("User selected:", text)
        filepath = self.tolerance_filemap.get(text)
        if not filepath:
            print("No XML file found for:", text)
            return

        self.current_tolerance = self.parseToleranceFile(filepath)

        radius = self.parent.getRadiusFromSelection()
        if radius is not None:
            diameter = radius * 2
            limits = self.findToleranceLimits(diameter)
            if limits is not None:
                t_unit = self.current_tolerance["Unit"]
                u_limit = float(limits['Upper_limit'])
                l_limit = float(limits['Lower_limit'])
                u_limit = u_limit * self.parent.MICROMETERTOMM if t_unit == "µm" else u_limit
                l_limit = l_limit * self.parent.MICROMETERTOMM if t_unit == "µm" else l_limit
                u_limit = round(u_limit, 5)
                l_limit = round(l_limit, 5)
                
                self.setGeneralToleranceInputFields(l_limit, u_limit)
            else:
                App.Console.PrintWarning(f"No general tolerance found for {text} with diameter {diameter}")
                self.setGeneralToleranceInputFields("-", "-")
        else:
            self.setGeneralToleranceInputFields("-", "-")


    def findToleranceLimits(self, value):
        """
        data: dict returned by parse_tolerance_file()
        value: float to test
        """
        for size_range, limits in self.current_tolerance["Nominal_size"].items():
            try:
                lower_str, upper_str = size_range.split("-")
                lower = float(lower_str)
                upper = float(upper_str)
            except ValueError:
                continue  # skip malformed ranges

            if lower < value <= upper:
                return limits  # dict with Upper_limit / Lower_limit

        return None  # not found        

    def parseToleranceFile(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()

        result = {}
        # Extract <Unit>
        unit_el = root.find("Unit")
        if unit_el is not None:
            result["Unit"] = unit_el.text.strip()

        # Extract <Nominal_size>
        sizes = {}
        for ns in root.findall("Nominal_size"):
            value = ns.attrib.get("value")
            if not value:
                continue
            sizes[value] = {
                "Upper_limit": ns.findtext("Upper_limit"),
                "Lower_limit": ns.findtext("Lower_limit")
            }
        result["Nominal_size"] = sizes

        return result
    

    def setGeneralToleranceInputFields(self, lower, upper):
        str_u_limit = str(upper)
        str_l_limit = str(lower)
        upper_input = self.form.UpperToleranceLimit
        lower_input = self.form.LowerToleranceLimit
        upper_input.blockSignals(True)
        lower_input.blockSignals(True)
        upper_input.setText(str_u_limit)
        lower_input.setText(str_l_limit)
        if lower != "-" and upper != "-":
            self.parent.surf_sense.setBaseTolerance("upper", upper)
            self.parent.surf_sense.setBaseTolerance("lower", lower)
            self.form.MeasureBtn.setEnabled(True)
            self.form.MeasureBtn.setToolTip("")
        else:
            if self.form.DoubleEditContainer.isVisible() is True:
                self.form.MeasureBtn.setEnabled(False)
                self.form.MeasureBtn.setToolTip("Invalid tolerances")
        upper_input.blockSignals(False)
        lower_input.blockSignals(False)


    def handleWholePartBtnClick(self):
        sel = Gui.Selection.getSelection()
        if(len(sel) < 1):
            App.Console.PrintWarning("Selection is empty")
            return
        self.parent.selection_planner.sampleEveryFaceOnObject(sel[0])


    def showMeasurementExtraSettings(self, checked):
        if checked == True:
            self.form.ExtraSettingsFrame.show()
        else:
            self.form.ExtraSettingsFrame.hide()


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

        with open(json_path, 'r', encoding="utf-8") as f:
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
            name = entry.get("name", "Unknown")
            icon_path = entry.get("icon", "")
            item_type = entry.get("type", "")
            unit = entry.get("unit", "")

            # Resolve relative paths based on the JSON file's directory
            if not os.path.isabs(icon_path):
                icon_path = os.path.join(os.path.dirname(json_path), icon_path)

            icon = QtGui.QIcon(icon_path) if os.path.exists(icon_path) else QtGui.QIcon()
            combo_box.addItem(name)

            index = combo_box.count() - 1
            combo_box.setItemIcon(index, icon)
            combo_box.setItemData(index, {"type": item_type, "unit": unit, "name": name})
            # font = combo_box.font()
            # font.setPointSize(12)
            # combo_box.setFont(font)
            combo_box.setIconSize(QtCore.QSize(25, 25))
        
        
    def handleMeasurementHistory(self, measurement_widget):
        measurements = self.parent.surf_sense.getMeasurements()
        if len(measurements) == 0:
            measurement_widget.hide()
        else:
            measurement_widget.show()


    def handleToleranceChange(self, value, edit):
        if edit.isReadOnly():
            return
        line_edit = edit.objectName()
        value = value.replace(',', '.')
        (prev_lower_tolerance, prev_upper_tolerance) = self.parent.surf_sense.getBaseTolerance()
        match line_edit:
            case "UpperToleranceLimit":
                try:
                    val = float(value)
                    if val <= float(prev_lower_tolerance):
                        App.Console.PrintWarning(f"Upper tolerance should be bigger than lower tolerance")
                        raise ValueError
                    val = round(val, 5)
                    edit.setText(str(val))
                    self.parent.surf_sense.setBaseTolerance("upper", val)
                except ValueError:
                    edit.setText(str(prev_upper_tolerance))
                return
            case "LowerToleranceLimit":
                try:
                    val = float(value)
                    if val >= float(prev_upper_tolerance):
                        App.Console.PrintWarning(f"Lower tolerance should be smaller than upper tolerance")
                        raise ValueError
                    val = round(val, 5)
                    edit.setText(str(val))
                    self.parent.surf_sense.setBaseTolerance("lower", val)
                except ValueError:
                    edit.setText(str(prev_lower_tolerance))
                return
            case "unitLineEdit":
                try:
                    val = float(value)
                    if val < 0:
                        val = abs(val)
                    edit.setText(str(val))
                    val = round(val, 5)
                    self.parent.surf_sense.setBaseTolerance("upper", val)
                    self.parent.surf_sense.setBaseTolerance("lower", -val)
                except ValueError:
                    edit.setText(str(abs(prev_upper_tolerance)))
                return
            case _:
                App.Console.PrintWarning(f"Unexpected case: {line_edit}")
                return


    #TODO App.Gui.getLocale() to get the app language and update measurements.json
    def handleMeasureTypeChange(self):
        combo_box = self.form.MeasureTypeCombobox
        index = combo_box.currentIndex()
        data = combo_box.itemData(index)

        if combo_box.currentIndex() != -1:
            tolerance_type = data.get("type")
            self.showRelatedToleranceInput(tolerance_type)
            self.form.MeasureDetailsWidget.show()
            self.form.ToleranceLabel.show()
            (lower_tolerance, upper_tolerance) = self.parent.surf_sense.getBaseTolerance()
            if self.form.DoubleEditContainer.isVisible() is True:
                if self.form.UpperToleranceLimit.text() == "-" or self.form.LowerToleranceLimit.text() == "-":
                    self.form.MeasureBtn.setEnabled(False)
                    self.form.MeasureBtn.setToolTip("Invalid tolerances")
                else:
                    self.form.MeasureBtn.setEnabled(True)
                    self.parent.surf_sense.setBaseTolerance("upper", upper_tolerance)
                    self.parent.surf_sense.setBaseTolerance("lower", lower_tolerance)
            else:
                new_lower_tolerance = -upper_tolerance if upper_tolerance > 0 else upper_tolerance
                self.parent.surf_sense.setBaseTolerance("upper", abs(upper_tolerance))
                self.parent.surf_sense.setBaseTolerance("lower", new_lower_tolerance)
                self.form.unitLineEdit.setText(str(abs(upper_tolerance)))
                self.form.MeasureBtn.setToolTip("")
                self.form.MeasureBtn.setEnabled(True)


    def showRelatedToleranceInput(self, tolerance_type):
        match tolerance_type:
            case "size":
                self.form.DoubleEditContainer.show()
                self.form.GeneralTolerancesframe.show()
                self.form.SignalEditContainer.hide()
                return
            case "tolerance":
                self.form.DoubleEditContainer.hide()
                self.form.GeneralTolerancesframe.hide()
                self.form.SignalEditContainer.show()
                return
            case _:
                App.Console.PrintWarning("Unexpected tolerance type")
                return


    def runMeasurement(self):
        sel = Gui.Selection.getSelectionEx()
        if(len(sel) < 1):
            App.Console.PrintWarning("Selection is empty")
            return
        combo_box = self.form.MeasureTypeCombobox
        
        for current_sel in sel:
            selected_value = combo_box.itemData(combo_box.currentIndex())
            m_type = selected_value.get("name")
            (lower_tolerance, upper_tolerance) = self.parent.surf_sense.getBaseTolerance()
            m_unit = self.form.LowerUnitLabel.text()
            m_document_name = App.ActiveDocument.Label
            m_object_list = current_sel.SubElementNames
            m_object_name = current_sel.ObjectName
            m_sampling_rate = self.form.SamplingRate.value()

            data = MeasurementData(m_type, lower_tolerance, upper_tolerance, m_unit, m_object_list, 0, m_document_name, m_sampling_rate, m_object_name)
            measurement = self.parent.selection_planner.getElementsFromSelection()
            data.measurement = measurement
            self.parent.surf_sense.addMeasurementToList(data)

            self.addMeasurementToHistory(data)
            self.handleMeasurementUIItems()

        self.parent.populateSensorComboBox()


    def addMeasurementToHistory(self, data):
        # list_count = self.list_widget.count()
        # text = f"Measurement-{list_count + 1}: {data.measure_type} | {data.measurement} {data.unit}"
        self.addListItemWithToListWidget(self.list_widget, data.name, data.id)
        self.addListItemWithToListWidget(self.parent.list_widget, data.name, data.id)


    def refreshMeasurementHistory(self):
        self.list_widget.clear()
        self.parent.list_widget.clear()

        measurements = self.parent.surf_sense.getMeasurements()
        for obj in measurements:
            # text = f"Measurement-{i + 1}: {obj.measure_type} | {obj.measurement} {obj.unit}"
            self.addListItemWithToListWidget(self.list_widget, obj.name, obj.id)
            self.addListItemWithToListWidget(self.parent.list_widget, obj.name, obj.id)        


    def onListItemClicked(self, index):
        item = self.list_widget.itemFromIndex(index)
        widget = self.list_widget.itemWidget(item)
        if widget:
            measurement = self.parent.surf_sense.getMeasurementByID(widget.measurement_id)
            if(measurement):
                Gui.Selection.clearSelection()
                for obj in measurement.object_list:
                    Gui.Selection.addSelection(measurement.doc_name, measurement.object_name, obj)
                #print("Clicked in self.list_widget:", vars(measurement))


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
        widget.itemRemoved.connect(self.parent.selection_planner.removeMeasurementNode)

        item.setSizeHint(widget.sizeHint())
        target_list_widget.addItem(item)
        target_list_widget.setItemWidget(item, widget)
                

    def handleMeasurementDeletion(self):
        self.handleMeasurementUIItems()
        self.refreshMeasurementHistory()
        self.parent.populateSensorComboBox()


    def handleMeasurementUIItems(self, id=0):
        self.handleMeasurementHistory(self.form.Measurements)
        self.handleMeasurementHistory(self.parent.form.Measurements)
        self.parent.handleMeasurementSaveButtonState()

    
    def resetMeasurementWidget(self):
        self.form.MeasureTypeCombobox.setCurrentIndex(-1)
        # self.form.unitLabel.setText("")
        # self.form.textbox.clear()
        base_tolerance = self.parent.surf_sense.getBaseTolerance()
        base_sampling_rate = 10
        self.form.SamplingRate.setValue(base_sampling_rate)
        self.parent.surf_sense.setSamplingRate(base_sampling_rate)
        
        if base_tolerance is not None:
            self.form.unitLineEdit.setText(str(abs(base_tolerance[1])))
            self.form.UpperToleranceLimit.setText(str(base_tolerance[1]))
            self.form.LowerToleranceLimit.setText(str(base_tolerance[0]))

        self.form.MeasureDetailsWidget.hide()
        self.form.ToleranceLabel.hide()
        self.form.MeasureBtn.setEnabled(False)
        self.current_tolerance = {}
        self.form.SearchBox.setText("")


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
        self.label.setObjectName(f"Measurement-{self.measurement_id}")
        self.button = QtWidgets.QToolButton()
        icon = QtGui.QIcon(os.path.join(loc, "icons\\close_sign.svg"))
        self.button.setIcon(icon)
        self.button.setFixedSize(20, 20)
        self.button.clicked.connect(lambda: self.remove_self(True))

        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.button)


    def remove_self(self, from_self = True):
        surf_sense_id = -1
        for i in range(self.list_widget.count()):
            if self.list_widget.itemWidget(self.list_widget.item(i)) == self:
                surf_sense_id = self.measurement_id
                self.list_widget.takeItem(i)
                break
        
        self.itemRemoved.emit(self.measurement_id)
        if from_self:
            for obj in App.ActiveDocument.Objects:
                if hasattr(obj, "SurfSenseID"):
                    if obj.SurfSenseID == surf_sense_id:
                        App.ActiveDocument.removeObject(obj.Name)
