import random
import wsnsimpy.wsnsimpy_tk as wsp

SOURCE = 12
MSG_NBITS = 1000*8

###########################################################
class MyNode(wsp.LayeredNode):
    tx_range = 120

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
        self.send(wsp.BROADCAST_ADDR, nbits=MSG_NBITS)

    ##################
    def on_receive(self,sender,*args,**kwargs):
        self.log(f"Receive message from {sender}")
        if self.recv:
            self.log(f"Message seen; reject")
            return
        self.log(f"New message; prepare to rebroadcast")
        self.recv = True
        self.scene.nodecolor(self.id,0,0,1)
        yield self.timeout(random.uniform(0.5,1.0))
        #yield self.timeout(0.1)
        self.broadcast()

    ##################
    def show_stats(self):
        # Physical layer
        self.log(f"PHY: Number of transmissions = {self.phy.stat.total_tx}")
        self.log(f"PHY: Number of successful receptions = {self.phy.stat.total_rx}")
        self.log(f"PHY: Number of collisions = {self.phy.stat.total_collision}")
        self.log(f"PHY: Number of errors = {self.phy.stat.total_error}")
        self.log(f"PHY: Total channel busy time (s) = {self.phy.stat.total_channel_busy}")
        self.log(f"PHY: Total channel tx time (s) = {self.phy.stat.total_channel_tx}")
        self.log(f"PHY: Number of bits transmitted = {self.phy.stat.total_bits_tx}")
        self.log(f"PHY: Number of bits received successfully = {self.phy.stat.total_bits_rx}")

        # MAC layer
        self.log(f"MAC: Number of broadcasts sent = {self.mac.stat.total_tx_broadcast}")
        self.log(f"MAC: Number of unicasts sent = {self.mac.stat.total_tx_unicast}")
        self.log(f"MAC: Number of broadcasts received = {self.mac.stat.total_rx_broadcast}")
        self.log(f"MAC: Number of unicasts received = {self.mac.stat.total_rx_unicast}")
        self.log(f"MAC: Number of retransmissions = {self.mac.stat.total_retransmit}")
        self.log(f"MAC: Number of acks sent = {self.mac.stat.total_ack}")
        
###########################################################
sim = wsp.Simulator(
        until=15,
        timescale=1,
        visual=True,
        terrain_size=(700,700),
        title="Flooding Demo")
for x in range(10):
    for y in range(10):
        px = 50 + x*60 + random.uniform(-20,20)
        py = 50 + y*60 + random.uniform(-20,20)
        node = sim.add_node(MyNode, (px,py))
        node.logging = True
sim.scene.linestyle("collision",color=(0,0,1),width=3)
sim.run()

for n in sim.nodes:
    n.show_stats()
