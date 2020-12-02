import random
import wsnsimpy.wsnsimpy_tk as wsp
import numpy as np

SOURCE = 0
DEST   = int(99*random.uniform(0,1))

###########################################################
class IoTDevice(wsp.IoTNode):

    def init(self):
        super().init()
        self.prev = None
        self.noderesp = 0

    def run(self):
        if self.id == SOURCE:
            self.send(wsp.BROADCAST_ADDR, msg='lifemsg', src=self.id)

    ###################
    def send_data(self,src,seq):
        self.log(f"Forward data with seq {seq} via {self.next}")
        self.send(self.next, msg='data', src=src, seq=seq)

    ###################
    def on_receive(self, sender, msg, src, **kwargs):
        if msg == 'lifemsg':
            self.send(src, msg='lifeackmsg', src = self.id)
        
        if msg == 'lifeackmsg':
            self.noderesp = self.noderesp + 1
            self.scene.addlink(self.id, sender, "parent")
            self.log(f"Receive ACK from {self.noderesp}")

###########################################################
sim = wsp.Simulator(
        until=100,
        timescale=1,
        visual=True,
        terrain_size=(100,100),
        title="IOTDevice WiSARD Routing")

# define a line style for parent links
sim.scene.linestyle("parent", color=(0,.8,0), arrow="tail", width=2)

# place nodes over 100x100 grids
for x in range(10):
    for y in range(10):
        px = 100 + x*60 + random.uniform(-10,10)
        py = 50 + y*60 + random.uniform(-10,10)
        node = sim.add_node(IoTDevice, (px,py))
        node.tx_range = 100
        node.logging = True

# start the simulation
sim.run()
