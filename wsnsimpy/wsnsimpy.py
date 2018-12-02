from collections import deque
import bisect
import inspect
import random
import simpy
from simpy.util import start_delayed

BROADCAST_ADDR = 0xFFFF

###########################################################
def ensure_generator(env,func,*args,**kwargs):
    '''
    Make sure that func is a generator function.  If it is not, return a
    generator wrapper
    '''
    if inspect.isgeneratorfunction(func):
        return func(*args,**kwargs)
    else:
        def _wrapper():
            func(*args,**kwargs)
            yield env.timeout(0)
        return _wrapper()

###########################################################
def distance(pos1,pos2):
    return ((pos1[0]-pos2[0])**2 + (pos1[1]-pos2[1])**2)**0.5

###########################################################
class Stat:
    pass

###########################################################
class Node:
    tx_range = 0

    ############################
    def __init__(self,sim,id,pos):
        self.pos = pos
        self.sim = sim
        self.id  = id
        self.logging = True
        self.neighbor_distance_list = []
        self.timeout = self.sim.timeout

    ############################
    def __repr__(self):
        return '<Node %d:(%.2f,%.2f)>' % (self.id,self.pos[0],self.pos[1])

    ############################
    def __lt__(self,obj):
        return self.id < obj.id

    ############################
    @property
    def now(self):
        return self.sim.env.now

    ############################
    def log(self,msg):
        if self.logging:
            print(f"Node {'#'+str(self.id):4}[{self.now:10.5f}] {msg}")

    ############################
    def send(self,dst,*args,**kwargs):
        for (dist,node) in self.neighbor_distance_list:
            if dist <= self.tx_range:
                if dst == BROADCAST_ADDR or dst is node.id:
                    prop_time = dist/1000000
                    self.delayed_exec(
                            prop_time,node.on_receive,self.id,*args,**kwargs)
            else:
                break

    ############################
    @property
    def neighbors(self):
        _neighbors = []
        for (dist,node) in self.neighbor_distance_list:
            if dist <= self.tx_range:
                _neighbors.append(node)
            else:
                break
        return _neighbors

    ############################
    def create_event(self):
        return self.sim.env.event()

    ############################
    def create_process(self,func,*args,**kwargs):
        return ensure_generator(self.sim.env,func,*args,**kwargs)

    ############################
    def start_process(self,process):
        return self.sim.env.process(process)

    ############################
    def delayed_exec(self,delay,func,*args,**kwargs):
        return self.sim.delayed_exec(delay,func,*args,**kwargs)

    ############################
    def init(self):
        pass

    ############################
    def run(self):
        pass

    ###################
    def move(self,x,y):
        self.pos = (x,y)
        self.sim.update_neighbor_list(self.id)

    ############################
    def on_receive(self,sender,*args,**kwargs):
        '''To be overriden'''
        pass

    ############################
    def on_timer_fired(self,*args,**kwargs):
        '''To be overriden'''
        pass

    ############################
    def finish(self):
        '''To be overriden'''
        pass

###########################################################
class PDU:
    def __init__(self,layer,nbits,**fields):
        self.layer = layer
        self.nbits = nbits
        for f in fields:
            setattr(self,f,fields[f])

###########################################################
class DefaultPhyLayer:

    LAYER_NAME = 'phy'

    def __init__(self,node,bitrate=250e3,ber=0):
        self.node = node
        self.bitrate = bitrate
        self.ber = ber
        self._current_rx_count = 0
        self._channel_busy_start = 0

        self.stat = Stat()
        self.stat.total_tx = 0
        self.stat.total_rx = 0
        self.stat.total_collision = 0
        self.stat.total_error = 0
        self.stat.total_bits_tx = 0
        self.stat.total_bits_rx = 0
        self.stat.total_channel_busy = 0
        self.stat.total_channel_tx = 0

    def send_pdu(self,pdu):
        tx_time = pdu.nbits/self.bitrate
        self.on_tx_start(pdu)
        self.node.delayed_exec(tx_time,self.on_tx_end,pdu)
        self.stat.total_tx += 1
        self.stat.total_bits_tx += pdu.nbits
        self.stat.total_channel_tx += tx_time
        for (dist,node) in self.node.neighbor_distance_list:
            if dist <= self.node.tx_range:
                prop_time = dist/3e8
                self.node.delayed_exec(
                        prop_time,node.phy.on_rx_start,pdu)
                self.node.delayed_exec(
                        prop_time+tx_time,node.phy.on_rx_end,pdu)
            else:
                break

    def on_tx_start(self,pdu):
        pass

    def on_tx_end(self,pdu):
        pass

    def on_rx_start(self,pdu):
        self._current_rx_count += 1
        if self._current_rx_count > 1:
            self._collision = True
            self.on_collision(pdu)
        else:
            self._collision = False
        if self._channel_busy_start == 0:
            self._channel_busy_start = self.node.now

    def on_rx_end(self,pdu):
        self._current_rx_count -= 1
        if self._current_rx_count != 0:
            self._collision = True
        else:
            self.stat.total_channel_busy += self.node.now - self._channel_busy_start
            self._channel_busy_start = 0
        if not self._collision:
            if self.node.sim.random.random() < (1-self.ber)**pdu.nbits:
                self.node.mac.on_receive_pdu(pdu)
                self.stat.total_rx += 1
                self.stat.total_bits_rx += pdu.nbits
            else:
                self.stat.total_error += 1
        else:
            self.stat.total_collision += 1

    def on_collision(self,pdu):
        pass

    def cca(self):
        """Return True if the channel is clear"""
        return self._current_rx_count == 0


###########################################################
class DefaultMacLayer:

    LAYER_NAME = 'mac'
    HEADER_BITS = 64

    def __init__(self,node):
        self.node = node
        self.tx_queue = deque()
        self.ack_event = None
        self.stat = Stat()
        self.stat.total_tx_broadcast = 0
        self.stat.total_tx_unicast = 0
        self.stat.total_rx_broadcast = 0
        self.stat.total_rx_unicast = 0
        self.stat.total_retransmit = 0
        self.stat.total_ack = 0

    def process_queue(self):
        retries = 0
        while self.tx_queue:
            frame = self.tx_queue[0]

            # persistent process with exponential backoff
            k = 1
            while True:
                wait_time = self.node.sim.random.randrange(k)*5e-3
                yield self.node.timeout(wait_time)
                if self.node.phy.cca():
                    break
                k = k*2
            self.node.phy.send_pdu(frame)

            # wait for ack if this is a unicast frame
            if frame.dst != BROADCAST_ADDR:
                self.ack_event = self.node.create_event()
                self.ack_event.wait_for = frame
                duration = frame.nbits/self.node.phy.bitrate + 1e-3
                yield simpy.AnyOf(self.node.sim.env, [
                    self.node.timeout(duration),
                    self.ack_event,
                    ])
                if self.ack_event.triggered:
                    retries = 0
                    self.tx_queue.popleft()
                    self.stat.total_tx_unicast += 1
                else:
                    retries += 1
                    backoff_time = self.node.sim.random.randrange(2**retries)*5e-3
                    yield self.node.timeout(backoff_time)
                    self.stat.total_retransmit += 1
            else:
                retries = 0
                self.tx_queue.popleft()
                self.stat.total_tx_broadcast += 1
            self.ack_event = None

    def send_pdu(self,dst,pdu):
        mac_pdu = PDU(self.LAYER_NAME,pdu.nbits+self.HEADER_BITS,
                type='data',
                src=self.node.id,
                dst=dst,
                payload=pdu)
        self.tx_queue.append(mac_pdu)
        if len(self.tx_queue) == 1:
            self.node.start_process(self.node.create_process(
                self.process_queue))

    def on_receive_pdu(self,pdu):
        if pdu.type == 'data':
            if pdu.dst == BROADCAST_ADDR or pdu.dst == self.node.id:
                # TODO: need to get rid of duplications
                self.node.net.on_receive_pdu(pdu.src,pdu.payload)

                # ack if this is a unicast frame
                if pdu.dst != BROADCAST_ADDR:
                    ack = PDU(self.LAYER_NAME,nbits=self.HEADER_BITS,
                            type='ack',
                            for_frame=pdu)
                    self.node.phy.send_pdu(ack)
                    self.stat.total_ack += 1
                    self.stat.total_rx_unicast += 1
                else:
                    self.stat.total_rx_broadcast += 1
        elif pdu.type == 'ack' and self.ack_event is not None:
            if pdu.for_frame == self.ack_event.wait_for:
                self.ack_event.succeed()

###########################################################
class DefaultNetLayer:

    LAYER_NAME = 'net'
    HEADER_BITS = 64

    def __init__(self,node):
        self.node = node
        self.stat = Stat()

    def send_pdu(self,dst,pdu):
        net_pdu = PDU(self.LAYER_NAME,pdu.nbits+self.HEADER_BITS,
                src=self.node.id,
                dst=dst,
                payload=pdu)
        self.node.mac.send_pdu(dst,net_pdu)

    def on_receive_pdu(self,src,pdu):
        self.node.on_receive_pdu(src,pdu.payload)

###########################################################
class LayeredNode(Node):

    DEFAULT_MSG_NBITS = 64*8

    ############################
    def __init__(self,sim,id,pos):
        super().__init__(sim,id,pos)
        self.phy = DefaultPhyLayer(self)
        self.mac = DefaultMacLayer(self)
        self.net = DefaultNetLayer(self)

    ############################
    def set_layers(self,phy=None,mac=None,net=None):
        if phy is not None:
            self.phy = phy(self)
        if mac is not None:
            self.mac = mac(self)
        if net is not None:
            self.net = net(self)

    ############################
    def send(self,dst,*args,**kwargs):
        nbits = kwargs.get("nbits",self.DEFAULT_MSG_NBITS)
        app_pdu = PDU("app",nbits,args=args,kwargs=kwargs)
        self.net.send_pdu(dst,app_pdu)

    ############################
    def on_receive_pdu(self,src,pdu):
        # use process just in case on_receive is a generator
        self.start_process(self.create_process(
            self.on_receive,src,*pdu.args,**pdu.kwargs))

###########################################################
class Simulator:

    ############################
    def __init__(self,until,timescale=1,seed=0):
        if timescale > 0:
            self.env = simpy.rt.RealtimeEnvironment(factor=timescale,strict=False)
        else:
            self.env = simpy.Environment()
        self.nodes = []
        self.until = until
        self.timescale = timescale
        self.timeout = self.env.timeout
        self.random = random.Random(seed)

    ############################
    def init(self):
        pass

    ############################
    @property
    def now(self):
        return self.env.now

    ############################
    def delayed_exec(self,delay,func,*args,**kwargs):
        func = ensure_generator(self.env,func,*args,**kwargs)
        start_delayed(self.env,func,delay=delay)

    ############################
    def add_node(self,nodeclass,pos):
        id = len(self.nodes)
        node = nodeclass(self,id,pos)
        self.nodes.append(node)
        self.update_neighbor_list(id)
        return node

    ############################
    def update_neighbor_list(self,id):
        '''
        Maintain each node's neighbor list by sorted distance after affected
        by addition or relocation of node with ID id
        '''
        me = self.nodes[id]

        # (re)sort other nodes' neighbor lists by distance
        for n in self.nodes:
            # skip this node
            if n is me:
                continue

            nlist = n.neighbor_distance_list

            # remove this node from other nodes' neighbor lists
            for i,(dist,neighbor) in enumerate(nlist):
                if neighbor is me:
                    del nlist[i]
                    break

            # then insert it while maintaining sort order by distance
            bisect.insort(nlist,(distance(n.pos,me.pos),me))

        self.nodes[id].neighbor_distance_list = [
                (distance(n.pos,me.pos),n)
                for n in self.nodes if n is not me
                ]
        self.nodes[id].neighbor_distance_list.sort()

    ############################
    def run(self):
        self.init()
        for n in self.nodes:
            n.init()
        for n in self.nodes:
            self.env.process(ensure_generator(self.env,n.run))
        self.env.run(until=self.until)
        for n in self.nodes:
            n.finish()
