from microbit import *

zones = {}
lastZone = ""

class actorBit():
    def __init__(self,name):
        self.name = name
        self.zones = {}
        self.lastZone =""
        
    def receivePing(self, name, rssi):
        if name not in zones:
            zones.update({name: [1, -1000, -1000, -1000]})
            
        if zones.get(name)[0] > 3:
            zones.get(name)[0] = 1
        
        zones.get(name)[zones.get(name)[0]] = rssi
        zones.get(name)[0] += 1
        
        currentZone = ""
        temp = -3000
        zoneVals = [-1000 for x in range(len(zones))]
        x = 0
        for key, arrs in zones.items():
            for y in range(3):
                zoneVals[x] += arrs[y+1]
            if zoneVals[x] >= temp:
                temp = zoneVals[x]
                currentZone = key
            x += 1
                
        if self.lastZone != currentZone:
            self.lastZone = currentZone
            return currentZone
        else: return "N"

    def checkPresence(self, nameToCheck):
        if nameToCheck in zones:
            zones.pop(nameToCheck)
            
    def getZoneCount(self):
        return len(zones)
    
    def clearZones(self):
        self.zones.clear()
        self.lastZone = ""