SimPy-based WSN Simulator 
=========================

WsnSimPy is a simulator for wireless sensor networks.  It is written in Python
3 and built on top of the [SimPy](https://simpy.readthedocs.io/en/latest/)
simulation framework.

Installation
------------

    pip install wsnsimpy
    
Running Examples
----------------

Examples can be found in the directory `wsnsimpy/examples`, which can be started
directly from a command line.

    python -m wsnsimpy.examples.flood

![Flooding Demostration](img/flood.png)

    python -m wsnsimpy.examples.aodv

![AODV Demostration](img/aodv.png)
