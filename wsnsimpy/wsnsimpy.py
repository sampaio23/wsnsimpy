import bisect
import inspect
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
        return '<Node %d:(%s,%s)>' % (self.id,self.pos[0],self.pos[1])

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
    def send(self,dest,*args,**kwargs):
        for (dist,node) in self.neighbor_distance_list:
            if dist <= self.tx_range:
                if dest == BROADCAST_ADDR or dest is node.id:
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
    def on_receive(self,sender,**kwargs):
        '''
        To be overriden
        '''
        pass

    ############################
    def on_timer_fired(self,*args,**kwargs):
        '''
        To be overriden
        '''
        pass

    ############################
    def finish(self):
        '''
        To be overriden
        '''
        pass

###########################################################
class Simulator:

    ############################
    def __init__(self,until,timescale=1):
        if timescale > 0:
            self.env = simpy.rt.RealtimeEnvironment(factor=timescale,strict=False)
        else:
            self.env = simpy.Environment()
        self.nodes = []
        self.until = until
        self.timescale = timescale
        self.timeout = self.env.timeout

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
