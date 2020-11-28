import random
import wsnsimpy.wsnsimpy_tk as wsp
import numpy as np

battery = []

SOURCE = 0
DEST   = int(99*random.uniform(0,1))

###########################################################
def delay():
    return random.uniform(.2,.8)

###########################################################
class IoTDevice(wsp.IoTNode):

    ###################
    def init(self):
        super().init()
        self.prev = None

    ###################
    def run(self):
        self.scene.nodecolor(self.id, 0, 0, 0.5)
        self.scene.nodewidth(self.id, 0.5+4*self.WiSARD)
        if self.id is SOURCE:
            self.scene.nodecolor(self.id,1,0,0)
            self.scene.nodewidth(self.id,1)
            yield self.timeout(1)
            self.send_rreq(self.id)
        elif self.id is DEST:
            self.scene.nodecolor(self.id,1,0,0)
            self.scene.nodewidth(self.id,1)
       # else:
            #self.scene.nodecolor(self.id,.7,.7,.7)

    ###################
    def send_rreq(self,src):
        self.send(wsp.BROADCAST_ADDR, msg='rreq', src=src)

    ###################
    def send_rreply(self,src):
        #if self.id is not DEST:
        #    self.scene.nodecolor(self.id,0,.7,0)
        #    self.scene.nodewidth(self.id,2)
        battery.append(self.WiSARD)
        self.send(self.prev, msg='rreply', src=src)

    ###################
    def start_send_data(self):
        #self.scene.clearlinks()
        seq = 0
        while True:
            yield self.timeout(1)
            self.log(f"Send data to {DEST} with seq {seq}")
            self.log(str(np.mean(battery)) + " " + str(len(battery)))
            break
            self.send_data(self.id, seq)
            seq += 1

    ###################
    def send_data(self,src,seq):
        self.log(f"Forward data with seq {seq} via {self.next}")
        self.send(self.next, msg='data', src=src, seq=seq)

    ###################
    def on_receive(self, sender, msg, src, **kwargs):
        if msg == 'rreq':
            if self.prev is not None: return
            self.prev = sender
            self.scene.addlink(sender,self.id,"parent")
            if self.id is DEST:
                self.log(f"Receive RREQ from {src}")
                yield self.timeout(5)
                self.log(f"Send RREP to {src}")
                self.send_rreply(self.id)
            else:
                yield self.timeout(delay())
                self.send_rreq(self.id)

        elif msg == 'rreply':
            self.next = sender
            if self.id is SOURCE:
                self.log(f"Receive RREP from {src}")
                yield self.timeout(5)
                self.log("Start sending data")
                self.start_process(self.start_send_data())
            else:
                yield self.timeout(delay())
                self.send_rreply(src)

        elif msg == 'data':
            if self.id is not DEST:
                yield self.timeout(.2)
                self.send_data(src,**kwargs)
            else:
                seq = kwargs['seq']
                self.log(f"Got data from {src} with seq {seq}")

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
count = 0
for x in range(10):
    count = count + 1
    for y in range(10):
        count = count + 1
        px = 100 + x*80 + random.uniform(-20,20)
        py = 100 + y*60 + random.uniform(-20,20)
        node = sim.add_node(IoTDevice, (px,py))
        node.logging = True

# start the simulation
sim.run()
