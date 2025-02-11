import sys
import re
from flexlogger.automation import Application, FlexLoggerError

class FlexLoggerInterface:
    def __init__(self):
        self.app = Application()
        self.project = None
        self.chan_spec = None

    def connect_to_instance(self):
        """Establish connection to the active FlexLogger project"""
        self.project = self.app.get_active_project()
        
        if self.project is None:
            print("No project is open in FlexLogger! Please open an instance and try again.")
            return False
        else:
            self.chan_spec = self.project.open_channel_specification_document()
            return True
    
    def check_active_project(self):
        if self.app.get_active_project() is None:
            return False
        else:
            return True
        
    def get_sensor_list(self):
        """Get list of active channel names"""
        all_channels = self.chan_spec.get_channel_names()
        active_channels = []
        for ch in all_channels:
            try:
                if self.chan_spec.is_channel_enabled(ch):  # Check if channel is enabled
                    active_channels.append(ch)
            except FlexLoggerError:
                continue 
        return active_channels

    def read_sensor_val(self, name):
        """Read the value of a specified sensor."""
        if not self.chan_spec:
            print("Error: Channel specification not initialized. Call connect_to_instance() first.")
            return None

        chan_val = self.chan_spec.get_channel_value(name)
        match = re.search(r'",\s*([\d.e-]+),\s*datetime\.datetime', str(chan_val))
        if match:
            return float(match.group(1))
        else:
            print(f"Error: Could not parse value for sensor '{name}'.")
            return None

    def disable_sensor(self, name):
        """Disable a sensor by name."""
        if self.chan_spec:
            self.chan_spec.set_channel_enabled(name, False)

    def enable_sensor(self, name):
        """Enable a sensor by name."""
        if self.chan_spec:
            self.chan_spec.set_channel_enabled(name, True)

if __name__ == "__main__":
    flex_logger = FlexLoggerInterface()
    
    if flex_logger.connect_to_instance():
        print("Pressure0 Value:")
        for sensor in flex_logger.get_sensor_list():
            print(f"{sensor}: {flex_logger.read_sensor_val(sensor)}")


    sys.exit()
