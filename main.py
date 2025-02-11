import sys
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication, QGroupBox, QPushButton,QLayout, 
                               QMainWindow, QLabel, QVBoxLayout,QCheckBox,
                               QHBoxLayout, QWidget, QDoubleSpinBox, QGridLayout)
from flexlogger_lib import FlexLoggerInterface


class PumpControlApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initialize()
        self.initialize_widgets()
        #Test case:
        self.test_case()  
        self.initialize_layouts()  

        self.sensor_update_timer = QTimer(self)
        self.sensor_update_timer.timeout.connect(self.update_sensor_values)
        self.sensor_update_timer.start(1000)                                               

        # Main Horizontal Layout (3 columns)
        self.set_widgets_size()
        main_layout = QHBoxLayout()
        main_layout.addWidget(self.col1_widget)
        main_layout.addWidget(self.col2_widget)
        main_layout.addWidget(self.col3_widget)

        # Central widget setup
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def initialize(self):
        self.setWindowTitle("Pump Control")
        self.setGeometry(100, 100, 600, 300)
        
        # Declare enables
        self.fluid_cycle_enable = False
        self.chamber_cycle_enable = False
        self.pressure_cycle_enable = False

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
        self.pressure_period = 0.0
        self.pressure_min_psi = 0
        self.pressure_max_psi = 0

    def initialize_widgets(self):
        """Initialize widgets"""
        # Column 1 widgets
        self._test_param_title = self.create_title_widget("TEST PARAMETERS")
        self.create_total_test_box()
        self.create_fluid_cycle_box()
        self.create_chamber_cycle_box()
        self.create_pressure_cycle_box()
        self._generate_plot_button = self.create_button("generate plot", self.generate_plot)

        # Column 2 widgets
        self._main_title = self.create_title_widget("AUTOMATED MANIFOLD TESTING")

        self._flexlogger_button = self.create_button("Connect FlexLogger", self.connect_flexlogger)
        self._flexlogger_conn_status = self.create_conn_status(self.flexlogger_connected)

        self._canalyzer_button = self.create_button("Connect CANalyzer", self.connect_canalyzer)
        self._canalyzer_conn_status = self.create_conn_status(self.canalyzer_connected)

        self._easytemp_button = self.create_button("Connect easytemp", self.connect_easytemp)       
        self._easytemp_conn_status = self.create_conn_status(self.easytemp_connected) 

        self.create_graph() # Create graph
        self._start_resume_button = self.create_button("TEMP START", self.start_test)
        self._pause_stop__button = self.create_button("TEMP PAUSE", self.pause_test)  
        # Column 3 widgets
        self._live_status_title = self.create_title_widget("LIVE STATUS")
        if self.flexlogger_connected:
            self._pressure_sensors = self.create_sensor_box(self._flex.get_sensor_list())
        else: 
            self._pressure_sensors = self.create_sensor_box(None)
    
    def initialize_layouts(self):
        # Column 1 Layout
        self.col1_layout = QVBoxLayout()
        self.col1_layout.addWidget(self._test_param_title)
        self.col1_layout.addWidget(self._total_test_box)
        self.col1_layout.addWidget(self._fluid_cycle_box)
        self.col1_layout.addWidget(self._chamber_cycle_box)
        self.col1_layout.addWidget(self._pressure_cycle_box)
        self.col1_layout.addWidget(self._generate_plot_button)

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
        self.col2_layout.addLayout(self.conn_layout)
        self.col2_layout.addWidget(self._graph_widget)
        self.button_layout = QGridLayout()
        self.button_layout.addWidget(self._start_resume_button, 1, 0)
        self.button_layout.addWidget(self._pause_stop__button, 1, 1)
        self.col2_layout.addLayout(self.button_layout)


        # Column 3 Layout
        self.col3_layout = QVBoxLayout()
        self.col3_layout.addWidget(self._live_status_title)
        self.col3_layout.addWidget(self._pressure_sensors)

    def set_widgets_size(self):
        """Define column and individual widget sizing"""
        # Set column 1 size
        self.col1_widget = QWidget()
        self.col1_widget.setLayout(self.col1_layout)
        self.col1_widget.setFixedWidth(200)
        # Set column 2 size
        self.col2_widget = QWidget()
        self.col2_widget.setLayout(self.col2_layout)
        self.col2_widget.setFixedWidth(600)  
        # Set column 3 size
        self.col3_widget = QWidget()
        self.col3_widget.setLayout(self.col3_layout)
        self.col3_widget.setFixedWidth(200)
        # Set widget heights
        self._test_param_title.setFixedHeight(30)
        self._total_test_box.setFixedHeight(60)
        self._fluid_cycle_box.setFixedHeight(150)
        self._chamber_cycle_box.setFixedHeight(150)
        self._pressure_cycle_box.setFixedHeight(150)
        self._main_title.setFixedHeight(30)
        self._graph_widget.setFixedHeight(500)    
        self._live_status_title.setFixedHeight(30)
    
    def create_title_widget(self, title):
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
        self._fluid_cycle_box = QGroupBox("fluid cycle period")
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
        self._chamber_cycle_box = QGroupBox("chamber cycle period")
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

        # Create cycle input in hours
        cycle_input = QDoubleSpinBox(self)
        cycle_input.setSingleStep(0.25)
        cycle_input.setMaximum(9999.99)
        cycle_input.valueChanged.connect(lambda value: self.update_variable("pressure_period", value))
        layout.addWidget(cycle_input, 1, 0)
        layout.addWidget(QLabel("hours"), 1, 1)

        # Create min temp
        min_temp = QDoubleSpinBox(self)
        min_temp.setSingleStep(1)       
        min_temp.valueChanged.connect(lambda value: self.update_variable("pressure_min_psi", value))
        layout.addWidget(QLabel("min PSI"), 2, 0)
        layout.addWidget(min_temp, 2, 1)

        # Create max temp
        max_temp = QDoubleSpinBox(self)
        max_temp.setSingleStep(1)       
        max_temp.valueChanged.connect(lambda value: self.update_variable("pressure_max_psi", value))
        layout.addWidget(QLabel("max PSI"), 3, 0)
        layout.addWidget(max_temp, 3, 1)

        # Create enable checkbox
        checkbox = QCheckBox('enable', self)
        checkbox.setChecked(False)
        checkbox.stateChanged.connect(lambda state: self.update_boolean('pressure_cycle_enable', state))
        layout.addWidget(checkbox)

        self._pressure_cycle_box.setLayout(layout)

    def update_variable(self, var_name, value):
        """Modularly update a variable's value"""
        setattr(self, var_name, value)
        #print(f"{var_name} updated: {value}") # debug statement

    def update_boolean(self, var_name, state):
        """Modularly update a booleans's state"""
        setattr(self, var_name, state == 2)
        print(f"{var_name}: {state}")

    def create_button(self, label, callback):
        """Create a button"""
        button = QPushButton(label)
        button.clicked.connect(callback)
        return button

    def connect_flexlogger(self):
        print("connecting flexlogger")  
        self._flex = FlexLoggerInterface()
        self.flexlogger_connected = self._flex.connect_to_instance()
        self.sensor_update_timer.timeout.connect(self.check_conn)
        
        if self.flexlogger_connected:
            # Set connection to true
            self.flexlogger_connected = True

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
            self.col3_layout.removeWidget(self._pressure_sensors)
            self._pressure_sensors.deleteLater()
            self._pressure_sensors = new_sensor_box
            self.col3_layout.addWidget(self._pressure_sensors)

    def connect_canalyzer(self):
        print("connecting canalyzer")

    def connect_easytemp(self):
        print("connecting easytemp")
    
    def create_conn_status(self, conn_bool):
        conn_status = QLabel("")
        if conn_bool:
            conn_status.setText("Connected")
        else: 
            conn_status.setText("Not Connected")

        return conn_status

    def create_graph(self):
        """Create graph widget"""
        self._graph_widget = pg.PlotWidget()

        self._graph_widget.setBackground('w')
        self._graph_widget.setTitle(f"Step Function Temperature Cycles ({str(self.total_period)}) hours")
        self._graph_widget.setLabel('left', 'Temperature (°C)')
        self._graph_widget.setLabel('bottom', 'Hour (H)')
        self._graph_widget.showGrid(x=True, y=True)

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

    def plot(self, x, y, plotname, color):
        """Function for plotting calculated period"""
        pen = pg.mkPen(color=color, width=7)
        self._graph_widget.plot(x, y, name=plotname, pen=pen, stepMode=True)

    def generate_plot(self):
        """Generate a plot based on enabled cycles"""
        print("generating plot")
        self._graph_widget.clear()
        self._graph_widget.setXRange(0, self.total_period, padding=0)

        if self.fluid_cycle_enable:
            x, y = self.calculate_period(self.fluid_period, self.fluid_min_temp, self.fluid_max_temp)
            self.plot(x, y, "fluid temperature", 'b')

        if self.chamber_cycle_enable:
            x, y = self.calculate_period(self.chamber_period, self.chamber_min_temp, self.chamber_max_temp)
            self.plot(x, y, "chamber temperature", 'r')

        if self.pressure_cycle_enable:
            x, y = self.calculate_period(self.pressure_period, self.pressure_min_psi, self.pressure_max_psi)
            self.plot(x, y, "pressure", 'r')
   
    def start_test(self):
        print("start test")

    def pause_test(self):
        print("pause_test")

    def test_case(self):
        self.total_period = 216
        self.fluid_cycle_enable = True
        self.fluid_period = 18 
        self.fluid_max_temp = 30
        self.chamber_cycle_enable = True
        self.chamber_period = 16
        self.chamber_max_temp = 30

    def create_sensor_box(self, sensors):
        """Create widget for sensor data (FlexLogger)"""
        sensor_box = QGroupBox("Live Sensor Data")
        layout = QGridLayout()
        self.sensor_labels = {}

        if not sensors:  # Check if the list is empty
            no_sensors_label = QLabel("No sensors available")
            self.flexlogger_connected = False
            layout.addWidget(no_sensors_label, 0, 0, 1, 2)  # Centered message
        else:
            # For every sensor in the list, create a text and label widget
            for row, sen in enumerate(sensors):
                sensor_label = QLabel("0.00")
                self.sensor_labels[sen] = sensor_label

                layout.addWidget(QLabel(f"{str(sen)}:"), row, 0)
                layout.addWidget(sensor_label, row, 1)

        sensor_box.setLayout(layout)
        return sensor_box
     
    def update_sensor_values(self):
        for sen, label in self.sensor_labels.items():
            new_value = str(self._flex.read_sensor_val(sen))  # Get latest value
            label.setText(new_value)

    def check_conn(self):

        if self._flex.check_active_project() is None:
            # Create a new label
            new_flex_status = QLabel("Not connected")
            # Replace label widget
            self.conn_layout.removeWidget(self._flexlogger_conn_status)
            self._flexlogger_conn_status.deleteLater()
            self._flexlogger_conn_status = new_flex_status
            self.conn_layout.addWidget(self._flexlogger_conn_status, 1, 1)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PumpControlApp()
    window.show()
    
    sys.exit(app.exec())
