import sys
import os
from . import wsnsimpy 
from .wsnsimpy import BROADCAST_ADDR, start_delayed, ensure_generator
from threading import Thread
from .topovis import Scene,LineStyle
from .topovis.TkPlotter import Plotter

###########################################################
class Node(wsnsimpy.Node):

    ###################
    def __init__(self,sim,id,pos):
        super().__init__(sim,id,pos)
        self.scene = self.sim.scene
        self.scene.node(id,*pos)

    ###################
    def send(self,dest,*args,**kwargs):
        obj_id = self.scene.circle(
                    self.pos[0], self.pos[1],
                    self.tx_range,
                    line="wsnsimpy:tx")
        super().send(dest,*args,**kwargs)
        self.delayed_exec(0.2,self.scene.delshape,obj_id)
        if dest is not wsnsimpy.BROADCAST_ADDR:
            destPos = self.sim.nodes[dest].pos
            obj_id = self.scene.line(
                self.pos[0], self.pos[1],
                destPos[0], destPos[1],
                line="wsnsimpy:unicast")
            self.delayed_exec(0.2,self.scene.delshape,obj_id)

    ###################
    def move(self,x,y):
        super().move(x,y)
        self.scene.nodemove(self.id,x,y)


###########################################################
class DefaultPhyLayer(wsnsimpy.DefaultPhyLayer):

    def on_tx_start(self,pdu):
        super().on_tx_start(pdu)
        if pdu.type == "ack":
            linetype = "wsnsimpy:ack"
        else:
            linetype = "wsnsimpy:tx"
        x,y = self.node.pos
        tx_time = pdu.nbits/self.bitrate
        oid = self.node.scene.circle(
                x,y,self.node.tx_range,line=linetype)
        self.node.delayed_exec(max(tx_time,0.2),
                self.node.scene.delshape,oid)

    def on_collision(self,pdu):
        super().on_collision(pdu)
        x,y = self.node.pos
        line1 = self.node.scene.line(x-5,y-5,x+5,y+5,line="wsnsimpy:collision")
        line2 = self.node.scene.line(x+5,y-5,x-5,y+5,line="wsnsimpy:collision")
        self.node.delayed_exec(0.2,self.node.scene.delshape,line1)
        self.node.delayed_exec(0.2,self.node.scene.delshape,line2)


###########################################################
class DefaultMacLayer(wsnsimpy.DefaultMacLayer):
    def on_receive_pdu(self,pdu):
        super().on_receive_pdu(pdu)
        if pdu.type != "data" or pdu.dst != self.node.id:
            return
        sx,sy = self.node.sim.nodes[pdu.src].pos
        dx,dy = self.node.pos
        oid = self.node.scene.line(sx,sy,dx,dy,line="wsnsimpy:unicast")
        self.node.delayed_exec(0.2,self.node.scene.delshape,oid)

###########################################################
class DefaultNetLayer(wsnsimpy.DefaultNetLayer):
    pass

###########################################################
class LayeredNode(wsnsimpy.LayeredNode):

    ###################
    def __init__(self,sim,id,pos):
        super().__init__(sim,id,pos)
        self.scene = self.sim.scene
        self.scene.node(id,*pos)
        self.set_layers(
                phy=DefaultPhyLayer,
                mac=DefaultMacLayer,
                net=DefaultNetLayer)

    ###################
    def move(self,x,y):
        super().move(x,y)
        self.scene.nodemove(self.id,x,y)


###########################################################
class _FakeScene:
    def _fake_method(self,*args,**kwargs):
        pass
    def __getattr__(self,name):
        return self._fake_method

###########################################################
class Simulator(wsnsimpy.Simulator):
    '''Wrap WsnSimPy's Simulator class so that Tk main loop can be started in the
    main thread'''

    def __init__(self,until,timescale=1,terrain_size=(500,500),visual=True,title=None):
        super().__init__(until,timescale)
        self.visual = visual
        self.terrain_size = terrain_size
        if self.visual:
            self.scene = Scene(realtime=True)
            self.scene.linestyle("wsnsimpy:tx", color=(0,0,1), dash=(5,5))
            self.scene.linestyle("wsnsimpy:ack", color=(0,1,1), dash=(5,5))
            self.scene.linestyle("wsnsimpy:unicast", color=(0,0,1), width=3, arrow='head')
            self.scene.linestyle("wsnsimpy:collision", color=(1,0,0), width=3)
            if title is None:
                title = "WsnSimPy"
            self.tkplot = Plotter(windowTitle=title,terrain_size=terrain_size)
            self.tk = self.tkplot.tk
            self.scene.addPlotter(self.tkplot)
            self.scene.init(*terrain_size)
        else:
            self.scene = _FakeScene()

    def init(self):
        super().init()

    def _update_time(self):
        while True:
            self.scene.setTime(self.now)
            yield self.timeout(0.1)

    def run(self):
        if self.visual:
            self.env.process(self._update_time())
            thr = Thread(target=super().run)
            thr.setDaemon(True)
            thr.start()
            self.tkplot.tk.mainloop()
        else:
            super().run()
