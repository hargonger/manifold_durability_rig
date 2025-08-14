""" Library from https://github.com/jopekonk/julabolib/blob/master/julabolib.py"""
import logging
import serial
import time
import re

# Set the minimum safe time interval between sent commands that is required according to the user manual
SAFE_TIME_INTERVAL = 0.25

END_CHAR = '\x0D'

class JULABO():
	def __init__(self,port,baud):
		self.port = port
		self.ser = serial.Serial( port=self.port,
					  bytesize=serial.SEVENBITS,
					  parity=serial.PARITY_EVEN,
					  stopbits=serial.STOPBITS_ONE,
					  baudrate=baud,
					  xonxoff=False,
					  rtscts=False,
					  timeout=1 )

		logging.basicConfig(format='julabolib: %(asctime)s - %(message)s', datefmt='%y-%m-%d %H:%M:%S', level=logging.WARNING)
		#logging.basicConfig(format='julabolib: %(asctime)s - %(message)s', datefmt='%y-%m-%d %H:%M:%S', level=logging.DEBUG)
		logging.debug('Serial port ' + self.port + ' opened at speed ' + str(baud))

		time.sleep(0.1) # Wait 100 ms after opening the port before sending commands
		self.ser.flushOutput() # Flush the output buffer of the serial port before sending any new commands
		self.ser.flushInput() # Flush the input buffer of the serial port before sending any new commands

	def close(self):
		"""The function closes and releases the serial port connection attached to the unit.

		"""
		if self.ser != None :
			self.ser.close()

	def send_command(self, command=''):
		"""The function sends a command to the unit and returns the response string."""
		if command == '':
			return ''

		time.sleep(SAFE_TIME_INTERVAL)
		
		# Flush input buffer before sending a new command
		self.ser.flushInput()  
		
		# Send command
		self.ser.write(bytes(command + END_CHAR, 'ascii'))
		time.sleep(0.1)
		logging.debug(f"Command sent to the unit: {command}")

		# Manually read the response with timeout handling
		start_time = time.time()
		response = b''

		while (time.time() - start_time) < 2:  # 2-second timeout
			byte = self.ser.read(1)  # Read byte-by-byte
			if byte:
				response += byte
				if response.endswith(b'\r'):  # Stop when response is complete
					break
			else:
				break  # No data received, exit loop

		# Decode and log response
		response_str = response.decode('ascii').strip()
		logging.debug(f"Response from unit: {response_str}")

		return response_str
	
	def get_version(self):
		"""Get the Julabo software version."""
		return self.send_command("version")

	def flush_input_buffer(self):
		""" Flush the input buffer of the serial port.
		"""
		self.ser.flushInput()

	def set_power_off(self):
		#print("1.1") # debug
		response = self.send_command('out_mode_05 %d' % 0)
		print(f"Command response: {response}")  # Debug
		#print("1.2") # debug

	def set_power_on(self):
		""" The function turns the power ON.

		"""
		response = self.send_command( 'out_mode_05 %d' % 1 )

	def get_power(self):
		""" The function gets the power state of the unit.
			1 == ON
			0 == OFF

		"""
		response = self.send_command( 'in_mode_05' )
		return response

	def set_work_temperature(self, temp):
		""" The function sets the working temperature to the given value.

		"""
		response = self.send_command( 'out_sp_00 %.2f' % temp )

	def get_work_temperature(self):
		""" The function gets the working temperature to the given value.

		"""
		response = self.send_command( 'in_sp_00')
		return float(response)

	def get_version(self):
		""" The function gets the software version of the unit.

		"""
		response = self.send_command( 'version')
		return response

	def get_status(self):
		""" The function gets the status message or error message from the unit.

		"""
		response = self.send_command( 'status')
		return response

	def get_temperature(self):
		""" The function gets the actual bath temperature of the unit

		"""
		response = self.send_command( 'in_pv_00')
		return float(response)
	
if __name__ == "__main__":
    mychiller = JULABO('COM4', baud=4800)


    mychiller.close()