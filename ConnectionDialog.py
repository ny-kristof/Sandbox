import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets, QtCore, QtGui
import re
import json
from pathlib import Path


class ConnectionDialog(QtWidgets.QDialog):
    def __init__(self, json_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connection Settings")
        self.setModal(True)
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.MSWindowsFixedSizeDialogHint)

        self.json_path = json_path

        # Load existing values if available
        self.config_data = self.load_json()

        # Layout
        layout = QtWidgets.QVBoxLayout(self)

        # --- IP input ---
        ip_label = QtWidgets.QLabel("IP Address:")
        self.ip_input = QtWidgets.QLineEdit()
        self.ip_input.setPlaceholderText("e.g. 192.168.1.100")
        layout.addWidget(ip_label)
        layout.addWidget(self.ip_input)

        # --- Port input ---
        port_label = QtWidgets.QLabel("Port:")
        self.port_input = QtWidgets.QLineEdit()
        self.port_input.setPlaceholderText("e.g. 8080")
        layout.addWidget(port_label)
        layout.addWidget(self.port_input)

        # Prefill from file (if available)
        sensor_data = self.config_data.get("sensor-data", {})
        self.ip_input.setText(sensor_data.get("sensor-ip", ""))
        self.port_input.setText(str(sensor_data.get("sensor-port", "")))

        # --- OK button ---
        self.ok_button = QtWidgets.QPushButton("OK")
        self.ok_button.clicked.connect(self.validate_inputs)
        layout.addWidget(self.ok_button)

        # Store results
        self.ip_address = None
        self.port = None

    # --------------------------
    def load_json(self):
        """Load existing data.json if available, otherwise return default."""
        try:
            if self.json_path.exists():
                with open(self.json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            App.Console.PrintError(f"Failed to load config file: {e}\n")

        # Default structure
        return {
            "sensor-data": {
                "sensor-ip": "",
                "sensor-port": "",
                "tools-path": "/tools/"
            },
            "tools": []
        }

    # --------------------------
    def save_json(self, ip, port):
        """Save updated IP and port to data.json."""
        try:
            self.config_data["sensor-data"]["sensor-ip"] = ip
            self.config_data["sensor-data"]["sensor-port"] = port

            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(self.config_data, f, indent=4)
            App.Console.PrintMessage(f"Configuration saved to {self.json_path}\n")

        except Exception as e:
            App.Console.PrintError(f"Failed to save config file: {e}\n")

    # --------------------------
    def validate_inputs(self):
        """Validate IP and port fields before closing."""
        ip_text = self.ip_input.text().strip()
        port_text = self.port_input.text().strip()

        # IP validation using regex
        ip_pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
        if not ip_pattern.match(ip_text):
            QtWidgets.QMessageBox.warning(self, "Invalid IP", "Please enter a valid IPv4 address.")
            return

        if any(int(octet) > 255 for octet in ip_text.split(".")):
            QtWidgets.QMessageBox.warning(self, "Invalid IP", "IP address octets must be between 0 and 255.")
            return

        # Port validation
        if not port_text.isdigit() or not (1 <= int(port_text) <= 65535):
            QtWidgets.QMessageBox.warning(self, "Invalid Port", "Please enter a valid port (1–65535).")
            return

        # All good
        self.ip_address = ip_text
        self.port = int(port_text)

        # Save to JSON file
        self.save_json(self.ip_address, self.port)

        self.accept()
