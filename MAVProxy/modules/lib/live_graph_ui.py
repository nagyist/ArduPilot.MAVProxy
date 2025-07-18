from MAVProxy.modules.lib.wx_loader import wx
from MAVProxy.modules.lib import icon
import time
import numpy, pylab

class GraphFrame(wx.Frame):
    """ The main frame of the application
    """

    def __init__(self, state):
        wx.Frame.__init__(self, None, -1, state.title)
        try:
            self.SetIcon(icon.SimpleIcon().get_ico())
        except Exception:
            pass
        self.state = state
        self.data = []
        for i in range(len(state.fields)):
            self.data.append([])
        self.paused = False
        self.clear_data = False

        self.create_main_panel()

        self.Bind(wx.EVT_IDLE, self.on_idle)

        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)
        self.redraw_timer.Start(int(1000*self.state.tickresolution))

        self.last_yrange = (None, None)

    def create_main_panel(self):
        import platform
        if platform.system() == 'Darwin':
            from MAVProxy.modules.lib.MacOS import backend_wxagg
            FigCanvas = backend_wxagg.FigureCanvasWxAgg
        else:
            from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigCanvas
        self.panel = wx.Panel(self)

        self.init_plot()
        self.canvas = FigCanvas(self.panel, -1, self.fig)


        self.close_button = wx.Button(self.panel, -1, "Close")
        self.Bind(wx.EVT_BUTTON, self.on_close_button, self.close_button)

        self.pause_button = wx.Button(self.panel, -1, "Pause")
        self.Bind(wx.EVT_BUTTON, self.on_pause_button, self.pause_button)
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_pause_button, self.pause_button)

        self.clear_button = wx.Button(self.panel, -1, "Clear")
        self.Bind(wx.EVT_BUTTON, self.on_clear_button, self.clear_button)
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_clear_button, self.clear_button)

        did_one = False
        self.hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        for button in self.close_button, self.pause_button, self.clear_button:
            if did_one:
                self.hbox1.Add(self.close_button, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
                self.hbox1.AddSpacer(1)
                did_one = True
            self.hbox1.Add(button, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, flag=wx.LEFT | wx.TOP | wx.GROW)
        self.vbox.Add(self.hbox1, 0, flag=wx.ALIGN_LEFT | wx.TOP)

        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)

    def init_plot(self):
        self.dpi = 100
        from matplotlib.figure import Figure
        self.fig = Figure((6.0, 3.0), dpi=self.dpi)

        self.axes = self.fig.add_subplot(111)
        try:
            self.axes.set_facecolor('white')
        except AttributeError as e:
            # this was removed in matplotlib 2.2.0:
            self.axes.set_axis_bgcolor('white')

        pylab.setp(self.axes.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference
        # to the plotted line series
        #
        self.plot_data = []
        if len(self.data[0]) == 0:
            max_y = min_y = 0
        else:
            max_y = min_y = self.data[0][0]
        num_labels = 0 if not self.state.labels else len(self.state.labels)
        labels = []
        for i in range(len(self.data)):
            if i < num_labels and self.state.labels[i] is not None:
                label = self.state.labels[i]
            else:
                label = self.state.fields[i]
            labels.append(label)
            p = self.axes.plot(
                self.data[i],
                linewidth=1,
                color=self.state.colors[i],
                label=label
                )[0]
            self.plot_data.append(p)
            if len(self.data[i]) != 0:
                min_y = min(min_y, min(self.data[i]))
                max_y = max(max_y, max(self.data[i]))

        # create X data
        self.xdata = numpy.arange(-self.state.timespan, 0, self.state.tickresolution)
        self.axes.set_xbound(lower=self.xdata[0], upper=0)
        if min_y == max_y:
            self.axes.set_ybound(min_y, max_y+0.1)
        self.axes.legend(labels, loc='upper left', bbox_to_anchor=(0, 1.1))

    def draw_plot(self):
        """ Redraws the plot
        """
        state = self.state

        if len(self.data[0]) == 0:
            print("no data to plot")
            return
        vhigh = max(self.data[0])
        vlow  = min(self.data[0])

        for i in range(1,len(self.plot_data)):
            vhigh = max(vhigh, max(self.data[i]))
            vlow  = min(vlow,  min(self.data[i]))
        ymin = vlow  - 0.05*(vhigh-vlow)
        ymax = vhigh + 0.05*(vhigh-vlow)

        if ymin == ymax:
            ymax = ymin + 0.1 * ymin
            ymin = ymin - 0.1 * ymin

        if (ymin, ymax) != self.last_yrange:
            self.last_yrange = (ymin, ymax)

            if ymax == ymin:
                ymin = ymin-0.5
                ymax = ymin+1

            self.axes.set_ybound(lower=ymin, upper=ymax)
            #self.axes.ticklabel_format(useOffset=False, style='plain')
            self.axes.grid(True, color='gray')
            pylab.setp(self.axes.get_xticklabels(), visible=True)
            pylab.setp(self.axes.get_legend().get_texts(), fontsize='small')

        for i in range(len(self.plot_data)):
            ydata = numpy.array(self.data[i])
            xdata = self.xdata
            if len(ydata) < len(self.xdata):
                xdata = xdata[-len(ydata):]
            self.plot_data[i].set_xdata(xdata)
            self.plot_data[i].set_ydata(ydata)

        self.canvas.draw()
        self.canvas.Refresh()

    def on_pause_button(self, event):
        self.paused = not self.paused

    def on_update_pause_button(self, event):
        label = "Resume" if self.paused else "Pause"
        self.pause_button.SetLabel(label)

    def on_update_clear_button(self, event):
        pass

    def on_clear_button(self, event):
        self.clear_data = True

    def on_close_button(self, event):
        self.redraw_timer.Stop()
        self.Destroy()

    def on_idle(self, event):
        time.sleep(self.state.tickresolution*0.5)

    def on_redraw_timer(self, event):
        # if paused do not add data, but still redraw the plot
        # (to respond to scale modifications, grid change, etc.)
        #
        state = self.state
        if state.close_graph.wait(0.001):
            self.redraw_timer.Stop()
            self.Destroy()
            return
        while state.child_pipe.poll():
            state.values = state.child_pipe.recv()
        if self.paused:
            return

        if self.clear_data:
            self.clear_data = False
            for i in range(len(self.plot_data)):
                if state.values[i] is not None:
                    while len(self.data[i]):
                        self.data[i].pop(0)

        for i in range(len(self.plot_data)):
            if (type(state.values[i]) == list):
                print("ERROR: Cannot plot array of length %d. Use 'graph %s[index]' instead"%(len(state.values[i]), state.fields[i]))
                self.redraw_timer.Stop()
                self.Destroy()
                return
            if state.values[i] is not None:
                self.data[i].append(state.values[i])
                while len(self.data[i]) > len(self.xdata):
                    self.data[i].pop(0)

        for i in range(len(self.plot_data)):
            if state.values[i] is None or len(self.data[i]) < 2:
                return
        self.draw_plot()
