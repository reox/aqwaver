from aqwaver import AQWave

with AQWave('COM5') as aq:
    print(aq.get_info())
    print("Recording Counter:", aq.get_recording_counter(), "seconds")
    print("Recording Time started:", aq.get_recording_time())
    print("Is Recording?:", aq.is_recording())

    N = 600
    data = list(aq.data(N))
    x = range(N)

    import matplotlib.pyplot as plt
    import numpy as np

    pulse, ppg, unk2, hr, spo2 = zip(*data)

    plt.figure(figsize=(16, 8))
    fig, axes = plt.subplots(nrows=5, ncols=1, sharex=True)
    axes[0].plot(x, pulse)
    axes[0].set_ylabel('Pulse')
    axes[1].plot(x, ppg)
    axes[1].set_ylabel('PPG')
    axes[2].plot(x, unk2)
    axes[2].set_ylabel('Unknown PPG')
    axes[3].plot(x, hr)
    axes[3].set_ylabel('Heart Rate [1/min]')
    axes[4].plot(x, spo2)
    axes[4].set_ylabel('SpO2 [%]')
    axes[4].set_xlabel('Packets [60*s]')
    plt.show()

    print('min', np.min(np.array(data), axis=0))
    print('max', np.max(np.array(data), axis=0))

