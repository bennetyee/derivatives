# derivatives

This repository contains a PyQt5 based program to aid in visualizing
taking limits in obtaining the derivative of a function.

The program `visualize.py` puts up two graphs, one for f(x) and the
other for f'(x) over a range x0 to x1.  The function f and the range
boundaries x0 and x1 are command-line arguments.  Beneath the two
graphs are sliders, one for x and the other for Δx, where Δx is used
in the numerical derivative f'(x).

To run it, you can specify the function to be plotted using the `-f`
command line flag.  It takes a string as an argument, which is
evaluated as python code.  The default function is `math.sin`.  There
is help for the rest of the argument, so try `./visualize.py --help`
and experiment!

The `-D` flag specifies the number of derivative graphs (minium 1) to
display.  I wouldn't recommend too many if you want to be able to play
with the sliders, since it will probably be too slow.

Different functions you might try:
```
$ ./visualize.py  -f 'lambda x: x**3' -D 2
$ ./visualize.py  -f 'lambda x: math.sin(x)*math.cos(10*x)'
```
