# -*- coding: utf-8 -*-
"""
Copyright 2010 Olivier Belanger

This file is part of pyo, a python module to help digital signal
processing script creation.

pyo is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pyo is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pyo.  If not, see <http://www.gnu.org/licenses/>.
"""
from types import ListType, SliceType, FloatType, StringType
import random, threading, time, os, inspect
from subprocess import call
from math import pow, log10
from distutils.sysconfig import get_python_lib

import Tkinter
from Tkinter import *
Tkinter.NoDefaultRoot()

from _pyo import *

######################################################################
### Utilities
######################################################################
SNDS_PATH = os.path.join(get_python_lib(), "pyolib", "snds")
XNOISE_DICT = {'uniform': 0, 'linear_min': 1, 'linear_max': 2, 'triangle': 3, 
                'expon_min': 4, 'expon_max': 5, 'biexpon': 6, 'cauchy': 7, 
                'weibull': 8, 'gaussian': 9, 'poisson': 10, 'walker': 11, 
                'loopseg': 12}

class Clean_objects(threading.Thread):
    """
    Stops and deletes PyoObjects after a given time.
    
    Parameters:
    
    time : float
        Time, in seconds, to wait before calling stop on the given 
        objects and deleting them.
    *args : PyoObject(s)
        Objects to delete.
        
    Methods:
    
    start() : Starts the thread. The timer begins on this call.    

    Examples:
    
    >>> s = Server().boot()
    >>> s.start()
    >>> a = Noise(mul=.5).out()
    >>> b = Fader(fadein=.1, fadeout=1, dur=5).play()
    >>> c = Biquad(a, freq=1000, q=2, mul=b).out()
    >>> dump = Clean_objects(time=6, a, b, c)
    >>> dump.start()
    
    """
    def __init__(self, time, *args):
        threading.Thread.__init__(self)
        self.t = time
        self.args = args
        
    def run(self):
        time.sleep(self.t)
        for arg in self.args:
            try: arg.stop()
            except: pass
        for arg in self.args:
            del arg 
        
def convertArgsToLists(*args):
    """
    Convert all arguments to list if not already a list or a PyoObject. 
    Return new args and maximum list length.
    
    """
    first = True
    for i in args:
        if isinstance(i, PyoObject): pass  
        elif isinstance(i, PyoTableObject): pass 
        elif type(i) != ListType: i = [i]
            
        if first: tup = (i,)
        else: tup = tup + (i,)
        
        first = False
        
    lengths = [len(i) for i in tup]
    max_length = max(lengths)
    tup = tup + (max_length, )  
    return tup

def wrap(arg, i):
    """
    Return value at position `i` from `arg` with wrap around `arg` length.
    
    """
    x = arg[i % len(arg)]
    if isinstance(x, PyoObject):
        return x[0]
    else:
        return x

def example(cls, dur=5):
    """
    Runs the example given in the __doc__ string of the object in argument.
    
    example(cls, dur=5)
    
    Parameters:
    
    cls : PyoObject class
        Class reference of the desired object example.
    dur : float, optional
        Duration of the example.
        
    """
    doc = cls.__doc__.split("Examples:")[1]
    lines = doc.splitlines()
    ex_lines = [line.lstrip("    ") for line in lines if ">>>" in line or "..." in line]
    ex = "import time\nfrom pyo import *\n"
    for line in ex_lines:
        if ">>>" in line: line = line.lstrip(">>> ")
        if "..." in line: line = "    " +  line.lstrip("... ")
        ex += line + "\n"
    ex += "time.sleep(%f)\ns.stop()\ns.shutdown()\n" % dur
    f = open("tmp_example.py", "w")
    f.write('print """\n%s\n"""\n' % ex)
    f.write(ex)
    f.close()    
    p = call(["python", "tmp_example.py"])
    os.remove("tmp_example.py")
      
def removeExtraDecimals(x):
    if type(x) == FloatType:
        return "=%.2f" % x
    elif type(x) == StringType:
        return '="%s"' % x    
    else:
        return "=" + str(x)    

def class_args(cls):
    """
    Returns the init line of a class reference.
    
    class_args(cls)
    
    This function takes a class reference (not an instance of that class) 
    in input and returns the init line of that class with the default values.
    
    Parameters:
    
    cls : PyoObject class
        Class reference of the desired object init line.

    """
    name = cls.__name__
    arg = inspect.getargspec(getattr(cls, "__init__"))
    arg = inspect.formatargspec(*arg, formatvalue=removeExtraDecimals)
    arg = arg.replace("self, ", "")
    return name + arg
        
######################################################################
### Map -> rescale values from sliders
######################################################################
class Map:
    """
    Converts value between 0 and 1 on various scales.
    
    Base class for Map objects.
    
    Parameters:
    
    min : int or float
        Lowest value of the range.
    max : int or float
        Highest value of the range.
    scale : string {'lin', 'log'}
        Method used to scale the input value on the specified range.
        
    Methods:
    
    get(x) : Returns scaled value for `x` between 0 and 1.
    set(x) : Returns the normalized value (0 -> 1) for `x` in the real range.  

    Attributes:
    
    min : Lowest value of the range.
    max : Highest value of the range.
    scale : Method used to scale the input value.

    Examples:
    
    >>> m = Map(20., 20000., 'log')
    >>> print m.get(.5)
    632.455532034
    >>> print m.set(12000)
    0.926050416795
    
    """
    def __init__(self, min, max, scale):
        self._min, self._max, self._scale = min, max, scale

    def get(self, x):
        """
        Takes `x` between 0 and 1 and returns scaled value.
        
        """
        if x < 0: x = 0.0
        elif x > 1: x = 1.0 
        
        if self._scale == 'log':
            return pow(10, x * log10(self._max/self._min) + log10(self._min))
        else:
            return (self._max - self._min) * x + self._min

    def set(self, x):
        """
        Takes `x` in the real range and returns value unscaled 
        (between 0 and 1).
        
        """
        
        if self._scale == 'log':
            return log10(x/self._min) / log10(self._max/self._min)
        else:
            return (x - self._min) / (self._max - self._min)

    @property
    def min(self): return self._min
    @property
    def max(self): return self._max
    @property
    def scale(self): return self._scale

class SLMap(Map):
    """
    Base Map class used to manage control sliders. 
    
    Derived from Map class, a few parameters are added for sliders 
    initialization.
    
    Parent class: Map
    
    Parameters:

    min : int or float
        Smallest value of the range.
    max : int or float
        Highest value of the range.
    scale : string {'lin', 'log'}
        Method used to scale the input value on the specified range.    
    name : string
        Name of the attributes the slider is affected to.
    init : int or float
        Initial value. Specified in the real range, not between 0 and 1. Use
        the `set` method to retreive the normalized corresponding value.
    res : string {'int', 'float'}, optional
        Sets the resolution of the slider. Defaults to 'float'.
    ramp : float, optional
        Ramp time, in seconds, used to smooth the signal sent from slider 
        to object's attribute. Defaults to 0.025.

    Methods:
    
    get(x) : Returns the scaled value for `x` between 0 and 1.
    set(x) : Returns the normalized value (0 -> 1) for `x` in the real range.  

    Attributes:
    
    min : Lowest value of the range.
    max : Highest value of the range.
    scale : Method used to scale the input value.
    name : Name of the parameter to control.
    init : Initial value of the slider.
    res : Slider resolution {int or float}.
    ramp : Ramp time in seconds.
    
    Examples:
    
    >>> s = Server().boot()
    >>> initvals = [350,360,375,388]
    >>> maps = [SLMap(20., 2000., 'log', 'freq', initvals), SLMapMul(.2)]
    >>> a = Sine(freq=initvals, mul=.2).out()
    >>> a.ctrl(maps)  
    >>> s.gui(locals())      

    """
    def __init__(self, min, max, scale, name, init, res='float', ramp=0.025):
        Map.__init__(self, min, max, scale)
        self._name, self._init, self._res, self._ramp = name, init, res, ramp

    @property
    def name(self): return self._name
    @property
    def init(self): return self._init
    @property
    def res(self): return self._res
    @property
    def ramp(self): return self._ramp
    
class SLMapFreq(SLMap):
    """
    SLMap with normalized values for a 'freq' slider.

    Parent class: SLMap
    
    Parameters:
    
    init : int or float, optional
        Initial value. Specified in the real range, not between 0 and 1.
        Defaults to 1000.

    SLMapFreq values are: 
        
    min = 20.0
    max = 20000.0
    scale = 'log'
    name = 'freq'
    res = 'float'
    ramp = 0.025

    Methods:
    
    get(x) : Returns scaled value for `x` between 0 and 1.
    set(x) : Returns the normalized value (0 -> 1) for `x` in the real range.  

    """
    def __init__(self, init=1000):
        SLMap.__init__(self, 20., 20000., 'log', 'freq', init, 'float', 0.025)

class SLMapMul(SLMap):
    """
    SLMap with normalized values for a 'mul' slider.

    Parent class: SLMap
    
    Parameters:
    
    init : int or float, optional
        Initial value. Specified in the real range, not between 0 and 1.
        Defaults to 1.

    SLMapMul values are: 
        
    min = 0.0
    max = 2.0
    scale = 'lin'
    name = 'mul'
    res = 'float'
    ramp = 0.025

    Methods:
    
    get(x) : Returns scaled value for `x` between 0 and 1.
    set(x) : Returns the normalized value (0 -> 1) for `x` in the real range.  

    """
    def __init__(self, init=1.):
        SLMap.__init__(self, 0., 2., 'lin', 'mul', init, 'float', 0.025)

class SLMapPhase(SLMap):
    """
    SLMap with normalized values for a 'phase' slider.

    Parent class: SLMap
    
    Parameters:
    
    init : int or float, optional
        Initial value. Specified in the real range, not between 0 and 1.
        Defaults to 0.

    SLMapPhase values are: 
        
    min = 0.0
    max = 1.0
    scale = 'lin'
    name = 'phase'
    res = 'float'
    ramp = 0.025

    Methods:
    
    get(x) : Returns scaled value for `x` between 0 and 1.
    set(x) : Returns the normalized value (0 -> 1) for `x` in the real range.  

    """
    def __init__(self, init=0.):
        SLMap.__init__(self, 0., 1., 'lin', 'phase', init, 'float', 0.025)

class SLMapPan(SLMap):
    """
    SLMap with normalized values for a 'pan' slider.

    Parent class: SLMap
    
    Parameters:
    
    init : int or float, optional
        Initial value. Specified in the real range, not between 0 and 1.
        Defaults to 0.

    SLMapPhase values are: 
        
    min = 0.0
    max = 1.0
    scale = 'lin'
    name = 'pan'
    res = 'float'
    ramp = 0.025

    Methods:
    
    get(x) : Returns scaled value for `x` between 0 and 1.
    set(x) : Returns the normalized value (0 -> 1) for `x` in the real range.  

    """
    def __init__(self, init=0.):
        SLMap.__init__(self, 0., 1., 'lin', 'pan', init, 'float', 0.025)

class SLMapQ(SLMap):
    """
    SLMap with normalized values for a 'q' slider.

    Parent class: SLMap
    
    Parameters:
    
    init : int or float, optional
        Initial value. Specified in the real range, not between 0 and 1.
        Defaults to 1.

    SLMapQ values are: 
        
    min = 0.1
    max = 100.0
    scale = 'log'
    name = 'q'
    res = 'float'
    ramp = 0.025

    Methods:
    
    get(x) : Returns scaled value for `x` between 0 and 1.
    set(x) : Returns the normalized value (0 -> 1) for `x` in the real range.  

    """
    def __init__(self, init=1.):
        SLMap.__init__(self, 0.1, 100., 'log', 'q', init, 'float', 0.025)

class SLMapDur(SLMap):
    """
    SLMap with normalized values for a 'dur' slider.

    Parent class: SLMap
    
    Parameters:
    
    init : int or float, optional
        Initial value. Specified in the real range, not between 0 and 1.
        Defaults to 1.

    SLMapDur values are: 
        
    min = 0.
    max = 60.0
    scale = 'lin'
    name = 'dur'
    res = 'float'
    ramp = 0.025

    Methods:
    
    get(x) : Returns scaled value for `x` between 0 and 1.
    set(x) : Returns the normalized value (0 -> 1) for `x` in the real range.  

    """
    def __init__(self, init=1.):
        SLMap.__init__(self, 0., 60., 'lin', 'dur', init, 'float', 0.025)

######################################################################
### Multisliders
######################################################################
class MultiSlider(Frame):
    def __init__(self, master, init, key, command): 
        Frame.__init__(self, master, bd=0, relief=FLAT)
        self._values = init
        self._nchnls = len(init)
        self._key = key
        self._command = command
        self._lines = []
        self._height = 16
        self._yoff = 4 # hack for OSX display
        self.canvas = Canvas(self, height=self._height*self._nchnls+1, 
                            width=225, relief=FLAT, bd=0, bg="#BCBCAA")
        w = self.canvas.winfo_width()
        for i in range(self._nchnls):
            x = int(self._values[i] * w)
            y = self._height * i + self._yoff
            self._lines.append(self.canvas.create_rectangle(0, y, x, 
                                y+self._height-1, width=0, fill="#121212"))
        self.canvas.bind("<Button-1>", self.clicked)
        self.canvas.bind("<Motion>", self.move)
        self.canvas.bind("<Configure>", self.size)
        self.canvas.grid(sticky=E+W)
        self.columnconfigure(0, weight=1)
        self.grid()

    def size(self, event):
        w = self.canvas.winfo_width()
        for i in range(len(self._lines)):
            y = self._height * i + self._yoff
            x = self._values[i] * w
            self.canvas.coords(self._lines[i], 0, y, x, y+self._height-1)
        
    def clicked(self, event):
        self.update(event)
        
    def move(self, event):
        if event.state == 0x0100:
            slide = (event.y - self._yoff) / self._height
            if 0 <= slide < len(self._lines):
                self.update(event)

    def update(self, event):
        w = self.canvas.winfo_width()
        slide = (event.y - self._yoff) / self._height
        val = event.x / float(w)
        self._values[slide] = val
        y = self._height * slide + self._yoff
        self.canvas.coords(self._lines[slide], 0, y, event.x, y+self._height-1)
        self._command(self._key, self._values)
           
######################################################################
### Control window for PyoObject
######################################################################
class Command:
    def __init__(self, func, key):
        self.func = func
        self.key = key

    def __call__(self, value):
        self.func(self.key, value)

class PyoObjectControl(Frame):
    def __init__(self, master=None, obj=None, map_list=None):
        Frame.__init__(self, master, bd=1, relief=GROOVE)
        self.bind('<Destroy>', self._destroy)
        self._obj = obj
        self._map_list = map_list
        self._sliders = []
        self._excluded = []
        self._values = {}
        self._displays = {}
        self._maps = {}
        self._sigs = {}
        for i, m in enumerate(self._map_list):
            key, init = m.name, m.init
            # filters PyoObjects
            if isinstance(init, PyoObject):
                self._excluded.append(key)
            else:    
                self._maps[key] = m
                # label (param name)
                label = Label(self, height=1, width=10, highlightthickness=0, text=key)
                label.grid(row=i, column=0)
                # create and pack slider
                if type(init) != ListType:
                    self._sliders.append(Scale(self, command=Command(self.setval, key),
                                  orient=HORIZONTAL, relief=GROOVE, from_=0., to=1., showvalue=False, 
                                  resolution=.0001, bd=1, length=225, troughcolor="#BCBCAA", width=12))
                    self._sliders[-1].set(m.set(init))
                    disp_height = 1
                else:
                    self._sliders.append(MultiSlider(self, [m.set(x) for x in init], key, self.setval)) 
                    disp_height = len(init)   
                self._sliders[-1].grid(row=i, column=1, sticky=E+W)
                # display of numeric values
                textvar = StringVar(self)
                display = Label(self, height=disp_height, width=10, highlightthickness=0, textvariable=textvar)
                display.grid(row=i, column=2)
                self._displays[key] = textvar
                if type(init) != ListType:
                    self._displays[key].set("%.4f" % init)
                else:
                    self._displays[key].set("\n".join(["%.4f" % i for i in init]))
                # set obj attribute to PyoObject SigTo     
                self._sigs[key] = SigTo(init, .025, init)
                setattr(self._obj, key, self._sigs[key])
        # padding        
        top = self.winfo_toplevel()
        top.rowconfigure(0, weight=1)
        top.columnconfigure(0, weight=1)       
        self.columnconfigure(1, weight=1)
        self.grid(ipadx=15, ipady=15, sticky=E+W)

    def _destroy(self, event):
        for m in self._map_list:
            key = m.name
            if key not in self._excluded:
                setattr(self._obj, key, self._values[key])
                del self._sigs[key]
            
        
    def setval(self, key, x):
        if type(x) != ListType:
            value = self._maps[key].get(float(x))
            self._displays[key].set("%.4f" % value)
        else:    
            value = [self._maps[key].get(float(y)) for y in x] 
            self._displays[key].set("\n".join(["%.4f" % i for i in value]))
            
        self._values[key] = value
        setattr(self._sigs[key], "value", value)
        
######################################################################
### PyoObject -> base class for pyo sound objects
######################################################################
class PyoObject(object):
    """
    Base class for all pyo objects that manipulate vectors of samples.
    
    The user should never instantiate an object of this class.

    Methods:

    play() : Start processing without sending samples to output. 
        This method is called automatically at the object creation.
    stop() : Stop processing.
    out(chnl, inc) : Start processing and send samples to audio output 
        beginning at `chnl`.
    mix(voices) : Mix object's audio streams into `voices` streams and 
        return the Mix object.
    setMul(x) : Replace the `mul` attribute.
    setAdd(x) : Replace the `add` attribute.
    setDiv(x) : Replace and inverse the `mul` attribute.
    setSub(x) : Replace and inverse the `add` attribute.
    ctrl(map_list, title) : Opens a sliders window to control parameters.
    get(all) : Return the first sample of the current buffer as a float.
    dump() : Print current status of the object's attributes.

    Attributes:

    mul : float or PyoObject
        Multiplication factor.
    add : float or PyoObject
        Addition factor.
    
    Notes:

    - Other operations:
    
    len(obj) : Return the number of audio streams in an object.
    obj[x] : Return stream `x` of the object. `x` is a number 
        from 0 to len(obj) - 1.
    del obj : Perform a clean delete of the object.
    
    - Arithmetics:
    
    Multiplication, addition, division and substraction can be applied 
    between pyo objects or between pyo objects and numbers. Doing so 
    returns a Dummy object with the result of the operation.
    `b = a * 0.5` creates a Dummy object `b` with `mul` attribute set 
    to 0.5 and leave `a` untouched.
    
    Inplace multiplication, addition, division and substraction can be 
    applied between pyo objects or between pyo objects and numbers. 
    These operations will replace the `mul` or `add` factor of the object. 
    `a *= 0.5` replaces the `mul` attribute of `a`.
    
    """
    def __init__(self):
        pass

    def __add__(self, x):
        x, lmax = convertArgsToLists(x)
        self._add_dummy = Dummy([obj + wrap(x,i) for i, obj in enumerate(self._base_objs)])
        return self._add_dummy
        
    def __radd__(self, x):
        x, lmax = convertArgsToLists(x)
        self._add_dummy = Dummy([obj + wrap(x,i) for i, obj in enumerate(self._base_objs)])
        return self._add_dummy
            
    def __iadd__(self, x):
        self.setAdd(x)
        return self

    def __sub__(self, x):
        x, lmax = convertArgsToLists(x)
        self._add_dummy = Dummy([obj - wrap(x,i) for i, obj in enumerate(self._base_objs)])
        return self._add_dummy

    def __rsub__(self, x):
        x, lmax = convertArgsToLists(x)
        self._add_dummy = Dummy([Sig(wrap(x,i)) - obj for i, obj in enumerate(self._base_objs)])
        return self._add_dummy

    def __isub__(self, x):
        self.setSub(x)
        return self
 
    def __mul__(self, x):
        x, lmax = convertArgsToLists(x)
        self._mul_dummy = Dummy([obj * wrap(x,i) for i, obj in enumerate(self._base_objs)])
        return self._mul_dummy
        
    def __rmul__(self, x):
        x, lmax = convertArgsToLists(x)
        self._mul_dummy = Dummy([obj * wrap(x,i) for i, obj in enumerate(self._base_objs)])
        return self._mul_dummy
            
    def __imul__(self, x):
        self.setMul(x)
        return self
 
    def __div__(self, x):
        x, lmax = convertArgsToLists(x)
        self._mul_dummy = Dummy([obj / wrap(x,i) for i, obj in enumerate(self._base_objs)])
        return self._mul_dummy

    def __rdiv__(self, x):
        x, lmax = convertArgsToLists(x)
        self._mul_dummy = Dummy([Sig(wrap(x,i)) / obj for i, obj in enumerate(self._base_objs)])
        return self._mul_dummy

    def __idiv__(self, x):
        self.setDiv(x)
        return self
        
    def __getitem__(self, i):
        if type(i) == SliceType or i < len(self._base_objs):
            return self._base_objs[i]
        else:
            print "'i' too large!"         
 
    def __len__(self):
        return len(self._base_objs)

    def __del__(self):
        for obj in self._base_objs:
            obj.deleteStream()
            del obj
            
    def __repr__(self):
        return '< Instance of %s class >' % self.__class__.__name__
        
    def dump(self):
        """
        Print the number of streams and the current status of the 
        object's attributes.
        
        """
        attrs = dir(self)
        pp =  '< Instance of %s class >' % self.__class__.__name__
        pp += '\n-----------------------------'
        pp += '\nNumber of audio streams: %d' % len(self)
        pp += '\n--- Attributes ---'
        for attr in attrs:
            pp += '\n' + attr + ': ' + str(getattr(self, attr))
        pp += '\n-----------------------------'
        return pp    
            
    def get(self, all=False):
        """
        Return the first sample of the current buffer as a float.
        
        Can be used to convert audio stream to usable Python data.

        Parameters:

            all : boolean, optional
                If True, the first value of each object's stream
                will be returned as a list. Otherwise, only the value
                of the first object's stream will be returned as a float.
                Defaults to False.
                 
        """
        if not all:
            return self._base_objs[0]._getStream().getValue()
        else:
            return [obj._getStream().getValue() for obj in self._base_objs]
            
    def getBaseObjects(self):
        """
        Return a list of audio Stream objects.
        
        """
        return self._base_objs
        
    def play(self):
        """
        Start processing without sending samples to output. 
        This method is called automatically at the object creation.
        
        """
        self._base_objs = [obj.play() for obj in self._base_objs]
        return self

    def out(self, chnl=0, inc=1):
        """
        Start processing and send samples to audio output beginning at `chnl`.
        
        Parameters:

        chnl : int, optional
            Physical output assigned to the first audio stream of the object. 
            Defaults to 0.

            If `chnl` is an integer equal or greater than 0: successive 
            streams increment the output number by `inc` and wrap around 
            the global number of channels.
            
            If `chnl` is a negative integer: streams begin at 0, increment 
            the output number by `inc` and wrap around the global number of 
            channels. Then, the list of streams is scrambled.
            
            If `chnl` is a list: successive values in the list will be 
            assigned to successive streams.
            
        inc : int, optional
            Output increment value.
        
        """
        if type(chnl) == ListType:
            self._base_objs = [obj.out(wrap(chnl,i)) for i, obj in enumerate(self._base_objs)]
        else:
            if chnl < 0:    
                self._base_objs = [obj.out(i*inc) for i, obj in enumerate(random.sample(self._base_objs, len(self._base_objs)))]
            else:
                self._base_objs = [obj.out(chnl+i*inc) for i, obj in enumerate(self._base_objs)]
        return self
    
    def stop(self):
        """
        Stop processing.
        
        """
        [obj.stop() for obj in self._base_objs]
        return self

    def mix(self, voices=1):
        """
        Mix the object's audio streams into `voices` streams and return 
        the Mix object.
        
        Parameters:

        voices : int, optional
            Number of audio streams of the Mix object created by this method. 
            If more than 1, object's streams are alternated and added into 
            Mix object's streams. Defaults to 1.
            
        """
        self._mix = Mix(self, voices)
        return self._mix
        
    def setMul(self, x):
        """
        Replace the `mul` attribute.
        
        Parameters:

        x : float or PyoObject
            New `mul` attribute.
        
        """
        self._mul = x
        x, lmax = convertArgsToLists(x)
        [obj.setMul(wrap(x,i)) for i, obj in enumerate(self._base_objs)]
        
    def setAdd(self, x):
        """
        Replace the `add` attribute.
                
        Parameters:

        x : float or PyoObject
            New `add` attribute.
        
        """
        self._add = x
        x, lmax = convertArgsToLists(x)
        [obj.setAdd(wrap(x,i)) for i, obj in enumerate(self._base_objs)]

    def setSub(self, x):
        """
        Replace and inverse the `mul` attribute.
        
        Parameters:

        x : float or PyoObject
            New inversed `mul` attribute.
        
        """
        self._add = x
        x, lmax = convertArgsToLists(x)
        [obj.setSub(wrap(x,i)) for i, obj in enumerate(self._base_objs)]

    def setDiv(self, x):
        """
        Replace and inverse the `add` attribute.
                
        Parameters:

        x : float or PyoObject
            New inversed `add` attribute.
        
        """
        self._mul = x
        x, lmax = convertArgsToLists(x)
        [obj.setDiv(wrap(x,i)) for i, obj in enumerate(self._base_objs)]

    def ctrl(self, map_list=None, title=None):
        """
        Opens a sliders window to control parameters of the object. 
        Only parameters that can be set to a PyoObject are allowed 
        to be mapped on a slider.

        If a list of values are given to a parameter, a multisliders 
        will be used to control each stream independently.
        
        Parameters:

        map_list : list of SLMap objects, optional
            Users defined set of parameters scaling. There is default 
            scaling for each object that accept `ctrl` method.
        title : string, optional
            Title of the window. If none is provided, the name of the 
            class is used.

        """
        if map_list == None:
            map_list = self._map_list
        if map_list == []:
            print("There is no controls for %s object." % self.__class__.__name__)
            return
    
        win = Tk()    
        f = PyoObjectControl(win, self, map_list)
        if title == None: title = self.__class__.__name__
        win.title(title)

    @property
    def mul(self):
        """float or PyoObject. Multiplication factor.""" 
        return self._mul
    @mul.setter
    def mul(self, x): self.setMul(x)

    @property
    def add(self):
        """float or PyoObject. Addition factor.""" 
        return self._add
    @add.setter
    def add(self, x): self.setAdd(x)


######################################################################
### View window for PyoTableObject
######################################################################
class ViewTable(Frame):
    def __init__(self, master=None, samples=None):
        Frame.__init__(self, master, bd=1, relief=GROOVE)
        self.samples = samples
        self.line_points = []
        self.width = 400
        self.height = 150
        self.half_height = self.height / 2
        self.wave_amp = self.half_height -2
        self.canvas = Canvas(self, height=self.height, width=self.width, relief=SUNKEN, bd=1, bg="#EFEFEF")
        step = len(samples) / float(self.width - 1)
        for i in range(self.width):
            y = self.samples[int(i*step)-1] * self.wave_amp + self.wave_amp - 1
            self.line_points.append(i+4)
            self.line_points.append(self.height-y)
            self.line_points.append(i+4)
            self.line_points.append(self.height-y)
        self.canvas.create_line(0, self.half_height+3, self.width, self.half_height+3, fill='grey', dash=(4,2))    
        self.canvas.create_line(*self.line_points)
        self.canvas.grid()
        self.grid(ipadx=10, ipady=10)
           
######################################################################
### PyoTableObject -> base class for pyo table objects
######################################################################
class PyoTableObject(object):
    """
    Base class for all pyo table objects. 
    
    A table object is a buffer memory to store precomputed samples. 
    
    The user should never instantiate an object of this class.
 
    Methods:
    
    getSize() : Return table size in samples.
    view() : Opens a window showing the contents of the table.
    dump() : Print current status of the object's attributes.
    write(path) : Writes the content of the table into a text file.
    read(path) : Sets the content of the table from a text file.
    normalize() : Normalize table samples between -1 and 1.
    
    Notes:
    
    Operations allowed on all table objects :
    
    len(obj) : Return the number of table streams in an object.
    obj[x] : Return table stream `x` of the object. `x` is a number 
        from 0 to len(obj) - 1.

    """
    def __init__(self):
        pass

    def __getitem__(self, i):
        if i < len(self._base_objs):
            return self._base_objs[i]
        else:
            print "'i' too large!"         
 
    def __len__(self):
        return len(self._base_objs)

    def __repr__(self):
        return '< Instance of %s class >' % self.__class__.__name__
        
    def dump(self):
        """
        Print the number of streams and the current status of the 
        object's attributes.
        
        """
        attrs = dir(self)
        pp =  '< Instance of %s class >' % self.__class__.__name__
        pp += '\n-----------------------------'
        pp += '\nNumber of audio streams: %d' % len(self)
        pp += '\n--- Attributes ---'
        for attr in attrs:
            pp += '\n' + attr + ': ' + str(getattr(self, attr))
        pp += '\n-----------------------------'
        return pp    

    def write(self, path):
        """
        Writes the content of the table into a text file.
        
        This function can be used to store the table data as a
        list of floats into a text file.
         
        """
        f = open(path, "w")
        f.write(str([obj.getTable() for obj in self._base_objs]))
        f.close()

    def read(self, path):
        """
        Reads the content of a text file and replaces the table data
        with the values in the file.
        
        Format is a list of lists of floats. For example, A two 
        tablestreams object must be given a content like this:
        
        [[0.0,1.0,0.5,...], [1.0,0.99,0.98,0.97,...]]
        
        Each object's tablestream will be resized according to the 
        length of the lists.
        
        """
        f = open(path, "r")
        f_list = eval(f.read())
        f_len = len(f_list)
        f.close()
        [obj.setData(f_list[i%f_len]) for i, obj in enumerate(self._base_objs)]
        
    def getBaseObjects(self):
        """
        Return a list of table Stream objects.
        
        """
        return self._base_objs

    def getSize(self):
        """
        Return table size in samples.
        
        """
        return self._size

    def normalize(self):
        """
        Normalize table samples between -1 and 1.

        """
        [obj.normalize() for obj in self._base_objs]
        return self

    def view(self):
        """
        Opens a window showing the contents of the table.
        
        """
        samples = self._base_objs[0].getTable()
        win = Tk()
        f = ViewTable(win, samples)
        win.resizable(False, False)
        win.title("Table waveform")
       
######################################################################
### Internal classes -> Used by pyo
######################################################################
class Mix(PyoObject):
    """
    Mix audio streams to arbitrary number of streams.
    
    Mix the object's audio streams in `ìnput` into `voices` streams.
    
    Parent class: PyoObject

    Parameters:

    input : PyoObject or list of PyoObjects
        Input signal(s) to mix the streams.
    voices : int, optional
        Number of streams of the Mix object. If more than 1, object's 
        streams are alternated and added into Mix object's streams. 
        Defaults to 1.

    Notes:
    
    The mix method of PyoObject creates and returns a new Mix object
    with mixed streams of the object that called the method. User
    don't have to instantiate this class directly. These two calls
    are identical:
    
    >>> b = a.mix()
    >>> b = Mix(a)
    
    Examples:
    
    >>> s = Server().boot()
    >>> s.start()
    >>> a = Sine([random.uniform(400,600) for i in range(50)], mul=.01)
    >>> b = Mix(a).out()
    >>> print len(a)
    50
    >>> print len(b)
    1

    """
    def __init__(self, input, voices=1, mul=1, add=0):
        self._input = input
        self._mul = mul
        self._add = add
        if type(input) == ListType:
            input_objs = []
            input_objs = [obj for pyoObj in input for obj in pyoObj.getBaseObjects()]
        else:    
            input_objs = input.getBaseObjects()
        if voices < 1: voices = 1
        elif voices > len(input_objs): voices = len(input_objs)
        sub_lists = []
        for i in range(voices):
            sub_lists.append([])
        [sub_lists[i % voices].append(obj) for i, obj in enumerate(input_objs)]
        self._base_objs = [Mix_base(l) for l in sub_lists]

    def __dir__(self):
        return ['mul', 'add']
        
class Dummy(PyoObject):
    """
    Dummy object used to perform arithmetics on PyoObject.
    
    The user should never instantiate an object of this class.
    
    Parent class: PyoObject

    Parameters:

    objs_list : list of audio Stream objects
        List of Stream objects return by the PyoObject hiden method 
        getBaseObjects.

    Notes:
    
    Multiplication, addition, division and substraction don't changed
    the PyoObject on which the operation is performed. A dummy object
    is created, which is just a copy of the audio Streams of the object,
    and the operation is applied on the Dummy, leaving the original
    object unmodified. This lets the user performs multiple different 
    arithmetic operations on an object without conficts. Here, `b` is
    a thru of the audio processing of `a` with a different `mul` 
    attribute:

    >>> a = Sine()
    >>> b = a * .5
    >>> print a
    <pyolib.input.Sine object at 0x11fd610>
    >>> print b
    <pyolib._core.Dummy object at 0x11fd710>

    Examples:
    
    >>> s = Server().boot()
    >>> s.start()
    >>> m = Metro().play()
    >>> p = TrigRand(m, 250, 400)
    >>> a = Sine(p, mul=.25).out()
    >>> b = Sine(p*1.25, mul=.25).out()
    >>> c = Sine(p*1.5, mul=.25).out()
    
    """
    def __init__(self, objs_list):
        self._mul = 1
        self._add = 0
        self._base_objs = objs_list

    def __dir__(self):
        return ['mul', 'add']

    def deleteStream(self):
        for obj in self._base_objs:
            obj.deleteStream()
            del obj
        
class InputFader(PyoObject):
    """
    Audio streams crossfader.

    Parameters:
    
    input : PyoObject
        Input signal.

    Methods:

    setInput(x, fadetime) : Replace the `input` attribute.

    Attributes:
    
    input : PyoObject. Input signal.

    Notes:
    
    The setInput method, on object with `input` attribute, already uses 
    an InputFader object to performs crossfade between the old and the 
    new `input` of an object. 
    
    Examples:
    
    >>> s = Server().boot()
    >>> s.start()
    >>> a = Sine(450, mul=.5)
    >>> b = Sine(650, mul=.5)
    >>> c = InputFader(a).out()
    >>> # to created a crossfade, calls:
    >>> c.setInput(b, 20)
    
    """
    def __init__(self, input):
        self._input = input
        input, lmax = convertArgsToLists(input)
        self._base_objs = [InputFader_base(wrap(input,i)) for i in range(lmax)]

    def __dir__(self):
        return ['input', 'mul', 'add']

    def setInput(self, x, fadetime=0.05):
        """
        Replace the `input` attribute.
        
        Parameters:

        x : PyoObject
            New signal to process.
        fadetime : float, optional
            Crossfade time between old and new input. Defaults to 0.05.

        """
        self._input = x
        x, lmax = convertArgsToLists(x)
        [obj.setInput(wrap(x,i), fadetime) for i, obj in enumerate(self._base_objs)]

    @property
    def input(self):
        """PyoObject. Input signal.""" 
        return self._input
    @input.setter
    def input(self, x): self.setInput(x)

class Sig(PyoObject):
    """
    Convert numeric value to PyoObject signal.
    
    Parent class: PyoObject

    Parameters:

    value : float or PyoObject
        Numerical value to convert.

    Methods:

    setValue(x) : Changes the value of the signal stream.
    
    Attributes:
    
    value : float or PyoObject. Numerical value to convert.
    
    Notes:

    The out() method is bypassed. Sig's signal can not be sent to audio outs.
    
    Examples:
    
    >>> s = Server().boot()
    >>> fr = Sig(value=400)
    >>> p = Port(fr, risetime=1, falltime=1)
    >>> a = Sine(freq=p, mul=.5).out()
    >>> s.start()
    >>> fr.value = 800

    """
    def __init__(self, value, mul=1, add=0):
        self._value = value
        self._mul = mul
        self._add = add
        value, mul ,add, lmax = convertArgsToLists(value, mul, add)
        self._base_objs = [Sig_base(wrap(value,i), wrap(mul,i), wrap(add,i)) for i in range(lmax)]

    def __dir__(self):
        return ['value', 'mul', 'add']

    def setValue(self, x):
        """
        Changes the value of the signal stream.

        Parameters:

        x : float or PyoObject
            Numerical value to convert.

        """
        x, lmax = convertArgsToLists(x)
        [obj.setValue(wrap(x,i)) for i, obj in enumerate(self._base_objs)]

    def ctrl(self, map_list=None, title=None):
        self._map_list = [SLMap(0, 1, "lin", "value", 0)]
        PyoObject.ctrl(self, map_list, title)
    
    @property
    def value(self):
        """float or PyoObject. Numerical value to convert.""" 
        return self._value
    @value.setter
    def value(self, x): self.setValue(x)    

class SigTo(PyoObject):
    """
    Convert numeric value to PyoObject signal with ramp time.
    
    When `value` attribute is changed, a ramp is applied from the
    current value to the new value.
    
    Parent class: PyoObject

    Parameters:

    value : float
        Numerical value to convert.
    time : float, optional
        Ramp time, in seconds, to reach the new value. Defaults to 0.025.
    init : float, optional
        Initial value of the internal memory. Defaults to 0.

    Methods:

    setValue(x) : Changes the value of the signal stream.
    setTime(x) : Changes the ramp time.
    
    Attributes:
    
    value : float. Numerical value to convert.
    time : float. Ramp time.
    
    Notes:

    The out() method is bypassed. Sig's signal can not be sent to audio outs.
    
    Examples:
    
    >>> s = Server().boot()
    >>> fr = SigTo(value=400, time=.5, init=400)
    >>> a = Sine(freq=fr, mul=.5).out()
    >>> s.start()
    >>> fr.value = 800

    """
    def __init__(self, value, time=0.025, init=0.0, mul=1, add=0):
        self._value = value
        self._time = time
        self._mul = mul
        self._add = add
        value, time, init, mul ,add, lmax = convertArgsToLists(value, time, init, mul, add)
        self._base_objs = [SigTo_base(wrap(value,i), wrap(time,i), wrap(init,i), wrap(mul,i), wrap(add,i)) for i in range(lmax)]

    def __dir__(self):
        return ['value', 'time', 'mul', 'add']

    def setValue(self, x):
        """
        Changes the value of the signal stream.

        Parameters:

        x : float
            Numerical value to convert.

        """
        x, lmax = convertArgsToLists(x)
        [obj.setValue(wrap(x,i)) for i, obj in enumerate(self._base_objs)]

    def setTime(self, x):
        """
        Changes the ramp time of the object.

        Parameters:

        x : float
            New ramp time.

        """
        x, lmax = convertArgsToLists(x)
        [obj.setTime(wrap(x,i)) for i, obj in enumerate(self._base_objs)]

    def ctrl(self, map_list=None, title=None):
        self._map_list = []
        PyoObject.ctrl(self, map_list, title)
    
    @property
    def value(self):
        """float. Numerical value to convert.""" 
        return self._value
    @value.setter
    def value(self, x): self.setValue(x)    

    @property
    def time(self):
        """float. Ramp time.""" 
        return self._time
    @time.setter
    def time(self, x): self.setTime(x)    
