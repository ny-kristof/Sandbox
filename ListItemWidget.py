import FreeCADGui as Gui
import FreeCAD as App
from PySide import QtGui, QtWidgets
import os

class ListItemWidget(QtWidgets.QWidget):
    from PySide.QtCore import Signal
    itemRemoved = Signal(object)
    # itemEdited = Signal(object)

    def __init__(self, text, list_widget, loc, measurement_id, surf_sense_panel):
        super().__init__()
        self.list_widget = list_widget
        self.measurement_id = measurement_id
        self.surf_sense_panel = surf_sense_panel

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)

        self.label = QtWidgets.QLabel(text)
        self.label.setObjectName(f"Measurement-{self.measurement_id}")

        self.edit_button = QtWidgets.QToolButton()
        edit_icon = QtGui.QIcon(os.path.join(loc, "icons", "edit.svg"))
        self.edit_button.setIcon(edit_icon)
        self.edit_button.setFixedSize(20, 20)
        self.edit_button.clicked.connect(self.emit_edit_signal)

        self.button = QtWidgets.QToolButton()
        icon = QtGui.QIcon(os.path.join(loc, "icons\\close_sign.svg"))
        self.button.setIcon(icon)
        self.button.setFixedSize(20, 20)
        self.button.clicked.connect(lambda: self.remove_self(True))

        layout.addWidget(self.label)
        layout.addStretch()
        layout.addWidget(self.edit_button)
        layout.addWidget(self.button)


    def emit_edit_signal(self):
        measurement_data = self.surf_sense_panel.surf_sense.getMeasurementByID(self.measurement_id)
        mw = Gui.getMainWindow()
        measurement_widget = mw.findChild(QtWidgets.QWidget, "NewMeasure")
        # print(measurement_data)
        if measurement_widget.isVisible() == False:
            self.surf_sense_panel.openNewMeasure()
        self.surf_sense_panel.new_measure.setSelfMeasrurementEditingState(self.measurement_id)
        self.surf_sense_panel.new_measure.handleMeasurementEdit(measurement_data)



    def remove_self(self, from_self = True):
        surf_sense_id = -1
        for i in range(self.list_widget.count()):
            if self.list_widget.itemWidget(self.list_widget.item(i)) == self:
                surf_sense_id = self.measurement_id
                self.list_widget.takeItem(i)
                break
        
        self.itemRemoved.emit(self.measurement_id)
        if from_self:
            # print("Removing measurement with ID:", surf_sense_id)
            for obj in App.ActiveDocument.Objects:
                if hasattr(obj, "SurfSenseID"):
                    if obj.SurfSenseID == surf_sense_id:
                        App.ActiveDocument.removeObject(obj.Name)

    def renameItem(self, new_name):
        #self.setObjectName(new_name)
        self.label.setText(new_name)