import nidaqmx
from nidaqmx.constants import ThermocoupleType, TemperatureUnits, CJCSource
import time

with nidaqmx.Task() as task:
    task.ai_channels.add_ai_thrmcpl_chan("cDAQ2mod1/ai1")
    task.read()