import os
from pathlib import Path
import FreeCADGui as Gui
import FreeCAD as App
from PySide import QtGui, QtCore, QtWidgets
from SurfSense import SurfSense, MeasurementData
import CSExporter
import xml.etree.ElementTree as ET
from Utils import getListItemWidgetByID

class NewMeasure:
    #TODO separate connections and ui setup
    def __init__(self, parent, loc):
        self.parent = parent
        self.loc = loc
        path =  os.path.join(self.loc, "UI\\NewMeasure.ui")
        self.form = Gui.PySideUic.loadUi(path)
        self.list_widget = self.form.MeasurementsList
        self.current_tolerance = {}
        self.tolerance_type = None
        self.is_measurement_editing = False
        self.current_edited_measurement_id = -1

        self.form.MeasureCancelBtn.clicked.connect(lambda: self.parent.closeMeasureWidget(self.form))
        self.form.MeasureBtn.clicked.connect(self.runMeasurement)
        self.form.ToleranceLabel.hide()
        self.form.MeasureDetailsWidget.hide()
        self.form.MeasureBtn.setEnabled(False)
        self.form.ULToleranceLimit.editingFinished.connect(lambda: self.handleToleranceChange(self.form.ULToleranceLimit.text(), self.form.ULToleranceLimit))
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
        self.parent.form.InfoLabel1.setPixmap(info_icon)
        self.parent.form.InfoLabel2.setPixmap(info_icon)
        self.parent.form.InfoLabel1.setToolTip("tooltip here...")
        self.parent.form.InfoLabel2.setToolTip("tooltip here...")
        self.parent.form.ExportWholePartBtn.clicked.connect(self.handleWholePartBtnClick)
        self.parent.form.ExportCoordinateSystemBtn.clicked.connect(lambda: CSExporter.add_selected_LCS_to_xml(self.parent.selection_planner.root_node))
        self.form.MeasurementNameLabel.hide()
        self.form.MeasurementName.hide()
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
            if self.tolerance_type == "size":
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
        
        
    def handleMeasurementHistory(self, measurement_widget, label):
        measurements = self.parent.surf_sense.getMeasurements()
        if len(measurements) == 0:
            measurement_widget.hide()
            label.hide()
        else:
            measurement_widget.show()
            label.show()


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
            case "ULToleranceLimit":
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



    def handleMeasureTypeChange(self):
        combo_box = self.form.MeasureTypeCombobox
        index = combo_box.currentIndex()
        data = combo_box.itemData(index)
        
        if combo_box.currentIndex() != -1:
            measurement_type = data.get("name")
            tolerance_type = data.get("type")
            self.showRelatedToleranceInput(tolerance_type)
            #TODO If user change the measuremnt type, is it still an update or a new measurement?
            if self.is_measurement_editing == False:
                self.updateMeasurementName(measurement_type)
            self.form.MeasureDetailsWidget.show()
            self.form.ToleranceLabel.show()
            (lower_tolerance, upper_tolerance) = self.parent.surf_sense.getBaseTolerance()
            if self.tolerance_type == "size":
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
                self.form.ULToleranceLimit.setText(str(abs(upper_tolerance)))
                self.form.MeasureBtn.setToolTip("")
                self.form.MeasureBtn.setEnabled(True)


    def updateMeasurementName(self, measure_type):
        measurement_id = self.parent._measurement_count + 1
        name = f"Measurement-{measurement_id}: {measure_type}"
        self.form.MeasurementName.setText(name)
        if self.form.MeasurementNameLabel.isHidden():
            self.form.MeasurementNameLabel.show()
            self.form.MeasurementName.show()

    def showRelatedToleranceInput(self, tolerance_type):
        self.tolerance_type = tolerance_type
        match tolerance_type:
            case "size":
                self.form.UpperLabel.show()
                self.form.UpperToleranceLimit.show()
                self.form.UpperUnitLabel.show()
                self.form.LowerLabel.show()
                self.form.LowerToleranceLimit.show()
                self.form.LowerUnitLabel.show()
                self.form.GeneralTolerancesframe.show()
                self.form.PlusLessLabel.hide()
                self.form.ULToleranceLimit.hide()
                self.form.ULToleranceUnit.hide()
                return
            case "tolerance":
                self.form.UpperLabel.hide()
                self.form.UpperToleranceLimit.hide()
                self.form.UpperUnitLabel.hide()
                self.form.LowerLabel.hide()
                self.form.LowerToleranceLimit.hide()
                self.form.LowerUnitLabel.hide()
                self.form.GeneralTolerancesframe.hide()
                self.form.PlusLessLabel.show()
                self.form.ULToleranceLimit.show()
                self.form.ULToleranceUnit.show()
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
            selected_element_list = []
            for elem in current_sel.SubElementNames:
                selected_element_list.append(f"{current_sel.ObjectName}.{elem}")
            selected_value = combo_box.itemData(combo_box.currentIndex())
            m_type = selected_value.get("name")
            (lower_tolerance, upper_tolerance) = self.parent.surf_sense.getBaseTolerance()
            m_unit = self.form.LowerUnitLabel.text()
            m_document_name = App.ActiveDocument.Label
            m_object_list = selected_element_list
            m_object_name = self.getTopLevelName(current_sel)
            m_sampling_rate = self.form.SamplingRate.value()
            m_name = self.form.MeasurementName.text()

            if self.is_measurement_editing == False:
                data = MeasurementData(m_type, lower_tolerance, upper_tolerance, m_unit, m_object_list, 0, m_document_name, m_sampling_rate, m_name, m_object_name)
                measurement = self.parent.selection_planner.getElementsFromSelection(m_name, data.id)
            else:
                self.parent.selection_planner.removeMeasurementNode(self.current_edited_measurement_id)
                list_widget_item = getListItemWidgetByID(self.current_edited_measurement_id)
                if list_widget_item:
                    list_widget_item.remove_self()
                data = MeasurementData(m_type, lower_tolerance, upper_tolerance, m_unit, m_object_list, 0, m_document_name, m_sampling_rate, m_name, m_object_name, self.current_edited_measurement_id)
                measurement = self.parent.selection_planner.getElementsFromSelection(m_name, self.current_edited_measurement_id)
            data.measurement = measurement
            self.parent.surf_sense.addMeasurementToList(data)
            
            self.addMeasurementToHistory(data)
            self.setSelfMeasrurementEditingState()
            self.handleMeasurementUIItems()
            self.updateMeasurementName(m_type)
            self.parent.populateSensorComboBox()
            

    def getTopLevelName(self, sel):
        obj = sel.Object
        if not obj:
            return None

        parent = obj.getParentGeoFeatureGroup()
        if parent:
            return parent.Name
        return obj.Name         # fallback if no parent

    def getSelectedTopLevelNames(self):
        selection = Gui.Selection.getSelectionEx()
        names = []
        for sel in selection:
            name = self.getTopLevelName(sel)
            if name:
                names.append(name)
        return names
    

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
        from ListItemWidget import ListItemWidget
        item = QtWidgets.QListWidgetItem()
        widget = ListItemWidget(text, target_list_widget, self.loc, measurement_id, self.parent)

        # TODO handle clearselection if a selected item is deleted (if it's needed)
        widget.itemRemoved.connect(self.parent.surf_sense.removeMeasurement)
        widget.itemRemoved.connect(self.handleMeasurementDeletion)
        widget.itemRemoved.connect(self.parent.selection_planner.removeMeasurementNode)

        item.setSizeHint(widget.sizeHint())
        insert_row = target_list_widget.count()
        for i in range(target_list_widget.count()):
            existing_item = target_list_widget.item(i)
            existing_widget = target_list_widget.itemWidget(existing_item)
            existing_id = existing_widget.measurement_id
            if measurement_id < existing_id:
                insert_row = i
                break

        target_list_widget.insertItem(insert_row, item)
        target_list_widget.setItemWidget(item, widget)
                

    def handleMeasurementDeletion(self):
        self.handleMeasurementUIItems()
        self.refreshMeasurementHistory()
        self.parent.populateSensorComboBox()


    def handleMeasurementUIItems(self, id=0):
        self.handleMeasurementHistory(self.form.Measurements, self.form.MeasurementsListLabel)
        self.handleMeasurementHistory(self.parent.form.Measurements, self.parent.form.MeasurementsLabel)
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
            self.form.ULToleranceLimit.setText(str(abs(base_tolerance[1])))
            self.form.UpperToleranceLimit.setText(str(base_tolerance[1]))
            self.form.LowerToleranceLimit.setText(str(base_tolerance[0]))

        self.form.MeasureDetailsWidget.hide()
        self.form.ToleranceLabel.hide()
        self.form.MeasureBtn.setEnabled(False)
        self.current_tolerance = {}
        self.form.SearchBox.setText("")


    def handleMeasurementEdit(self, measurement_data):
        if measurement_data is None:
            return
        self.form.MeasureTypeCombobox.blockSignals(True)
        index = self.form.MeasureTypeCombobox.findText(measurement_data.measure_type)
        if index != -1:
            self.form.MeasureTypeCombobox.setCurrentIndex(index)
            tolerance_type = self.form.MeasureTypeCombobox.itemData(index).get("type")
            self.showRelatedToleranceInput(tolerance_type)
            self.form.MeasureTypeCombobox.blockSignals(False)

            self.updateMeasurementName(measurement_data.measure_type)
            self.form.MeasureDetailsWidget.show()
            self.form.ToleranceLabel.show()
            self.form.MeasureBtn.setEnabled(True)

            self.form.MeasurementName.setText(measurement_data.name)

            self.form.SamplingRate.setValue(measurement_data.sampling_rate)
            self.parent.surf_sense.setSamplingRate(measurement_data.sampling_rate)

            if tolerance_type == "tolerance":
                self.form.ULToleranceLimit.setText(str(abs(measurement_data.upper_tolerance)))
            else:
                self.form.UpperToleranceLimit.setText(str(measurement_data.upper_tolerance))
                self.form.LowerToleranceLimit.setText(str(measurement_data.lower_tolerance))
                self.parent.surf_sense.setBaseTolerance("upper", measurement_data.upper_tolerance)
                self.parent.surf_sense.setBaseTolerance("lower", measurement_data.lower_tolerance)

            # Select the associated objects in the 3D view
            Gui.Selection.clearSelection()
            for obj in measurement_data.object_list:
                # print("measurement_data.object_name: ", measurement_data.object_name)
                Gui.Selection.addSelection(measurement_data.doc_name, measurement_data.object_name, obj)
        else:
            self.form.MeasureTypeCombobox.blockSignals(False)
            self.setSelfMeasrurementEditingState()
            App.Console.PrintWarning(f"Could not find measurement type: {measurement_data.measure_type}")
        

    def setSelfMeasrurementEditingState(self, id = -1):
        if id != -1:
            self.is_measurement_editing = True
            self.current_edited_measurement_id = id
        else:
            self.is_measurement_editing = False
            self.current_edited_measurement_id = -1

