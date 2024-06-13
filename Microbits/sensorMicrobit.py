from microbit import *

DATARATE = 1000
MOVEMENT_THRESHOLD = 1000 #Temporary value, should change to suit needs
MAX_LIGHT = 255
MAX_TEMP = 40
members = []

class sensorBit():
    def __init__(self,name):
        self.name = name
        self.isLocked = True
        self.attempts = {}
        self.pos = [0, 0, 0]
        
    # Sensor code 
    def getNoiseLevel(self):
        return str(microphone.sound_level())
    
    def getTempValue(self):
        return str(temperature())
    
    def getLightValue(self):
        return str(display.read_light_level())

    def displayLight(self, light):
        fill = Image("99999:99999:99999:99999:99999")
        brightness = round((light/MAX_LIGHT)*9)
        fill.fill(brightness)
        display.show(fill)
        return brightness
    
    def adjustSpeed(self, temp):
        speed = round(temp/MAX_TEMP)*1023
        return speed

    # Proximity code
    def memberChange(self, env, member):
        if member in members:
            members.remove(member)
            
        if self.name == env: 
            if member not in members:
                members.append(member)
                
    def getMembers(self):
        return len(members)

    #Check if new zone was once a recognised agent, remove if they are 
    def checkPresence(self, nameToCheck):
        if nameToCheck in members:
            members.remove(nameToCheck)
            
    def getStartPos(self):
        self.pos[0] = accelerometer.get_x()
        self.pos[1] = accelerometer.get_y()
        
    def comparePos(self):
        currentPos = [accelerometer.get_x(), accelerometer.get_y()]
                       
        for x in range(2):
            if (currentPos[x] - self.pos[x]) >= MOVEMENT_THRESHOLD:
                return "Door moved!"     

    def clearMembers(self):
        members.clear()