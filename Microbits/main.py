import struct
from microbit import *
from sensorMicrobit import *
from actorMicrobit import *
from radio_func import *
import radio
import machine
import music
import utime
import speech
import time

# Lights on each zone.
# Rework paging.

SEC = 1000
MIN = 60*DATARATE
HOUR = 60*MIN
DAY = 24*HOUR

# Microbit agent commands
MESSAGES = [
    ("z", Image("00000:09990:09990:09990:00000")),
    ("N", "Name"),
    ("P", "PanicMode"),      
    ("G", "GeneralHelp"),
    ("T", "TechnicalHelp"),
    ("M", "MedicalHelp"),
    ("S", "SafetyConcern")
]

# Messages to be used in paging
definedMessages = [
    "Serving",
    "Event commencing",
    "Front of house",
    "Remain in place",
    "Assembly point",
    "Wake up call",
    "Lights out"
]

# Functions
# Basic fundatmental functions that will be used.

# Get the physical name of each micobit. Each name is unique from each other.
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

# Used to convert the received signals to environment state
def convState(isQuiet):
    state = 0
    if isQuiet == 1: state = 2
    else: state = 1
    
    return state

# Attempts to switch environment state (quiet or loud)
def tryStateChange(message):
    try:
        isQuiet = int(message[2])
        return isQuiet
    except:
        print("Error with:", message, "\nExpecting:", message[0]+",e,quiet")
        return 0

# Assign jobs and relevant information to the microbit.
def jobAssignment(message, env, quiet, initPos):
    job = ""
    isQuiet = quiet
    if  message[1]  == 'e':
        job = "environment"
                
        if initPos == False:
            env.getStartPos()
            initPos = True
                    
    elif message[1]  == 'a':
        job = "agent"
        initPos = False
        
    if len(message) == 3: tryStateChange(message)
            
    return job, convState(isQuiet), initPos

# Registers itself everytime it is turned on to check if it is alive.
# Assigns relevant info at the same time if it is needed. (job data is sent before acknowledgement is done). 
def register(name, env):
    packet = name + ",c,f"
    radio.send(packet)
    print("Sending packet:", packet)
    
    job = ""
    isQuiet = 1
    initPos = False
    t = utime.ticks_ms()
    
    while True:
        received = radio.receive_full()
        message = handleRadio("message", received)
        
        if utime.ticks_diff(utime.ticks_ms(), t) > 1*DATARATE:
            sendMessage(packet)
            t = utime.ticks_ms()
        
        # Message Handling - Ignore irrelevant messages.
        if not message or message == "" or len(message) < 2: continue
        
        if name in message[0] and (message[1] == 'e' or message[1] == 'a'):
            job, isQuiet, initPos = jobAssignment(message, env, isQuiet, False)
            print("Job found! (Acked!)")
            return message, job, convState(isQuiet), initPos
            
        if name in message[0] and message[1] == 'ack':
            print("Acknowledged the acknowledgement")
            return message, job, convState(isQuiet), initPos
      
# Check if led is clear
def is_led_cleared():
    return all(display.get_pixel(x, y) == 0 for x in range(5) for y in range(5))

# Alarm. Just a basic universal alarm that can be used in any situation.
'''Add option to change pitch.'''
def alarm(x, environmentState):
    if environmentState == 1:
        display.clear()
        display.show(Image.HEART_SMALL)
        music.play(music.BA_DING)
        utime.sleep_ms(500)
        display.show(Image("00000:00000:00000:00000:00000"))
        time.sleep(x-1)
    elif x > 0:
        display.clear()
        display.show(Image.DIAMOND)
        music.pitch(880, 500)
        utime.sleep_ms(500)
        display.show(Image("00000:00000:00000:00000:00000"))
        alarm(x-1, environmentState)
        time.sleep(x-1)
        
def setVars():
    return "", 0, False, 0, 0, 0, True, True, 1.5, True    

# Main method
# It first registers with the server then it will go in the loop.
# The loop has two main sections. Non message based, and message based. Both agent and env has these sections.

# Both agent and env are classes and their functions exist in a separate file.
        
# Non message based 
    # Automated run in background processes that does not need any info from any form of messaging.

# Message based 
    # Needs info from other microbits to function properly.
    # It constantly receives messages from the radio and only listens to real messages (non - None). 
    # Once it does, it sorts out the message and filters it into: Name,Flag,+Any extra data. The microbit only
    # responds to the name it is addressed to in the message.

# Start of main method
def main():
    radio.config(channel=69, queue=6)
    radio.on()

    # Variables
    job, zzzCounter, initializedPos, environmentState, msgidx, light, auto_light, auto_fan, trackTime, idle = setVars()
    
    # Initialize important inoformation/tools.
    name = getMicroName()
    print("Microbit name:", name)
    env = sensorBit(name)
    act = actorBit(name)
    env.getStartPos()
    
    # Registration. Assign information during registration if needed. 
    result, job, environmentState, initializedPos = register(name,env)
    
    # Times - add a new time object for each automated feature.
    t1 = utime.ticks_ms()
    t2 = utime.ticks_ms()
    t3 = utime.ticks_ms()

    while True:
    # Non message based - Automated and doesnt need any commands from other microbits. 
        # Button A, B and Pin is used by agent for paging
        # Environment
        if job == 'environment':
            # Decide which timer to use depending on how busy the MicroBit is used
            # Values should be changed depending on how many MicroBits we use for demo
            if env.getMembers() <=1:
                trackTime = 3
            elif env.getMembers() >= 5:
                trackTime = 1
            else:
                trackTime = 2
            
            # Detects if mocrobit is moved, if it is, sounds alarm.
            if env.comparePos() is not None:
                alarm(1, environmentState)
                sleep(1)
                if utime.ticks_diff(utime.ticks_ms(), t3) > 5 * SEC:
                    packet = name +",move"
                    sendMessage(packet)
                    t3 = utime.ticks_ms()

            # Tracker pings to track movements of all agents.   
            if utime.ticks_diff(utime.ticks_ms(), t2) > trackTime *SEC:
                radio.send("all,tp,"+name)
                t2 = utime.ticks_ms()

            # If light display is auto, light value is dependent on how bright the room is
            if auto_light:
                light = 255 - int(env.getLightValue())
                
            # Display light.
            env.displayLight(light)

            # If fan is auto, then Will run based on temperature
            if auto_fan:
                speed = env.adjustSpeed(temperature())
                pin0.write_analog(speed)
          
        # Agent
        if job == 'agent':
            if idle:
                display.show(Image.STICKFIGURE)
            # Aliveness checks.
            zoneCounter = act.getZoneCount() * 3
            if zoneCounter > 0 and zzzCounter == zoneCounter:
                packet = name+",here"
                sendMessage(packet)
                zzzCounter = 0

            # Switch between each option
            # Check if button A is pressed and update message index
            if button_a.was_pressed():
                idle = False
                msgidx = (msgidx + 1) % len(MESSAGES)
                # Clear display if first option then show the rest.
                display.show(MESSAGES[msgidx][0]) if msgidx != 0 else display.show(Image.STICKFIGURE)
            
            # Check if pin is pressed to show instructions
            if pin_logo.is_touched() and msgidx != 0:
                display.scroll(MESSAGES[msgidx][1], delay = 100, monospace=True)
                display.show(MESSAGES[msgidx][0], wait =False)
                sleep(200)

            # Press B to confirm choice
           # Press B to confirm choice
            if button_b.was_pressed() and not is_led_cleared():
                # Clear the display
                display.clear()
                # Play confirmation sound 
                music.play(["B4:4"], pin1)
                # Show name
                if msgidx == 1:
                    speech.say(name)
                    display.scroll(name)
                elif msgidx == 2: 
                    packet = name+",pa"
                    if act.lastZone != "": packet = packet + "," + act.lastZone
                    sendMessage(packet)
                    alarm(2,environmentState)
                    time.sleep(2)
                # Send quick message
                elif msgidx >= 3 and msgidx <= 6: 
                    sendMessage("{0},M,{1},{2}".format(name, MESSAGES[msgidx][1], act.lastZone))
                # Set idle == True
                idle = True
    
    # Message based - Needs information from other microbits
        # Message Processing
        received = radio.receive_full()
        message =  handleRadio("message", received)

        # Message Handling - Ignore irrelevant messages.
        if not message or message == "" or len(message) < 2: continue
        
        # Messages processed as:
        # Destination,Flag,Sender,+Any extra data
        
        # Clear known MicroBits
        if message[1] == "clear":
            act.clearZones()
            env.clearMembers()
            job, zzzCounter, initializedPos, environmentState, msgidx, light, auto_light, auto_fan, trackTime = setVars()
        
        # Job allocation check - Assign information from db whenever needed in the while loop
        if name in message[0] and (message[1] == 'e' or message[1] == 'a'):
            job, environmentState, initializedPos = jobAssignment(message, env, environmentState, initializedPos)
                
        # Alarm    
        if message[1] == 'id':
            alarm(2, environmentState)
            time.sleep(2)
            
        # Paging
        elif name in message[0] and message[1] == 'm':
            try:
                alarm(1, environmentState)
                toDisplay = definedMessages[int(message[2])]
                print("Displaying:", toDisplay)
                display.scroll(toDisplay)
            except:
                print("Cant find message", message[2])
                
        # Lockdown
        if name == message[0] and message[1] == 'ap':
                alarm(2, environmentState)
                display.scroll("LOCKDOWN!")
                time.sleep(2)
        
        # Environment
        if job == 'environment':
            # Sends evironment data when addressed by controller.
            if name == message[0] and message[1] == 'e':
                packet = name + ",e," + env.getTempValue() + "," + env.getLightValue() + "," + env.getNoiseLevel()
                sendMessage(packet)

            # Check if new zone was once a recognised agent, remove if they are 
            elif message[1] == 'e':
                env.checkPresence(message[0])

            elif message[1] == 'in':
                env.memberChange(message[0], message[2])
                
            # Set light value from front end (0-9) (11)
            elif name == message[0] and message[1] == 'L':
                auto_light = int(message[2]) == 11  # Set auto mode
                if not auto_light:                  
                    light = (int(message[2])/9) * 255

            # Set light value from fan (0-9) (11)
            elif message[1] == 'F':
                if pin0.read_analog() > 50:
                    auto_fan = int(message[2]) == 11  # Set auto mode
                    if not auto_fan:                  
                        speed = int(message[2]) * 100
                        pin0.write_analog(speed)
        # Agent
        if job =='agent':
            if message[1] == 'a':
                act.checkPresence(message[0])

            elif  message[1] == 'tp':
                # Updates it's location
                closest = act.receivePing(message[2], handleRadio("strength", received))

                if closest != 'N':
                    packet = closest+",in,"+name
                    sendMessage(packet)
                else:
                    zzzCounter += 1
                    
                # Once an agent is sufficiently close to an environment sensor, then it will sent a message to the 
                # closest microbit to unlock it. (Always will be door sensor because you need to be very close to
                # it, like practivally touching.)
                if handleRadio("strength", received) > -30:
                    music.play(["B4:4"], pin1)
                    packet = message[2]+",l,"+name 
                    sendMessage(packet)
    
if __name__ == "__main__":
    main()