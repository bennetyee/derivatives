#!/usr/bin/python3

import argparse
import math
import matplotlib
import sys
from typing import Callable, List

matplotlib.use('Qt5Agg')

from PyQt5 import QtCore, QtGui, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

INITIAL_WIDTH = 1000
INITIAL_HEIGHT = 800
options: argparse.Namespace

WIDER=True

class Func:
    def __init__(self) -> None:
        pass

    def f(self, x: float) -> float:
        pass

class PrecomputedFunc(Func):
    def __init__(self,
                 f: Callable[[float], float],
                 x0: float,
                 x1: float,
                 num_segs: int) -> None:
        super(PrecomputedFunc, self).__init__()
        self._func = f
        self._x0 = x0
        self._x1 = x1
        self._num_segs = num_segs
        self._dx = (self._x1 - self._x0) / self._num_segs
        if WIDER:
            # to maintain display fidelity and to allow larger Δx values,
            # we widen the precomputation region
            width = x1 - x0
            self._x0 = x0 - width
            self._x1 = x1 + width
            self._num_segs = 3 * num_segs
        self._prex: List[float] = []
        self._prey: List[float] = []
        self.update_precomputes()

    def update_precomputes(self) -> None:
        prex = []
        prey = []
        dx = self._dx
        x0 = self._x0
        f = self._func
        for i in range(self._num_segs + 1):
            x = x0 + i * dx
            y = f(x)
            prex.append(x)
            prey.append(y)
        self._prex = prex
        self._prey = prey

    def f(self, x: float) -> float:
        if x < self._x0 or self._x1 < x:
            # derivative computation may require evaluation from
            # outside the precomputation range
            return self._func(x)
        lower = int((x - self._x0) // self._dx)
        lower_x = self._x0 + lower * self._dx
        if x - lower_x <= self._dx / 2:
            ix = lower
        else:
            ix = lower + 1
        return self._prey[ix]

        
class FuncCanvas(FigureCanvasQTAgg):
    def __init__(self,
                 func: Func,
                 title: str,
                 xmin: float,
                 xmax: float,
                 num_segs: int,
                 width: int=5,
                 height: int=4,
                 dpi: int=300) -> None:
        self._fig = Figure(figsize=(width, height), dpi=dpi)
        super(FuncCanvas, self).__init__(self._fig)
        self._func = func
        self._title = title
        self._xmin = xmin
        self._xmax = xmax
        self._num_segs = num_segs

    def update_canvas(self, extra: Callable[..., None]=None) -> None:
        if options.debug:
            print("update_canvas(self=%s" % self)
        dx = (self._xmax - self._xmin) / self._num_segs
        xs = []
        ys = []
        for i in range(self._num_segs + 1):
            x = self._xmin + i *  dx
            y = self._func.f(x)
            xs.append(x)
            ys.append(y)
        self._fig.clf()
        self._axes = self._fig.add_subplot(111)
        self._axes.set_title(self._title)
        self._axes.plot(xs, ys)
        if extra is not None:
            extra(self._axes, self._func)
        self._axes.grid()
        self.draw()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self,
                 f: Callable[[float], float],
                 fname: str,
                 xmin: float,
                 xmax: float,
                 num_segs: int,
                 *args, **kwargs):
        assert num_segs > 0
        assert xmin < xmax
        super(MainWindow, self).__init__(*args, **kwargs)

        self._deltax_format = '𝝙x = %11.4g'
        self._x_format = ' x = %11.4g'

        self._slider_width = 1000
        self._deltax_scale = (xmax - xmin) / float(self._slider_width)
        self._deltax = (xmax - xmin) / num_segs
        self._min_deltax = (xmax - xmin) / 1.e6
        deltax_initial_slider_value: int = int(self._deltax / self._deltax_scale)

        self._x = (xmin + xmax) / 2
        self._xbase = xmin
        self._xscale = (xmax - xmin) / self._slider_width
        x_initial_slider_value: int = self._slider_width // 2

        self._update_x = []
        self._update_deltax = []

        self._f = f

        def derivative_plus(f: Callable[[float], float]) -> Callable[[float], float]:
            def fprime(x: float) -> float:
                return (f(x + self._deltax) - f(x)) / self._deltax
            return fprime

        def derivative_minus(f: Callable[[float], float]) -> Callable[[float], float]:
            def fprime(x: float) -> float:
                return (f(x) - f(x - self._deltax)) / self._deltax
            return fprime

        def derivative_balanced(f: Callable[[float], float]) -> Callable[[float], float]:
            def fprime(x: float) -> float:
                half = self._deltax / 2.0
                return (f(x + half) - f(x - half)) / self._deltax
            return fprime

        methods = {
            'plus': (derivative_plus, self.show_x_plus_delta_x),
            'minus': (derivative_minus, self.show_x_minus_delta_x),
            'balanced': (derivative_balanced, self.show_x_balanced)
        }
        deriv, show_x = methods[options.approximation_method]

        layout = QtWidgets.QVBoxLayout()

        fobj = PrecomputedFunc(f, xmin, xmax, num_segs)
        prev_canvas = FuncCanvas(fobj, 'f = ' + fname, xmin, xmax, num_segs, width=5, height=4, dpi=300)
        if options.debug:
            print("prev_canvas: %s" % prev_canvas)

        layout.addWidget(prev_canvas)

        nextf = f
        title = "f"

        for _ in range(options.differentiate):
            nextf = deriv(nextf)
            title = title + "'"
            fobj = PrecomputedFunc(nextf, xmin, xmax, num_segs)

            new_canvas = FuncCanvas(fobj, title, xmin, xmax, num_segs, width=5, height=4, dpi=300)
            layout.addWidget(new_canvas)
            if options.debug:
                print("new_canvas: %s" % new_canvas)

            # need to capture current value of prev_canvas, rather than
            # let it lambda bind to the variable which will change later.
            def ShowXAndDeltaXUpdater(canvas: FigureCanvasQTAgg) -> Callable[[], None]:
                def Updater():
                    canvas.update_canvas(show_x)
                return Updater
            def ShowXUpdater(canvas: FigureCanvasQTAgg) -> Callable[[], None]:
                def Updater():
                    canvas.update_canvas(self.show_just_x)
                return Updater
            self._update_x.append(ShowXAndDeltaXUpdater(prev_canvas))
            self._update_deltax.append(ShowXAndDeltaXUpdater(prev_canvas))
            self._update_deltax.append(fobj.update_precomputes)

            prev_canvas = new_canvas
        self._update_x.append(ShowXUpdater(new_canvas))
        self._update_deltax.append(ShowXUpdater(new_canvas))

        slider = QtWidgets.QSlider() # deltax value slider
        slider.setOrientation(QtCore.Qt.Horizontal)
        slider.setRange(0, self._slider_width)
        slider.setValue(deltax_initial_slider_value)
        slider.setTickInterval(1)
        slider.setSingleStep(1)
        slider.valueChanged.connect(self.delta_x_slot)

        sliderLayout = QtWidgets.QHBoxLayout()
        # should set a fixed width font and set width
        self._slider_value = QtWidgets.QLabel()
        font = self._slider_value.font()
        br = QtGui.QFontMetrics(font).boundingRect(self._deltax_format % -8.8888e-88)
        self._slider_value.setFixedSize(br.width(), br.height())
        # use same for x slider
        sliderLayout.addWidget(self._slider_value)
        sliderLayout.addWidget(slider)

        layout.addStretch(1)
        layout.addLayout(sliderLayout)

        slider = QtWidgets.QSlider()  # x value slider
        slider.setOrientation(QtCore.Qt.Horizontal)
        slider.setRange(0, self._slider_width)
        slider.setValue(x_initial_slider_value)
        slider.setTickInterval(1)
        slider.setSingleStep(1)
        slider.valueChanged.connect(self.x_slot)

        sliderLayout = QtWidgets.QHBoxLayout()
        # should set a fixed width font and set width
        self._slider_xvalue = QtWidgets.QLabel()
        self._slider_xvalue.setFixedSize(br.width(), br.height())
        sliderLayout.addWidget(self._slider_xvalue)
        sliderLayout.addWidget(slider)
        layout.addLayout(sliderLayout)

        # Create a placeholder widget to hold our toolbar and canvas.
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.resize(INITIAL_WIDTH, INITIAL_HEIGHT)

        self.delta_x_slot(deltax_initial_slider_value)
        self.x_slot(x_initial_slider_value)

    def show_just_x(self, ax: matplotlib.axes.Axes, func: Func) -> None:
        x = self._x
        y = func.f(x)
        ax.plot([x], [y], color='red', marker='o')

    def show_x_plus_delta_x(self, ax: matplotlib.axes.Axes, func: Func) -> None:
        x0 = self._x
        y0 = func.f(x0)
        x1 = self._x + self._deltax
        y1 = func.f(x1)
        ax.plot([x0, x1], [y0, y1], color='red', marker='o')

    def show_x_minus_delta_x(self, ax: matplotlib.axes.Axes, func: Func) -> None:
        x0 = self._x
        y0 = func.f(x0)
        x1 = self._x - self._deltax
        y1 = func.f(x1)
        ax.plot([x0, x1], [y0, y1], color='red', marker='o')

    def show_x_balanced(self, ax: matplotlib.axes.Axes, func: Func) -> None:
        x = self._x
        y = func.f(x)
        ax.plot([x], [y], color='blue', marker='o')
        half = self._deltax / 2.0
        x0 = x - half
        y0 = func.f(x0)
        x1 = x + half
        y1 = func.f(x1)
        ax.plot([x0, x1], [y0, y1], color='red', marker='o')

    def delta_x_slot(self, value: int) -> None:
        self._deltax = self._deltax_scale * value
        if abs(self._deltax) < self._min_deltax:
            self._deltax = self._min_deltax
        for f in self._update_deltax:
            f()
        self._slider_value.setText(self._deltax_format % self._deltax)
        self.show()

    def x_slot(self, value: int) -> None:
        self._x = self._xbase + value * self._xscale
        for f in self._update_x:
            f()
        self._slider_xvalue.setText(self._x_format % self._x)
        self.show()

def main(argv: List[str]) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', '-d', action='store_true',
                        help='generate debugging output')
    parser.add_argument('--function', '-f', type=str, default='math.sin',
                        help='function to plot')
    parser.add_argument('--function-name', '-F', type=str, default='',
                        help='name of function to use in plot title')
    parser.add_argument('--min-x', '-m', type=float, default=-2.0 * math.pi,
                        help='mininum x value to use in plot')
    parser.add_argument('--max-x', '-M', type=float, default= 2.0 * math.pi,
                        help='maximum x value to use in plot')
    parser.add_argument('--num-segments', '-n', type=int, default=1024,
                        help='number of line segments used in graphing functions') 
    parser.add_argument('--differentiate', '-D', type=int, default=1,
                        help='number of times to differentiate')
    parser.add_argument('--approximation-method', '-a', default='plus',
                        choices=['plus', 'minus', 'balanced'],
                        help='approximation method for computing numerical differentiation: "plus" means use the slope between (x, f(x)) and (x+Δx, f(x+Δx)); "minus" means use the slope between (x-Δx, f(x-Δx)) and (x, f(x)); "balanced" means use the slope between (x-Δx/2, f(x-Δx/2)) and (x+Δx/2, f(x+Δ/2x)).')
    global options
    options, extra = parser.parse_known_args(argv[1:])
    if options.differentiate < 1:
        sys.stderr.write('%s: -D should be at least 1 (%d given)\n' %
                         (argv[0], options.differentiate))
        sys.exit(1)
    qtargv = [argv[0]] + extra
    app = QtWidgets.QApplication(qtargv)  # allow for --style, --reverse etc
    fname = options.function_name
    if fname == '':
        fname = options.function
    w = MainWindow(eval(options.function), fname, options.min_x,
                   options.max_x, options.num_segments)
    app.exec_()

if __name__ == '__main__':
    main(sys.argv)
