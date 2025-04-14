import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QFileDialog, QLabel, QTextEdit, QTableWidget, QTableWidgetItem, QDialog, QListWidget, QHBoxLayout
)

class SettingsEditor(QDialog):
    def __init__(self, settings_file):
        super().__init__()
        self.settings_file = settings_file
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Edit Settings File")
        self.setGeometry(300, 100, 800, 600)
        
        layout = QHBoxLayout()
        
        # Left list of sections
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self.display_section)
        layout.addWidget(self.list_widget, 2)
        
        # Right table of parameters
        self.table = QTableWidget()
        layout.addWidget(self.table, 3)
        
        # Connect table's itemChanged signal
        self.table.itemChanged.connect(self.on_item_changed)
        
        # Load file settings into sections
        self.load_settings()
        
        # Button to save
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(save_button)
        
        self.setLayout(main_layout)
    
    def load_settings(self):
        """
        Reads the settings file line by line. Sections are identified by '##' lines.
        Parameters (key=value) go into self.sections as a list of tuples (param_id, key, value).
        """
        with open(self.settings_file, "r") as f:
            lines = f.readlines()
        
        self.sections = {}
        self.original_lines = lines  # Keep a copy to preserve comments/format
        current_section = None
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("##"):
                # This is a new section.
                # We'll store it in our dictionary and add to the list widget.
                current_section = stripped.replace("##", "").strip()
                self.sections[current_section] = []
                self.list_widget.addItem(current_section)
            
            elif "=" in stripped and current_section is not None:
                # key=value line
                key, value = stripped.split("=", 1)
                key = key.strip()
                value = value.strip()
                param_id = f"{current_section}::{key}"
                self.sections[current_section].append((param_id, key, value))
        
        # Display first section by default if there is one
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
    
    def display_section(self, index):
        """
        When a section is selected in the list, show its parameters in the table.
        """
        if index < 0:
            return
        
        section = self.list_widget.item(index).text()
        parameters = self.sections.get(section, [])
        
        self.table.blockSignals(True)  # Temporarily block signals to avoid triggers while populating
        self.table.setRowCount(len(parameters))
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.table.setColumnWidth(1, 300)
        
        for row, (param_id, key, value) in enumerate(parameters):
            # First column is read-only param name
            item_key = QTableWidgetItem(key)
            item_key.setFlags(item_key.flags() & ~2)  # Remove editable flag
            self.table.setItem(row, 0, item_key)
            
            # Second column is editable param value
            item_value = QTableWidgetItem(value)
            self.table.setItem(row, 1, item_value)
        
        self.table.blockSignals(False)
    
    def on_item_changed(self, item):
        """
        Sync the edits in the table back to self.sections immediately.
        """
        row = item.row()
        col = item.column()
        
        # Only handle changes in the 'Value' column
        if col != 1:
            return
        
        # Identify which section is currently displayed
        section_index = self.list_widget.currentRow()
        if section_index < 0:
            return
        
        section_name = self.list_widget.item(section_index).text()
        # Retrieve the parameter list for that section
        param_list = self.sections[section_name]
        
        # The (param_id, key, old_value) for this row
        param_id, key, _old_value = param_list[row]
        
        # Grab new value from the edited cell
        new_value = item.text()
        
        # Update the tuple in self.sections
        param_list[row] = (param_id, key, new_value)
    
    def save_settings(self):
        """
        Write the updated parameter values in self.sections back to the file,
        preserving lines that don't match the pattern or comments.
        """
        # Build a dictionary of param_id -> new_value
        new_values = {}
        for section_name, param_list in self.sections.items():
            for (param_id, _key, val) in param_list:
                new_values[param_id] = val
        
        # Read original lines again (could also use self.original_lines)
        with open(self.settings_file, "r") as f:
            lines = f.readlines()
        
        with open(self.settings_file, "w") as f:
            current_section = None
            for line in lines:
                stripped_line = line.strip()
                
                if stripped_line.startswith("##"):
                    # This line defines a new section
                    current_section = stripped_line.replace("##", "").strip()
                    f.write(line)  # write the original line (including newline)
                
                elif "=" in stripped_line and current_section is not None:
                    # It's a key=value line within a known section
                    key = stripped_line.split("=", 1)[0].strip()
                    param_id = f"{current_section}::{key}"
                    
                    # If there's a new value for this param, use it; otherwise keep old line
                    if param_id in new_values:
                        f.write(f"{key}={new_values[param_id]}\n")
                    else:
                        f.write(line)
                else:
                    # Comments or lines outside sections
                    f.write(line)
        
        self.close()


class AcoliteLauncher(QWidget):
    def __init__(self):
        super().__init__()
        
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        self.settings_label = QLabel("Select Settings File:")
        layout.addWidget(self.settings_label)
        
        self.settings_button = QPushButton("Browse Settings File")
        self.settings_button.clicked.connect(self.select_settings_file)
        layout.addWidget(self.settings_button)
        
        self.edit_settings_button = QPushButton("Edit Settings File")
        self.edit_settings_button.clicked.connect(self.edit_settings_file)
        self.edit_settings_button.setVisible(False)
        layout.addWidget(self.edit_settings_button)
        
        self.folder_label = QLabel("Select Image Folder:")
        layout.addWidget(self.folder_label)
        
        self.folder_button = QPushButton("Browse Image Folder")
        self.folder_button.clicked.connect(self.select_image_folder)
        layout.addWidget(self.folder_button)
        
        self.image_list = QTextEdit()
        self.image_list.setReadOnly(True)
        layout.addWidget(self.image_list)
        
        self.command_button = QPushButton("Show Command")
        self.command_button.clicked.connect(self.show_command)
        layout.addWidget(self.command_button)

        self.command_button = QPushButton("Run Acolite")
        self.command_button.clicked.connect(self.run_acolite)
        layout.addWidget(self.command_button)
        
        self.setLayout(layout)
        self.setWindowTitle("Acolite Launcher")
        self.setGeometry(200, 100, 800, 600)
        
        self.settings_file = ""
        self.image_paths = []
    def run_acolite(self):
        if not self.settings_file or not self.image_paths:
            self.image_list.setText("Error: Please select both a settings file and an image folder with .SAFE files.")
            return

        images_arg = ",".join(self.image_paths)
        command = ["python", "launch_acolite.py", "--cli", "--settings", self.settings_file, "--inputfile", images_arg]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        output = ""
        for line in iter(process.stdout.readline, ''):
            output += line
            QApplication.processEvents()  # Ensure UI updates in real-time

        error_output = process.stderr.read()
        output += error_output

        self.show_output(output)
    def show_output(self, output):
        output_dialog = QDialog(self)
        output_dialog.setWindowTitle("Acolite Output")
        output_dialog.setGeometry(300, 200, 600, 400)

        layout = QVBoxLayout()
        output_text = QTextEdit()
        output_text.setReadOnly(True)
        output_text.setText(output)
        layout.addWidget(output_text)

        output_dialog.setLayout(layout)
        output_dialog.exec_()

    def select_settings_file(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Settings File", 
            "", 
            "Text Files (*.txt);;All Files (*)", 
            options=options
        )
        if file_name:
            self.settings_file = file_name
            self.settings_label.setText(f"Settings File: {file_name}")
            self.edit_settings_button.setVisible(True)
    
    def select_image_folder(self):
        folder_name = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder_name:
            self.image_paths = [
                os.path.join(folder_name, f) 
                for f in os.listdir(folder_name) 
                if f.endswith(".SAFE")
            ]
            
            if not self.image_paths:
                self.image_list.setText("No .SAFE images found in the selected folder.")
            else:
                self.image_list.setText("\n".join(self.image_paths))
    
    def show_command(self):
        if not self.settings_file or not self.image_paths:
            self.image_list.setText("Error: Please select both a settings file and an image folder with .SAFE files.")
            return
        
        images_arg = ",".join(self.image_paths)
        command = f"python launch_acolite.py --cli --settings {self.settings_file} --inputfile=\"{images_arg}\""
        
        self.image_list.setText("Generated Command:\n" + command)
    
    def edit_settings_file(self):
        if self.settings_file:
            self.editor = SettingsEditor(self.settings_file)
            self.editor.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AcoliteLauncher()
    ex.show()
    sys.exit(app.exec_())
