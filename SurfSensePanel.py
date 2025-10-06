from PySide import QtGui, QtCore, QtWidgets
import FreeCADGui as Gui
import FreeCAD as App
import Part
import os
import json
from SurfSense import SurfSense
import SelectionPlanner
import NewMeasure
import CSExporter
import xml.etree.ElementTree as ET



class SurfSensePanel(QtWidgets.QWidget):
    _measurement_count = 0
    _sensor_icon_size = QtCore.QSize(16, 16)
    MICROMETERTOMM = 0.001
    # TODO avoid magic numbers?
    # ZERO = 0
    # ONE = 1
    # TWO = 2
    # THREE = 3
    def __init__(self, loc, parent=None):
        super().__init__(parent)
        # dlg =  os.path.join(loc, "SurfSenseHorizontal.ui")
        self.loc = loc
        dlg =  os.path.join(self.loc, "UI\\SurfSenseVertical.ui")
        sensor_dialog =  os.path.join(self.loc, "UI\\SensorSpecification.ui")
        self.sensor_widget = Gui.PySideUic.loadUi(sensor_dialog)
        self.loadSensorUnits()
        self.form = Gui.PySideUic.loadUi(dlg)
        self.surf_sense = SurfSense(self)
        self.list_widget = self.form.MeasurementsListWidget
        self.new_measure = NewMeasure.NewMeasure(self, loc)
        self.selection_planner = SelectionPlanner.SelectionPlanner(self.new_measure.form)
        self.selObserver = SurfSenseSelObserver(self, self.new_measure)
        self.docObserver = DocObserver(self)
        App.addDocumentObserver(self.docObserver)


    def setupUi(self):
        if App.ActiveDocument != None:
            if len(App.ActiveDocument.Objects) > 0:
                self.form.toolBox.setCurrentIndex(1)
            else:
                self.form.toolBox.setCurrentIndex(0)
        else:
            self.form.toolBox.setCurrentIndex(0)
        
        self.new_measure.handleMeasurementHistory(self.form.Measurements, self.form.MeasurementsLabel)
        icon = QtGui.QIcon(os.path.join(self.loc, "icons\\plus_sign.svg"))
        self.form.AddSensor.setIcon(icon)
        self.form.AddKinematic.setIcon(icon)
        # self.disableSensorSelectorUI()
        self.handleMeasurementSaveButtonState()
        self.populateSensorLegendLabel()
        dialog =  os.path.join(self.loc, "UI\\SensorDetails.ui")
        self.form.SensorDataLayout.setWidget(0, QtGui.QFormLayout.FieldRole, Gui.PySideUic.loadUi(dialog))
        # findchild?
        self.form.SensorDataLayout.itemAt(0, QtGui.QFormLayout.FieldRole).widget().hide()
        # self.form.KinematicsComboBox.hide()
        # self.form.KinematicsComboBoxLabel.hide()
        self.form.KinematicDetailsFrame.hide()
        self.loadKinematics()
    
    def initConnections(self):
        self.form.ImportBtn.clicked.connect(self.importModel)
        self.form.NewMeasureBtn.clicked.connect(self.openNewMeasure)
        self.form.FinishMeasure.clicked.connect(self.saveMeasurementsToXML)
        self.list_widget.model().rowsInserted.connect(self.handleMeasurementSaveButtonState)
        self.list_widget.model().rowsRemoved.connect(self.handleMeasurementSaveButtonState)
        self.form.MatteButton.clicked.connect(self.handleProductDataReflectionAbilityButtons)
        self.form.GlossyButton.clicked.connect(self.handleProductDataReflectionAbilityButtons)
        self.form.RobotButton.clicked.connect(self.handleKinematicsButtons)
        self.form.SaveSensorButton.clicked.connect(self.saveSensorData)
        self.form.ManipulatorButton.clicked.connect(self.handleKinematicsButtons)
        self.form.SensorCombobox.currentIndexChanged.connect(lambda: self.handleSensorChange())
        self.form.SensorCounterLineEdit.editingFinished.connect(lambda: self.handleSensorCounterChange(self.form.SensorCounterLineEdit.text()))
        self.form.ShowSensorData.clicked.connect(self.showSensorDetails)
        self.sensor_widget.SensorCancelBtn.clicked.connect(self.handleSensorBackButton)
        self.form.KinematicsComboBox.currentIndexChanged.connect(lambda: self.handleKinematicChange())
        QtWidgets.QApplication.instance().installEventFilter(self)


    def handleKinematicChange(self):
        robot_btn_check_state = self.form.RobotButton.isChecked()
        combo_box = self.form.KinematicsComboBox
        index = combo_box.currentIndex()
        data = combo_box.itemData(index)
        if robot_btn_check_state and index != -1:
            data_list = []
            max_load = ("Maxload", str(data.get("max_load")))
            max_reach = ("MaxReach", str(data.get("max_reach")))
            data_list.append(max_load)
            data_list.append(max_reach)
            self.populateKinematicDetails(data_list)
        else:
            pass
        
        # print(data)

    def handleSensorBackButton(self):
        self.form.ExtraLayout.removeWidget(self.sensor_widget)
        self.sensor_widget.hide()
        self.form.toolBox.show()


    def loadKinematics(self):
        filename = os.path.join(self.loc, "Data\\Kinematics.xml")
        tree = ET.parse(filename)
        root = tree.getroot()

        self.robots = {}
        self.manipulators = {}

        for kin in root.findall("Kinematics"):
            robot = {
                "name": kin.attrib.get("name"),
                "manufacturer": kin.attrib.get("Manuf"),
                "type": kin.attrib.get("Type", "Robot"),  # default fallback
                "max_speed": float(kin.attrib.get("MaxPathSpeed", 0)),
                "max_accel": float(kin.attrib.get("MaxPathAccel", 0)),
                "max_load": float(kin.attrib.get("MaxLoad", 0)),
                "max_reach": float(kin.attrib.get("MaxReach", 0)),
                "axes": [],
                "params": []
            }

            # --- collect params if present ---
            params_el = kin.find("params")
            if params_el is not None:
                for p in params_el.findall("param"):
                    robot["params"].append({
                        "value": p.text.strip() if p.text else None,
                        "note": p.attrib.get("note")
                    })

            # --- collect axis data ---
            for axis in kin.findall("Axis"):
                axis_data = {
                    "name": axis.attrib.get("name"),
                    "reference": axis.attrib.get("reference"),
                    "type": axis.attrib.get("type"),
                    "rangeMin": axis.attrib.get("rangeMin"),
                    "rangeMax": axis.attrib.get("rangeMax"),
                    "maxSpeed": float(axis.attrib.get("maxSpeed", 0)),
                    "maxAccel": float(axis.attrib.get("maxAccel", 0)),
                    "offset": float(axis.attrib.get("offset", 0)),
                    "sign": int(axis.attrib.get("sign", 1)),
                    "q0": float(axis.attrib.get("q0", 0)),
                    "dh": None,
                    "dh_note": None,
                }
                dh_el = axis.find("DH")
                if dh_el is not None and dh_el.text:
                    axis_data["dh"] = [v.strip() for v in dh_el.text.strip("[]").split(",")]
                    axis_data["dh_note"] = dh_el.attrib.get("note")

                robot["axes"].append(axis_data)

            # --- separate robots vs manipulators ---
            if robot["manufacturer"] == "None":
                self.manipulators[robot["name"]] = robot
            else:
                self.robots[robot["name"]] = robot
        self.populateKinematicsCombobox()


    def populateKinematicsCombobox(self):
        robot_btn_check_state = self.form.RobotButton.isChecked()
        combo_box = self.form.KinematicsComboBox
        combo_box.clear()

        if robot_btn_check_state:
            for name, data in self.robots.items():
                combo_box.addItem(name, data)

            self.form.KinematicsComboBox.setPlaceholderText("Select a robot...")
            self.form.AddKinematic.show()
        else:
            for name, data in self.manipulators.items():
                combo_box.addItem(name, data)
            self.form.KinematicsComboBox.setPlaceholderText("Select a manipulator...")
            self.form.KinematicDetailsFrame.hide()

        self.form.KinematicsComboBox.show()
        self.form.KinematicsComboBoxLabel.show()

    def loadSensorUnits(self):
        sensor_unit_path = os.path.join(self.loc, "Data\\sensor_unit.xml")
        tree = ET.parse(sensor_unit_path)
        root = tree.getroot()

        data = {}
        for child in root:
            data[child.tag] = child.text.strip() if child.text else None
        self.sensor_unit = data


    def importModel(self):
        Gui.runCommand("Std_Open")
        if Gui.ActiveDocument == None:
            return
        elif len(App.ActiveDocument.Objects) > 0:
            self.form.toolBox.setCurrentIndex(1)


    def openNewMeasure(self):
        measure_widget = self.new_measure.form
        self.form.ExtraLayout.addWidget(measure_widget)
        self.form.toolBox.hide()
        measure_widget.show()
        self.new_measure.setupMeasureTypeCombobox()
        self.new_measure.resetMeasurementWidget()
        self.new_measure.handleMeasurementHistory(measure_widget.Measurements, self.new_measure.form.MeasurementsListLabel)
                            
        Gui.Selection.addObserver(self.selObserver)
        self.selObserver.addSelectedItemToSelection()
       

    def closeMeasureWidget(self, measure_widget):
        measure_widget.MeasurementNameLabel.hide()
        measure_widget.MeasurementName.hide()
        self.form.ExtraLayout.removeWidget(measure_widget)
        measure_widget.hide()
        self.form.toolBox.show()
        self.new_measure.setSelfMeasrurementEditingState()
        Gui.Selection.removeObserver(self.selObserver)


    def handleMeasurementSaveButtonState(self):
        finish_button = self.form.FinishMeasure 
        if len(self.surf_sense.getMeasurements()) > 0:
            finish_button.setDisabled(False)
            finish_button.setToolTip("")
        else:
            finish_button.setDisabled(True)
            finish_button.setToolTip("There isn't any finished measurement")


    def handleProductDataReflectionAbilityButtons(self, checked):
        if checked == False:
            self.surf_sense.setReflectionAbility(None)
            return
        sender = self.sender()
        if sender is self.form.MatteButton:
            self.form.GlossyButton.setChecked(False)
            self.surf_sense.setReflectionAbility("Matte")

        elif sender is self.form.GlossyButton:
            self.form.MatteButton.setChecked(False)
            self.surf_sense.setReflectionAbility("Glossy")


    def handleKinematicsButtons(self, checked):
        if checked == False:
            self.surf_sense.setKinematics(None)
            return
        sender = self.sender()
        if sender is self.form.RobotButton:
            self.form.ManipulatorButton.setChecked(False)
            self.surf_sense.setReflectionAbility("Robot")
            # self.form.AddKinematic.show()

        elif sender is self.form.ManipulatorButton:
            self.form.RobotButton.setChecked(False)
            self.surf_sense.setReflectionAbility("Manipulator")
            # self.form.AddKinematic.hide()

        self.populateKinematicsCombobox()
        

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
            # pos = event.globalPosition().toPoint()  # For PySide6
            pos = event.globalPos() #.toPoint()  # For PySide

            # Handle self.list_widget
            widget_pos = self.list_widget.mapFromGlobal(pos)
            item = self.list_widget.itemAt(widget_pos)
            if self.list_widget.rect().contains(widget_pos) and item is None:
                if self.list_widget.selectedItems():
                    self.list_widget.clearSelection()
                    Gui.Selection.clearSelection()

            # Handle new_measure.list_widget
            new_widget_pos = self.new_measure.list_widget.mapFromGlobal(pos)
            new_item = self.new_measure.list_widget.itemAt(new_widget_pos)
            if self.new_measure.list_widget.rect().contains(new_widget_pos) and new_item is None:
                if self.new_measure.list_widget.selectedItems():
                    self.new_measure.list_widget.clearSelection()
                    Gui.Selection.clearSelection()

        return super().eventFilter(obj, event)


    def handleSensorChange(self):
        combo_box = self.form.SensorCombobox
        index = combo_box.currentIndex()
        data = combo_box.itemData(index)
        manufacturer = data.get('manufacturer')
        series = data.get('series')
        sensor_data = self.findSensorByManufacturerAndSeries(manufacturer, series)
        if sensor_data is not None:
            sensor_dict = self.sensorElementToDict(sensor_data)
            # print(sensor_dict)

        ffov = sensor_dict['Field_of_View_FAR'].split("x")
        nfov = sensor_dict['Field_of_View_NEAR'].split("x")
        
        fov_data = {}    
        fov_data["x"] = sensor_dict["Sensor_size_width"]
        fov_data["y"] = sensor_dict["Sensor_size_length"]
        fov_data["z"] = sensor_dict["Sensor_size_height"]
        fov_data["D"]  = "??"
        fov_data["NFOV X"] = nfov[0]
        fov_data["NFOV Y"] = nfov[1]
        fov_data["FFOV X"] = ffov[0]
        fov_data["FFOV Y"] = ffov[1]
        fov_data["CD"] = sensor_dict["Clearance_Distance"]
        fov_data["MR"] = "??"

        sensor_layout = self.form.SensorHelperMsgLayout
        if sensor_layout.rowCount() != 0:
            while sensor_layout.rowCount() > 0:
                sensor_layout.removeRow(0)

        conflict_count = data.get("_conflict_count")
        state = self.getConflictIcon(conflict_count)
        tool_tip = self.createToolTipForSensorMeasure(data.get("_cannot_measure"))

        icon_label = QtGui.QLabel()
        icon_label.setPixmap(state[0].pixmap(self._sensor_icon_size))
                    
        sensor_layout.addRow(icon_label, QtGui.QLabel(state[1]))
        if conflict_count != 0:
            sensor_layout.addRow("", QtGui.QLabel(tool_tip))
        
        if index > -1:
            if self.form.SensorDetails.isHidden():
                self.form.SensorDetails.show()
            
            self.loadSensorDetails(fov_data)
            #detail_layout = self.form.SensorDetailsLayout
        self.handleSensorCounterChange(self.form.SensorCounterLineEdit.text())
        

    def loadSensorDetails(self, fov_data):
        fov_x = fov_data["x"]
        fov_y = fov_data["y"]
        fov_z = fov_data["z"]
        fov_d = fov_data["D"]
        nfov_x = fov_data["NFOV X"]
        nfov_y = fov_data["NFOV Y"]
        ffov_x = fov_data["FFOV X"]
        ffov_y = fov_data["FFOV Y"]
        fov_cd = fov_data["CD"]
        fov_mr = fov_data["MR"]
        sensor_details_widget = self.form.SensorDataLayout.itemAt(0, QtGui.QFormLayout.FieldRole).widget()
        sensor_details_widget.FOV_X.setText(str(fov_x))
        sensor_details_widget.FOV_Y.setText(str(fov_y))
        sensor_details_widget.FOV_Z.setText(str(fov_z))
        sensor_details_widget.FOV_D.setText(str(fov_d))
        sensor_details_widget.NFOV_X.setText(str(nfov_x))
        sensor_details_widget.NFOV_Y.setText(str(nfov_y))
        sensor_details_widget.FFOV_X.setText(str(ffov_x))
        sensor_details_widget.FFOV_Y.setText(str(ffov_y))
        sensor_details_widget.FOV_CD.setText(str(fov_cd))
        sensor_details_widget.FOV_MR.setText(str(fov_mr))


    def findSensorByManufacturerAndSeries(self, manufacturer, series):
        xml_path = os.path.join(self.loc, "Data", "sensors.xml")
        if not os.path.exists(xml_path):
            App.Console.PrintError(f"File not found: {xml_path}")
            return None

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            App.Console.PrintError(f"Error parsing XML: {e}")
            return None

        for sensor_elem in root.findall("sensor"):
            m = sensor_elem.findtext("Manufacturer", "").strip()
            s = sensor_elem.findtext("Series", "").strip()
            if m == manufacturer and s == series:
                return sensor_elem

        return None


    def sensorElementToDict(self, sensor_elem):
        return {
            child.tag: child.text.strip() if child.text else None
            for child in sensor_elem
        }

    def saveMeasurementsToXML(self):
        from pathlib import Path
        
        try:
            documents_dir = Path.home() / "Documents" / "SurfSense"
            documents_dir.mkdir(parents=True, exist_ok=True)  # Create folder if missing

            # Get the Measurements element
            measurements_elem = self.selection_planner.root_node.find("Measurements")
            if measurements_elem is not None:
                # Sort Measurement elements by SurfSenseID (numerically if possible)
                sorted_measurements = sorted(
                    measurements_elem.findall("Measurement"),
                    key=lambda m: int(m.get("SurfSenseID", "0"))
                )

                # Clear existing children and re-append in sorted order
                measurements_elem[:] = sorted_measurements

            # Save XML
            file_path = documents_dir / "measurements.xml"
            tree = ET.ElementTree(self.selection_planner.root_node)
            tree.write(file_path, encoding="utf-8", xml_declaration=True)

            App.Console.PrintMessage("File saved successfully\n")

        except Exception as e:
            App.Console.PrintError(f"Failed to save the measurements: {e}\n")


    def populateSensorLegendLabel(self):
        green_tuple =  self.getConflictIcon(0)
        yellow_tuple = self.getConflictIcon(1)
        orange_tuple = self.getConflictIcon(2)
        red_tuple = self.getConflictIcon(3)

        green_icon_label = QtGui.QLabel()
        green_icon_label.setPixmap(green_tuple[0].pixmap(self._sensor_icon_size))

        yellow_icon_label = QtGui.QLabel()
        yellow_icon_label.setPixmap(yellow_tuple[0].pixmap(self._sensor_icon_size))

        orange_icon_label = QtGui.QLabel()
        orange_icon_label.setPixmap(orange_tuple[0].pixmap(self._sensor_icon_size))

        red_icon_label = QtGui.QLabel()
        red_icon_label.setPixmap(red_tuple[0].pixmap(self._sensor_icon_size))

        # legend_label = QtGui.QLabel("Legend:")
        # font = QtGui.QFont("Arial", 13)
        # legend_label.setFont(font)
        # self.form.SensorLegendLayout.addRow(legend_label)
        self.form.SensorLegendLayout.addRow(green_icon_label, QtGui.QLabel(green_tuple[1]))
        self.form.SensorLegendLayout.addRow(yellow_icon_label, QtGui.QLabel(yellow_tuple[1]))
        self.form.SensorLegendLayout.addRow(orange_icon_label, QtGui.QLabel(orange_tuple[1]))
        self.form.SensorLegendLayout.addRow(red_icon_label, QtGui.QLabel(red_tuple[1]))


    def sortSensorsByMeasurements(self, sensors, measurements):
        sorted_list = []
        for sensor in sensors:
            for measurement in measurements:
                m_type = measurement.measure_type
                u_tolerance =  self.safeToFloat(measurement.upper_tolerance)
                l_tolerance = self.safeToFloat(measurement.lower_tolerance)
                m_sampling_rate =  self.safeToFloat(measurement.sampling_rate)
                res_xy_far = self.safeToFloat(sensor.get("Resolution_XY_FAR", 0.0))
                res_z_far = self.safeToFloat(sensor.get("Resolution_Z_FAR", 0.0))
                # res_xy_far_in_mm = res_xy_far / SurfSensePanel.MMTOMICROMETER # measurement unit is mm so to compare to µm need this divison
                res_xy_far_in_mm = res_xy_far * SurfSensePanel.MICROMETERTOMM if self.sensor_unit["Resolution_XY_FAR"] == "µm" else res_xy_far
                res_z_far_in_mm = res_z_far * SurfSensePanel.MICROMETERTOMM if self.sensor_unit["Resolution_Z_FAR"] == "µm" else res_z_far
                # print(f"++++++++++++++++++++++++++++++++++")
                # print(f"snesor: {sensor}")
                # print(f"m_type: {m_type}")
                # print(f"m_tolerance: {m_tolerance}")
                # print(f"m_sampling_rate: {m_sampling_rate}")
                # print(f"res_xy_far: {res_xy_far_in_mm}")
                # print(f"res_z_far: {res_z_far_in_mm}")
                # print(f"++++++++++++++++++++++++++++++++++")
                m_tolerance = abs(u_tolerance) if abs(u_tolerance) < abs(l_tolerance) else abs(l_tolerance)
                                                                        # res_z_far is unknown at this moment
                if m_tolerance * m_sampling_rate >= res_xy_far_in_mm:   # and m_tolerance * m_sampling_rate >= res_z_far_in_mm:
                    sensor["_conflict_count"] += 1
                    sensor["_cannot_measure"].append(measurement.name)

            sorted_list.append(sensor)

        # Sort: first by conflict count, then alphabetically by 'manufacturer'
        sorted_list.sort(key=lambda s: (s["_conflict_count"], s.get("manufacturer", "")))
        return sorted_list


    def getConflictIcon(self, count):
        match count:
            case 0:
                return (QtGui.QIcon(os.path.join(self.loc, "icons\\measurement_suitability\\for_all.svg")), "Suitable for all measurements")
            case 1:
                return (QtGui.QIcon(os.path.join(self.loc, "icons\\measurement_suitability\\except_one.svg")), "Not suitable for 1 measurement")
            case 2:
                return (QtGui.QIcon(os.path.join(self.loc, "icons\\measurement_suitability\\except_two.svg")), "Not suitable for 2 measurements")
            case _:
                return (QtGui.QIcon(os.path.join(self.loc, "icons\\measurement_suitability\\3_or_more.svg")), "Not suitable for 3 or more measurements")


    def safeToFloat(self, value):
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    # def populateSensorComboBox(self):
    #     combo_box = self.form.SensorCombobox
    #     combo_box.blockSignals(True)
    #     measurement_types = self.surf_sense.getMeasurementTypes()
    #     if len(measurement_types) == 0:
    #         self.disableSensorSelectorUI()
    #         return
        
    #     self.form.SensorCombobox.setEnabled(True)
    #     self.form.AddSensor.setEnabled(True)
    #     self.form.SensorCombobox.setToolTip("")
    #     self.form.AddSensor.setToolTip("")
        
    #     combo_box.clear()
    #     json_path = os.path.join(self.loc, "Data\\sensors.json")
    #     if not os.path.exists(json_path):
    #         App.Console.PrintError(f"File not found: {json_path}")
    #         return

    #     with open(json_path, 'r', encoding="utf-8") as f:
    #         try:
    #             data = json.load(f)
    #         except json.JSONDecodeError as e:
    #             App.Console.PrintError(f"Error parsing JSON: {e}")
    #             return
            
    #     sensors = data.get("sensors", [])
    #     if not isinstance(sensors, list):
    #         App.Console.PrintError("Invalid format: 'sensors' should be a list.")
    #         return
        
    #     sorted_sensors = self.sortSensorsByMeasurements(sensors, measurement_types)

    #     for sensor in sorted_sensors:
    #         sensor_name = sensor.get("type", "Unknown")
    #         sensor_manufacturer = sensor.get("manufacturer")
    #         cannot = set(sensor.get("cannot_measure", []))
    #         conflicts = measurement_types & cannot
    #         conflict_count = len(conflicts)
    #         sensor["_conflict_count"] = conflict_count
    #         sensor["_conflict_list"] = conflicts

    #         tooltip = ""
    #         if conflict_count > 0:
    #             tooltip = self.createToolTipForSensorMeasure(conflicts)

    #         icon = self.getConflictIcon(conflict_count)
    #         combo_box.addItem(icon[0], f"{sensor_manufacturer} {sensor_name}")

    #         index = combo_box.count() - 1
    #         combo_box.setItemData(index, sensor)
    #         combo_box.setItemData(index, tooltip, QtCore.Qt.ToolTipRole)
        
    #     self.form.SensorCombobox.setMaxVisibleItems(3)
    #     self.form.SensorCombobox.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
    #     combo_box.blockSignals(False)


    def populateSensorComboBox(self):
        combo_box = self.form.SensorCombobox
        combo_box.blockSignals(True)

        measurements = self.surf_sense.getMeasurements()
        if len(measurements) == 0:
            self.disableSensorSelectorUI()
            return

        self.form.SensorCombobox.setEnabled(True)
        self.form.AddSensor.setEnabled(True)
        self.form.SensorCombobox.setToolTip("")
        self.form.AddSensor.setToolTip("")
       
        combo_box.clear()
        xml_path = os.path.join(self.loc, "Data", "sensors.xml")
        if not os.path.exists(xml_path):
            App.Console.PrintError(f"File not found: {xml_path}")
            return

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except ET.ParseError as e:
            App.Console.PrintError(f"Error parsing XML: {e}")
            return

        sensors = []
        for sensor_elem in root.findall("sensor"):
            sensor_type = sensor_elem.findtext("Type", default="Unknown")
            if sensor_type.strip().lower() != "snapshot":
                continue  

            sensor = {
                "type": sensor_type,
                "manufacturer": sensor_elem.findtext("Manufacturer", default="Unknown"),
                "series": sensor_elem.findtext("Series", default=""),
                "Resolution_XY_FAR": sensor_elem.findtext("Resolution_XY_FAR", default=""),
                "Resolution_Z_FAR": sensor_elem.findtext("Resolution_Z_FAR", default=""),
                "_conflict_count": 0,
                "_cannot_measure": [],
                #"cannot_measure": self.inferCannotMeasure(sensor_elem)
            }
            sensors.append(sensor)

        sorted_sensors = self.sortSensorsByMeasurements(sensors, measurements)

        for sensor in sorted_sensors:
            sensor_name = sensor.get("series", "Unknown")
            sensor_manufacturer = sensor.get("manufacturer", "Unknown")

            tooltip = ""
            if sensor["_conflict_count"] > 0:
                conflicts = sensor["_cannot_measure"]
                tooltip = self.createToolTipForSensorMeasure(conflicts)

            icon = self.getConflictIcon(sensor["_conflict_count"])
            combo_box.addItem(icon[0], f"{sensor_manufacturer} {sensor_name}")

            index = combo_box.count() - 1
            combo_box.setItemData(index, sensor)
            combo_box.setItemData(index, tooltip, QtCore.Qt.ToolTipRole)

        self.form.SensorCombobox.setMaxVisibleItems(3)
        self.form.SensorCombobox.view().setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        combo_box.blockSignals(False)

        

    def disableSensorSelectorUI(self):
        self.form.SensorCombobox.setCurrentIndex(-1)
        self.form.SensorCombobox.setEnabled(False)
        self.form.AddSensor.setEnabled(False)
        self.form.SensorCombobox.setToolTip("Run any measurement to select sensor")
        self.form.AddSensor.setToolTip("Run any measurement to add sensor")
        self.form.SensorDetails.hide()
        self.form.SaveSensorButton.setEnabled(False)
        # if self.form.


    def createToolTipForSensorMeasure(self, conflict_list):
        conflict_list = "\n".join(conflict_list)
        tooltip = f"Cannot measure:\n{conflict_list}"
        return tooltip


    def handleSensorCounterChange(self, value):
        line_edit = self.form.SensorCounterLineEdit
        try:
            val = int(value)
            line_edit.setText(str(val))
            # self.surf_sense.setNumberOfSensors(value)
        except ValueError:
            line_edit.setText(str(self.surf_sense.getNumberOfSensors()))

        if int(line_edit.text()) > 0:
            self.form.SaveSensorButton.setEnabled(True)
        else:
            self.form.SaveSensorButton.setEnabled(False)
 

    def showSensorDetails(self, checked):
        sensor_detail_widget = self.form.findChild(QtWidgets.QWidget, "FOVwidget")
        if checked == True:
            self.form.SensorLegend.hide()
            self.form.NumberOfSensorLabel.hide()
            self.form.SensorCounterLineEdit.hide()
            self.form.PcsLabel.hide()
            sensor_detail_widget.show()
            self.form.ShowSensorData.setText("Hide details")
        else:
            self.form.SensorLegend.show()
            self.form.NumberOfSensorLabel.show()
            self.form.SensorCounterLineEdit.show()
            self.form.PcsLabel.show()
            sensor_detail_widget.hide()
            self.form.ShowSensorData.setText("Show details")


    def saveSensorData(self):
        combo_box = self.form.SensorCombobox
        index = combo_box.currentIndex()
        data = combo_box.itemData(index)

        line_edit = self.form.SensorCounterLineEdit
        number_of_sensor = int(line_edit.text())

        self.surf_sense.setSensor(data)
        self.surf_sense.setNumberOfSensors(number_of_sensor)
               
        sensor_widget = self.sensor_widget
        self.form.ExtraLayout.addWidget(sensor_widget)
        self.form.toolBox.hide()
        
        sensor_widget.show()
        list_widget = sensor_widget.MeasurementsSummaryList
        measurements = self.surf_sense.getMeasurements()
        for obj in measurements:
            self.new_measure.addListItemWithToListWidget(list_widget, obj.name, obj.id)
        
        combo_box = self.form.SensorCombobox
        index = combo_box.currentIndex()
        data = combo_box.itemData(index)
        manufacturer = data.get('manufacturer')
        series = data.get('series')
        self.sensor_widget.SelectedSensorLabel.setText(f"{manufacturer} {series}")
        
        sensor_data = self.findSensorByManufacturerAndSeries(manufacturer, series)
        if sensor_data is not None:
            sensor_dict = self.sensorElementToDict(sensor_data)
            # print(sensor_dict)
            res_xy_far = self.safeToFloat(sensor_dict.get("Resolution_XY_FAR", 0.0))
            res_z_far = self.safeToFloat(sensor_dict.get("Resolution_Z_FAR", 0.0))
            # print(f"res_xy_far: {res_xy_far}")
            res_xy_far_in_mm = res_xy_far * SurfSensePanel.MICROMETERTOMM if self.sensor_unit["Resolution_XY_FAR"] == "µm" else res_xy_far
            self.sensor_widget.NewResolution.setText(str(res_xy_far_in_mm))


    def populateKinematicDetails(self, data):
        """
        data: list of (label_text, value_text) tuples
        Example: [("Manufacturer", "KUKA"), ("Axes", "6")]
        """
        layout = self.form.KinematicDetail_gridLayout

        # Clear previous widgets in the layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # Add new rows
        for row, (label_text, value_text) in enumerate(data):
            label = QtWidgets.QLabel(label_text)
            value = QtWidgets.QLabel(value_text)

            layout.addWidget(label, row, 0)
            layout.addWidget(value, row, 1)

        self.form.KinematicDetailsFrame.show()

    def getRadiusFromSelection(self):
        try:
            sel = Gui.Selection.getSelectionEx()
            if not sel:
                print("No selection")
                return None

            # If user selected the whole object instead of sub-elements
            if not sel[0].SubObjects:
                print("No sub-shapes selected (edge/face needed)")
                return None

            shape = sel[0].SubObjects[0]  # First selected sub-shape

            if shape.ShapeType == "Edge":
                curve = shape.Curve
                if curve.TypeId == 'Part::GeomCircle':
                    return curve.Radius
                potCircle = self.bsplineEdgeIsCircle(shape)
                if potCircle is not None:
                    radius, center = potCircle
                    return radius
                else:
                    print("Edge is not a circle")
                    return None
                    
            elif shape.ShapeType == "Face":
                surf = shape.Surface
                if surf.TypeId == 'Part::GeomCylinder':
                    return surf.Radius
                elif surf.TypeId == 'Part::GeomSphere':
                    return surf.Radius
                elif surf.TypeId == 'Part::GeomTorus':
                    return surf.MinorRadius
                else:
                    print("Face is not cylinder/sphere/torus")
                    return None

            else:
                print(f"Unsupported shape type: {shape.ShapeType}")
                return None

        except Exception as e:
            print("Error while computing radius:", e)

        return None
    
    def bsplineEdgeIsCircle(self, edge, samples=10, rel_tol=1e-3, abs_tol=1e-4):
        """
        Check if a BSpline edge is actually a circular arc by testing curvature constancy.
        Returns (radius: float, center: App.Vector) if circular, otherwise None.
        """
        # Basic guards
        if edge is None or not hasattr(edge, "Curve"):
            return None

        curve = edge.Curve
        try:
            is_bspline = getattr(curve, "TypeId", "") == "Part::GeomBSplineCurve"
        except Exception:
            is_bspline = False

        if not is_bspline:
            return None

        # Use discretize to get points along the curve
        try:
            points = edge.discretize(samples)
            if len(points) < 3:
                return None
        except Exception:
            return None

        # Calculate curvature at 10 evenly spaced points
        curvatures = []
        param_range = edge.LastParameter - edge.FirstParameter
        
        for i in range(samples):
            param = edge.FirstParameter + (i / (samples - 1)) * param_range
            try:
                curvature = curve.curvature(param)
                curvatures.append(curvature)
            except Exception:
                return None

        if not curvatures:
            return None

        # Check if all curvatures are within tolerance
        avg_curvature = sum(curvatures) / len(curvatures)
        if avg_curvature == 0.0:
            return None
            
        for curvature in curvatures:
            if abs(curvature - avg_curvature) / avg_curvature > rel_tol:
                return None

        # Calculate radius from average curvature
        radius = 1.0 / avg_curvature
        
        # Calculate center using three well-spaced points
        n = len(points)
        pA = points[int(0.1 * n)]
        pB = points[int(0.5 * n)]
        pC = points[int(0.9 * n)]
        
        try:
            circ = Part.Circle(pA, pB, pC)
            center = circ.Center
        except Exception:
            return None

        return (radius, center)


class SurfSenseSelObserver:
    """
    causes an action to the mouse click on an object
    This function remains resident (in memory) with the function "addObserver(s)"
    "removeObserver(s) # Uninstalls the resident function
    """
    def __init__(self, parent, m_widget):
        self.measure_widget = m_widget
        self.parent = parent
        self.selected_parts = []
        # self.list_view = measure_widget.SelectedObjects
        self.model = QtGui.QStandardItemModel()
        # self.list_view.setModel(self.model)


    def setPreselection(self,doc,obj,sub):                                      # Preselection object
        pass
        # App.Console.PrintMessage("setPreselection" + str(sub)+ "\n")          # The part of the object name


    def addSelection(self,doc,obj,sub,pnt):                                   # Selection object
        # App.Console.PrintMessage("add"+ "\n")
        # App.Console.PrintMessage(str(doc)+ "\n")                              # Name of the document
        # App.Console.PrintMessage(str(obj)+ "\n")                              # Name of the object
        # App.Console.PrintMessage(str(sub)+ "\n")                              # The part of the object name
        # App.Console.PrintMessage(str(pnt)+ "\n")                              # Coordinates of the object
        # App.Console.PrintMessage("______"+ "\n")
        # self.addSelectedItemToSelection()
        self.selected_parts.append(f"{str(obj)}.{str(sub)}")
        # print("%" * 50)
        self.getSelectedTopLevelLabels()
        # print("%" * 50)
        self.handleSelection()


    def removeSelection(self,doc,obj,sub):                                    # Remove the selection
        # App.Console.PrintMessage("remove"+ "\n")
        self.model.clear()
        #self.addSelectedItemToSelection()
        self.handleSelection()


    def setSelection(self,doc):                                               # Set selection
        return
        App.Console.PrintMessage("set"+ "\n")


    def clearSelection(self,doc):
        #App.Console.PrintMessage("clear"+ "\n")                               # If click on another object, clear the previous object
        self.model.clear()
        self.handleSelection()


    def getTopLevelLabel(self, sel):
        obj = sel.Object
        if not obj:
            return None

        parent = obj.getParentGeoFeatureGroup()
        if parent:
            return parent.Name
        return obj.Name 


    def getSelectedTopLevelLabels(self):
        selection = Gui.Selection.getSelectionEx()
        labels = []
        for sel in selection:
            label = self.getTopLevelLabel(sel)
            if label:
                labels.append(label)
        return labels


    def addSelectedItemToSelection(self, doc=None, obj1=None, sub=None):
        self.model.clear()
        sel = Gui.Selection.getSelectionEx()
        if len(sel):
            for i in range(len(sel)):
                for idx, obj in enumerate(sel[i].SubElementNames):
                    message = f"{idx + 1} - {obj}"
                    item = QtGui.QStandardItem(message)
                    self.model.appendRow(item)
    

    def handleSelection(self):
        sel = Gui.Selection.getSelectionEx()
        mw = Gui.getMainWindow()
        general_tolerance = mw.findChild(QtGui.QLineEdit, "GeneralToleranceSearchBox")
        if general_tolerance is not None:
            if len(sel):
                if len(sel[0].SubElementNames) == 1:
                    if general_tolerance.text() != "":
                        self.measure_widget.onOptionSelected(general_tolerance.text())
                else:
                    if general_tolerance.text() != "":
                        self.parent.new_measure.setGeneralToleranceInputFields("-", "-")


class DocObserver:
    def __init__(self, parent=None):
        self.parent = parent




    def slotChangedObject(self, obj, prop):
        if prop == "Label" and hasattr(obj, "SurfSenseID"):
            measurement = self.parent.surf_sense.getMeasurementByID(obj.SurfSenseID)
            if measurement:
                measurement.name = obj.Label
                self.parent.new_measure.refreshMeasurementHistory()
                self.parent.populateSensorComboBox()


    def slotDeletedObject(self, obj):
        from Utils import getListItemWidgetByID
        if hasattr(obj, "SurfSenseID"):
            surf_sense_id = obj.SurfSenseID
            measurement = self.parent.surf_sense.getMeasurementByID(surf_sense_id)
            if measurement:
                succes = self.parent.surf_sense.removeMeasurement(surf_sense_id)
                if succes:
                    print(f"Measurement with ID-{surf_sense_id} is removed")
                    list_item_widget = getListItemWidgetByID(surf_sense_id)
                    if list_item_widget:
                        list_item_widget.remove_self(False)
                else:
                    print(f"Something went wrong {surf_sense_id}")


    def slotDeletedDocument(self, doc):
        objs = doc.Objects
        for obj in objs:
            self.slotDeletedObject(obj)