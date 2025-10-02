from PySide import QtWidgets
from ListItemWidget import ListItemWidget
from FreeCAD import Gui

def getListItemWidgetByID(id):
    mw = Gui.getMainWindow()
    list_item_widget_id = f"Measurement-{id}"
    label  = mw.findChild(QtWidgets.QLabel, list_item_widget_id)
    if label:
        parent_widget = label.parentWidget()
        if isinstance(parent_widget, ListItemWidget):
            return parent_widget
    return None
