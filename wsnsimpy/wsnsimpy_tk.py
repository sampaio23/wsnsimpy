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
    def send(self,dest,**kwargs):
        obj_id = self.scene.circle(
                    self.pos[0], self.pos[1],
                    self.tx_range,
                    line="wsnsimpy:tx")
        super().send(dest,**kwargs)
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
            self.scene.linestyle("wsnsimpy:tx", color=(1,0,0), dash=(5,5))
            self.scene.linestyle("wsnsimpy:unicast", color=(1,0,0), width=3, arrow='head')
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
