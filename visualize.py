#!/usr/bin/python3

import math
import sys
import matplotlib
matplotlib.use('Qt5Agg')

from PyQt5 import QtCore, QtGui, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

INITIAL_WIDTH = 1000
INITIAL_HEIGHT = 800

class FuncCanvas(FigureCanvasQTAgg):
    def __init__(self, func, title, xmin, xmax, num_segs, width=5, height=4, dpi=300):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super(FuncCanvas, self).__init__(self.fig)
        self.func = func
        self.title = title
        self.xmin = xmin
        self.xmax = xmax
        self.num_segs = num_segs

    def Update(self, extra=None):
        dx = (self.xmax - self.xmin) / self.num_segs
        xs = []
        ys = []
        for i in range(self.num_segs + 1):
            x = self.xmin + i *  dx
            y = self.func(x)
            xs.append(x)
            ys.append(y)
        self.fig.clf()
        self.axes = self.fig.add_subplot(111)
        self.axes.set_title(self.title)
        self.axes.plot(xs, ys)
        if extra is not None:
            extra(self.axes)
        self.axes.grid()
        self.draw()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, f, fname, xmin, xmax, num_segs, *args, **kwargs):
        assert num_segs > 0
        assert xmin < xmax
        super(MainWindow, self).__init__(*args, **kwargs)

        self.deltax_format = '𝝙x = %11.4g'
        self.x_format = ' x = %11.4g'

        self.slider_width = 1000
        self.deltax_scale = (xmax - xmin) / float(self.slider_width)
        self.deltax = (xmax - xmin) / num_segs
        self.min_deltax = (xmax - xmin) / 1.e6
        deltax_initial_slider_value = self.deltax // self.deltax_scale

        self.x = (xmin + xmax) / 2
        self.xbase = xmin
        self.xscale = (xmax - xmin) / self.slider_width
        x_initial_slider_value = self.slider_width // 2

        self.f = f

        def fprime(x):
            return (f(x + self.deltax) - f(x)) / self.deltax

        def balanced_fprime(x):
            half = self.deltax / 2.0
            return (f(x + half) - f(x - half)) / self.deltax

        self.main_func_canvas = FuncCanvas(f, fname, xmin, xmax, num_segs, width=5, height=4, dpi=300)
        self.derivative_canvas = FuncCanvas(fprime, "derivative", xmin, xmax, num_segs, width=5, height=4, dpi=300)

        self.show_x = self.show_x_and_deltax  # fprime

        # self.derivative_canvas = FuncCanvas(balanced_fprime, "derivative", xmin, xmax, num_segs, width=5, height=4, dpi=300)
        # self.show_x = self.show_x_balanced  # balanced_fprime

        layout = QtWidgets.QVBoxLayout()
        # layout.addWidget(toolbar)
        layout.addWidget(self.main_func_canvas)
        layout.addWidget(self.derivative_canvas)

        slider = QtWidgets.QSlider() # deltax value slider
        slider.setOrientation(QtCore.Qt.Horizontal)
        slider.setRange(0, self.slider_width)
        slider.setValue(deltax_initial_slider_value)
        slider.setTickInterval(1)
        slider.setSingleStep(1)
        slider.valueChanged.connect(self.DeltaXSlot)

        sliderLayout = QtWidgets.QHBoxLayout()
        # should set a fixed width font and set width
        self.slider_value = QtWidgets.QLabel()
        font = self.slider_value.font()
        br = QtGui.QFontMetrics(font).boundingRect(self.deltax_format % -8.8888e-88)
        self.slider_value.setMinimumSize(br.width(), br.height())
        # use same for x slider
        sliderLayout.addWidget(self.slider_value)
        sliderLayout.addWidget(slider)

        layout.addStretch(1)
        layout.addLayout(sliderLayout)

        slider = QtWidgets.QSlider()  # x value slider
        slider.setOrientation(QtCore.Qt.Horizontal)
        slider.setRange(0, self.slider_width)
        slider.setValue(x_initial_slider_value)
        slider.setTickInterval(1)
        slider.setSingleStep(1)
        slider.valueChanged.connect(self.XSlot)

        sliderLayout = QtWidgets.QHBoxLayout()
        # should set a fixed width font and set width
        self.slider_xvalue = QtWidgets.QLabel()
        self.slider_xvalue.setMinimumSize(br.width(), br.height())
        sliderLayout.addWidget(self.slider_xvalue)
        sliderLayout.addWidget(slider)
        layout.addLayout(sliderLayout)

        self.DeltaXSlot(deltax_initial_slider_value)
        self.XSlot(x_initial_slider_value)

        # Create a placeholder widget to hold our toolbar and canvas.
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.resize(INITIAL_WIDTH, INITIAL_HEIGHT)
        self.show()

    def show_x_and_deltax(self, ax):
        x0 = self.x
        y0 = self.f(x0)
        # ax.plot([x0], [y0], color='red', marker='o')
        x1 = self.x + self.deltax
        y1 = self.f(x1)
        # ax.plot([x1], [y1], color='red', marker='o')
        ax.plot([x0, x1], [y0, y1], color='red', marker='o')

    def show_x_balanced(self, ax):
        x = self.x
        y = self.f(x)
        ax.plot([x], [y], color='blue', marker='o')
        half = self.deltax / 2.0
        x0 = x - half
        y0 = self.f(x0)
        x1 = x + half
        y1 = self.f(x1)
        ax.plot([x0, x1], [y0, y1], color='red', marker='o')

    def DeltaXSlot(self, value):
        self.deltax = self.deltax_scale * value
        if abs(self.deltax) < self.min_deltax:
            self.deltax = self.min_deltax
        self.UpdateDerivativeCanvas()
        self.UpdateMainCanvas()
        self.show()

    def UpdateDerivativeCanvas(self):
        self.derivative_canvas.Update()
        # should set a fixed width font and set width
        self.slider_value.setText(self.deltax_format % self.deltax)

    def XSlot(self, value):
        self.x = self.xbase + value * self.xscale
        self.UpdateMainCanvas()
        self.show()

    def UpdateMainCanvas(self):
        self.main_func_canvas.Update(self.show_x)
        # should set a fixed width font and set width
        self.slider_xvalue.setText(self.x_format % self.x)

def Main(argv):
    app = QtWidgets.QApplication(argv)
    w = MainWindow(math.sin, "sin(x)", -2.0 * math.pi, 2.0 * math.pi, 100)
#    w = MainWindow(lambda x: x*x, "y=x*x", -2.0 * math.pi, 2.0 * math.pi, 100)
    app.exec_()

if __name__ == '__main__':
    Main(sys.argv)
