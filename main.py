import sys
import os
import serial
import csv
import pyqtgraph as pg
import numpy as np
import time
import threading
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication, QGroupBox, QPushButton, QDialog, QMessageBox,
                               QMainWindow, QLabel, QVBoxLayout,QCheckBox, QLineEdit,
                               QHBoxLayout, QWidget, QDoubleSpinBox, QGridLayout)
from flexlogger_lib import FlexLoggerInterface
from can_controller_lib import Cantroller
from julabo_lib import JULABO
from timer_lib import PausableTimer


class PumpControlApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initialize()
                                                     
    def test_case(self):
        self.total_period = 648
        self.fluid_period = 12 
        self.fluid_min_temp = -20
        self.fluid_max_temp = 40
        self.chamber_period = 13.5
        self.chamber_min_temp = -20
        self.chamber_max_temp = 60
        self.pressure_num_cycles = 444000
        self.pressure_max_psi = 35
        self.pressure_min_psi = 0

    def create_test_widget(self):
        self.test_case_checkbox = QCheckBox("enable cyclic profile")
        self.test_case_checkbox.setChecked(False)
        self.test_case_checkbox.stateChanged.connect(lambda state: self.update_boolean('test_case_enabled', state))

    def initialize(self):
        self.setWindowTitle("Manifold Durability Cyclic Pressure Test")
        self.setGeometry(100, 100, 800, 200)
        
        # Declare enables
        self._test_active = False
        self.profile_generated = False
        self.logging_enabled = False
        self.test_case_enabled = False
        self.resume_cycle_enabled = False
        self.initial_start = False

        # Declare connections
        self.flexlogger_connected = False
        self.canbus_connected = False
        self.julabo_connected = False

        # Declare constants
        self.timer_ms = 1000
        self.plot_width_1 = 3 #line thickness
        self.plot_width_2 = 10 #line thickness
        self.log_file_name = ""

        # Declare variables 
        self.total_period = 0.0
        self.fluid_period = 0.0
        self.fluid_num_cycles = 0
        self.fluid_min_temp = 0
        self.fluid_max_temp = 0
        self.chamber_period = 0.0
        self.chamber_num_cycles = 0
        self.chamber_min_temp = 0
        self.chamber_max_temp = 0
        self.pressure_num_cycles = 0
        self.pressure_min_psi = 0
        self.pressure_max_psi = 0
        self.fluid_remaining_time = 0
        self.chamber_remaining_time = 0

        self.initialize_widgets()
        self.initialize_layouts()  
        
        # Initialize continuous updating timer
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

        self._canbus_button = self.create_button("Connect canbus", self.connect_canbus)
        self._canbus_conn_status = self.create_connection_status_label(self.canbus_connected)

        self._julabo_button = self.create_button("Connect julabo", self.connect_julabo)       
        self._julabo_conn_status = self.create_connection_status_label(self.julabo_connected) 

        self._graph_1 = self.create_graph("Temperature Cycles", "Hour", "Temperature (C)")
        self._graph_2 = self.create_graph("Pressure", "Hour", "Pressure(PSI)")
        self._start_resume_button = self.create_button("START/RESUME", self.start_test)
        self._pause_stop_button = self.create_button("TEMP PAUSE", self.pause_test)  

        # Column 3 widgets
        self._live_status_title = self.create_title_label("LIVE STATUS")
        self.create_cycle_count_box()
        self.create_logging_widgets()
        self.create_test_widget()
        self._resume_cycle_button = self.create_button("RESUME FROM CYCLES", self.resume_cycle_entry)

        # Widget depending on connection
        if self.flexlogger_connected:
            self._sensors_list = self.create_sensor_box(self._flex.get_sensor_list())
        else: 
            self._sensors_list = self.create_sensor_box(None)
    
    def initialize_layouts(self):
        # Column 1 Layout
        self.col1_layout = QVBoxLayout()
        self.col1_layout.addWidget(self._test_param_title)
        self.col1_layout.addWidget(self.test_case_checkbox)
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
        self.conn_layout.addWidget(self._canbus_button, 2, 0)
        self.conn_layout.addWidget(self._canbus_conn_status, 2, 1)
        self.conn_layout.addWidget(self._julabo_button, 3, 0)
        self.conn_layout.addWidget(self._julabo_conn_status, 3, 1)
        self.conn_layout.addWidget(self._graph_1, 4, 0)
        self.conn_layout.addWidget(self._graph_2, 4, 1)
        self.col2_layout.addLayout(self.conn_layout)
        self.button_layout = QGridLayout()
        self.button_layout.addWidget(self._start_resume_button, 1, 0)
        self.button_layout.addWidget(self._pause_stop_button, 1, 1)
        self.col2_layout.addLayout(self.button_layout)

        # Column 3 Layout
        self.col3_layout = QVBoxLayout()
        self.col3_layout.addWidget(self._live_status_title)
        self.col3_layout.addWidget(self._cycle_count_box)
        self.col3_layout.addWidget(self._resume_cycle_button)
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
        self.col2_widget.setFixedWidth(900)  
        # Set column 3 size
        self.col3_widget = QWidget()
        self.col3_widget.setLayout(self.col3_layout)
        self.col3_widget.setFixedWidth(260)
        # Set widget heights
        # Col1
        self._test_param_title.setFixedHeight(30)
        self._total_test_box.setFixedHeight(60)
        self._fluid_cycle_box.setFixedHeight(150)
        self._chamber_cycle_box.setFixedHeight(150)
        self._pressure_cycle_box.setFixedHeight(150)
        # Col2
        self._main_title.setFixedHeight(30)
        self._graph_1.setFixedHeight(500)    
        self._graph_2.setFixedHeight(500) 
        # Col3
        self._live_status_title.setFixedHeight(30)
    
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

        self._chamber_cycle_box.setLayout(layout)

    def create_pressure_cycle_box(self):
        """Create input widget for pressure cycle period input"""
        self._pressure_cycle_box = QGroupBox("pressure cycle period")
        layout = QGridLayout()

        # Create cycle input in number of cycles
        cycle_input = QDoubleSpinBox(self)
        cycle_input.setSingleStep(0.25)
        cycle_input.setMaximum(999999.99)
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

        self._pressure_cycle_box.setLayout(layout)

    def create_cycle_count_box(self):
        self._cycle_count_box = QGroupBox("Live Cycle Count")
        layout = QGridLayout()

        self.pressure_cycle_count_label = QLabel(f"Pressure Cycle Count: 0/{self.pressure_num_cycles}")
        self.fluid_cycle_count_label = QLabel(f"Fluid Cycle Count: 0/{self.fluid_num_cycles}")
        self.chamber_cycle_count_label = QLabel(f"Chamber Cycle Count: 0/{self.chamber_num_cycles}")

        layout.addWidget(self.pressure_cycle_count_label)
        layout.addWidget(self.fluid_cycle_count_label)
        layout.addWidget(self.chamber_cycle_count_label)

        self._cycle_count_box.setLayout(layout)
    
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
    
    def create_logging_widgets(self):
        # File name input
        self.file_name_input = QLineEdit()
        self.file_name_input.setPlaceholderText("Enter file name") 
        self.file_name_input.textChanged.connect(lambda value: self.update_variable("log_file_name", value))
         
        # Enable checkbox
        self.log_checkbox = QCheckBox("enable logging")
        self.log_checkbox.setChecked(False)
        self.log_checkbox.stateChanged.connect(lambda state: self.update_boolean('logging_enabled', state))

    def create_button(self, label, callback):
        """Create a button"""
        button = QPushButton(label)
        button.clicked.connect(callback)
        return button

    def create_dialogue_ok_box(self, win_title, message):
        dlg = QMessageBox(self)
        dlg.setWindowTitle(win_title)
        dlg.setText(message)
        button = dlg.exec()

    def create_dialogue_yes_no_box(self, win_title, message):
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
    
    def update_variable(self, var_name, value):
        """Modularly update a variable's value"""
        setattr(self, var_name, value)
        #print(f"{var_name} updated: {value}") # debug statement

    def update_boolean(self, var_name, state):
        """Modularly update a boolean's state"""
        setattr(self, var_name, state == 2)
        print(f"{var_name}: {state}")

    def connect_flexlogger(self):
        """Attached to flexlogger button, creates an instance and starts updating sensor values"""

        print("Connecting FlexLogger")  
        self._flex = FlexLoggerInterface()
        self.flexlogger_connected = self._flex.connect_to_instance()
        #self.timer.timeout.connect(self.check_connections)
        
        if self.flexlogger_connected:
            # Create a new label
            print("Connected to FlexLogger successfully")
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
            print("Error: FlexLogger did not respond")
            self.create_dialogue_ok_box("Connection Error", "Could not connect to FlexLogger!")
            
    def connect_canbus(self):
        print("Connecting CANBUS")
        self._cantroller = Cantroller()
        self.canbus_connected = self._cantroller.connect_to_instance()

        if self.canbus_connected:
            # Create a new label
            print("Connected to CANBUS successfully")
            new_flex_status = QLabel("Connected")
            # Replace label widget
            self.conn_layout.removeWidget(self._canbus_conn_status)
            self._canbus_conn_status.deleteLater()
            self._canbus_conn_status = new_flex_status
            self.conn_layout.addWidget(self._canbus_conn_status, 2, 1)
        else:
            print("Error: CANBUS did not respond")
            self.create_dialogue_ok_box("Connection Error", "Could not connect to CANBUS!")
    
    def connect_julabo(self):
        """Attempt to connect and verify communication with Julabo."""
        print("Connecting to Julabo")

        try:
            self._julabo = JULABO('COM6', baud=4800) #change based on COM port

            # Test if communication works
            response = self._julabo.get_version()
            if response:
                print(f"Connected to Julabo Version: {response}")
                self.julabo_connected = True
            else:
                print("Error: Julabo did not respond")
                self.julabo_connected = False

        except serial.SerialException:
            print("Error: Could not open COM. Check code for chosen COM port.")
            self.julabo_connected = False


        if self.julabo_connected:
            # Update UI status
            new_status_label = QLabel("Connected" if self.julabo_connected else "Not Connected")

            self.conn_layout.removeWidget(self._julabo_conn_status)
            self._julabo_conn_status.deleteLater()
            self._julabo_conn_status = new_status_label
            self.conn_layout.addWidget(self._julabo_conn_status, 3, 1)
        else:
            self.create_dialogue_ok_box("Connection Error", "Could not connect to julabo!")

    def check_connections(self):
        if self._flex.check_active_project() is None:
            # Create a new label
            new_flex_status = QLabel("Not connected")
            # Replace label widget
            self.conn_layout.removeWidget(self._flexlogger_conn_status)
            self._flexlogger_conn_status.deleteLater()
            self._flexlogger_conn_status = new_flex_status
            self.conn_layout.addWidget(self._flexlogger_conn_status, 1, 1)

    def resume_cycle_entry(self):
        """Dialog box for entering in cycles to resume test"""
        dialog = QDialog()
        dialog.setWindowTitle("Enter Values")
        dialog.setFixedSize(300, 200)

        # Layout
        layout = QVBoxLayout()

        # Resume pressure cycle
        row1 = QHBoxLayout()
        label1 = QLabel("Resume pressure cycle #:")
        spinbox1 = QDoubleSpinBox()
        spinbox1.setRange(0,999999)  
        row1.addWidget(label1)
        row1.addWidget(spinbox1)

        # Resume fluid cycle
        row2 = QHBoxLayout()
        label2 = QLabel("Resume fluid cycle #:")
        spinbox2 = QDoubleSpinBox()
        spinbox2.setRange(0,999999)   
        row2.addWidget(label2)
        row2.addWidget(spinbox2)
        # Remaining time
        row3 = QHBoxLayout()
        label3 = QLabel("Remaining time (s): ")
        spinbox3 = QDoubleSpinBox()
        spinbox3.setRange(0,999999)
        row3.addWidget(label3)
        row3.addWidget(spinbox3)

        # Resume fluid cycle
        row4 = QHBoxLayout()
        label4  = QLabel("Resume chamber cycle #:")
        spinbox4 = QDoubleSpinBox()
        spinbox4.setRange(0,999999)   
        row4.addWidget(label4)
        row4.addWidget(spinbox4)
        # Remaining time
        row5 = QHBoxLayout()
        label5 = QLabel("Remaining time (s): ")
        spinbox5 = QDoubleSpinBox()
        spinbox5.setRange(0,999999)
        row5.addWidget(label5)
        row5.addWidget(spinbox5)

        # OK Button
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)

        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addLayout(row3)
        layout.addLayout(row4)
        layout.addLayout(row5)
        layout.addWidget(ok_button)

        dialog.setLayout(layout)

        # Execute dialog
        if dialog.exec() and self.profile_generated:
            self.pressure_cycle_count = spinbox1.value()

            self.fluid_cycle_count = spinbox2.value()
            self._fluid_timer.remaining_time = spinbox3.value() #set fluid timer remaining time
            self.fluid_remaining_time = spinbox3.value()
            self._fluid_timer.paused = True #set to paused to simulate resuming
            self.fluid_cycle_count_label.setText(f"Fluid Cycle Count: {self.fluid_cycle_count}/{self.fluid_num_cycles}")

            self.chamber_cycle_count = spinbox4.value()
            self._chamber_timer.remaining_time = spinbox5.value() #set chamber timer remaining time
            self.chamber_remaining_time = spinbox5.value()
            self._chamber_timer.paused = True #set to paused to simulate resuming
            self.chamber_cycle_count_label.setText(f"Chamber Cycle Count: {self.chamber_cycle_count}/{self.chamber_num_cycles}")

            for sen in self.sensor_data:
                self.sensor_data[sen]["time_counter"] = (self.fluid_cycle_count - 1) * (self.fluid_period * 3600) + (self.fluid_period * 3600 - self.fluid_remaining_time)
                print("hi")

            self.resume_cycle_enabled = True
                       
        else:
            self.create_dialogue_ok_box("Error", "Profile not generated! Generate profile first.")
                       
            print("updated cycle status")


    def calculate_period(self, cycle_period, cycle_min, cycle_max):
        """(STATIC) Create lists for x-axis and y-axis based on period, min, and max"""
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
                return x, y, len(y) - 1 # This is number of cycles, a cycle being inbetween point A and B

        else:
            print("Entry Error")

    def plot(self, graph, x, y, plotname, color, width):
        """(DYNAMIC) Function for plotting calculated period"""
        pen = pg.mkPen(color=color, width=width)
        graph.plot(x, y, name=plotname, pen=pen, stepMode=True)

    def generate_profile(self):
        """(STATIC) Generate a plot based on enabled cycles"""
        
        if self.create_dialogue_yes_no_box("Confirmation", "Are you sure you want to generate new profile?"):
            print("generating profile")
            # Enable bool
            self.profile_generated = True
            self.initial_start = True
            
            #test case
            if self.test_case_enabled:
                self.test_case() 

            # Deactivate and reset test
            self._test_active = False
            self.pressure_cycle_count = 0

            # Resuming test
            if not self.resume_cycle_enabled:
                self.fluid_cycle_count = 0
                self.chamber_cycle_count = 0
                self.pressure_drop_count = 0 # For pressure drop check

            # Initialize fluid cycling timer
            self._fluid_timer = PausableTimer(self.fluid_period*3600, self.set_julabo_temp)
            self._chamber_timer = PausableTimer(self.chamber_period*3600, self.set_chamber_temp)

            # Clear both graphs and reset the range
            self._graph_1.clear()
            self._graph_2.clear()
            self._graph_1.setXRange(0, self.total_period, padding=0)

            # Re-intialize dict ["curve"] with live plotting because we cleared all .plot()
            self._test_timer_count = 0 # This counter is for 'data[x_values]'
            for sen in self.sensor_data:
                self.sensor_data[sen]["curve"] = self.init_curve_plot(self._choose_graph(sen), 'r')
                self.sensor_data[sen]["values"] = []
                self.sensor_data[sen]["x_values"] = []
                self.sensor_data[sen]["time_counter"] = 0


            # Plot profiles
            x, y, self.fluid_num_cycles = self.calculate_period(self.fluid_period, self.fluid_min_temp, self.fluid_max_temp)
            self.plot(self._graph_1,x, y, "fluid temperature", 'm', self.plot_width_1)

            x, y, self.chamber_num_cycles = self.calculate_period(self.chamber_period, self.chamber_min_temp, self.chamber_max_temp)
            self.plot(self._graph_1,x, y, "chamber temperature", 'k', self.plot_width_1)

            # Update cycle labels
            self.pressure_cycle_count_label.setText(f"Pressure Cycle Count: {self.pressure_cycle_count}/{self.pressure_num_cycles}")
            self.fluid_cycle_count_label.setText(f"Fluid Cycle Count: {self.fluid_cycle_count}/{self.fluid_num_cycles}")
            self.chamber_cycle_count_label.setText(f"Chamber Cycle Count: {self.chamber_cycle_count}/{self.chamber_num_cycles}")

            # LOGGING
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
                        self._graph_2.setXRange(x_data[0], x_data[-1], padding=0.1)

                if self.logging_enabled:
                    self.update_log_file()

    def _choose_graph(self, sensor_label):
        """(STATIC) Internal function to choose which graph to display on based on sensor name"""
        if "temp" in sensor_label.lower():
            return self._graph_1
        elif "psi" in sensor_label.lower():
            return self._graph_2
        else:    
            return self._graph_2

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

                    if len(data["values"]) > 100:
                        data["values"].pop(0)
                        data["x_values"].pop(0)
                    
                    # inlet pressure drop check
                    if "psi" in sensor.lower() and "inlet" in sensor.lower():
                        curr_pressure = new_value # Sets current value to sensor reading
                        if curr_pressure < self.pressure_max_psi - 5: # if current pressure < max psi add to count -5 for range
                            self.pressure_drop_count +=1
                        else:                                     # if not, reset count
                            self.pressure_drop_count = 0
                        
                        print(f"Pressure drop count: {self.pressure_drop_count}") # Debug statement
                        if self.pressure_drop_count > 100:
                            print("Pressure drop detected, test crashed")
                            self._test_active = False
                            self.create_crash_file()
                            self.create_dialogue_ok_box("Test Error", "Pressure drop detected, test paused")
                            

            except ValueError:
                print(f"Warning: Non-numeric value received for {sensor}: {new_value}")

    def get_timestamp(self):
        """(DYNAMIC) Return the current timestamp as a filename-safe formatted string"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # Replace colons with dashes

    def start_test(self):
        
        """(STATIC) Enables test active bool and starts the test loop in a separate thread"""
        if not self.flexlogger_connected:
            self.create_dialogue_ok_box("Warning", "FlexLogger not connected!")
            return

        if not self.canbus_connected:
            self.create_dialogue_ok_box("Warning", "CANBUS not connected!")
            return
        
        if not self.julabo_connected:
            self.create_dialogue_ok_box("Warning", "JULABO not connected!")
            return

        if self.profile_generated:
            print("Starting test")
            # Activate test bool
            self._test_active = True 

            # Updating live curve
            self.p_timer = QTimer(self) # Initialize timer 
            self.p_timer.timeout.connect(self.update_curve)
            self.p_timer.start(self.timer_ms)

            # Run pressure profile            
            self.test_thread = threading.Thread(target=self.run_test_profile, daemon=True) # This is in separate thread to allow for GUI interaction
            self.test_thread.start()

            # Time
            if self.initial_start:
                self.last_fluid_time = time.time() - self.fluid_remaining_time
                self.last_chamber_time = time.time() - self.chamber_remaining_time
                self.initial_start = False


        else:
            self.create_dialogue_ok_box("Warning", "Profile not generated!")

    def pause_test(self):
        """(STATIC) Disables test active bool"""
        # Disable test bool
        self._test_active = False
        self._fluid_timer.pause()
        self._chamber_timer.pause()
        print("Pausing test")
        # Stops the pressure profile (does not reset pressure_cycle_count)
        if hasattr(self, "test_thread") and self.test_thread.is_alive():
            self.test_thread.join()  # Ensure the test thread stops cleanly
        print("Test paused")
        self.create_dialogue_ok_box("Test Status", "Test paused!")
    
    def create_crash_file(self):
        """"(STATIC) Create a file with status of test on crash as a backup"""
        # Get crash timestamp and float(time)
        crash_timestamp = self.get_timestamp()
        crash_time = time.time()

        # Create crash file
        self.crash_filename = crash_timestamp + "_Crash"
        with open(self.crash_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["pressure_cycle_count", "fluid_cycle_count", "fluid_cycle_remaining_seconds", "chamber_cycle_count", "chamber_cycle_remaining_seconds"])

        # Fill crash file with remaining status
        data = [self.pressure_cycle_count] + [self.fluid_cycle_count] + [(self.fluid_period*3600) - (crash_time - self.last_fluid_time)] + [self.chamber_cycle_count] + [(self.chamber_period*3600) - (crash_time - self.last_chamber_time)]
        with open(self.crash_filename, mode='a', newline='') as file:  # Use 'a' (append mode)
            writer = csv.writer(file)
            writer.writerow(data)  # Write row with timestamp + sensor values

        print(f"Crash file '{self.crash_filename}' created successfully.")

    def create_log_file(self, name):
        """(STATIC) Creates a CSV file with a timestamped header including sensor names."""
        sensors = self._flex.get_sensor_list()  # Get list of sensor names
        self.curr_filename = self.get_timestamp() + "_" + name
        with open(self.curr_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp"] + ["pressure_cycle_count"] + sensors)  # Write header row once
        print(f"Log file '{self.curr_filename}' created successfully.")

    def update_log_file(self):
        """(DYNAMIC) Updates CSV file with values"""
        curr_data = [self.get_timestamp()] + [self.pressure_cycle_count] # Start with timestamp as first element

        # Extract the latest values from each sensor and append them
        for sen, data in self.sensor_data.items():
            if data["values"]:  
                curr_data.append(data["values"][-1])  # Get the most recent value

        with open(self.curr_filename, mode='a', newline='') as file:  # Use 'a' (append mode)
            writer = csv.writer(file)
            writer.writerow(curr_data)  # Write row with timestamp + sensor values

    def run_test_profile(self):
        """(STATIC) Runs the test loop, cycling pumps on and off while test is active."""
        self._cantroller.start()
        self._julabo.set_power_on()
        self._fluid_timer.start()
        self._chamber_timer.start()
        
        # Initial sequence to let test warm up
        if self._test_active and self.pressure_cycle_count < self.pressure_num_cycles:
            self._cantroller.set_bcm_power(60)
            self._cantroller.set_pump2_power(60)
            time.sleep(2)

        while self._test_active and self.pressure_cycle_count < self.pressure_num_cycles:
            self._cantroller.set_bcm_power(84)
            self._cantroller.set_pump2_power(84)
            time.sleep(4.52)

            self._cantroller.set_bcm_power(0)
            self._cantroller.set_pump2_power(0)
            time.sleep(.75)  

            #print(f"Julabo temp: {self._julabo.get_temperature()}") # Debug statement

            self.pressure_cycle_count += 1
            self.pressure_cycle_count_label.setText(f"Pressure Cycle Count: {self.pressure_cycle_count}/{self.pressure_num_cycles}")

        # PAUSING BEHAVIOUR
        if self.pressure_cycle_count < self.pressure_num_cycles:
            self._cantroller.stop()
            self._fluid_timer.pause()
            self._chamber_timer.pause()
            self._julabo.set_power_off()
        # PUMP PROFILE FINISHED
        else:
            time.sleep(5) # Allow time for clean log finish
            self._test_active = False
            self.stop_test()
            #self.create_dialogue_ok_box("Test Status", "Test is completed!")
            print("pressure_profile_finished")

    def set_julabo_temp(self):
        """(DYNAMIC) Function to change temperature of fluid in julabo based on even/odd (called at end of timer)"""
        self.last_fluid_time = time.time()

        if self.fluid_cycle_count % 2 == 0:
            self._julabo.set_work_temperature(self.fluid_max_temp)
            print(f"Set julabo temp to max_temp: {self.fluid_max_temp}")
        else: 
            self._julabo.set_work_temperature(self.fluid_min_temp)
            print(f"Set julabo temp to min_temp: {self.fluid_min_temp} ")

        self.fluid_cycle_count+=1
        self.fluid_cycle_count_label.setText(f"Fluid Cycle Count: {self.fluid_cycle_count}/{self.fluid_num_cycles}")

    def set_chamber_temp(self):
        """(DYNAMIC) Filler for logging chamber cycle status"""
        self.last_chamber_time = time.time()
        self.chamber_cycle_count+=1
        self.chamber_cycle_count_label.setText(f"Chamber Cycle Count: {self.chamber_cycle_count}/{self.chamber_num_cycles}")
        

    def stop_test(self):
        """(STATIC) Stop moving components of test"""
        if self.julabo_connected:
            self._fluid_timer.stop()
            self._julabo.set_power_off()
        if self.canbus_connected:
            self._cantroller.stop()
        self._chamber_timer.stop()

    def closeEvent(self, event):
        """(STATIC) Override to cleanly stop the timer on window close"""
        if self._test_active:
            self.stop_test()
        if self.julabo_connected:
            self._julabo.close()
        if self.canbus_connected:
            self._cantroller.shutdown()
        event.accept()  # Proceed with window closing


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PumpControlApp()
    window.show()


    sys.exit(app.exec())
    
   