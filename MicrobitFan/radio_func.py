from microbit import *
import radio
import utime

def handleRadio(mode, received):
        if received:
            packet, strength, ts = received

            if mode == "message":
                components = str(packet, 'utf8')[3:].split(",")
                while '' in components:
                    components.remove('')
                return components
            
            if mode == "strength":
               return strength
            
            if mode == "time":
               return ts
            
# Both methods used to check if radio channel has no messages, then only send message. 
# This is avoid message collision problems (combining messages).        
def isChannelClear():
    start_time = utime.ticks_ms()
    # Check if radio has any messages for 10 ticks. Keep repeating until return true.
    while utime.ticks_diff(utime.ticks_ms(), start_time) < 10: 
        if radio.receive():
            return False
    return True 

def sendMessage(message):
    # SpinLock. Only get out of loop if the channel is free
    while not isChannelClear(): pass 
    # Send message after channel is clear
    radio.send(message)
    return message
