import random
import wsnsimpy.wsnsimpy_tk as wsp

SOURCE = 35

###########################################################
class MyNode(wsp.Node):
    tx_range = 100

    ##################
    def init(self):
        super().init()
        self.recv = False

    ##################
    def run(self):
        if self.id == SOURCE:
            self.scene.nodecolor(self.id,0,0,0)
            self.recv = True
            yield self.timeout(2)
            self.broadcast()
        else:
            self.scene.nodecolor(self.id,.7,.7,.7)

    ##################
    def broadcast(self):
        self.scene.nodewidth(self.id, 3)
        self.log(f"Broadcast message")
        self.send(wsp.BROADCAST_ADDR)

    ##################
    def on_receive(self, sender, **kwargs):
        self.log(f"Receive message from {sender}")
        if self.recv:
            self.log(f"Message seen; reject")
            return
        self.log(f"New message; prepare to rebroadcast")
        self.recv = True
        self.scene.nodecolor(self.id,1,0,0)
        yield self.timeout(random.uniform(0.5,1.0))
        self.broadcast()
        
###########################################################
sim = wsp.Simulator(
        until=100,
        timescale=1,
        visual=True,
        terrain_size=(700,700),
        title="Flooding Demo")
for x in range(10):
    for y in range(10):
        px = 50 + x*60 + random.uniform(-20,20)
        py = 50 + y*60 + random.uniform(-20,20)
        node = sim.add_node(MyNode, (px,py))
        node.tx_range = 75
        node.logging = True
sim.run()
