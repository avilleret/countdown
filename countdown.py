#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import pyossia.ossia_python as ossia
import time
import apa102
import logging.handlers
import os
import sys
import datetime
from bitarray import bitarray
import signal

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
parameter_color = node.create_parameter(ossia.ValueType.Vec3f)
parameter_color.access_mode = ossia.AccessMode.Bi
parameter_color.bounding_mode = ossia.BoundingMode.Clip
parameter_color.make_domain(0,255)
parameter_color.apply_domain()
parameter_color.value = [255,255,255]

node = local_device.add_node("/text")
parameter_text = node.create_parameter(ossia.ValueType.String)
parameter_text.value = ""

node = local_device.add_node("/speed")
parameter_speed = node.create_parameter(ossia.ValueType.Float)
parameter_speed.access_mode = ossia.AccessMode.Bi
parameter_speed.bounding_mode = ossia.BoundingMode.Clip
parameter_speed.make_domain(-10,10)
parameter_speed.apply_domain()
parameter_speed.value = 1

node = local_device.add_node("/brightness")
parameter_brightness = node.create_parameter(ossia.ValueType.Int)
parameter_brightness.access_mode = ossia.AccessMode.Bi
parameter_brightness.bounding_mode = ossia.BoundingMode.Clip
parameter_brightness.make_domain(0,31)
parameter_brightness.apply_domain()
parameter_brightness.value = 1

node = local_device.add_node("/play")
parameter_play = node.create_parameter(ossia.ValueType.Bool)
parameter_play.access_mode = ossia.AccessMode.Bi
parameter_play.value = 0

node = local_device.add_node("/time")
parameter_time = node.create_parameter(ossia.ValueType.Float)
parameter_time.access_mode = ossia.AccessMode.Get
node.refresh_rate = 200
parameter_time.value = 0

# TODO : make blink work
node = local_device.add_node("/blink/delay")
parameter_blink_del = node.create_parameter(ossia.ValueType.Float)
parameter_blink_del.access_mode = ossia.AccessMode.Bi
parameter_blink_del.value = 1000.

node = local_device.add_node("/blink/on")
parameter_blink_on = node.create_parameter(ossia.ValueType.Bool)
parameter_blink_on.access_mode = ossia.AccessMode.Bi
parameter_blink_on.value = False

node = local_device.add_node("/admin/update")
parameter = node.create_parameter(ossia.ValueType.Impulse)

node = local_device.add_node("/admin/shutdown")
parameter = node.create_parameter(ossia.ValueType.Impulse)

node = local_device.add_node("/admin/reboot")
parameter = node.create_parameter(ossia.ValueType.Impulse)

node = local_device.add_node("/admin/test")
parameter_led_test = node.create_parameter(ossia.ValueType.Bool)
parameter_led_test.access_mode = ossia.AccessMode.Bi
parameter_led_test.value = False

globq = ossia.GlobalMessageQueue(local_device)

# Setup LED
# 6 LED / segments, 7 segments per digit, 4 digits + 4 points to separate min and seconds
# 6 * 7 * 4 + 8 = 176 LEDS
strip = apa102.APA102(176, 2)

try:
  def sighandler(signum, frame):
    strip.clearStrip()
    strip.cleanup()

  signal.signal(signal.SIGTERM, sighandler)

  time_flag = False
  alast_time = datetime.datetime.now()
  blink_last_time = datetime.datetime.now()
  blink_status = True # Whether the LED are ON or OFF, default ON
  print("started on " + str(alast_time) )

  dictionnary = { '0' : bitarray('1111110'),
                  '1' : bitarray('0011000'),
                  '2' : bitarray('0110111'),
                  '3' : bitarray('0111101'),
                  '4' : bitarray('1011001'),
                  '5' : bitarray('1101101'),
                  '6' : bitarray('1101111'),
                  '7' : bitarray('0111000'),
                  '8' : bitarray('1111111'),
                  '9' : bitarray('1111001'),
                  'A' : bitarray('1111011'),
                  'B' : bitarray('1001111'),
                  'C' : bitarray('1100110'),
                  'D' : bitarray('0011111'),
                  'E' : bitarray('1100111'),
                  'F' : bitarray('1100011'),
                  'H' : bitarray('1011011'),
                  'I' : bitarray('1000010'),
                  'J' : bitarray('0011100'),
                  'L' : bitarray('1000110'),
                  'N' : bitarray('0001011'),
                  'O' : bitarray('0001111'),
                  'P' : bitarray('1110011'),
                  'R' : bitarray('0000011'),
                  'S' : bitarray('1101101'),
                  'T' : bitarray('1000111'),
                  'U' : bitarray('1011110'),
                  'Y' : bitarray('1011101'),
                  'Z' : bitarray('0110111') }

  def display_string( str ):
    global_brightness = (parameter_brightness.value & 0b00011111) | 0b11100000
    
    global blink_status
    #print("blink_status: " + str(blink_status))

    if not blink_status:
      global_brightness = 0b11100000

    global_color = parameter_color.value
    r = int(global_color[0])
    g = int(global_color[1])
    b = int(global_color[2])
    for i in range(4):
      try:
        arr = dictionnary[str.upper()[i]];
        for seg in range(7): #loop over segments
          on = arr[seg]
          start = i*7+seg
          offset = 0
          if i > 1:
            offset += 8 # jump over the 8 seperating LEDs
          for y in range(6): #loop over LEDs in the segment
            id = (start*6 + y + offset)*4
            if on:
              strip.leds[id] = global_brightness
              strip.leds[id+1] = b
              strip.leds[id+2] = g
              strip.leds[id+3] = r
            else:
              strip.leds[id+1] = 0
              strip.leds[id+2] = 0
              strip.leds[id+3] = 0
      except:
        pass


  def update_led_display():
    global blink_status
    if time_flag:
      minutes = int(parameter_time.value/60)
      seconds = int(parameter_time.value%60)
      time_string = '{0:02d}'.format(minutes) + '{0:02d}'.format(seconds)

      display_string(time_string)

      offset = 7*2*6

      global_brightness = (parameter_brightness.value & 0b00011111) | 0b11100000
      if not blink_status:
        global_brightness = (0 & 0b00011111) | 0b11100000
      
      global_color = parameter_color.value
      r = int(global_color[0])
      g = int(global_color[1])
      b = int(global_color[2])

      for i in range(8):
        id = (offset+i) * 4
        if (int(parameter_time.value*2) % 2) == 1:
          strip.leds[id] = global_brightness
          strip.leds[id+1] = b
          strip.leds[id+2] = g
          strip.leds[id+3] = r
        else:
          strip.leds[id+1] = 0
          strip.leds[id+2] = 0
          strip.leds[id+3] = 0

    else:
      display_string(parameter_text.value)

      offset = 7*2*6

      for i in range(8):
        id = (offset+i) * 4
        strip.leds[id] = 0b11100000
        strip.leds[id+1] = 0
        strip.leds[id+2] = 0
        strip.leds[id+3] = 0

    strip.show()

  def update_time():
    global alast_time
    if parameter_play.value:
      if (parameter_time.value > 0 and parameter_speed.value > 0) or parameter_speed.value < 0:
        now = datetime.datetime.now()
        delta = now - alast_time
        parameter_time.value -= delta.total_seconds() * parameter_speed.value
    alast_time = datetime.datetime.now()

  def set_time():
    global time_flag
    s = parameter_text.value
    try:
      minutes = int(float(s[:2]))
      seconds = int(float(s[-2:]))
      parameter_time.value = minutes*60 + seconds
      print("set_time: " + str(minutes) + ":" + str(seconds))
      time_flag = True
    except:
      print("can't parse text to time")
      parameter_play.value = False
      time_flag = False

  def blink():
    global blink_last_time
    global blink_status
    if (parameter_blink_on.value):
      now = datetime.datetime.now()
      delta = now - blink_last_time
      if (delta.total_seconds() * 1000) > parameter_blink_del.value:
        blink_last_time = now
        blink_status = not blink_status
    else:
      blink_status = True



  while(True):
    global time_flag 
    global blink_status
    res = globq.pop()
    while res != None:
      parameter, value = res
      if str(parameter.node) == "/text":
        set_time()
      elif str(parameter.node) == "/admin/update":
        print("receive '/admin/update'")
        os.system("cd " + os.path.dirname(os.path.realpath(__file__)) + "&& git pull")
        # TODO send feedback to a WS logger
        # TODO check for update before pull
      elif str(parameter.node) == "/admin/reboot":
        print("I'm going to reboot now !")
        os.system("reboot")
      elif str(parameter.node) == "/admin/shutdown":
        print("I'm going to shutdown now !")
        os.system("shutdown -P now")
      elif str(parameter.node) == "/time":
        time_flag = True

      print("globq: Got " +  str(parameter.node) + " => " + str(value))
      res=globq.pop()

    if parameter_led_test.value:
      numPixels = 176
      for j in range(numPixels): # Shift the start of the rainbow across the strip
        for i in range(numPixels): # spread (or compress) one rainbow onto the strip
            # For a faster shift, add more than 1 * j per loop (e.g. + 2 * j)
            index = strip.wheel((((i << 8) // numPixels) + j*4) & 255)
            strip.setPixelRGB(i, index);
        strip.show() 
    else:
      blink()
      update_time()
      update_led_display()
      time.sleep(0.01)

except:  # Abbruch...
  print("Unexpected error:", sys.exc_info()[0])
  print("value: ", sys.exc_info()[1])
  print(sys.exc_info()[2])
  print('Interrupted...')
  strip.clearStrip()
  print('Strip cleared')
  strip.cleanup()
  print('SPI closed')
