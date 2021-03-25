from aqwaver import AQWave

with AQWave('COM5') as aq:
    print(aq.get_info())
    print("Recording Counter:", aq.get_recording_counter(), "seconds")
    print("Recording Time started:", aq.get_recording_time())
    #print("Is Recording?:", aq.is_recording())
    #aq.recorded_data()

    N = 60 * 60
    data = list(aq.data(N))

    import matplotlib.pyplot as plt
    import numpy as np

    x, pulse, ppg, unk2, hr, spo2 = zip(*data)
    x = np.array(x)
    x -= np.min(x)

    fig, axes = plt.subplots(nrows=5, ncols=1, sharex=True, figsize=(8, 6))
    axes[0].plot(x, pulse)
    axes[0].set_ylabel('Pulse')
    axes[0].set_yticks([])
    axes[1].plot(x, ppg)
    axes[1].set_ylabel('PPG')
    axes[1].set_yticks([])
    axes[2].plot(x, unk2)
    axes[2].set_ylabel('Other PPG')
    axes[2].set_yticks([])
    axes[3].plot(x, hr)
    axes[3].set_ylabel('Heart Rate [1/min]')
    axes[4].plot(x, spo2)
    axes[4].set_ylabel('SpO2 [%]')
    axes[4].set_xlabel('Time [s]')
    plt.show()

    print('min', np.min(np.array(data), axis=0))
    print('max', np.max(np.array(data), axis=0))
