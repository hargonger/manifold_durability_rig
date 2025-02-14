import can
import threading
import time

class Cantroller:
    def __init__(self):
        
        
        # Default values
        self.bcm_power = 0
        self.pump2_power = 0

        # Thread control flags
        self.running = False
        self.bcm_thread = None
        self.pump2_thread = None
    
    def connect_to_instance(self, channel=0, bitrate=500000):
        try:
            self.bus = can.interface.Bus(interface='vector', app_name='CANalyzer', channel=channel, bitrate=bitrate, receive_own_messages=True)
            return True
        except can.CanInitializationError:
            print("Could not connect to CANBUS")
            return False

    def encode_signal(self, value, scale, min_val, max_val):
        raw_value = int(value / scale)
        return max(min_val, min(raw_value, max_val))

    def _send_bcm_command(self):
        while self.running:
            raw_value = self.encode_signal(self.bcm_power, 1, 0, 100)
            data = [raw_value, 0, 0xC8, 0x01, 0, 0, 0, 0]
            message = can.Message(arbitration_id=0x203, data=data, is_extended_id=False, is_rx=False)
            self.bus.send(message)
            time.sleep(0.2)

    def _send_pump2_command(self):
        while self.running:
            raw_value = self.encode_signal(self.pump2_power, 0.5, 0, 200)
            data = [0x05, 0, 0, raw_value, 0, 0, 0, 0]
            message = can.Message(arbitration_id=0x18EF01FE, data=data, is_extended_id=True, is_rx=False)
            self.bus.send(message)
            time.sleep(0.2)

    def start(self):
        if not self.running:
            self.running = True
            self.bcm_thread = threading.Thread(target=self._send_bcm_command, daemon=True)
            self.pump2_thread = threading.Thread(target=self._send_pump2_command, daemon=True)
            self.bcm_thread.start()
            self.pump2_thread.start()

    def stop(self):
        self.running = False
        # Allow threads to exit cleanly without forcing join()
        if self.bcm_thread and self.bcm_thread.is_alive():
            self.bcm_thread.join(timeout=1)
        if self.pump2_thread and self.pump2_thread.is_alive():
            self.pump2_thread.join(timeout=1)

    def shutdown(self):
        """Stops all CAN operations and ensures a clean shutdown."""
        self.stop()  # Stop ongoing transmissions
        self.bus.shutdown()
        print("CAN bus shutdown complete.")


    def set_bcm_power(self, value):
        self.bcm_power = value
        print(f"Updated BCM Work Percent to {value}%")

    def set_pump2_power(self, value):
        self.pump2_power = value
        print(f"Updated PUMP2 Motor Speed Command to {value}%")

if __name__ == '__main__':
    controller = Cantroller()
    controller.connect_to_instance()
    controller.start()

    time.sleep(5)
    controller.set_bcm_power(40)
    controller.set_pump2_power(40)

    time.sleep(10)  # Run at 40%

    controller.stop()

