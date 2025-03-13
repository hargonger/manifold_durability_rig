import can
import threading
import time

class Cantroller:
    def __init__(self):
        
        
        # Default values
        self.bcm_power = 0
        self.ptn_power = 0
        self.pump2_power = 0

        # Thread control flags
        self.running = False
        self.bcm_thread = None
        self.ptn_thread = None
        self.pump2_thread = None
    
    def connect_to_instance(self, channel=0, bitrate=500000):
        """ Creates CANBUS connection between pump and computer """
        try:
            self.bus = can.interface.Bus(interface='vector', channel=channel, bitrate=bitrate, receive_own_messages=True)
            return True
        except can.CanInitializationError:
            print("Could not connect to CANBUS")
            return False

    def encode_signal(self, value, scale, min_val, max_val):
        """ Takes a raw value and ensures it is within range of sendable value"""
        raw_value = int(value / scale)
        return max(min_val, min(raw_value, max_val))

    def _send_bcm_command(self):
        """ Translate raw value to sendable 'message' to thermal box battery pump """
        while self.running:
            raw_value = self.encode_signal(self.bcm_power, 1, 0, 100)
            data = [raw_value, 0, 0xC8, 0x01, 0, 0, 0, 0]
            message = can.Message(arbitration_id=0x203, data=data, is_extended_id=False, is_rx=False) #ID is 0x203 for BCM pump
            self.bus.send(message)
            time.sleep(0.2)

    def _send_ptn_command(self):
        """ Translate raw value to sendable 'message' to thermal box powertrain pump """
        while self.running:
            raw_value = self.encode_signal(self.ptn_power, 1, 0, 100)
            data = [raw_value, 0, 0xC8, 0x01, 0, 0, 0, 0]
            message = can.Message(arbitration_id=0x204, data=data, is_extended_id=False, is_rx=False) #ID is 0x204 for PTN pump
            self.bus.send(message)
            time.sleep(0.2)

    def _send_pump2_command(self):
        """ Translate raw value to sendable 'message' to emp pump """
        while self.running:
            raw_value = self.encode_signal(self.pump2_power, 0.5, 0, 200)
            data = [0x05, 0, 0, raw_value, 0, 0, 0, 0]
            message = can.Message(arbitration_id=0x18EF01FE, data=data, is_extended_id=True, is_rx=False) #ID is for EMP pump (EMP pumps historically have underperformed/failed)
            self.bus.send(message)
            time.sleep(0.2)

    def start(self):
        """ Creates and starts threads """
        if not self.running:
            self.running = True
            self.bcm_thread = threading.Thread(target=self._send_bcm_command, daemon=True)
            self.ptn_thread = threading.Thread(target=self._send_ptn_command, daemon=True)
            #self.pump2_thread = threading.Thread(target=self._send_pump2_command, daemon=True)
            self.bcm_thread.start()
            self.ptn_thread.start()
            #self.pump2_thread.start()

    def stop(self):
        """ Stops threads """
        self.running = False
        # Allow threads to exit cleanly without forcing join()
        if self.bcm_thread and self.bcm_thread.is_alive():
            self.bcm_thread.join(timeout=1)
        if self.ptn_thread and self.ptn_thread.is_alive():
            self.ptn_thread.join(timeout=1)
        #if self.pump2_thread and self.pump2_thread.is_alive():
            #self.pump2_thread.join(timeout=1)

    def shutdown(self):
        """Stops all CAN operations and ensures a clean shutdown."""
        self.stop()  # Stop ongoing transmissions
        self.bus.shutdown()
        print("CAN bus shutdown complete.")

    def set_bcm_power(self, value):
        self.bcm_power = value
        print(f"Updated 'BCM Work Percent' to {value}%")

    def set_ptn_power(self, value):
        self.ptn_power = value
        print(f"Updated 'PTN Work Percent' to {value}%")

    def set_pump2_power(self, value):
        self.pump2_power = value
        print(f"Updated 'PUMP2 Motor Speed' Command to {value}%")

if __name__ == '__main__':
    controller = Cantroller()
    controller.connect_to_instance()
    controller.start()

    time.sleep(3)
    controller.set_bcm_power(75)
    controller.set_ptn_power(75)
    time.sleep(5)
    print("pump1 (bcm) 40%")
    

    controller.stop()
    controller.shutdown()

