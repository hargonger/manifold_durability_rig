from can_controller_lib import Cantroller
import time
import sys

def closeEvent(self, event):
        controller.shutdown()
        event.accept()  # Proceed with window closing

if __name__ == "__main__":

    controller = Cantroller(megatron=1)
    if controller.connect_to_instance():
        print("Successfully connected to CANBUS")
        pass
    else:
        print("Exiting in 5s...")
        time.sleep(5)
        sys.exit()
    controller.start()

    while True:
        try:
            total_cycles = int(input("Enter Total Cycle Count: "))
            
            if total_cycles > 0:
                print(f"Valid input of {total_cycles}.")
            else: 
                print(f"Invalid input of {total_cycles}.")

            current_cycle = int(input("Enter Cycle to Resume From: "))
            if current_cycle > 0 and current_cycle < total_cycles:
                print(f"Valid input of {current_cycle}.")
                break
            else: 
                print(f"Invalid input of {current_cycle}.")            
            
        except ValueError:
            print("Invalid input, try again.")
    
    while True:
        try:
            percent = int(input("Enter pump percent 0-100 (Typically 75%): "))
            if percent > 0 and percent <= 100:
                print(f"Valid input of {percent}%.")
                break
            else:
                print(f"Invalid input of {percent}%.")

        except ValueError:
            print("Invalid input, try again.")

    while current_cycle < total_cycles:

        controller.set_pump_power(percent)
        print(f"Pumps to {percent}%")
        time.sleep(4)

        print("pumps to 0%")    
        controller.set_pump_power(0)
        time.sleep(1.27)
        current_cycle+=1
    
    controller.stop()
    controller.shutdown()

    