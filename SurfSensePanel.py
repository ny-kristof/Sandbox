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
    # TODO avoid magic numbers?
    # ZERO = 0
    # ONE = 1
    # TWO = 2
    # THREE = 3
    def __init__(self, loc, parent=None):
        super().__init__(parent)
        # dlg =  os.path.join(loc, "SurfSenseHorizontal.ui")
        dlg =  os.path.join(loc, "UI\\SurfSenseVertical.ui")
        self.loc = loc
        self.form = Gui.PySideUic.loadUi(dlg)
        self.surf_sense = SurfSense(self)
        self.list_widget = self.form.MeasurementsListWidget
        self.new_measure = NewMeasure.NewMeasure(self, loc)
        self.selection_planner = SelectionPlanner.SelectionPlanner(self.new_measure.form)
        # self.selObserver = SurfSenseSelObserver(self.new_measure.form)
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
        
        self.new_measure.handleMeasurementHistory(self.form.Measurements)
        icon = QtGui.QIcon(os.path.join(self.loc, "icons\\plus_sign.svg"))
        self.form.AddSensor.setIcon(icon)
        self.disableSensorSelectorUI()
        self.handleMeasurementSaveButtonState()
        self.populateSensorLegendLabel()
        dialog =  os.path.join(self.loc, "UI\\SensorDetails.ui")
        self.form.SensorDataLayout.setWidget(0, QtGui.QFormLayout.FieldRole, Gui.PySideUic.loadUi(dialog))
        # findchild?
        self.form.SensorDataLayout.itemAt(0, QtGui.QFormLayout.FieldRole).widget().hide()
        
        
    
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
        self.form.KinematicsComboBox.hide()
        self.form.KinematicsComboBoxLabel.hide()
        QtWidgets.QApplication.instance().installEventFilter(self)


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
        self.new_measure.handleMeasurementHistory(measure_widget.Measurements)
                            
        # Gui.Selection.addObserver(self.selObserver)
        # self.selObserver.addSelectedItemToSelection()
       

    def closeMeasureWidget(self, measure_widget):
        self.form.ExtraLayout.removeWidget(measure_widget)
        measure_widget.hide()
        self.form.toolBox.show()
        # Gui.Selection.removeObserver(self.selObserver)


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

        elif sender is self.form.ManipulatorButton:
            self.form.RobotButton.setChecked(False)
            self.surf_sense.setReflectionAbility("Manipulator")
        

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
            pos = event.globalPosition().toPoint()  # For PySide6

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
            print(sensor_dict)
            
        # fov_data = data.get("FOV")

        # sensor_layout = self.form.SensorHelperMsgLayout
        # if sensor_layout.rowCount() != 0:
        #     while sensor_layout.rowCount() > 0:
        #         sensor_layout.removeRow(0)

        # conflict_count = data.get("_conflict_count")
        # state = self.getConflictIcon(conflict_count)
        # tool_tip = self.createToolTipForSensorMeasure(data.get("_conflict_list"))

        # icon_label = QtGui.QLabel()
        # icon_label.setPixmap(state[0].pixmap(self._sensor_icon_size))
                    
        # sensor_layout.addRow(icon_label, QtGui.QLabel(state[1]))
        # if conflict_count != 0:
        #     sensor_layout.addRow("", QtGui.QLabel(tool_tip))
        
        # if index > -1:
        #     if self.form.SensorDetails.isHidden():
        #         self.form.SensorDetails.show()
            
        #     self.loadSensorDetails(fov_data)
            #detail_layout = self.form.SensorDetailsLayout
        

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
        try:
            CSExporter.add_coordinate_systems_to_xml(self.selection_planner.root_node)
            tree = ET.ElementTree(self.selection_planner.root_node)
            #App.Console.PrinteMessage(f"tree: {tree}")
            tree.write("C:\\Users\\KaszaZsolt\\Documents\\SurfSense\\measurements.xml", encoding="utf-8", xml_declaration=True)
            # for dim in self.dimensions:
            #     App.ActiveDocument.removeObject(dim.Name)
            App.Console.PrintMessage("File saved succesfully")
        except:
            App.Console.PrintError("Failed to save the measurements")


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
                m_tolerance =  self.safeToFloat(measurement.tolerance)
                m_sampling_rate =  self.safeToFloat(measurement.sampling_rate)
                res_xy_far = self.safeToFloat(sensor.get("Resolution_XY_FAR", 0.0))
                res_z_far = self.safeToFloat(sensor.get("Resolution_Z_FAR", 0.0))
                res_xy_far_in_mm = res_xy_far / 1000 # measurement unit is mm so to compare to µm need this divison
                res_z_far_in_mm = res_z_far / 1000 # measurement unit is mm so to compare to µm need this divison
                # print(f"++++++++++++++++++++++++++++++++++")
                # print(f"snesor: {sensor}")
                # print(f"m_type: {m_type}")
                # print(f"m_tolerance: {m_tolerance}")
                # print(f"m_sampling_rate: {m_sampling_rate}")
                # print(f"res_xy_far: {res_xy_far_in_mm}")
                # print(f"res_z_far: {res_z_far_in_mm}")
                # print(f"++++++++++++++++++++++++++++++++++")
                if m_tolerance * m_sampling_rate < res_xy_far_in_mm:
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
        conflict_list = ", ".join(conflict_list)
        tooltip = f"Cannot measure: {conflict_list}"
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
            self.form.PcsLabel.hide()
            sensor_detail_widget.show()
            self.form.ShowSensorData.setText("Hide details")
        else:
            self.form.SensorLegend.show()
            self.form.NumberOfSensorLabel.show()
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
        print(vars(self.surf_sense))


class SurfSenseSelObserver:
    """
    causes an action to the mouse click on an object
    This function remains resident (in memory) with the function "addObserver(s)"
    "removeObserver(s) # Uninstalls the resident function
    """
    def __init__(self, m_widget):
        measure_widget = m_widget
        self.list_view = measure_widget.SelectedObjects
        self.model = QtGui.QStandardItemModel()
        self.list_view.setModel(self.model)


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
        self.addSelectedItemToSelection()


    def removeSelection(self,doc,obj,sub):                                    # Remove the selection
        # App.Console.PrintMessage("remove"+ "\n")
        self.model.clear()
        self.addSelectedItemToSelection()


    def setSelection(self,doc):                                               # Set selection
        return
        App.Console.PrintMessage("set"+ "\n")


    def clearSelection(self,doc):
        #App.Console.PrintMessage("clear"+ "\n")                               # If click on another object, clear the previous object
        self.model.clear()


    def addSelectedItemToSelection(self, doc=None, obj1=None, sub=None):
        self.model.clear()
        sel = Gui.Selection.getSelectionEx()
        if len(sel):
            for i in range(len(sel)):
                for idx, obj in enumerate(sel[i].SubElementNames):
                    message = f"{idx + 1} - {obj}"
                    item = QtGui.QStandardItem(message)
                    self.model.appendRow(item) 



class DocObserver:
    def __init__(self, parent=None):
        self.parent = parent

    def slotActivateDocument(self,doc):
        print(doc.Name)


    def slotChangedObject(self, obj, prop):
        if prop == "Label" and hasattr(obj, "SurfSenseID"):
            measurement = self.parent.surf_sense.getMeasurementByID(obj.SurfSenseID)
            if measurement:
                measurement.name = obj.Label
                self.parent.new_measure.refreshMeasurementHistory()
                self.parent.populateSensorComboBox()