import random
import wsnsimpy.wsnsimpy_tk as wsp
import numpy as np
import pickle

battery = []

SOURCE = 55

DESTS = list(range(100))
DESTS.remove(SOURCE)

TX_RANGE = pickle.load( open( "TX_RANGE.p", "rb" ) )
PX = pickle.load( open( "PX.p", "rb" ) )
PY = pickle.load( open( "PY.p", "rb" ) )
NEXT = pickle.load( open( "NEXT.p", "rb" ) )
BATTERY = pickle.load( open( "BATTERY.p", "rb") )

###########################################################
class IoTDevice(wsp.IoTNode):

    tx_energy = 0
    rx_energy = 0
    idle_energy = 0

    ###################
    def init(self):
        super().init()

        # at tx_range = 100, tx_energy = 1 uJ/bit
        self.tx_energy = 64*(2*10**-7 + self.tx_range**2/(10000/(8*10**-7)))
        self.rx_energy = 64*0.5*10**-6
        self.idle_energy = 10**-7

    ###################
    def run(self):
        self.scene.nodecolor(self.id, 0, 0, 0.5)
        self.scene.nodewidth(self.id, 2)
        if self.id is SOURCE:
            DEST = random.sample(DESTS, 1)[0]
            #self.log(f"Final destination: {DEST}")
            self.scene.nodecolor(self.id,1,0,0)
            self.scene.nodewidth(self.id,2)
            self.send(self.next[DEST], final = DEST, msg='rreq', src=self.id)
            #self.log(f"Send data to {self.next[DEST]}")

        else:
            self.scene.nodecolor(self.id,.7,.7,.7)

    ###################
    def on_receive(self, sender, final, msg, src, **kwargs):
        if msg == 'rreq':
            self.scene.addlink(self.id, sender, "parent")
            self.battery = self.now*self.idle_energy
            self.battery = self.battery + self.rx_energy
            self.battery = self.battery + self.tx_energy

            if self.battery >= self.capacity*2*10**-4:
                self.log("DEPLETED!!!\nDEPLETED!!!\nDEPLETED!!!\nDEPLETED!!!\n")
                yield self.timeout(2000)

            if self.id is final:
                self.scene.clearlinks()

                self.send(self.next[SOURCE], final = SOURCE, msg='rreply', src = self.id)

            else:
                self.send(self.next[final], final = final, msg='rreq', src = self.id)

        elif msg == 'rreply':
            self.scene.addlink(self.id, sender, "parent")
            if self.id is SOURCE:

                yield self.timeout(0.25)
                self.scene.clearlinks()
                yield self.timeout(0.25)

                DEST = random.sample(DESTS, 1)[0]
                #self.log(f"Final destination: {DEST}")

                self.scene.nodecolor(self.id,1,0,0)
                self.scene.nodewidth(self.id,2)
                
                self.send(self.next[DEST], final = DEST, msg='rreq', src=self.id)
            else:
                self.battery = self.now*self.idle_energy
                self.battery = self.battery + self.rx_energy
                self.battery = self.battery + self.tx_energy
                
                if self.battery >= self.capacity*2*10**-4:
                    self.log("DEPLETED!!!\nDEPLETED!!!\nDEPLETED!!!\nDEPLETED!!!\n")
                    yield self.timeout(2000)

                self.send(self.next[SOURCE], final = SOURCE, msg='rreply', src = self.id)

###########################################################
def delay():
    return random.uniform(.2,.8)

###########################################################

sim = wsp.Simulator(
        until=2000,
        timescale=0.01,
        visual=True,
        terrain_size=(100,100),
        title="IOTDevice Transmission Control")

# define a line style for parent links
sim.scene.linestyle("parent", color=(0,.8,0), arrow="tail", width=2)

# place nodes over 100x100 grids
count = 0
for x in range(10):
    for y in range(10):
        node = sim.add_node(IoTDevice, (PX[count], PY[count]))
        node.tx_range = TX_RANGE[count]
        node.next = NEXT[count]
        node.capacity = BATTERY[count]/100
        node.logging = True
        count += 1

# start the simulation
sim.run()
