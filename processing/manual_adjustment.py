import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

class ManualAdjustment:
    def __init__(self, data, canvas):
        self.done = False
        self.initial_data = data
        self.data = data
        self.xlim = (np.max(data[0].frequency_axis_ppm()), np.min(data[0].frequency_axis_ppm()))
        ylim = np.max(np.abs(np.real(data[0].spectrum())))
        self.ylim = (-ylim, ylim)
        self.fig = canvas.figure

        self.ax = self.fig.add_subplot(1, 1, 1)
        self.ax.clear()
        self.fig.subplots_adjust(bottom=0.3)

        freq_ax = self.fig.add_axes([0.1, 0.05, 0.3, 0.03])
        self.freq_slider = Slider(
            ax=freq_ax,
            label='Frequency [ppm]',
            valmin=-10,
            valmax=10,
            valinit=0,
            valstep=0.01
        )
        self.freq_slider.on_changed(self.update)

        phase_ax = self.fig.add_axes([0.55, 0.05, 0.3, 0.03])
        self.phase_slider = Slider(
            ax=phase_ax,
            label="0th-order phase [deg]",
            valmin=-180,
            valmax=180,
            valinit=0,
            valstep=1
        )
        self.phase_slider.on_changed(self.update)

        phase1_ax = self.fig.add_axes([0.55, 0.1, 0.3, 0.03])
        self.phase1_slider = Slider(
            ax=phase1_ax,
            label="1st-order phase [rad]",
            valmin=-0.02,
            valmax=0.02,
            valinit=0,
        )
        self.phase1_slider.on_changed(self.update)

        reset_ax = self.fig.add_axes([0.88, 0.07, 0.1, 0.04])
        self.reset_button = Button(reset_ax, 'Reset', hovercolor='0.975')
        self.reset_button.on_clicked(self.on_reset)
        done_ax = self.fig.add_axes([0.88, 0.025, 0.1, 0.04])
        self.done_button = Button(done_ax, 'Done', hovercolor='0.975')
        self.done_button.on_clicked(self.on_done)

        self.ax.set_xlabel('Chemical shift (ppm)')
        self.ax.set_ylabel('Amplitude')
        self.ax.grid(which='major', linestyle='-', linewidth='0.5', color='black')
        self.ax.grid(which='minor', linestyle=':', linewidth='0.5', color='gray')
        self.ax.minorticks_on()
        self.ax.tick_params(axis='x', which='both', bottom=True, top=False, direction='inout')
        self.ax.tick_params(axis='y', which='both', left=True, right=False, direction='inout')
        self.fig.suptitle("Adjust frequency and phase shifts")
        self.ax.set_xlim(self.xlim)
        self.ax.set_ylim(self.ylim)
        
        self.lines = []
        for i in range(len(data)):
            self.lines.append(self.ax.plot(data[i].frequency_axis_ppm(), np.real(data[i].spectrum()))[0])
        self.fig.canvas.draw_idle()
        
    def update(self, val):
        self.data = []
        freq = self.initial_data[0].ppm_to_hertz(self.freq_slider.val)
        for i in range(len(self.initial_data)):
            self.data.append(self.initial_data[i].adjust_frequency(freq).adjust_phase(self.phase_slider.val*np.pi/180, first_phase=self.phase1_slider.val))
            self.lines[i].set_ydata(np.real(self.data[i].spectrum()))
        self.fig.canvas.draw_idle()

    def on_reset(self, event):
        self.freq_slider.reset()
        self.phase_slider.reset()
        self.phase1_slider.reset()

    def on_done(self, event):
        self.done = True
    
    def run(self):
        while not self.done:
            plt.pause(0.1)
        return self.data