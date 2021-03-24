from aqwaver import AQWave

with AQWave('COM7') as aq:
    print(aq.get_info())
    print("Recording Counter:", aq.get_recording_counter())
    print("Recording Time:", aq.get_recording_time())

