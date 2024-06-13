from bme680 import bme680
from microbit import *
from radio_func import *
import machine
import struct
import music
import math

# Objects
b = bme680()

# Constants
GAS_LIMIT = 0
GAS_WEIGHTING = 75
HUM_LIMIT = 40.0
HUM_WEIGHTING = 25
NUM_SEGMENTS = 5
MODES = { # Maximum possible values
    0: ("AIR", 300), 
    1: ("SPEED", 1023),
    2: ("TEMP", 40)
}

# Functions
# Get microbit physical name
def getMicroName():
        length = 5
        letters = 5
        codebook = [
            ['z', 'v', 'g', 'p', 't'],
            ['u', 'o', 'i', 'e', 'a'],
            ['z', 'v', 'g', 'p', 't'],
            ['u', 'o', 'i', 'e', 'a'],
            ['z', 'v', 'g', 'p', 't']
        ]
        name = []
        _, n = struct.unpack("II", machine.unique_id())
        ld = 1
        d = letters
        for i in range(0, length):
            h = (n % d) // ld
            n -= h
            d *= letters
            ld *= letters
            name.insert(0, codebook[i][h])
        return  "".join(name)

# Run sensor for a burn-in period to get gas upper limit reference.
def getGasLimit():
    # Set up acculmulation variable
    total_gas = []
    # Get total gas in a period
    for i in range(2000):
        total_gas.append(round(b.gas()/1000))
    # Get average value
    gas_burn_in = sum(total_gas)/len(total_gas)
    # Return average value as burn in data
    return gas_burn_in 

# Assign burn-in data to gas limit
GAS_LIMIT = getGasLimit()

# calculate air quality (Air Quality Index) based on humidity and gas concentration.
def getIAQ(hum, gas):
    gas_offset = GAS_LIMIT - gas
    hum_offset = hum - HUM_LIMIT
    # calculate humidity score based on how far it is from optimal value. Adjust based on weighting.
    if      hum_offset > 0: hum_score = (100 - HUM_LIMIT - hum_offset) / (100 - HUM_LIMIT) * HUM_WEIGHTING
    else:   hum_score = (HUM_LIMIT + hum_offset) / HUM_LIMIT * HUM_WEIGHTING
    # calculate gas score based on how far it is from optimal value. Adjust based on weighting.
    if      gas_offset > 0: gas_score = (gas / GAS_LIMIT) * GAS_WEIGHTING
    else:   gas_score = GAS_WEIGHTING 
    # combine all scores to get the total score
    total_score =  hum_score + gas_score
    # scale to 0 - 500 to get air quality score
    air_quality_index  = (100 - total_score) * 5
    # return air quality
    return air_quality_index

# adjust the fan's speed based on air quality. (0-1023 speed max)
def adjustSpeed(score):
    speed_ranges = {
        (301, 500): 1000,   # Hazardous
        (201, 300): 900,    # Very Unhealthy
        (176, 200): 800,    # Unhealthy
        (151, 175): 700,    # Unhealthy for Sensitive Groups
        (51, 150): 600,     # Moderate
        (0, 50): 500        # Good 
    }

    for (min_score, max_score), speed in speed_ranges.items():
        if min_score <= score <= max_score:
            return speed # Return speed just in case
        
    # Return default speed if not within range
    return 0

# change to display modes on button press
def diplayChart(mode):
    if MODES[mode][0] == "AIR" :    val = score
    if MODES[mode][0] == "SPEED" :  val = speed
    if MODES[mode][0] == "TEMP" :   val = temp

    rows = math.ceil((val / MODES[mode][1]) * NUM_SEGMENTS)

    # If value is over threshold flash else display value as bar chart.
    if rows > NUM_SEGMENTS: 
        # Dimming phase
        fill = Image("99999:99999:99999:99999:99999")
        for brightness in range(9, 0, -1):
            fill.fill(brightness)
            display.show(fill)
            sleep(100)
        # Brightening phase
        for brightness in range(1, 10):
            fill.fill(brightness)
            display.show(fill)
            sleep(100)
    else:
        # Display relevant columns
        for x in range(5):
            # Display number of rows
            for y in range(rows):
                display.set_pixel(x, NUM_SEGMENTS - 1 - y, 9)
                
        # Clear irrelevant columns
        for x in range(5):
            # Clear number of rows
            for y in range(NUM_SEGMENTS - rows):
                display.set_pixel(x, y, 0)

# Register the microbit with the database
def register(name):
    max_retries = 1000
    retries = 0
    
    packet = "{0},c,f,{1}".format(name, "fan")
    sendMessage(packet)
    t = utime.ticks_ms()
   
    while retries < max_retries:
        received = radio.receive_full()
        message = handleRadio("message", received)
        
        if utime.ticks_diff(utime.ticks_ms(), t) > 1*1000:
            sendMessage(packet)
            t = utime.ticks_ms()

        if message:
            if name in message[0] and message[1] == 'ack':
                print("Acknowledged the acknowledgement")
                return 
            
# Initiate radio
radio.on()
radio.config(channel = 70)
# Variables
auto = True
speed = 0
score = 0
temp = 0
brightness = 0
msgidx = 0
mode = 0
name = getMicroName()
print("Microbit name:", name)
# Register with the database first
register(name)

while True:
    received = radio.receive_full()
    message = handleRadio("message", received)

    # temp get from other zone sensors and calculate average
    # Read sensor data
    temp = b.temperature()
    hum = b.humidity()
    pressure = b.pressure
    gass = b.gas() / 1000

    # Calculate Air Quality Index (AQI)
    score = getIAQ(hum, gass)

    # Process received message
    if message:
        received = radio.receive_full()
        message =  handleRadio("message", received)

        if message[0] == name:
            # Set fan speed from front end. 0-11 (0 is off, 11 is auto mode)
            if message[1] == 'F':
                auto = int(message[2]) == 11  # Set auto mode
                if not auto:                  
                    speed = int(message[2]) * 100
                    pin0.write_analog(speed)

            # Send air quality and speed to front end
            elif message[1] == 'f':
                sendMessage("{0},f,{1},{2}".format(name, speed, score))  

    # Auto adjust speed if in auto mode
    if auto:
        speed = adjustSpeed(score)
        pin0.write_analog(speed)
    
    # Display speed
    if mode >= 0 and mode <= 2:
        diplayChart(1)
    
    # fill = Image("99999:99999:99999:99999:99999")
    # brightness = 9-(value/255)*9)
    # fill.fill(brightness)
    # display.show(fill)
    # Describe fan speed and descripte lights
    
  