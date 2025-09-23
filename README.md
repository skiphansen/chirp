# What is this ?

This fork of the __[CHIRP](https://www.chirpmyradio.com)__ repository contains a [driver](https://github.com/skiphansen/chirp/blob/waris_py3_port/chirp/drivers/Waris.py) for the Motorola "Waris" series of radios.

The driver is useful currently (see below), but it has not be submitted to the official project since it is incomplete.

# Why

Executive summary:  I bought a UHF range 2 CDM1550 LS+ on ebay and needed
to "hex edit" the code plug to move it in the HAM band.

The Waris family was introduced in 1999 and was manufactured for a number of years.
They are very plentiful on the used market for reasonable prices.

In particular the CDM series of radios are the basis of many repeaters as well as being widely used for UHF links and they have an excellent reputation.

A google search for "motorola waris" yielded lots of useful information on what was required.

After watching Bryan Fields's YouTube video [Motorola Waris Tuning Pier Adjustment](https://www.youtube.com/watch?v=QKpG_1buX5g)
I decided to use Chirp and the Waris.py driver to assist my Hex editing.

I immediately discovered that the driver was written when Chrip was still using
Python 2.x and that it no longer worked with the recent versions of Chrip.

I don't have much experience with Python, but I decided to try to port the driver
to Python 3 rather than using a old version of Chirp.

# Status

The driver works for editing tuning data and to a limited extent channel data.

Lots of things are NOT supported such as zones, scan lists, channel names and 
button assignments.

All of this could be added, but additional reverse engineering of the code plug
format is required.

Since the Motorola CPS for the Waris is "out there" and runs well on a
modern system (Windows 10 VM running under Windows 11), I see little reason
in expending further effort with this driver.

# Usage

If you are already using a recent version of Chirp you can enable deverloper mode and manually load the Waris [driver](https://github.com/skiphansen/chirp/blob/waris_py3_port/chirp/drivers/Waris.py).

You can run also run the entire project in the usual way.

See the [CHIRP](https://www.chirpmyradio.com) website for documentation.

# Converting 450-520 Mhz to 440-510 Mhz

I've added an auto convert function to the driver.  When you download the tuning
data from a UHF range 2 radio you will be offered with choice to automatically 
modify it for the Ham band.

<img width="587" height="437" alt="image" src="https://github.com/user-attachments/assets/b686bea8-9052-463b-9c73-86e15beb8a76" />

By clicking "Yes" the following edits are made:

1. All tuning piers, RF test channels, and data tables are moved up one slot to make room for a 440 -> 450 pier at position 0.
2. The data for the new 440 pier is extrapolated from the existing data for all data tables.
3. The conventional channel limit is set to 255 channels.

The most significant change is to the front end filter's data table which will
probably increase the receiver sensitivity in the 440->450 Mhz region.

<img width="592" height="369" alt="image" src="https://github.com/user-attachments/assets/1457424f-67c5-443e-b556-ee624d2194f0" />

Of course if you have the appropriate test equipment you should tune the 
radio using the universal tuner software for ultimate performance.

# Converting 42-50 Mhz to 46-54 MHz

Not supported currently, but easy to add.

Please open a [**issue**](https://github.com/skiphansen/chirp/issues) if you have a low band radio and are willing to help add support.

**NB:** component changes are necessary to cover the entire 6m Ham band, see W9CR's [wiki](https://wiki.w9cr.net/index.php/Waris#CDM_Low_Band_Range_3_to_46-54_MHz) for more information.

