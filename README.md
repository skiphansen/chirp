# What is this ?

This is a fork of the __[CHIRP](https://www.chirpmyradio.com)__ repository which adds a [driver](https://github.com/skiphansen/chirp/blob/waris_py3_port/chirp/drivers/Waris.py) for the Motorola "Waris" series of radios.

The driver is useful currently (see below), but it has not be submitted to the official project since it is incomplete.

The Waris family was introduced by Motorola in 1999 and supported until June 2015.
Since these radios are no long supported and many replacement parts are no longer 
available they are primarily of interest to hams.  

As of 2025 they are still plentiful on the used market for reasonable prices.

In particular the CDM series of radios are the basis of many ham repeaters as 
well as being widely used for UHF links and have an excellent reputation.

# Why

Executive summary:  I bought a UHF range 2 CDM1550 LS+ on ebay and needed
to "hex edit" the code plug to move it in the HAM band.

A google search for "motorola waris" yielded lots of useful information on what was required.

After watching Bryan Fields's YouTube video [Motorola Waris Tuning Pier Adjustment](https://www.youtube.com/watch?v=QKpG_1buX5g)
I decided to use Chirp and the Waris.py driver to assist my Hex editing.

I immediately discovered that the driver was written when Chrip was still using
Python 2.x and that it no longer worked with recent versions of Chrip.

I don't have much experience with Python, but I decided to try to port the driver
to Python 3 rather than using a old version of Chirp.

# Status

The driver works for editing tuning data and to a limited extent channel data.

Lots of things are **NOT** supported such as zones, scan lists, channel names and 
button assignments.

All of this could be added, but additional reverse engineering of the code plug
format is required.

Since the Motorola CPS for the Waris is "out there" and runs well on a
modern system, I see little reason in expending further effort with this driver.

# New features

I've added a function to automatically modify the tuning data of UHF Range 2 
radios to cover the 440 ham band.  

When you download the tuning data from an
unmodified UHF  range 2 radio you will be asked if you want to modify it for the 
Ham band. If you click "Yes" the following edits are made:

1. The lower band limit is changed from 450 Mhz to 440 Mhz.
2. The upper band limit is changed from 520 Mhz to 510 Mhz.
3. All tuning piers, RF test channels, and data tables are moved up one slot to make room for a 440 -> 450 pier at position 0.
4. The data for the new 440 pier is extrapolated from the existing data for all data tables.
5. The conventional channel limit is set to 255 channels.

A similar function could be added to convert a low band radio to 46-54 MHz.

Please open a [**issue**](https://github.com/skiphansen/chirp/issues) if you 
have a low band radio and are willing to help add support.

**NB:** component changes are necessary to cover the entire 6m Ham band, see W9CR's [wiki](https://wiki.w9cr.net/index.php/Waris#CDM_Low_Band_Range_3_to_46-54_MHz) for more information.

# Usage

If you are already using a recent version of Chirp you can enable developer mode and manually load the Waris [driver](https://github.com/skiphansen/chirp/blob/waris_py3_port/chirp/drivers/Waris.py).

You can run also run the entire project in the usual way.

See the [CHIRP](https://www.chirpmyradio.com) website for documentation.

# Converting 450-520 Mhz to 440-510 Mhz

Executive summary:
1. Read the tuning data from radio.
2. Save the **UNMODIFIED** data as a backup.
3. Use the auto convert option to modify the stock tuning data for the ham band.
4. Save the **MODIFIED** data as a backup.
5. Write the new tuning data to the radio.

At this point you can use the Waris CPS to read the radio and then reprogram it
in the usual way.


## Step 1 - Read tuning data from radio.

From Chirp's Radio menu select Download from Radio (or hit ALT-D).

Select "Motorola" for the vendor and "Waris Tuning" for the model, click "Ok".


<img width="531" height="436" alt="image" src="https://github.com/user-attachments/assets/96fc4d77-2597-4cf8-a235-2b83801d49f4" />


## Step 2 - Save the **UNMODIFIED** data as a backup.

From Chirp's File menu select "Save as".

<img width="518" height="448" alt="image" src="https://github.com/user-attachments/assets/62f78e68-a86d-4f8d-8555-22a3d6c9b8fb" />

Change the filename to something meaningful like "factoryTuning" and click "Save".

<img width="883" height="253" alt="image" src="https://github.com/user-attachments/assets/df427d5b-b529-4f90-97f6-5bd6269accef" />


## Step 3 - Auto convert the turning data for the ham band.

Click "Setting" to view the tuning data in the settings screen.

<img width="317" height="206" alt="image" src="https://github.com/user-attachments/assets/d6962216-9474-445a-8d3d-686d7f469b28" />

Click "Yes" to convert.

<img width="538" height="357" alt="image" src="https://github.com/user-attachments/assets/79ae9404-0d06-4eea-9612-30a5370d54f2" />

You will be reminded that you should backup your **UNMODIFED** tuning data, since we have already done this just click "Ok".

<img width="614" height="369" alt="image" src="https://github.com/user-attachments/assets/738f6218-721d-4bfb-9e46-db1158b06eb3" />

Note that the DTMF signalling test frequency is now in the ham band.

<img width="633" height="306" alt="image" src="https://github.com/user-attachments/assets/7ae5bd59-dcd8-445f-a64a-c06953005048" />

The most significant change is to the front end filter's data table which will
probably increase the receiver sensitivity in the 440->450 Mhz region.

<img width="509" height="432" alt="image" src="https://github.com/user-attachments/assets/7e2402ad-f749-469b-83bd-ec3abff74c44" />

Of course if you have test equipment you should still tune the 
radio using the universal tuner software for ultimate performance.


## Step 4 - Save the **MODIFIED** data as a backup.

From Chirp's File menu select "Save as".

<img width="518" height="448" alt="image" src="https://github.com/user-attachments/assets/62f78e68-a86d-4f8d-8555-22a3d6c9b8fb" />

Change the filename to something meaningful and click "Save".


## Step 5 - Write the new tuning data to the radio.

Finally upload the modified tuning data back to the radio by selecting "Upload to radio..." from Chirp's Radio menu (or by hitting ALT-U).

<img width="425" height="305" alt="image" src="https://github.com/user-attachments/assets/07c3df38-a1dc-4296-a502-45af5f6e6a96" />

You should now be able to use an unmodified Waris CPS to program up to 255 channels in the usual way.

