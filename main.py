import sys
import os
import csv
import pyqtgraph as pg
import numpy as np
import time
import threading
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication, QGroupBox, QPushButton, QLayout, QMessageBox,
                               QMainWindow, QLabel, QVBoxLayout,QCheckBox, QLineEdit,
                               QHBoxLayout, QWidget, QDoubleSpinBox, QGridLayout)
from flexlogger_lib import FlexLoggerInterface
from can_controller_lib import Cantroller


class PumpControlApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initialize()
        self.test_case() 
                                                     
    def initialize(self):
        self.setWindowTitle("Pump Control")
        self.setGeometry(100, 100, 600, 200)
        
        # Declare enables
        self.fluid_cycle_enable = False
        self.chamber_cycle_enable = False
        self.pressure_cycle_enable = False
        self._test_active = False
        self.profile_generated = False
        self.logging_enabled = False
        self.test_error_bool = False

        # Declare connections
        self.flexlogger_connected = False
        self.canalyzer_connected = False
        self.easytemp_connected = False

        # Declare variables 
        self.total_period = 0.0
        self.fluid_period = 0.0
        self.fluid_min_temp = 0
        self.fluid_max_temp = 0
        self.chamber_period = 0.0
        self.chamber_min_temp = 0
        self.chamber_max_temp = 0
        self.pressure_num_cycles = 0
        self.pressure_min_psi = 0
        self.pressure_max_psi = 0
        self.timer_ms = 1000
        self.plot_width_1 = 3
        self.plot_width_2 = 10
        self.log_file_name = ""

        self.initialize_widgets()
        self.initialize_layouts()  
        
        #initialize timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_sensor_values)
        self.timer.start(self.timer_ms)  

    def initialize_widgets(self):
        """Initialize widgets"""

        # Column 1 widgets
        self._test_param_title = self.create_title_label("TEST PARAMETERS")
        self.create_total_test_box()
        self.create_fluid_cycle_box()
        self.create_chamber_cycle_box()
        self.create_pressure_cycle_box()
        self._generate_profile_button = self.create_button("GENERATE PROFILE", self.generate_profile)

        # Column 2 widgets
        self._main_title = self.create_title_label("AUTOMATED MANIFOLD TESTING")

        self._flexlogger_button = self.create_button("Connect FlexLogger", self.connect_flexlogger)
        self._flexlogger_conn_status = self.create_connection_status_label(self.flexlogger_connected)

        self._canalyzer_button = self.create_button("Connect CANalyzer", self.connect_canalyzer)
        self._canalyzer_conn_status = self.create_connection_status_label(self.canalyzer_connected)

        self._easytemp_button = self.create_button("Connect EasyTemp", self.connect_easytemp)       
        self._easytemp_conn_status = self.create_connection_status_label(self.easytemp_connected) 

        self.graph_1 = self.create_graph("Temperature Cycles", "Hour", "Temperature (C)")
        self.graph_2 = self.create_graph("Pressure", "Hour", "Pressure(PSI)")
        self._start_resume_button = self.create_button("START/RESUME", self.start_test)
        self._pause_stop__button = self.create_button("TEMP PAUSE", self.pause_test)  
        # Column 3 widgets
        self._live_status_title = self.create_title_label("LIVE STATUS")
        self._cycle_count_title = self.create_title_label("Cycle Count: --")
        self.create_logging_widgets()

        # Widget depending on connection
        if self.flexlogger_connected:
            self._sensors_list = self.create_sensor_box(self._flex.get_sensor_list())
        else: 
            self._sensors_list = self.create_sensor_box(None)
    
    def initialize_layouts(self):
        # Column 1 Layout
        self.col1_layout = QVBoxLayout()
        self.col1_layout.addWidget(self._test_param_title)
        self.col1_layout.addWidget(self._total_test_box)
        self.col1_layout.addWidget(self._fluid_cycle_box)
        self.col1_layout.addWidget(self._chamber_cycle_box)
        self.col1_layout.addWidget(self._pressure_cycle_box)
        self.col1_layout.addWidget(self._generate_profile_button)
        self.col1_layout.addWidget(self.file_name_input)
        self.col1_layout.addWidget(self.log_checkbox)
        
        # Column 2 Layout
        self.col2_layout = QVBoxLayout()
        self.col2_layout.addWidget(self._main_title)
        self.conn_layout = QGridLayout()
        self.conn_layout.addWidget(self._flexlogger_button, 1, 0)
        self.conn_layout.addWidget(self._flexlogger_conn_status, 1, 1)
        self.conn_layout.addWidget(self._canalyzer_button, 2, 0)
        self.conn_layout.addWidget(self._canalyzer_conn_status, 2, 1)
        self.conn_layout.addWidget(self._easytemp_button, 3, 0)
        self.conn_layout.addWidget(self._easytemp_conn_status, 3, 1)
        self.conn_layout.addWidget(self.graph_1, 4, 0)
        self.conn_layout.addWidget(self.graph_2, 4, 1)
        self.col2_layout.addLayout(self.conn_layout)
        self.button_layout = QGridLayout()
        self.button_layout.addWidget(self._start_resume_button, 1, 0)
        self.button_layout.addWidget(self._pause_stop__button, 1, 1)
        self.col2_layout.addLayout(self.button_layout)

        # Column 3 Layout
        self.col3_layout = QVBoxLayout()
        self.col3_layout.addWidget(self._live_status_title)
        self.col3_layout.addWidget(self._cycle_count_title)
        self.col3_layout.addWidget(self._sensors_list)
        

        # Main Overall Layout (3 columns)
        self.set_widgets_size()
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.col1_widget)
        main_layout.addWidget(self.col2_widget)
        main_layout.addWidget(self.col3_widget)

        # Central widget setup
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def set_widgets_size(self):
        """Define column and individual widget sizing"""
        # Set column 1 size
        self.col1_widget = QWidget()
        self.col1_widget.setLayout(self.col1_layout)
        self.col1_widget.setFixedWidth(200)
        # Set column 2 size
        self.col2_widget = QWidget()
        self.col2_widget.setLayout(self.col2_layout)
        self.col2_widget.setFixedWidth(800)  
        # Set column 3 size
        self.col3_widget = QWidget()
        self.col3_widget.setLayout(self.col3_layout)
        self.col3_widget.setFixedWidth(200)
        # Set widget heights
        # Col1
        self._test_param_title.setFixedHeight(30)
        self._total_test_box.setFixedHeight(60)
        self._fluid_cycle_box.setFixedHeight(150)
        self._chamber_cycle_box.setFixedHeight(150)
        self._pressure_cycle_box.setFixedHeight(150)
        # Col2
        self._main_title.setFixedHeight(30)
        self.graph_1.setFixedHeight(500)    
        self.graph_2.setFixedHeight(500) 
        # Col3
        self._live_status_title.setFixedHeight(30)
        self._cycle_count_title.setFixedHeight(30)
    
    def create_title_label(self, title):
        """Create boxed title widget"""
        # Create box and layout
        title_widget = QGroupBox(None)
        layout = QGridLayout()
        # Create title text label
        label = QLabel(title)
        label.setAlignment(Qt.AlignCenter)
        # Add label to layout, then assign layout to box
        layout.addWidget(label)
        title_widget.setLayout(layout)
        # For modularity (no self.)
        return title_widget
    
    def create_total_test_box(self):
        """Create input widget for total test period input"""
        self._total_test_box = QGroupBox("total test period")
        layout = QGridLayout()

        # Create total period input in hours
        total_input = QDoubleSpinBox(self) 
        total_input.setSingleStep(0.25)    
        total_input.setMaximum(9999.99)
        total_input.valueChanged.connect(lambda value: self.update_variable("total_period", value))
        layout.addWidget(total_input, 1, 0)
        layout.addWidget(QLabel("hours"), 1, 1)

        self._total_test_box.setLayout(layout)
        
    def create_fluid_cycle_box(self):
        """Create input widget for fluid cycle peroid input"""
        self._fluid_cycle_box = QGroupBox("fluid cycle period (magenta)")
        layout = QGridLayout()

        # Create cycle input in hours
        cycle_input = QDoubleSpinBox(self)
        cycle_input.setSingleStep(0.25)
        cycle_input.setMaximum(9999.99)
        cycle_input.valueChanged.connect(lambda value: self.update_variable("fluid_period", value)) # updates self.fluid_period everytime input is updated
        layout.addWidget(cycle_input, 1, 0)
        layout.addWidget(QLabel("hours"), 1, 1)

        # Create min temp
        min_temp = QDoubleSpinBox(self)
        min_temp.setSingleStep(1)
        min_temp.setMinimum(-100.00)
        min_temp.valueChanged.connect(lambda value: self.update_variable("fluid_min_temp", value))  
        layout.addWidget(QLabel("min temp (°C)"), 2, 0)
        layout.addWidget(min_temp, 2, 1)

        # Create max temp
        max_temp = QDoubleSpinBox(self)
        max_temp.setSingleStep(1)
        max_temp.setMinimum(-100.00)
        max_temp.valueChanged.connect(lambda value: self.update_variable("fluid_max_temp", value))   
        layout.addWidget(QLabel("max temp (°C)"), 3, 0)
        layout.addWidget(max_temp, 3, 1)

        # Create enable checkbox
        checkbox = QCheckBox('enable', self)
        checkbox.setChecked(False)
        checkbox.stateChanged.connect(lambda state: self.update_boolean('fluid_cycle_enable', state))
        layout.addWidget(checkbox)

        self._fluid_cycle_box.setLayout(layout)

    def create_chamber_cycle_box(self):
        """Create input widget for chamber cycle period input"""
        self._chamber_cycle_box = QGroupBox("chamber cycle period (black)")
        layout = QGridLayout()

        # Create cycle input in hours
        cycle_input = QDoubleSpinBox(self)
        cycle_input.setSingleStep(0.25)
        cycle_input.setMaximum(9999.99)
        cycle_input.valueChanged.connect(lambda value: self.update_variable("chamber_period", value))
        layout.addWidget(cycle_input, 1, 0)
        layout.addWidget(QLabel("hours"), 1, 1)

        # Create min temp
        min_temp = QDoubleSpinBox(self)
        min_temp.setSingleStep(1)   
        min_temp.setMinimum(-100.00)
        min_temp.valueChanged.connect(lambda value: self.update_variable("chamber_min_temp", value))      
        layout.addWidget(QLabel("min temp (°C)"), 2, 0)
        layout.addWidget(min_temp, 2, 1)

        # Create max temp
        max_temp = QDoubleSpinBox(self)
        max_temp.setSingleStep(1)   
        max_temp.setMinimum(-100.00)  
        max_temp.valueChanged.connect(lambda value: self.update_variable("chamber_max_temp", value))  
        layout.addWidget(QLabel("max temp (°C)"), 3, 0)
        layout.addWidget(max_temp, 3, 1)

        # Create enable checkbox
        checkbox = QCheckBox('enable', self)
        checkbox.setChecked(False)
        checkbox.stateChanged.connect(lambda state: self.update_boolean('chamber_cycle_enable', state))
        layout.addWidget(checkbox)

        self._chamber_cycle_box.setLayout(layout)

    def create_pressure_cycle_box(self):
        """Create input widget for pressure cycle period input"""
        self._pressure_cycle_box = QGroupBox("pressure cycle period")
        layout = QGridLayout()

        # Create cycle input in number of cycles
        cycle_input = QDoubleSpinBox(self)
        cycle_input.setSingleStep(0.25)
        cycle_input.setMaximum(99999.99)
        cycle_input.valueChanged.connect(lambda value: self.update_variable("pressure_num_cycles", value))
        layout.addWidget(cycle_input, 1, 0)
        layout.addWidget(QLabel("cycles"), 1, 1)

        # Create min psi
        min_psi = QDoubleSpinBox(self)
        min_psi.setSingleStep(1)       
        min_psi.valueChanged.connect(lambda value: self.update_variable("pressure_min_psi", value))
        layout.addWidget(QLabel("min PSI"), 2, 0)
        layout.addWidget(min_psi, 2, 1)

        # Create max psi
        max_psi = QDoubleSpinBox(self)
        max_psi.setSingleStep(1)       
        max_psi.valueChanged.connect(lambda value: self.update_variable("pressure_max_psi", value))
        layout.addWidget(QLabel("max PSI"), 3, 0)
        layout.addWidget(max_psi, 3, 1)

        # Create enable checkbox
        checkbox = QCheckBox('enable', self)
        checkbox.setChecked(False)
        checkbox.stateChanged.connect(lambda state: self.update_boolean('pressure_cycle_enable', state))
        layout.addWidget(checkbox)

        self._pressure_cycle_box.setLayout(layout)

    def create_logging_widgets(self):
        # File name input
        self.file_name_input = QLineEdit()
        self.file_name_input.setPlaceholderText("Enter file name") 
        self.file_name_input.textChanged.connect(lambda value: self.update_variable("log_file_name", value))  
         
        # Enable checkbox
        self.log_checkbox = QCheckBox("enable logging")
        self.log_checkbox.setChecked(False)
        self.log_checkbox.stateChanged.connect(lambda state: self.update_boolean('logging_enabled', state))       

    def update_variable(self, var_name, value):
        """Modularly update a variable's value"""
        setattr(self, var_name, value)
        #print(f"{var_name} updated: {value}") # debug statement

    def update_boolean(self, var_name, state):
        """Modularly update a boolean's state"""
        setattr(self, var_name, state == 2)
        print(f"{var_name}: {state}")

    def create_button(self, label, callback):
        """Create a button"""
        button = QPushButton(label)
        button.clicked.connect(callback)
        return button

    def connect_flexlogger(self):
        """Attached to flexlogger button, creates an instance and starts updating sensor values"""

        print("connecting flexlogger")  
        self._flex = FlexLoggerInterface()
        self.flexlogger_connected = self._flex.connect_to_instance()
        self.timer.timeout.connect(self.check_connections)
        
        if self.flexlogger_connected:
            # Create a new label
            new_flex_status = QLabel("Connected")
            # Replace label widget
            self.conn_layout.removeWidget(self._flexlogger_conn_status)
            self._flexlogger_conn_status.deleteLater()
            self._flexlogger_conn_status = new_flex_status
            self.conn_layout.addWidget(self._flexlogger_conn_status, 1, 1)

            # Create a new sensor box with updated sensor list
            new_sensor_box = self.create_sensor_box(self._flex.get_sensor_list())
            # Remove old widget and replace it
            self.col3_layout.removeWidget(self._sensors_list)
            self._sensors_list.deleteLater()
            self._sensors_list = new_sensor_box
            self.col3_layout.addWidget(self._sensors_list)
        else: 
            self.dialogue_ok_box("Connection Error", "Could not connect to FlexLogger!")
            
    def connect_canalyzer(self):
        print("connecting canalyzer")
        self._cantroller = Cantroller()
        self.canalyzer_connected = self._cantroller.connect_to_instance()

        if self.canalyzer_connected:
            # Create a new label
            new_flex_status = QLabel("Connected")
            # Replace label widget
            self.conn_layout.removeWidget(self._canalyzer_conn_status)
            self._canalyzer_conn_status.deleteLater()
            self._canalyzer_conn_status = new_flex_status
            self.conn_layout.addWidget(self._canalyzer_conn_status, 2, 1)
        else:
            self.dialogue_ok_box("Connection Error", "Could not connect to CANBUS!")

    def connect_easytemp(self):
        print("connecting easytemp")
    
    def create_connection_status_label(self, conn_bool):
        conn_status = QLabel("")
        if conn_bool:
            conn_status.setText("Connected")
        else: 
            conn_status.setText("Not Connected")

        return conn_status

    def create_graph(self, title="Graph", x_label="X-Axis", y_label="Y-Axis"):
        """Create a customizable graph widget with a title and axis labels"""
        graph = pg.PlotWidget()

        graph.setBackground('w')
        graph.setTitle(title)
        graph.setLabel('left', y_label)
        graph.setLabel('bottom', x_label)
        graph.showGrid(x=True, y=True)

        return graph

    def calculate_period(self, cycle_period, cycle_min, cycle_max):
        """Create lists for x-axis and y-axis based on period, min, and max"""
        x = []  # Start with an empty list
        y = []  # Start with an empty list
        if cycle_period > 0 and cycle_max > cycle_min:  # Prevent division by zero
                indices = int(self.total_period / cycle_period) + 1
                for i in range(indices):
                    x.append(cycle_period * i)  # Append value to x
                    if i % 2 == 0:
                        y.append(cycle_max)  # Append max temp for even indices
                    else:
                        y.append(cycle_min)  # Append min temp for odd indices
                
                x.append(cycle_period * indices)
                print("X values:", x)
                print("Y values:", y)
                return x, y

        else:
            print("Entry Error")

    def plot(self, graph, x, y, plotname, color, width):
        """Function for plotting calculated period"""
        pen = pg.mkPen(color=color, width=width)
        graph.plot(x, y, name=plotname, pen=pen, stepMode=True)

    def generate_profile(self):
        """Generate a plot based on enabled cycles"""
        if self.dialogue_yes_no_box("Confirmation", "Are you sure you want to generate new profile?"):
            print("generating profile")
            # Enable bool
            self.profile_generated = True

            # Deactivate and reset test
            self._test_active = False
            self.cycle_count_num = 0

            # Clear both graphs and reset the range
            self.graph_1.clear()
            self.graph_2.clear()
            self.graph_1.setXRange(0, self.total_period, padding=0)

            # Re-intialize dict ["curve"] with live plotting because we cleared all .plot()
            self._test_timer_count = 0 # This counter is for 'data[x_values]'
            for sen in self.sensor_data:
                self.sensor_data[sen]["curve"] = self.init_curve_plot(self._choose_graph(sen), 'r')
                self.sensor_data[sen]["values"] = []
                self.sensor_data[sen]["x_values"] = []
                self.sensor_data[sen]["time_counter"] = 0

            # Plot profiles
            if self.fluid_cycle_enable:
                x, y = self.calculate_period(self.fluid_period, self.fluid_min_temp, self.fluid_max_temp)
                self.plot(self.graph_1,x, y, "fluid temperature", 'm', self.plot_width_1)
            if self.chamber_cycle_enable:
                x, y = self.calculate_period(self.chamber_period, self.chamber_min_temp, self.chamber_max_temp)
                self.plot(self.graph_1,x, y, "chamber temperature", 'k', self.plot_width_1)

            if self.logging_enabled:
                self.create_log_file(self.log_file_name)

    def init_curve_plot(self, graph, color):
        """(STATIC) Create a live plot 'curve' for a sensor"""
        curve = graph.plot([], [], pen=pg.mkPen(color=color, width=self.plot_width_2)) 
        return curve

    def update_curve(self):
            """(DYNAMIC) Update all live plots with new sensor values"""
            if self._test_active: 
                
                for sensor, data in self.sensor_data.items(): 
                    # Ensure alignment in plot update
                    x_data = np.array(data["x_values"], dtype=float)
                    y_data = np.array(data["values"], dtype=float)
                    data["curve"].setData(x_data, y_data)  # Update plot

                    # Auto-scroll X axis
                    if len(x_data) > 0:
                        self.graph_2.setXRange(x_data[0], x_data[-1], padding=0.1)

                if self.logging_enabled:
                    self.update_log_file()

    def _choose_graph(self, sensor_label):
        """(STATIC) Internal function to choose which graph to display on based on sensor name"""
        if "temp" in sensor_label.lower():
            return self.graph_1
        elif "psi" in sensor_label.lower():
            return self.graph_2
        else:    
            return self.graph_2

    def create_sensor_box(self, sensors):
        """(STATIC) Create widget for sensor data (FlexLogger)"""
        sensor_box = QGroupBox("Live Sensor Data")
        layout = QGridLayout()
        self.sensor_data = {}
        
        if not sensors:  # Check if the sensor list is empty
            no_sensors_label = QLabel("No sensors available")
            self.flexlogger_connected = False
            layout.addWidget(no_sensors_label, 0, 0, 1, 2)
        else:
            # For every sensor in the list, create a label widget, value array, curve
            for row, sen in enumerate(sensors):
                sensor_label = QLabel("0.00")

                # Initialize CSV file for logging
                if self.logging_enabled:
                    pass

                # Dict to store sensor properties
                self.sensor_data[sen] = {
                    "label": sensor_label,
                    "x_values": [],
                    "values": [],
                    "time_counter": 0,
                    "curve": self.init_curve_plot(self._choose_graph(sen), 'r')
                }
                
                layout.addWidget(QLabel(f"{str(sen)}:"), row, 0)
                layout.addWidget(sensor_label, row, 1)

        # Return created sensor widget layout 
        sensor_box.setLayout(layout)
        return sensor_box

    def update_sensor_values(self):
        """(DYNAMIC) Function connected to timer to append sensor values to dict & log to file"""
        for sensor, data in self.sensor_data.items():
            new_value = self._flex.read_sensor_val(sensor)  # Read latest sensor value
            
            try:
                new_value = float(new_value)  # Ensure it's a valid float
                data["label"].setText(str(new_value))  # Update QLabel

                if self._test_active:
                    
                    time_index = data["time_counter"] * (self.timer_ms / 3600000)  # X-axis value
                    data["time_counter"] += 1  # Increment array counter

                    # Append new value and time index (keep 200 most recent)
                    data["values"].append(new_value)
                    data["x_values"].append(time_index)

                    if len(data["values"]) > 200:
                        data["values"].pop(0)
                        data["x_values"].pop(0)

            except ValueError:
                print(f"Warning: Non-numeric value received for {sensor}: {new_value}")

    def get_timestamp(self):
        """Return the current timestamp as a filename-safe formatted string"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # Replace colons with dashes

    def start_test(self):
        
        """(STATIC) Enables test active bool and starts the test loop in a separate thread"""
        if not self.flexlogger_connected:
            self.dialogue_ok_box("Warning", "FlexLogger not connected!")
            return

        if not self.canalyzer_connected:
            self.dialogue_ok_box("Warning", "CANBUS not connected!")
            return

        if self.profile_generated:
            print("Starting test")
            self._test_active = True  # Enable test flag

            self.p_timer = QTimer(self)
            self.p_timer.timeout.connect(self.update_curve)
            self.p_timer.start(self.timer_ms)

            # Run the test in a separate thread so GUI remains responsive
            self.test_thread = threading.Thread(target=self.run_test, daemon=True)
            self.test_thread.start()

        else:
            self.dialogue_ok_box("Warning", "Profile not generated!")

    def pause_test(self):
        """(STATIC) Disables test active bool"""
        self._test_active = False
        print("pause_test")
            
        if hasattr(self, "test_thread") and self.test_thread.is_alive():
            self.test_thread.join()  # Ensure the test thread stops cleanly

        self._cantroller.set_bcm_power(0)
        self._cantroller.set_pump2_power(0)
        self._cantroller.stop()
        print("Test stopped.")

    def test_case(self):
        self.total_period = 216
        self.fluid_cycle_enable = True
        self.fluid_period = 18 
        self.fluid_max_temp = 30
        self.chamber_cycle_enable = True
        self.chamber_period = 16
        self.chamber_max_temp = 30
        self.pressure_cycle_enable = True
        self.pressure_num_cycles = 10
        self.pressure_max_psi = 35
        self.pressure_min_psi = 15

    def check_connections(self):
        if self._flex.check_active_project() is None:
            # Create a new label
            new_flex_status = QLabel("Not connected")
            # Replace label widget
            self.conn_layout.removeWidget(self._flexlogger_conn_status)
            self._flexlogger_conn_status.deleteLater()
            self._flexlogger_conn_status = new_flex_status
            self.conn_layout.addWidget(self._flexlogger_conn_status, 1, 1)

    def dialogue_ok_box(self, win_title, message):
        dlg = QMessageBox(self)
        dlg.setWindowTitle(win_title)
        dlg.setText(message)
        button = dlg.exec()

    def dialogue_yes_no_box(self, win_title, message):
        dlg = QMessageBox(self)
        dlg.setWindowTitle(win_title)
        dlg.setText(message)
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dlg.setIcon(QMessageBox.Question)
        button = dlg.exec()
        
        if button == QMessageBox.Yes:
            return True
        else:
            return False

    def create_log_file(self, name):
        """Creates a CSV file with a timestamped header including sensor names."""
        sensors = self._flex.get_sensor_list()  # Get list of sensor names
        self.curr_filename = self.get_timestamp() + "_" + name
        with open(self.curr_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp"] + sensors)  # Write header row once
        print(f"Log file '{self.curr_filename}' created successfully.")

    def update_log_file(self):
        """(DYNAMIC) Updates CSV file with values"""
        curr_data = [self.get_timestamp()]  # Start with timestamp as first element

        # Extract the latest values from each sensor and append them
        for sen, data in self.sensor_data.items():
            if data["values"]:  
                curr_data.append(data["values"][-1])  # Get the most recent value

        with open(self.curr_filename, mode='a', newline='') as file:  # Use 'a' (append mode)
            writer = csv.writer(file)
            writer.writerow(curr_data)  # Write row with timestamp + sensor values

    def run_test(self):
        """Runs the test loop, cycling pumps on and off while test is active."""
        self._cantroller.start()
        # Initial sequence to let test warm up
        if self._test_active and not self.test_error_bool and self.cycle_count_num < self.pressure_num_cycles:
            self._cantroller.set_bcm_power(60)
            self._cantroller.set_pump2_power(60)
            time.sleep(2)

        while self._test_active and self.cycle_count_num < self.pressure_num_cycles:
            self._cantroller.set_bcm_power(83)
            self._cantroller.set_pump2_power(83)
            time.sleep(4)

            self._cantroller.set_bcm_power(0)
            self._cantroller.set_pump2_power(0)
            time.sleep(1)  

            self.cycle_count_num += 1
            self._cycle_count_title.setTitle(f"Cycle Count: {self.cycle_count_num}/{self.pressure_num_cycles}")

        self._cantroller.stop()  # Ensure pumps turn off when exiting


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PumpControlApp()
    window.show()


    sys.exit(app.exec())
    
