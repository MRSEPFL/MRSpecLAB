import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, TextBox
from interface import utils

class ManualAdjustment:
    def __init__(self, data, canvas, params=None):
        self.done = False
        self.initial_data = data
        self.data = data
        # Determine x- and y-limits from the data
        self.xlim = (np.max(data[0].frequency_axis_ppm()), np.min(data[0].frequency_axis_ppm()))
        ylim = np.max(np.abs(np.real(data[0].spectrum())))
        self.ylim = (-ylim, ylim)
        self.fig: plt.Figure = canvas.figure

        self.ax = self.fig.add_subplot(1, 1, 1)
        self.ax.clear()
        # Adjust bottom margin to make room for the widgets
        self.fig.subplots_adjust(bottom=0.25)

        # ---------------------------
        # Frequency slider and text box (top)
        # ---------------------------
        freq_ax_height = 0.17
        freq_ax = self.fig.add_axes([0.1, freq_ax_height, 0.3, 0.03])
        self.freq_slider = Slider(
            ax=freq_ax,
            label='Frequency [ppm]',
            valmin=-10,
            valmax=10,
            valinit=0,
            valstep=0.01
        )
        self.freq_slider.on_changed(self.update)

        freq_text_ax = self.fig.add_axes([0.42, freq_ax_height, 0.05, 0.03])
        self.freq_text = TextBox(freq_text_ax, '', initial=str(self.freq_slider.val))
        self.freq_text.on_submit(self.on_freq_text_submit)

        # ---------------------------
        # 0th-order phase slider and text box (middle)
        # ---------------------------
        phase_ax_height = 0.12
        phase_ax = self.fig.add_axes([0.1, phase_ax_height, 0.3, 0.03])
        self.phase_slider = Slider(
            ax=phase_ax,
            label="0th-order phase [deg]",
            valmin=-180,
            valmax=180,
            valinit=0,
            valstep=1
        )
        self.phase_slider.on_changed(self.update)

        phase_text_ax = self.fig.add_axes([0.42, phase_ax_height, 0.05, 0.03])
        self.phase_text = TextBox(phase_text_ax, '', initial=str(self.phase_slider.val))
        self.phase_text.on_submit(self.on_phase_text_submit)

        # ---------------------------
        # 1st-order phase slider and text box (bottom)
        # ---------------------------
        phase1_ax_height = 0.07
        phase1_ax = self.fig.add_axes([0.1, phase1_ax_height, 0.3, 0.03])
        self.phase1_slider = Slider(
            ax=phase1_ax,
            label="1st-order phase [deg/ppm]",
            valmin=-140.00,
            valmax=140.00,
            valinit=0,
            valstep=0.01
        )
        self.phase1_slider.on_changed(self.update)

        phase1_text_ax = self.fig.add_axes([0.42, phase1_ax_height, 0.05, 0.03])
        self.phase1_text = TextBox(phase1_text_ax, '', initial=str(self.phase1_slider.val))
        self.phase1_text.on_submit(self.on_phase1_text_submit)

        # ---------------------------
        # Reset and Done buttons (unchanged)
        # ---------------------------
        reset_ax = self.fig.add_axes([0.88, 0.07, 0.1, 0.04])
        self.reset_button = Button(reset_ax, 'Reset', hovercolor='0.975')
        self.reset_button.on_clicked(self.on_reset)
        
        done_ax = self.fig.add_axes([0.88, 0.025, 0.1, 0.04])
        self.done_button = Button(done_ax, 'Done', hovercolor='0.975')
        self.done_button.on_clicked(self.on_done)

        # ---------------------------
        # Set up the main plot
        # ---------------------------
        self.ax.set_xlabel('Chemical shift (ppm)')
        self.ax.xaxis.set_label_coords(0.55, -0.1)
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
        
        # Draw initial state.
        if params is not None:
            self.freq_slider.set_val(params[0])
            self.phase_slider.set_val(params[1])
            self.phase1_slider.set_val(params[2])
        self.update(0)
        
    # --- TextBox submit callback functions ---
    def on_text_submit(self, text, slider, name):
        try: val = float(text)
        except ValueError:
            return utils.log_error(f"Invalid {name} value")
        if val < slider.valmin or val > slider.valmax:
            return utils.log_error(f"{name} value out of range")
        slider.set_val(val)
    
    def on_freq_text_submit(self, text):
        self.on_text_submit(text, self.freq_slider, "frequency")
    
    def on_phase_text_submit(self, text):
        self.on_text_submit(text, self.phase_slider, "0th-order phase")
    
    def on_phase1_text_submit(self, text):
        self.on_text_submit(text, self.phase1_slider, "1st-order phase")

    # --- Update function called when any slider is changed ---
    def update(self, val):
        self.freq_text.set_val(f"{self.freq_slider.val:.2f}")
        self.phase_text.set_val(f"{self.phase_slider.val:.1f}")
        self.phase1_text.set_val(f"{self.phase1_slider.val:.2f}")
        self.data = []
        freq = -self.freq_slider.val * self.initial_data[0].f0
        for i in range(len(self.initial_data)):
            self.data.append(
                self.initial_data[i]
                .adjust_frequency(freq)                
                .adjust_phase(self.phase_slider.val * np.pi / 180,
                              first_phase=self.phase1_slider.val * (np.pi / 180) * (1/self.initial_data[i].f0))
            )
            self.lines[i].set_ydata(np.real(self.data[i].spectrum()))
        self.fig.canvas.draw_idle()

    def on_reset(self, event):
        self.freq_slider.reset()
        self.phase_slider.reset()
        self.phase1_slider.reset()

    def on_done(self, event):
        self.done = True
    
    def run(self):
        while not self.done: plt.pause(0.1)
        return self.data, self.freq_slider.val, self.phase_slider.val, self.phase1_slider.val