#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import pyossia.ossia_python as ossia
import time
import apa102
import logging.handlers
import os
import datetime

"""
This script create an OSCQuery device that control an APA102 LED strip to make an interactive countdown.
"""

# Configure logging to log to a file, making a new file at midnight and keeping the last 3 day's data
LOG_LEVEL = logging.DEBUG
LOG_FILENAME = os.path.dirname(os.path.realpath(__file__)) + "/countdown.log"
print("logfile: " + LOG_FILENAME)
# Give the logger a unique name (good practice)
logger = logging.getLogger(__name__)
# Set the log level to LOG_LEVEL
logger.setLevel(LOG_LEVEL)
# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# Attach the formatter to the handler
handler.setFormatter(formatter)
# Attach the handler to the logger
logger.addHandler(handler)

# Replace stdout with logging to file at INFO level
#sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
#sys.stderr = MyLogger(logger, logging.ERROR)

# setup OSCQuery device
local_device = ossia.LocalDevice("countdown")
print("local device name: " + local_device.name)

local_device.create_oscquery_server(1234, 5678, False)

# create a node, create a float parameter, set its properties and initialize it
node = local_device.add_node("/color")
parameter = node.create_parameter(ossia.ValueType.Vec3f)
parameter.access_mode = ossia.AccessMode.Bi
parameter.bounding_mode = ossia.BoundingMode.Clip
parameter.make_domain(0,255)
parameter.apply_domain()
parameter.value = [255,0,0]

node = local_device.add_node("/text")
parameter_text = node.create_parameter(ossia.ValueType.String)
parameter_text.value = "HELP"

node = local_device.add_node("/speed")
parameter_speed = node.create_parameter(ossia.ValueType.Float)
parameter_speed.access_mode = ossia.AccessMode.Bi
parameter_speed.bounding_mode = ossia.BoundingMode.Clip
parameter_speed.make_domain(-10,10)
parameter_speed.apply_domain()
parameter_speed.value = 1

node = local_device.add_node("/brightness")
parameter = node.create_parameter(ossia.ValueType.Int)
parameter.access_mode = ossia.AccessMode.Bi
parameter.bounding_mode = ossia.BoundingMode.Clip
parameter.make_domain(0,31)
parameter.apply_domain()
parameter.value = 1

node = local_device.add_node("/play")
parameter_play = node.create_parameter(ossia.ValueType.Bool)
parameter_play.access_mode = ossia.AccessMode.Bi
parameter_play.value = 0

node = local_device.add_node("/time")
parameter_time = node.create_parameter(ossia.ValueType.Float)
parameter_time.access_mode = ossia.AccessMode.Get
node.refresh_rate = 200
parameter_time.value = 0

node = local_device.add_node("/blink/delay")
parameter_blink_del = node.create_parameter(ossia.ValueType.Float)
parameter_blink_del.access_mode = ossia.AccessMode.Bi
parameter_blink_del.value = 1000.

node = local_device.add_node("/blink/on")
parameter_blink_del = node.create_parameter(ossia.ValueType.Bool)
parameter_blink_del.access_mode = ossia.AccessMode.Bi
parameter_blink_del.value = False

globq = ossia.GlobalMessageQueue(local_device)

# Setup LED
# 6 LED / segments, 7 segments per digit, 4 digits + 4 points to separate min and seconds
# 6 * 7 * 4 + 8 = 176 LEDS
strip = apa102.APA102(176, 2)

time_flag = True
alast_time = datetime.datetime.now()
print("started on " + str(alast_time) )

def update_led_display():
  if time_flag:
    minutes = int(parameter_time.value/60)
    seconds = int(parameter_time.value%60)
    #print("time : " + str(minutes) + ":" + str(seconds))
  strip.show()

def update_time():
  if parameter_play.value:
    if parameter_time.value > 0:
      now = datetime.datetime.now()
      delta = now - alast_time
      parameter_time.value -= delta.total_seconds() * parameter_speed.value
      print(parameter_time.value)

def set_time():
  s = parameter_text.value
  try:
    minutes = int(float(s[:2]))
    seconds = int(float(s[-2:]))
    parameter_time.value = minutes*60 + seconds
    print("set_time: " + str(minutes) + ":" + str(seconds))
  except:
    print("can't parse text to time")
    parameter_play.value = False


while(True):

  res = globq.pop()
  while res != None:
    parameter, value = res
    if str(parameter.node) == "/text":
      set_time()
    print("globq: Got " +  str(parameter.node) + " => " + str(value))
    res=globq.pop()

  update_time()
  alast_time = datetime.datetime.now()
  update_led_display()
  time.sleep(0.01)

