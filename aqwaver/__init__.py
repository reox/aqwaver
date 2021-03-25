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
import serial
import math
from typing import Union, List, Tuple
from collections import namedtuple

import warnings

import datetime
import time

_info = namedtuple('DeviceInfo', ['device', 'product', 'manufacturer', 'id_1', 'id_2'])
_data = namedtuple('Data', ['time', 'pulse', 'ppg', 'ppg_alt', 'hr', 'spo2'])


class AQWaveException(Exception):
    pass


class AQWave:
    # All known commands
    CMD_START = 0xa1
    CMD_STOP = 0xa2
    CMD_RECORDING_INFO = 0xa4
    CMD_RECORDING_SETTINGS = 0xa5
    CMD_RECORDING_DATA = 0xa6
    CMD_ABORT_SEND_DATA = 0xa7
    CMD_INFO_DEVICE = 0xa8
    CMD_INFO_MANUFACTURER = 0xa9
    CMD_INFO_USER_1 = 0xaa
    CMD_INFO_USER_2 = 0xab
    CMD_KEEP_ALIVE = 0xaf

    TYPE_DATA = 0x01
    TYPE_INFO_DEVICE = 0x02
    TYPE_INFO_MANUFACTURER = 0x03
    TYPE_INFO_USER_1 = 0x04
    TYPE_INFO_USER_2 = 0x05
    TYPE_RECORDING_SETTINGS_1 = 0x07  # first package, seems to contain nothing...
    TYPE_RECORDING_INFO = 0x08
    TYPE_UNKNOWN = 0x0b  # just a guess that this codes for "unknown command"
    TYPE_OK = 0x0c  #  guessed that this codes for "OK"
    TYPE_RECORDING_DATA = 0x0f
    TYPE_RECORDING_SETTINGS_2 = 0x12  # Contains the time setting when the recording started

    def __init__(self, port: str):
        """
        AQWave is a class handling ReFleX AQWave RX101

        The serial interface can both work with the USB to Serial cable
        and also using the Bluetooth interface.

        The USB-Serial converter is a CP210x.
        The Bluetooth name of the device is SpO2 and the pairing key is 7762.

        On my machine, I see two serial ports on the Bluetooth device,
        however only one works.

        Internally, the TX & RX lines are wired to the Bluetooth transmitter.
        If Bluetooth is switched on, the USB-Serial converter can not be used.

        :param port: serial port
        """
        self.port = port

        self.timeout = 2

        self.__serial = serial.Serial(port,
                                      baudrate=115200,
                                      parity=serial.PARITY_NONE,
                                      bytesize=8,
                                      stopbits=1,
                                      timeout=self.timeout,  # As in PPGserial.cs
                                      write_timeout=self.timeout,  # As in PPGserial.cs
                                      )

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        """Open the device and check if the connection is good"""
        if self.__serial.is_open:
            return
        self.__serial.open()
        self.__serial.reset_input_buffer()

    def close(self):
        self.__serial.close()

    def read(self, size=None, *args, **kwargs):
        """Read from the serial line"""
        return self.__serial.read(size, *args, **kwargs)

    def get_info(self) -> _info:
        """Query all the device info"""
        device, product = self._read_string(self.CMD_INFO_DEVICE, self.TYPE_INFO_DEVICE, packets=2)
        manufacturer = self._read_string(self.CMD_INFO_MANUFACTURER, self.TYPE_INFO_MANUFACTURER)
        user_1 = self._read_string(self.CMD_INFO_USER_1, self.TYPE_INFO_USER_1)
        user_2 = self._read_string(self.CMD_INFO_USER_2, self.TYPE_INFO_USER_2)
        return _info(device, product, manufacturer, user_1, user_2)

    def get_recording_counter(self):
        """Returns the number of recorded tuples (SpO2 + HR) which is equal to seconds of recording"""
        self._send_command(self.CMD_RECORDING_INFO)
        type_, data = self._decode(self.__serial.read(8))
        if type_ != self.TYPE_RECORDING_INFO:
            raise AQWaveException("Wrong Response type for recording counter")
        # The field contains the number of individual values
        # as we have two values (SpO2 and HR) we need to divide by two...
        # We are actually not sure if this is actually an uint32, however there should be
        # a maximum of 24*60*60*2=172800 (i.e. a full day of recording) which would need 18 bits
        # to store.
        # TODO: actually test if the device will say "out of memory" after 24h of recording
        return (data[2] | data[3] << 8 | data[4] << 16 | data[5] << 24) >> 1

    def get_recording_time(self):
        """Returns the currently set time for recording"""
        self._send_command(self.CMD_RECORDING_SETTINGS)
        type_, _ = self._decode(self.__serial.read(8))  # The first package does not contain anything?
        # The data of the first package seems to be all zero.
        # However, we still check the type to be sure we read the correct thing
        if type_ != self.TYPE_RECORDING_SETTINGS_1:
            raise AQWaveException("First package of recording settings has wrong type!")
        type_, data = self._decode(self.__serial.read(8))
        if type_ != self.TYPE_RECORDING_SETTINGS_2:
            raise AQWaveException("Second package of recording settings has wrong type!")
        # data[2] ... hours
        # data[3] ... minutes
        return datetime.time(hour=data[2], minute=data[3])

    def is_recording(self) -> bool:
        """Checks if the device is currently recording
        This call takes up to timeout seconds, because there might be an unexpected amount of data
        """
        self._send_command(self.CMD_RECORDING_DATA)
        # Just read the first four bytes and discard the rest of the buffer
        type_, _ = self._decode(self.__serial.read(4))
        self._send_command(self.CMD_ABORT_SEND_DATA)
        # We can not make sure that the CMD_ABORT_SEND_DATA succeeded...
        # eventually we would read the OK package, but we do not know how many packages the device
        # will send in the mean time.
        # Thus, we simply reset the buffer and hope that the device has got the request
        # FIXME: Not sure why we have to read something here... Should reset_input_buffer not do the same?
        self.__serial.read(64)  # Do not expect more than 64 junk bytes... In our tests we usually had 14 or 22
        self.__serial.reset_input_buffer()
        # The recording_data command returns unknown type if in recording
        return type_ == self.TYPE_UNKNOWN

    def recorded_data(self):
        """Returns all recorded data

        This might take a while and will block the device during reading.

        .. warning::
            If you download a full day of recording (86400s), then the download
            will take about 25s!

        Returns the list of heart-rate and SpO2 readings.
        """
        values = self.get_recording_counter()
        packages = math.ceil(values / 3)  # Each package contains up to three tuples of values
        hr = []
        sp = []
        self._send_command(self.CMD_RECORDING_DATA)
        # NOTE: This really blocks the device! You can not even press buttons in that time!!!
        # Measured time for a full day of recording (86400 tuples = 28800 packages = 230400 bytes)
        # was about 25s. Thus we set the timeout here to 30s.
        self.__serial.timeout = 30
        raw_data = self.__serial.read(8 * packages)
        self.__serial.timeout = self.timeout
        for i in range(packages):
            type_, data = self._decode(raw_data[i*8:(i+1)*8])
            if type_ != self.TYPE_RECORDING_DATA:
                raise AQWaveException(f"Recorded Data package has wrong type: {type_}")
            hr.extend([data[1], data[3], data[5]])
            sp.extend([data[0], data[2], data[4]])
        # There might be 1 to 2 junk elements at the end
        return hr[:values], sp[:values]

    def data(self, n) -> _data:
        """Yield data from the device

        The tuple is: (time, pulse, ppg_value, smooth_ppg_value, heart_rate, sp02)
        The time is the current PC time, when the package was received.

        pulse gives a signal if a heartbeat is detected.
        The signal will be around 64 if a heartbeat is detected,
        128 if no finger is detected and 0 if there is no beat.
        Because we are not sure what the actual value is, the following check
        should probably work: x < 32 --> no beat, x <= 32 <= 96 --> beat, x > 96 --> finger out

        There are two PPG values, where the first one has a higher magnitude
        than the second.

        Data is send by the device about every 1/60s, i.e. 60 times per second.

        ppg_value is [0, 255] (maybe the value is actually always between 0 and 128?)
        other_ppg_value is [0, 255] (maybe this is always 0 to 32?)
        heart_rate is [0, 255]
        sp02 is [0, 255] (actually only [0, 100])

        The original source code only uses the items 1, 3, 4 from the data array
        """
        try:
            self._send_command(self.CMD_START)
            i = 1
            while i <= n:
                type_, data = self._decode(self.__serial.read(9))
                if type_ != self.TYPE_DATA:
                    raise AQWaveException(f"Returned Datatype was not DATA but {type_}")
                #                       Value if no finger present
                # 0 ... Pulse Signal    128
                # 1 ... PPG             64
                # 2 ... Another PPG     21
                # 3 ... Heart Rate      0
                # 4 ... SpO2            0
                # data[5] and data[6] are always (?) 255
                yield _data(time.time(), *data[:5])

                if i % 60 == 0:
                    # While a single start command usually sends around 1700 packages,
                    # the original software sends a Keepalive every 60 packets,
                    # i.e. every second
                    self._send_command(self.CMD_KEEP_ALIVE)
                    # Command does not return anything
                i += 1
        except StopIteration:
            pass
        finally:
            self._send_command(self.CMD_STOP)
            type_, _ = self._decode(self.__serial.read(2))
            if type_ != self.TYPE_OK:
                warnings.warn(f"Data stream was stopped but return type was not OK but {type_}")
            return

    def _send_command(self, command):
        """Send a command to the device"""
        # While the original software uses 9 byte long commands, where all the
        # trailing bytes are zero (0x80), we can also simply send a three byte long command
        self.__serial.write(bytearray([0x7d, 0x81, command]))

    def _read_string(self, cmd, expect, length=9, packets=1):
        """Read String commands and drops zero bytes"""
        self._send_command(cmd)
        res = []
        for _ in range(packets):
            type_, data = self._decode(self.__serial.read(length))
            if type_ != expect:
                raise AQWaveException(f"Command {cmd:02x} yielded no type {expect:02x} package!")
            res.append(''.join([chr(x) for x in data if x != 0]))
        return res[0] if packets == 1 else res

    def _decode(self, package: Union[bytearray, bytes]) -> Tuple[int, List[int]]:
        """
        Decode a package

        The package format is:

            | 00 | 01 | 02 | 03 | 04 | 05 | 06 | 07 | 08 |
            +----+----+----+----+----+----+----+----+----+
            |type|sign| d0   d1   d2   d3   d4   d5   d6 |
            +----+----+----+----+----+----+----+----+----+

        That means, there are 7 byte of data in the package
        The flag controls if each byte of the data array is signed or unsigned.
        If the i-th bit in the sign flag is one, the i-th data entry is unsigned.
        Otherwise, you have to subtract 128 from it to get a signed integer.

        In all instances we have recorded, the sign bit has always MSB==1.
        While in theory a package can be 10 bytes long, most packages are only 8 or 9 bytes.
        My theory is, that the sign bit has only 7 "useable" bits, because they set MSB to one.
        Therefore, the packages only have 7 payload bytes...

        Note, that some packages only have 8 bytes or even less.
        The error packages are usually 4 bytes in length.
        """
        assert 2 <= len(package) <= 9
        package = bytearray(package)
        type_ = package.pop(0)
        sign_ = package.pop(0)
        res = []
        for i, b in enumerate(package):
            if (sign_ & (1 << i)) == 0:
                b -= 128
            res.append(b)

        return type_, res
