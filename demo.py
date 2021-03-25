"""
Python Library to get data from ReFleX Wireless AQWave RX101 PPG Recorder

Copyright (C) 2021 Sebastian Bachmann

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from aqwaver import AQWave

with AQWave('COM5') as aq:
    print(aq.get_info())
    print("Recording Counter:", aq.get_recording_counter(), "seconds")
    print("Recording Time started:", aq.get_recording_time())
    #print("Is Recording?:", aq.is_recording())
    #aq.recorded_data()

    N = 60 * 30
    data = list(aq.data(N))

    import matplotlib.pyplot as plt
    import numpy as np

    x, ppg, hr, spo2, finger_out, pulse, bar, searching = zip(*data)
    x = np.array(x)
    x -= np.min(x)

    fig, axes = plt.subplots(nrows=4, ncols=1, sharex=True, figsize=(8, 6))
    axes[0].plot(x, pulse, label='Pulse')
    axes[0].plot(x, finger_out, label='Finger Out')
    axes[0].plot(x, searching, label='Searching')
    axes[0].legend()
    axes[0].set_ylabel('Flags')
    axes[0].set_yticks([])
    axes[1].plot(x, ppg)
    axes[1].set_ylabel('PPG')
    axes[1].set_yticks([])
    axes[2].plot(x, hr)
    axes[2].set_ylabel('Heart Rate [1/min]')
    axes[3].plot(x, spo2)
    axes[3].set_ylabel('SpO2 [%]')
    axes[3].set_xlabel('Time [s]')
    plt.show()

    print('min', np.min(np.array(data), axis=0))
    print('max', np.max(np.array(data), axis=0))
