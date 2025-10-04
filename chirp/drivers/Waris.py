
# special thanks to Yoz Ftseusj
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License Version 3, 
#    as published by the Free Software Foundation.
#
#   This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# --------------------------- Revision History ----------------------------------
# 2020-06-08    DH      Added FPP support
# 2020-10-20    DH      Added control head support 
# 2021-04-02    DH      Added this header

import io
import struct
from time import sleep

from chirp import bitwise, chirp_common, directory, errors, memmap, bandplan
#from chirp.ui import bandplans, config
from chirp.wxui import config
from chirp.util import hexprint
from chirp.settings import RadioSetting, RadioSettings, RadioSettingGroup, \
                RadioSettingValueBoolean, RadioSettingValueList, \
                RadioSettingValueInteger, RadioSettingValueString, \
                RadioSettingValueFloat, RadioSettingValueMap, InvalidValueError
from inspect import currentframe, getframeinfo
import wx


TUNING_FORMAT = """
// Tuning block
#seekto %d;
#seekto 0x19;
u8 vcoattn25[7];
#seek 2;
u8 modbalattn[7];
u8 kvalues[7];
u8 mvalues[7];
u8 unknownvalues[7];
u8 powerlevels[3];
#seekto 0x47;
u8 mdc1200level;
u8 dtmflevel;
#seekto 0x4c;
u8 targetvoltage;
u8 frontendfilter[7];
u8 squelch12[7];
u8 squelch20[7];
u8 squelch25[7];
#seek 7;
u8 ratedvolume;
u8 rssi;
#seekto 0x139;
u16 rxpier[7];
u16 txpier[7];
#seekto %d;
u16 testfreq[14];

#seekto 0x27f;
u8 tuningcs;

// Feature blocks
#seekto %d;

// Feature block 1
#seekto %d;
char serial[10];
u16  zeros1;
char model[16];
u16  zeros2;
bbcd cpversion[2];
u8   cpsource;
bbcd cpdate[6];
u8   channel_step;
u16  base_freq;
u16  lower_limit;
u16  upper_limit;
char firmware_pn[16];
u8   unknown2[2];
char tanapa[10];
u8   zeros3[7];
u8   region;
u8   fdb1cs;

// Feature block 2
#seekto %d;
u8 trunking;
u8 trunking_signaling3:1,
   trunking_signaling2:1,
   trunking_signaling1:1,
   trunking_signaling0:1,
   conventional_signaling3:1,
   conventional_signaling2:1,
   conventional_signaling1:1,
   conventional_signaling0:1;
u8 control_head;
u8 unknown[3];
u8 FPP;
u8 conventional;
#seek 1;
u8 fdb2cs;

#seekto 0x2ff;
u8 fdbcs;
"""
PROGRAMMING_HEADER_FORMAT = """
// Programming block
#seekto 0x300;
u16 always0x0400;
u16 programming_length;     // add 0x300 to find final checksum address
u16 unknown_addr;           // last section's cs is immediately before this
u16 section_map_addr;
#seekto 0x280;
#seekto 0x400;
#seekto 0x500;
#seekto 0x450;
"""
CODEPLUG_VERSION_AND_DATE = """
u8 majorversion;
u8 minorversion;
u8 source;
bbcd date[6];
"""
HT1250_SETTINGS = """
struct {
    u8 tx_inhibit_quick_key_override:1,
       unknown1:7;
    u8 unknown2a:1,
       monitor_type:1,          // ('Open Squelch', 'Silent')
       unknown2b:1,
       sticky_permanent_monitor_alert:1,
       unknown2c:2,
       keypad:2;    // ('?', 'Programmable-Menu', 'Programmable-Menu/Numeric')
    u8 power_up_tone:2,         // ('Disabled', 'Normal', 'Musical')
       unknown_basica:2,
       hot_keypad:1,
       radio_to_radio_cloning:1,
       vox_headset:1,
       unknown_basicb:1;
    u8 busy_led:1,
       tx_low_battery_led:1
       power_up_test_led:1,
       auto_backlight:1,
       recall_last_selected_menu:1,
       tx_low_battery_alert:1,
       auto_power_mode:1,
       radio_clock_update:1;
    u8 unknown_settingsa[2];
    u8 unknown_settingsxa:2,
       optionboard:3,           // (None, Simple Decoder, Simple Option Interface, Advanced Option Interface, Voice Storage, Advanced & Voice Storage)
       unknown_settingsxb:3;    // not sure, seems to invert with optionboard setting
    u8 unknown_basice:2,
       long_press_duration:6;   // n * 500ms
    u8 unknown_settingsaa[3];
    u8 wrap_around_alert:1,
       unknown_basicc:1,
       audio_processing_filter:1,
       scan_hang_time:5;        // n * 250ms
    u8 unknown_settingsba:6,
       scan_alerts_priority_scan:1,
       unknown_settingsbb:1;
    i8 alert_tone_volume_offset;
    u8 unknown_settingsc[5];
    u8 unknown_settingsda:1,
       enable_flat_tx_audio:1,
       unknown_settingsdb:1,
       menu_timeout:5;          // seconds
    u8 unknown_settingse[8];
    u8 mic_gain;                // 1-31 * 1.5 = dB
    u8 acc_mic_gain;            // 1-31 * 1.5 = dB
    u8 scan_selected_channel_lock:1,
       unknown_settingsf:7;
    u8 scan_priority_channel_1_lock:1,
       unknown_settingsg:7;
    u8 unknown_settingsh[2];
    u8 home_revert_1_zone;      // FF to disable
    u8 home_revert_1_channel;
    u8 unknown_settingsi;
    u8 unknown_settingsj:6,
       cps_password_enable:1,
       unknown_settingsk:1;
    char cps_password[7];       // won't exist if CPS pass has never been set
    u8 home_revert_2_zone;      // FF to disable
    u8 home_revert_2_channel;
    u8 unknown_settingshl[3];
} radio_configuration;
"""
ZONE_MEMBERS = """
struct {
  u8 num_zone_members;
  struct {
    u8 unknown;  // always 0x01?
    u8 personality;
  } zonemembers[num_zone_members];
} zones[zone_count];
"""
ZONE_NAMES = """
u8 zonenamelen;
struct {
  char name[14];
} zonenames[255];
"""
HT1250_SETTINGS2 = """
struct {
  u8 unknown0:6,
     disable_alerts:2; // ('None', 'Lights/LEDs', 'Tones', 'Lights/LEDs/Tones')
  u8 unknown1[3];
  u8 escalating_alerts:1,
     unknown2a:1,
     alert_tone_fixed_volume:1,
     unknown2b:5;
  u8 unknown3;
  u8 unknown4a:2,
     language:2,  // ('English', 'Spanish', 'Portuguese', 'French-Canadian')
     unknown4b:4;
  u16 radiopassword_enable:2,
      radiopassword:14; // 0000-9999
  //u8 unknown5[7];
} settings2;
"""
SCAN_LIST_MEMBERS = """
u8 scanlistlength;
struct {
  struct {
    u8 type;      // 0 is empty, 1 is conventional personality, 7 is <selected>
    u8 personality;
  } scanlistmember[16];
  u8 checksum;
} scanlist[16];
"""
CHANNELS = """
struct {
  u8 txstep:2,
     txunknown:2,
     rxstep:2,
     rxunknown:2;
  u16 txfreq;
  u16 rxfreq;
  u8 preemphasis:1,
     deemphasis:1,
     unknown1:1,
     optionboard:1,
     txwidth:2,
     rxwidth:2;
  u16 txtone;
  u16 rxtone;
  u8 rxtonemode:2,  // ('CSQ', 'TPL', 'DPL')
     txtonemode:2,  // ('CSQ', 'TPL', 'DPL')
     txdplinvert:1,
     rxdplinvert:1,
     unknown2a:1,
     bcl:1;
  u8 unknown3a:1,
     autoscan:1,
     talkaround:1,
     rxonly:1,
     dplturnoff:1,
     squelchtight:1,
     unknown3c:2;
  u8 nonstandardreverseburst:1,
     vox:1,
     unknown4a:3,
     tot:3;         // ('Infinite', 15, 30, 25, 60, 90, 120, 180)
  u8 compression:2, // ('Disabled', 'Full Compression', 'AGC mode')
     expansion:3,   // ('Disabled', 'Full Compression', 'AGC mode', 'Low-level Expansion')
     unknown5:1,    // related to simplex/talkaround?
     power:2;       // ('Low', 'High', 'Auto')
  u8 signalrx_unknown1:4,
     signaltx_unknown1:4;
  u8 signalrx_unknown2;
  u8 signaltx_unknown2;
  u8 phonesystem;
  u8 scanlist;
  u8 unknown7[5];
  u8 checksum;
} personality[255];
"""
BUTTON_ASSIGNMENTS = """
struct {
    u8 rotary_control;
    u8 top_button_short;  // weird index doesn't match CPS list
    u8 top_button_long;   // weird index doesn't match CPS list
    u8 side_button_1_upper_short;
    u8 side_button_1_upper_long;
    u8 side_button_2_middle_short;
    u8 side_button_2_middle_long;
    u8 side_button_3_lower_short;
    u8 side_button_3_lower_long;
    u8 front_button_p1_short;
    u8 front_button_p1_long;
    u8 front_button_p2_short;
    u8 front_button_p2_long;
    u8 front_button_p3_short;
    u8 front_button_p3_long;
} button_assignments;
"""
CHANNEL_NAMES = """
u8 personalitynamelen;
struct {
  char name[14];
} personalitynames[255];
"""
TRUNKING_BUTTON_ASSIGNMENTS = """
struct {
    u8 rotary_control;
    u8 top_button_short;  // weird index doesn't match CPS list
    u8 top_button_long;   // weird index doesn't match CPS list
    u8 side_button_1_upper_short;
    u8 side_button_1_upper_long;
    u8 side_button_2_middle_short;
    u8 side_button_2_middle_long;
    u8 side_button_3_lower_short;
    u8 side_button_3_lower_long;
    u8 front_button_p1_short;
    u8 front_button_p1_long;
    u8 front_button_p2_short;
    u8 front_button_p2_long;
    u8 front_button_p3_short;
    u8 front_button_p3_long;
} trunking_button_assignments;
"""
MAP = """
#seekto %d;
u16 section_map_length;
struct {
    // these are pointers to feature sections. #seekto their values.
    u16 fdb1;                           // 0
    u16 fdb2;                           // 1
    u16 fdb_unknown[6];                 // 2,3,4,5,6,7
    u16 codeplug_version_and_date;      // 8
    u16 settings;                       // 9
    u16 personality_assignment_to_zone; // 10
    u16 zone_names;                     // 11
    u16 settings2;                      // 12
    u16 phone_numbers;                  // 13
    u16 phone_names;                    // 14
    u16 unknown1;                       // 15
    u16 scan_list_members;              // 16
    u16 unknown2[2];                    // 17,18
    u16 mdc_call;                       // 19
    u16 dtmf_call;                      // 20
    u16 qc_call;                        // 21
    u16 mdc_msg;                        // 22
    u16 mdc_status;                     // 23
    u16 unknown3;                       // 24
    u16 mdc_system;                     // 25 ?
    u16 unknown4[3];                    // 26,27, 28
    u16 button_assignments;             // 29
    u16 unknown[18];                    // 30 -> 46
    u16 channels;                       // 47
    u16 channel_names;                  // 48
} addr;
"""
SECTION_NAMES = [
    "fdb1",
    "fdb2",
] + ["Unknown"] * 6 + [
    "Codeplug version and programming date",
    "HT1250 settings",
    "Personality assignment to zone",
    "Zone names",
    "Radio Configuration (Radio Password, language)",
    "Phone numbers",
    "Phone names",
    "Unknown",
    "Scan list members", # 07c3
] + ["Unknown"] * 31 + [
    "Channels",
    "Channel names",
] + ["Unknown"] * 6


# data: chr or bytearray
def calc_checksum(data, cs=0):
    offset = 0
    lastbyte = 0;
    if isinstance(data,bytearray):
        for byte in data:
            lastbyte = byte
            cs += byte
            offset += 1
    elif isinstance(data,bytes):
        offset = 0
        for byte in data:
            lastbyte = byte
            cs += byte
            offset += 1
    elif isinstance(data, str):
        for byte in data:
            lastbyte = byte
            cs += ord(byte)
            offset += 1

    # print hex(ord(byte)), hex(~cs & 0xff)
    ret = ~cs & 0xff
    #print(f'returning 0x{ret:x} offset 0x{offset-1:x}')
    return ~cs & 0xff

def _write(radio, data):
    print("write:")
    print(hexprint(data))
    radio.pipe.flushInput()
    radio.pipe.write(data)
    echo = radio.pipe.read(len(data))
    if not echo:
        raise errors.RadioError("No echo. Cable or driver fault.")
    if echo != data:
        print(hexprint(echo))
        raise errors.RadioError("Bad echo. Cable or driver fault.")


def _read_frame(radio):
    resp = radio.pipe.read(1)
    print("resp:")
    print(hexprint(resp))
    if resp != b'P':
        raise errors.RadioError('Radio is not in programming mode.')
    radio.pipe.read(1)  # 0xFF -- TODO: include this in 0x8b checksums
    data = radio.pipe.read(3)  # 0x80 00 24
    header_type, chunk_len = struct.unpack(">BH", data)
    data += radio.pipe.read(chunk_len)
    print("read:")
    print(hexprint(data))
    return data


def _request_frame(radio, offset, size):
    # send READ_DATA_REQ
    frame = create_frame(bytearray(b'\xf5\x11') + struct.pack(">BBH", size, 0, offset))
    _write(radio, frame)
    data = _read_frame(radio)
    header_type, length, pad, addr = struct.unpack(">BHBH", data[:6])
    return data[6:-1]  # FIXME: discard checksum for now


def _write_chunk(radio, offset, data):
    # send WRITE_DATA_REQ
    frame = create_frame(bytearray(b'\xff\x17') + struct.pack(">HBH", len(data) + 4, 0, offset) + data)
    _write(radio, frame)
    resp = radio.pipe.read(1)
    print("resp:")
    print(hexprint(resp))
    if resp != b'P':
        raise errors.RadioError('Radio did not acknowledge write.')
    ack = radio.pipe.read(6)
    print("F4 84 00 addr cs:")
    print(hexprint(ack))
    cmd, zero, addr, cs = struct.unpack(">HBHB", ack)
    if offset != addr:
        raise errors.RadioError('Short write at 0x%X' % offset)


def reboot_radio(radio):
    radio.pipe.write(b'\xF1\x10\xFE')

def create_frame(data):
    frame = bytearray(data)
    frame.extend(calc_checksum(frame).to_bytes(1,byteorder='little'))
    return frame

def do_connect(radio):
    print("timeout:", radio.pipe.timeout)
    status = chirp_common.Status()
    # enter program mode
    frame = create_frame(b'\xf2\x23\x05')

    for i in range(3):
        status.msg = "Connect to radio attempt %d" % (i + 1)
        radio.status_fn(status)
        try:
            _write(radio, frame)
            resp = _read_frame(radio)
        except errors.RadioError:
            sleep(0.8)
            continue
        if resp:
            break
    else:
        raise errors.RadioError("Radio did not respond.")

    # I think this is an ident:
    frame = create_frame(b'\xf2\x23\x0f')
    _write(radio, frame)
    print("ident:")
    print(hexprint(_read_frame(radio)))


def do_download(radio):
    do_connect(radio)
    if not radio._memsize:
        # get programming length
        programming_length, = struct.unpack(
            ">H", _request_frame(radio, 0x302, 2))
        radio._memsize = 0x300 + programming_length

    status = chirp_common.Status()
    status.msg = "Reading"
    status.max = radio._memsize

    data = bytearray()
    for offset in range(0, 0x4000, 0x20):
        data.extend(_request_frame(radio, offset, 0x20))
        status.cur = offset
        radio.status_fn(status)
        if len(data) >= radio._memsize:
            print(f'stopped reading @ 0x{offset:x}, 0x{len(data):x} > 0x{radio._memsize:x}')
            break
#debug only
    mapfile = open('/home/skip/e.bin', "wb")
    mapfile.write(bytes(data[:radio._memsize]))
    mapfile.close()
    print('saved ~/e.bin')

    return memmap.MemoryMapBytes(bytes(data))

def do_upload(radio, start=0x300):
    do_connect(radio)

    status = chirp_common.Status()
    status.msg = "Writing"
    status.max = radio._memsize

    for offset in range(start, radio._memsize, 0x20):
        _write_chunk(radio, offset, radio._mmap.get(offset, 0x20))
        status.cur = offset
        radio.status_fn(status)
    reboot_radio(radio)

def _find_blocks(mmap):
    f = io.BytesIO(mmap.get_packed())

    while True:
        read = f.read(2)
        if len(read) < 2:
            break
        #block_length = int(bitwise.parse("u16 length;", read.encode()))
        block_length = int(bitwise.parse("u16 length;", read)['length'])
        print(f'{block_length}/0x{block_length:x} byte block @ 0x{f.tell():x}')
        yield f.tell()
        f.read(block_length - 2)



CHUNK_HEADER = """
%s length;  // not including checksum byte at end of every
%s repeat;
"""
SMALL_CHUNK_HEADER = CHUNK_HEADER % ("u8", "u8")
ARRAY_CHUNK_HEADER = SMALL_CHUNK_HEADER + "\nu16 membersize;"


class Chunk:
    def calc_checksum(self):
        data = self.header_type.to_bytes(1,'big') + self.header._data.get(0,-1) + self.data.get_packed()
        #print(f'Chunk.calc_checksum byte_data {hexprint(data)}')
        return calc_checksum(data, 0xa5)

    def parse(self, memformat):
        self._memobj = bitwise.parse(memformat, self.data)
        return self._memobj

    def update_lengths(self):
        # for now, update length immediately in set_memory()
        pass

    def get_packed(self):
        self.update_lengths()
        frameinfo = getframeinfo(currentframe())
        print(f'{frameinfo.filename}:{frameinfo.lineno}')
        self.checksum = self.calc_checksum()
        return bytearray(self.header_type.to_bytes(1,'big')
                         + self.header._data[0:] + self.data[0:]
                         + self.checksum.to_bytes(1,'big'))

    def validate(self):
        assert self.checksum == self.calc_checksum()

    def fingerprint(self):
        return map(hex, map(int, [self.header_type, self.header.length]))

    def extend(self,new_entry):
        assert self.header.repeat  < 255
        assert len(new_entry) - 1 == self.header.length
        self.data = memmap.MemoryMapBytes(self.data.get(0,-1) + new_entry)
        self.header.repeat += 1

    def __repr__(self):
        return "\n".join([
            "start @ 0x%04x" % self.start,
            "header_type: 0x%02x" % self.header_type,
            repr(self.header),
            "data @ 0x%04x\n" % self.offset,
            self.data.printable(),
            "checksum: 0x%02x" % self.checksum,
            "calc_checksum: 0x%02x" % self.calc_checksum(),
            "end @ 0x%04x\n" % self.end,
        ])


def _find_chunks(mmap, start=0x00):
    f = io.BytesIO(mmap.get_packed())
    f.seek(start)
    while True:
        chunk = Chunk()
        chunk.start = f.tell()
        data = bytearray()

        byte = f.read(1)
        if byte == b'':
            # EOF
            break

        chunk.header_type = ord(byte)
        if chunk.header_type == 0x00:
            # end of block
            break
        elif chunk.header_type == 0x80:
            chunk.header = bitwise.parse(SMALL_CHUNK_HEADER,
                                         memmap.MemoryMap(f.read(2)))
            chunk.offset = f.tell()
            data.extend(f.read((chunk.header.length) * (chunk.header.repeat or 1)))
        elif chunk.header_type == 0x84:
            chunk.header = bitwise.parse(ARRAY_CHUNK_HEADER,
                                         memmap.MemoryMap(f.read(4)))
            chunk.offset = f.tell()
            if chunk.header.length == 0:
                for i in range(chunk.header.repeat):
                    membersize = int(f.read(1)[0])
                    data.append(membersize)
                    data.extend(f.read(membersize * int(chunk.header.membersize)))
            else:
                data.extend(f.read(chunk.header.length * chunk.header.repeat + 1))
        elif chunk.header_type == 0xc0:
            chunk.header = bitwise.parse(SMALL_CHUNK_HEADER,
                                         memmap.MemoryMap(f.read(2)))
            chunk.offset = f.tell()
            data.extend(f.read((chunk.header.length + 1) * chunk.header.repeat))
            # length + 1 accomodates a checksum after each item
        elif chunk.header_type == 0xc4:
            chunk.header = bitwise.parse(ARRAY_CHUNK_HEADER,
                                         memmap.MemoryMap(f.read(4)))
            chunk.offset = f.tell()
            data.extend((f.read((chunk.header.length + 1) * chunk.header.repeat + 1)))
            # length + 1 accomodates a checksum after each item
        else:
            msg = "Unknown header type: 0x%02X @ 0x%04X" % (
                chunk.header_type, f.tell())
            print(msg)
            break  # temporary until we know how to identify the end
            raise ValueError(msg)

        chunk.checksum = f.read(1)[0]
        chunk.end = f.tell()
        chunk.data = memmap.MemoryMapBytes(bytes(data))

        print(chunk)
        yield chunk


SOURCES = ['Factory', 'Depot Tool', 'CPS', 'Tuner', 'Source %d']
REGIONS = ['Super Tanapa', 'North America', 'Latin America', 'EMEA', 'Asia',
           'Federal', 'China Ministry of Rail', 'Japan']
MODES = ['?', 'NFM', 'FM', 'FM']
STEP = [2500, None, 5000, 6250]


class WarisBase(object):
    VENDOR = "Motorola"
    BAUD_RATE = 9600
    FORMATS = [directory.register_format('Motorola Waris binary codeplug', '*.bin')]

    def get_features(self):
        rf = chirp_common.RadioFeatures()
        rf.has_bank = False
        rf.has_dtcs = True
        rf.has_rx_dtcs = True
        rf.has_ctone = True
        rf.has_cross = True
        rf.has_settings = True
        rf.valid_characters = chirp_common.CHARSET_ASCII
        rf.valid_modes = MODES
        rf.valid_duplexes = ["", "-", "+", "split", "off"]
        rf.valid_tmodes = ['', 'Tone', 'TSQL', 'DTCS', 'Cross']
        rf.valid_tuning_steps = [s / 1e3 for s in filter(None, STEP)]
        rf.valid_cross_modes = [
            "Tone->Tone",
            "DTCS->",
            "->DTCS",
            "Tone->DTCS",
            "DTCS->Tone",
            "->Tone",
            "DTCS->DTCS"]
        rf.memory_bounds = (1, 255)
        if self._mmap is None:
            rf.valid_bands = [(29700000, 54000000), (136000000, 174000000),
                              (216000000, 225000000), (403000000, 512000000)]
        else:
            rf.valid_bands = [(
                self._decode_freq(self._tuning.lower_limit, 2),
                self._decode_freq(self._tuning.upper_limit, 2),
            )]
        return rf

    def process_mmap(self):
        # block_names = ('Tuning', 'FDB', 'Programming', 'Unknown')
        block_offsets = [block for block in _find_blocks(self._mmap)]
        # for i, offset in enumerate(block_offsets):
        #     try:
        #         print "%s0x%04x" % (block_names[i].ljust(10), offset)
        #     except IndexError:
        #         print "%s0x%04x" % ("Unknown".ljust(10), offset)
        #     print [c.offset for c in _find_chunks(self._mmap, offset)]
        fdb_offsets = [chunk.offset for chunk in _find_chunks(
            self._mmap, block_offsets[1])]
        # print "block_offsets:", [hex(x) for x in block_offsets]
        # for i, c in enumerate(_find_chunks(self._mmap, block_offsets[1])):
        #     print "fdb%d" % (i + 1)
        #     print c

        self._tuning = bitwise.parse(TUNING_FORMAT % (
            block_offsets[0],
            self._mmap.get(0,-1).find(b'\xff\xff\xff\xff\x07') + 5,
            block_offsets[1],
            fdb_offsets[0],
            fdb_offsets[1],
        ), self._mmap)
        self._memobj = self._tuning

    # Do a download of the radio from the serial port
    def sync_in(self):
        self._mmap = do_download(self)
        print('self._mmap:\n' + self._mmap.printable() + '\n')
        self.process_mmap()

    # Do an upload of the radio to the serial port
    def sync_out(self):
        # TODO: update programming date
        # TODO: self._mmap = self._prog.get_packed()
        # TODO: update programming_length
        self._memsize = 0x300 + self._memobj.programming_length
        self.update_checksums()
        do_upload(self)

    def load_mmap(self, filename):
        """Load the radio's memory map from @filename"""
        if filename.lower().endswith('.bin'):
            mapfile = open(filename, "rb")
            self._mmap = memmap.MemoryMapBytes(mapfile.read())
            mapfile.close()
            self.process_mmap()
        else:
            chirp_common.CloneModeRadio.load_mmap(self, filename)

    def save_mmap(self, filename):
        # try to open a file and write to it
        # If IOError raise a File Access Error Exception

        # _prog: list of Chunk objects
#        programming = ''.join([x.get_packed() for x in self._prog])

        if issubclass(self.__class__,WarisTuningRadio):
            new_image = bytearray(self._mmap.get(0,0x308))
        else:
            new_image = bytearray(self._mmap.get(0,0x308))
            for x in self._prog:
                new_image.extend(x.get_packed())
            print(f' Adding _misc {len(self._misc)}/0x{len(self._misc):x} bytes @ 0x{x.end:x}')
            new_image.extend(self._misc)
            print(f'len(new_image) {len(new_image)}/0x{len(new_image):x}')
            self._mmap = memmap.MemoryMapBytes(bytes(new_image))
        # TODO: update programming_length
        self.update_checksums()
        print(f'Saving img to {filename}')
        chirp_common.CloneModeRadio.save_mmap(self, filename)

    def update_checksums(self):
        data = self._mmap.get(0,0x27f)
        frameinfo = getframeinfo(currentframe())
        print(f'{frameinfo.filename}:{frameinfo.lineno}')
        self._tuning.tuningcs = calc_checksum(data, 0xa5)
        print(f'tuningcs ', self._tuning.tuningcs)
        # 0x282: adr of fdb1
        for chunk in _find_chunks(self._mmap, 0x282):
            frameinfo = getframeinfo(currentframe())
            print(f'{frameinfo.filename}:{frameinfo.lineno}')
            cksum = chunk.calc_checksum()
            print(f'chunk cksum 0x{cksum:x}')
            self._mmap.set(chunk.end-1,cksum)

        frameinfo = getframeinfo(currentframe())
        print(f'{frameinfo.filename}:{frameinfo.lineno}')
        self._tuning.fdbcs = calc_checksum(self._mmap.get(0x280,0x7f), 0xa5)
        print(f'fdbcs cksum ',self._tuning.fdbcs)

    def _decode_freq(self, freq, step=2):
        return int(freq) * STEP[int(step)] + self._tuning.base_freq * 25000

    def _encode_freq(self, freq, step=None):
        freq -= self._tuning.base_freq * 25000
        if step is not None:
            return freq / STEP[step]
        for i, step in reversed(list(enumerate(STEP))):
            if freq % step == 0:
                return freq / step, i

    def _set_pier(self, setting, obj, i):
        obj[i] = self._encode_freq(setting.value.get_value() * 1e6, 2)

    def _offset_freq(self, value, offset):
        freq = self._decode_freq(value, 2)
        freq += offset
        return self._encode_freq(freq, 2)

    def _auto_convert(self, freq_offset):
    # move all existing tuning values up one slot to make room for new ham
    # band slot at entry 0
        mem = self._memobj
        mem.conventional = 255
        mem.lower_limit = self._offset_freq(mem.lower_limit,freq_offset)
        mem.upper_limit = self._offset_freq(mem.upper_limit,freq_offset)
        lower_limit = self._decode_freq(mem.lower_limit,2)

        pier0 = self._decode_freq(mem.rxpier[0])
        pier1 = self._decode_freq(mem.rxpier[1])
        scale_rx_adj = abs(freq_offset) / (pier1 - pier0)

        pier0 = self._decode_freq(mem.txpier[0])
        pier1 = self._decode_freq(mem.txpier[1])
        scale_tx_adj = abs(freq_offset) / (pier1 - pier0)

        for i in range(6,0,-1):
            mem.rxpier[i] = mem.rxpier[i-1]
            mem.txpier[i] = mem.txpier[i-1]
            mem.testfreq[i*2] = mem.testfreq[(i * 2) - 2]
            mem.testfreq[(i*2) + 1] = mem.testfreq[(i * 2) - 1]

        mem.rxpier[0] = self._offset_freq(mem.rxpier[0],freq_offset)
        mem.txpier[0] = self._offset_freq(mem.txpier[0],freq_offset)
        mem.testfreq[0] = self._offset_freq(mem.testfreq[2],freq_offset)
        mem.testfreq[1] = self._offset_freq(mem.testfreq[3],freq_offset)

        for value, max_value, tx_val in self._tuning_items:
            for i in range(6,0,-1):
                value[i] = value[i-1]
            value[0] = value[1]
            delta = value[1] - value[2]
            if not delta == 0:
                if tx_val:
                    delta *= scale_tx_adj
                else:
                    delta *= scale_rx_adj
                delta = round(delta)
                value[0] += delta
                if(value[0] > max_value):
                    value[0] = max_value
                elif value[0] < 0:
                    value[0] = 0
        self.update_checksums()

    def _Offer_Autoconvert(self):
        self._auto_converted = False
        lower_limit = self._decode_freq(self._tuning.lower_limit, 2)
        upper_limit = self._decode_freq(self._tuning.upper_limit, 2)
        CanTweak = False
        if lower_limit == 450000000:
            CanTweak = True;
            freq_offset = -10000000

        if CanTweak:
            r = wx.MessageBox('Adjust tuning to cover 440 Mhz to 510 Mhz ?',
                              _('Auto Adjust'),
                              wx.YES_NO | wx.CANCEL)
            if r != wx.YES:
                return

            r = wx.MessageBox(
                _('Before modifing your tuning data make sure you have '
                  'a backup the of the unmodified tuning data!'),
                _('Auto Adjust'),
                wx.OK | wx.CANCEL | wx.CANCEL_DEFAULT)
            if r == wx.CANCEL:
                return

            self._auto_converted = True
            self._auto_convert(freq_offset)

    def _set_limit(self, setting, obj, name):
        setattr(obj, name,
                self._encode_freq(setting.value.get_value() * 1e6, 2))

    def get_tuning_settings(self):
        _mem = self._tuning

        tuning = RadioSettingGroup("tuning", "Tuning")

        rxpiers = [self._decode_freq(_mem.rxpier[i]) / 1e6 for i in range(7)]
        txpiers = [self._decode_freq(_mem.txpier[i]) / 1e6 for i in range(7)]
        center_freq = rxpiers[3]

        rx_point_str = ["%.3f MHz" % f for f in rxpiers]

        rsg = RadioSettingGroup("piers", "Tuning Piers")
        for i in range(7):
            rs = RadioSetting(
                "rxpier/%d" % i,
                "Tuning Pier RX %d" % (i + 1),
                RadioSettingValueFloat(0, 999.999, rxpiers[i], .005, 3))
            rs.set_apply_callback(self._set_pier, _mem.rxpier, i)
            rsg.append(rs)
            rs = RadioSetting(
                "txpier/%d" % i,
                "Tuning Pier TX %d" % (i + 1),
                RadioSettingValueFloat(0, 999.999, txpiers[i], .005, 3))
            rs.set_apply_callback(self._set_pier, _mem.txpier, i)
            rsg.append(rs)
        tuning.append(rsg)

        rsg = RadioSettingGroup("testfreqs", "RF Test Channels")
        for i in range(14):
            rs = RadioSetting(
                "testfreq/%d" % i,
                "Test Mode CH%02d/CH%02d %s" % (
                    i / 2 + 1, i / 2 + 8, ('TX', 'RX')[i % 2]),
                RadioSettingValueFloat(0, 999.999, self._decode_freq(
                    _mem.testfreq[i]) / 1e6, .005, 3))
            rs.set_apply_callback(self._set_pier, _mem.testfreq, i)
            rsg.append(rs)
        tuning.append(rsg)

        per_pier_valuse = (
            ("vcoattn25", "VCO Attenuation 25 Khz", _mem.vcoattn25,127),
            ("modbalattn", "front end filter", _mem.modbalattn,63),
            ("kvalues", "transmit power K value", _mem.kvalues,256),
            ("mvalues", "transmit power M value", _mem.mvalues,256),
            ("squelch12", "Squelch Attn. 12.5 KHz", _mem.squelch12,63),
            ("squelch20", "Squelch Attn. 20 KHz",   _mem.squelch20,63),
            ("squelch25", "Squelch Attn. 25 KHz",   _mem.squelch25,63),
        )
        for name, shortname, mem, max_val in per_pier_valuse:
            rsg = RadioSettingGroup(name, shortname)
            for i, freq in enumerate(rx_point_str):
                rs = RadioSetting(
                    "%s/%d" % (name, i),
                    freq,
                    RadioSettingValueInteger(0, max_val, int(mem[i])))
                rsg.append(rs)
            tuning.append(rsg)

        tuning_ints = (
            (_mem.mdc1200level,'mdc1200level',"MDC1200 signalling @ %.3f MHz" % center_freq,31),
            (_mem.dtmflevel,'dtmflevel',"DTMF signalling @ %.3f Mhz" % txpiers[0],31),
            (_mem.ratedvolume,'ratedvolume',"Rated Volume @ %.3f MHz" % center_freq,255),
            (_mem.targetvoltage,'targetvoltage','Battery Threshold',255),
            (_mem.powerlevels[0],'powerlevels_0','Power Level High',127),
            (_mem.powerlevels[1],'powerlevels_1','PA Bias2(High)',255),
            (_mem.powerlevels[2],'powerlevels_2','PA Bias3(High)',255))

        for mem, name, shortname, max_val in tuning_ints:
            rs = RadioSetting("%s" % name,shortname,
                RadioSettingValueInteger(0, max_val, int(mem)))
            tuning.append(rs)

        return tuning

    def get_fdb_settings(self):
        _mem = self._tuning
        fdb = RadioSettingGroup("fdb", "Feature Data")

        rs = RadioSetting("serial", "Serial", RadioSettingValueString(
            0, 10, str(_mem.serial).rstrip()))
        fdb.append(rs)

        rs = RadioSetting("model", "Model", RadioSettingValueString(
            0, 16, str(_mem.model).rstrip()))
        fdb.append(rs)

        rs = RadioSetting("cpversion", "CP Version", RadioSettingValueString(
            3, 5, "%d.%d" % (_mem.cpversion[0], _mem.cpversion[1])))

        def set_cpversion(setting, obj):
            obj.cpversion[0], obj.cpversion[1] = map(
                int, setting.value.get_value().split('.'))
        rs.set_apply_callback(set_cpversion, _mem)
        fdb.append(rs)

        rs = RadioSetting("cpsource", "Source", RadioSettingValueList(
            SOURCES, SOURCES[_mem.cpsource]))
        fdb.append(rs)

        rs = RadioSetting("cpdate", "Origin Date", RadioSettingValueInteger(
            0, 999999999999, _mem.cpdate))
        fdb.append(rs)

        BASE = {
            "20 MHz - VHF Low Band": 0x320,
            "103 MHZ - VHF and 200 MHz": 0x1018,
            "325 MHz - 330 MHz": 0x32C8,
            "375 MHz - UHF R1/R2": 0x3A98,
            "701 MHz - 700 MHz": 0x6D88,
            "801 MHz - 800 MHz": 0x7D28,
        }
        rs = RadioSetting("base_freq", "Base Frequency", RadioSettingValueMap(
            BASE.items(), int(_mem.base_freq)))
        fdb.append(rs)

        CHANNEL_STEP_ITEM = {
            "0x0 - UNKNOWN - only used on VHF Low Band": 0x0,
            "0x1 - 12.5/20/25 KHz - used on VHF only": 0x1,
            "0x2 - UNKNOWN - used on UHF R1, R2 only": 0x2,
            "0x3 - UNKNOWN - used on 800 MHz only": 0x3,
            "0x5 - 12.5 KHz only - used on 200 MHz only": 0x5,
            "0x6 - UNKNOWN - used on 700 MHz only": 0x6,
        }
        rs = RadioSetting("channel_step", "Channel Step", RadioSettingValueMap(
            CHANNEL_STEP_ITEM.items(), int(_mem.channel_step)))
        fdb.append(rs)


        rs = RadioSetting(
            "lower_limit",
            "Lower Limit (MHz)",
            RadioSettingValueFloat(0, 999.999, self._decode_freq(
                _mem.lower_limit) / 1e6, .005, 3))
        rs.set_apply_callback(self._set_limit, _mem, 'lower_limit')
        fdb.append(rs)

        rs = RadioSetting(
            "upper_limit",
            "Upper Limit (MHz)",
            RadioSettingValueFloat(0, 999.999, self._decode_freq(
                _mem.upper_limit) / 1e6, .005, 3))
        rs.set_apply_callback(self._set_limit, _mem, 'upper_limit')
        fdb.append(rs)

        rs = RadioSetting("firmware_pn", "Firmware", RadioSettingValueString(
            0, 16, str(_mem.firmware_pn).rstrip()))
        fdb.append(rs)

        rs = RadioSetting("tanapa", "TANAPA", RadioSettingValueString(
            0, 10, str(_mem.tanapa).rstrip()))
        fdb.append(rs)

        if _mem.region >= len(REGIONS):
        # invalid region (default code plug), set it to North America
            _mem.region = 1

        rs = RadioSetting("region", "Region", RadioSettingValueList(
            REGIONS, REGIONS[_mem.region]))
        fdb.append(rs)

        rs = RadioSetting(
            "trunking",
            "Trunking Channel Limit",
            RadioSettingValueInteger(0, 255, int(_mem.trunking)))
        fdb.append(rs)

        for name in ("Trunking Signaling", "Conventional Signaling"):
            for i in range(3, -1, -1):
                attr = "%s%i" % (name.lower().replace(' ', '_'), i)
                rs = RadioSetting(
                    attr,
                    "%s bit[%d]" % (name, i),
                    RadioSettingValueBoolean(getattr(_mem, attr)))
                fdb.append(rs)
        
        
        CONTROL_HEAD_ITEM = {
            "A, 0x40, Databox, No Display/Keypad Mobile, 25 Family": 0x40,
            "C, 0x00, No Display, Basic Keypad, Mobile, 25 Family": 0x0,
            "C, 0x10, No Display, Basic Keypad, Mobile/HT, 25/34/38/45/50 Family": 0x10,
            "D, 0x11, 1 Line Display, Limited Keypad, Mobile, 25 Family": 0x11,
            "D, 0x20, Keypad, HT, 34 Family": 0x20,
            "F, 0x21, 1 Line Display, Limited Keypad, Mobile, 25/34/38 Family": 0x21,
            "F, 0x21, 1 Line Display, Limited Keypad, HT, 25/34/38 Family": 0x21,
            "H, 0x21, 1 Line display, Full Keypad, HT, 25/34/38 Family": 0x21,
            "C/K/J, 0x30, No Display, No/Limited/Full Keypad, HT, 65 Family": 0x30,
            "F/H, 0x31, 1 Line display, Limited/Full Keypad, HT, 34 Family": 0x31,
            "N, 0x32, 4 Line Display, Full Keypad, Mobile/HT, 25 Family": 0x32,
            "F, 0x33, One Line Display, Standard Keypad, Mobile, 50/65 Family": 0x33,
            "H, 0x33, 1 Line display, Full Keypad, Mobile/HT, 65 Family": 0x33
            
            }

        rs = RadioSetting(
                          "control_head",
                          "Control Head Type",
                          RadioSettingValueMap(CONTROL_HEAD_ITEM.items(), int(_mem.control_head)))
        fdb.append(rs)

                          
                          
        rs = RadioSetting(
            "conventional",
            "Conventional Channel Limit",
            RadioSettingValueInteger(0, 255, int(_mem.conventional)))
        fdb.append(rs)

        rs = RadioSetting("FPP", "Edit Mode/FPP 0x2E1",  RadioSettingValueInteger(0, 255, int(_mem.FPP)))
        fdb.append(rs)

        return fdb


class WarisRadio(WarisBase):
    _programming_layout = {
        'CODEPLUG_VERSION_AND_DATE':    0,
    }

    def process_mmap(self):
        super(WarisRadio, self).process_mmap()
        prog_chunk_names = {
            8: "Codeplug version and programming date",
            9: "Radio Configuration (settings)",
            10: "Personality assignment to zone",
            11: "Zone names",
            12: "Radio Configuration (Radio Password, language)",
            13: "Phone numbers",
            15: "Phone names",
            17: "Scan list members",
            # 12: unknown exists on W9CR red but not KD7LXL
            21: "MDC Call",
            22: "DTMF Call",
            23: "QC Call",
            24: "MDC Message",
            25: "MDC Status",
            27: "MDC System?",
            30: "Personalties",
            31: "Button assignments",
            32: "Personality names",
            33: "LS Trunking button assignments",
            # 24 total in non-LS version, cp version 1.x
            # 31 in W9CR RED LS version, cp version 2.x also cdm1550 ls+ with passport 
            # 37 in PMUD1494C, cp version 4.x
            # 32 in PMUE1929D, cp version 11.0
        }
        self._memobj = bitwise.parse(PROGRAMMING_HEADER_FORMAT, self._mmap)
# old
#        section_map_length, = struct.unpack(">H",
#            self._mmap.get_packed()[self._memobj.section_map_addr:
#                       self._memobj.section_map_addr+2])
        section_map_addr = self._memobj['section_map_addr']
        map_length_data = self._mmap.get(section_map_addr,2)

        section_map_length, = struct.unpack(">H",map_length_data)
        self._addr = bitwise.parse("#seekto %d; u16 address[%d];" % (
            self._memobj.section_map_addr+2, section_map_length), self._mmap)
        # layout_rev = dict([(v, k) for k, v in self._programming_layout.items()])
        self._prog = []
        for c in _find_chunks(self._mmap, 0x308):
            self._prog.append(c)
        misc_len = 0x300 + self._memobj.programming_length - c.end
        print(f'misc {misc_len}/0x{misc_len:x} bytes @ {c.end:x}')

        self._misc = self._mmap.get(c.end,misc_len)
        self._byaddr = dict([(p.start, p) for p in self._prog])

        section_map_addr = self._memobj.section_map_addr

        misc1_len = section_map_addr - c.end

        self._map = bitwise.parse(MAP % self._memobj.section_map_addr,self._mmap)
        print(f'misc1 data @ 0x{c.end:x} for 0x{misc1_len:x} bytes:')
        misc1_data = self._mmap.get(c.end,misc1_len)
        print(hexprint(misc1_data))
        print('')

        section_map_length = self._map.section_map_length
        print(f'Section map @ {section_map_addr} for {section_map_length}:')
        print(self._map)
        print('')

        misc2_adr = c.end + misc1_len + section_map_length
        misc2_len = misc_len - misc1_len - section_map_length

        print(f'misc2 data @ 0x{misc2_adr:x} for 0x{misc2_len:x} bytes:')
        misc2_data = self._mmap.get(misc2_adr,misc2_len)
        print(hexprint(misc2_data))

#        for i, c in enumerate(self._prog):
#            print(f'{i:2d} {c.fingerprint()} {layout_rev.get(i, "")}')
#            print(c)

        channels_adr = int(self._map.addr.channels)
        self._channels = self._byaddr[channels_adr]
        self._channels.parse(CHANNELS)
        self._num_personality = self._channels.header.repeat

        self._channel_names = self._byaddr[int(self._map.addr.channel_names)]
        self._channel_names.parse(CHANNEL_NAMES)

        # for format, id in self._programming_layout.items():
        #     print id, format
        #     self._prog[id].parse(globals()[format])
        # f = StringIO(self._mmap)
        # self._personality_assignment_to_zone(f)
        # self._print_scan_lists()

    def update_checksums(self):
        super(WarisRadio, self).update_checksums()
        for i, c in enumerate(self._prog):
            frameinfo = getframeinfo(currentframe())
            print(f'{frameinfo.filename}:{frameinfo.lineno}')
            print("section %d: %x %x" % (i, c.checksum, c.calc_checksum()))
            print(repr(c))
            print('---')
            print('')
        cs_len = self._memobj.programming_length.get_value()
        cs_addr = 0x300 + cs_len
        print(f'cs_len {cs_len}/0x{cs_len:x}')
        print(f'cs_addr {cs_addr}/0x{cs_addr:x}')
        print("programming_checksum: %x %x" % (
            ord(self._mmap.get(cs_addr) or '\0'),
            calc_checksum(self._mmap.get(0x300,cs_len), 0xa5)
        ))

    def _personality_assignment_to_zone(self, f):
        """Personality assignment to zone map looks like
        0x 84 00 {zone_count} 00 02
        struct {
            u8 channel_count;
            struct {
                u8 unknown;  // always 0x01
                u8 personality;
            } assignment[channel_count];
        } zones[zone_count];
        """
        f.seek(self._prog[2].offset - 3)
        zone_count = ord(f.read(1))
        print("Zones:", zone_count)
        f.read(2)
        for zone in range(zone_count):
            channel_count = ord(f.read(1))
            print( "Zone %d: %s [%d channels]" % (
                zone + 1,
                self._memobj.zonenames[zone].name,
                channel_count))
            for channel in range(channel_count):
                f.read(1)
                personality = ord(f.read(1))
                print("%4d %s Conventional-%d" % (
                    channel + 1,
                    self._memobj.personalitynames[personality].name,
                    personality + 1))
        print( "next: 0x%04x" % f.tell())

    def _print_scan_lists(self):
        for i in range(self._prog[9].header.repeat):
            print("Scan List - %d" % (i + 1))
            for j in range(16):
                scanlistmember = self._memobj.scanlist[i].scanlistmember[j]
                if scanlistmember.type == 0:
                    break
                elif scanlistmember.type == 1:
                    name = self._get_name(scanlistmember.personality)
                elif scanlistmember.type == 7:
                    name = "<selected>"
                else:
                    print("Unknown scanlistmember type %d" % scanlistmember.type)
                    return
                print("\t%s" % name)

    def _decode_tone(self, mode, value, invert=False):
        if mode == 0 or value == 0:
            return None, None, None
        elif mode == 1:
            return "Tone", value / 10.0, None
        elif mode == 2:
            return "DTCS", chirp_common.ALL_DTCS_CODES[value - 0x800], \
                   invert and "R" or "N"
        else:
            raise errors.RadioError("Unknown tone mode 0x%04x" % mode)

    def get_raw_memory(self, number):
        return repr(self._channels._memobj.personality[number - 1]) + \
            repr(self._channel_names._memobj.personalitynames[number - 1])

    def get_memory(self, number):
        if not hasattr(self, "bandplan"):
            self.bandplans = bandplan.BandPlans(config.get())

        _mem = self._channels._memobj.personality[number - 1]
        mem = chirp_common.Memory()

        mem.number = number
        if number > self._num_personality:
            mem.empty = True
            return mem

        mem.freq = self._decode_freq(_mem.rxfreq, _mem.rxstep)
        mem.name = self._get_name(number - 1)

        chirp_common.split_tone_decode(
            mem,
            self._decode_tone(_mem.txtonemode, _mem.txtone, _mem.txdplinvert),
            self._decode_tone(_mem.rxtonemode, _mem.rxtone, _mem.rxdplinvert))

        def_offset = self.bandplans.get_defaults_for_frequency(mem.freq).offset
        txfreq = self._decode_freq(_mem.txfreq, _mem.txstep)
        if bool(_mem.rxonly):
            mem.duplex = "off"
        elif _mem.txfreq == _mem.rxfreq:
            mem.duplex = ""
        elif def_offset and def_offset == txfreq - mem.freq:
            mem.duplex = def_offset > 0 and "+" or "-"
            mem.offset = abs(def_offset)
        else:
            mem.duplex = "split"
            mem.offset = txfreq

        mem.mode = MODES[_mem.txwidth]
        mem.tuning_step = STEP[_mem.rxstep] / 1000.

        return mem

    def _get_name(self, i):
        return str(self._channel_names._memobj.personalitynames[i].name).rstrip('\x00')

    def set_memory(self, mem):
        _mem = self._channels._memobj.personality[mem.number - 1]

        if mem.empty:
            # TODO: how should we fill the gap?? shift up?
            return

        if mem.number > self._num_personality:
            # WARNING there be dragons here !
            # 1. The section map appears AFTER the _channels chunk so we need to 
            # update the  pointer to it in the programming header.
            # 2. adding new channels requires adding new names as well.
            # 3. There are unknown data blocks called misc1 and misc2 that 
            # also follow the _channels chunk and we have no idea if it contains 
            # pointer that need relocation.
            # So ... I'm giving up for now
            r = wx.MessageBox(_('The ability to add new channels is not fully implemented!\nDO NOT USE!'),
                              _('Warning'),
                              wx.ICON_WARNING)

            blank = b'\xccKPKP\xcf\x00\x00\x00\x00\x00\x08\x074\x11\x00\x00\xff\x00\x00\x00\x00\x00\xff7'

            while mem.number > self._num_personality:
                self._channels.extend(blank)

            self._channels.parse(CHANNELS)
            _mem = self._channels._memobj.personality[mem.number - 1]

        _mem.rxfreq, _mem.rxstep = self._encode_freq(mem.freq)
        _mem.txfreq, _mem.txstep = _mem.rxfreq, _mem.rxstep  # FIXME duplex

        for y, z in enumerate(chirp_common.split_tone_encode(mem)):
            type, value,invert = z
            if y == 0:  # TX values
                if type == 'Tone':
                    _mem.txtonemode = 1
                    _mem.txtone = value * 10
                elif type == 'DTCS':
                    _mem.txtonemode = 2
                    _mem.txtone = chirp_common.ALL_DTCS_CODES.index(value) + 0x800
                    _mem.txdplinvert = invert == 'R' and 1 or 0
                else:
                    _mem.txtonemode = 0
            else:       # RX values
                if type == 'Tone':
                    _mem.rxtonemode = 1
                    _mem.rxtone = value * 10
                elif type == 'DTCS':
                    _mem.rxtonemode = 2
                    _mem.rxtone = chirp_common.ALL_DTCS_CODES.index(value) + 0x800
                    _mem.rxdplinvert = invert == 'R' and 1 or 0
                else:
                    _mem.rxtonemode = 0

        _mem.checksum = 0xa5
        frameinfo = getframeinfo(currentframe())
        print(f'{frameinfo.filename}:{frameinfo.lineno}')
        _mem.checksum = calc_checksum(_mem.get_raw())

    def _set_name(self, mem):
        # TODO: can't write new names until we move it out of _memobj
        pass

    def get_settings(self):
        codeplug_version_and_date = self._byaddr[int(
            self._map.addr.codeplug_version_and_date)]
        codeplug_version_and_date.parse(CODEPLUG_VERSION_AND_DATE)
        _mem = codeplug_version_and_date._memobj
        tuning = self.get_tuning_settings()
        fdb = self.get_fdb_settings()
        prog = RadioSettingGroup("prog", "Programming Data")

        rs = RadioSetting("progversion", "Version", RadioSettingValueString(
            3, 5, "%d.%d" % (_mem.majorversion, _mem.minorversion)))
        prog.append(rs)

        rs = RadioSetting("source", "Source", RadioSettingValueList(
            SOURCES, SOURCES[_mem.source]))
        prog.append(rs)

        rs = RadioSetting(
            "date",
            "Programming Date",
            RadioSettingValueInteger(0, 999999999999, _mem.date))
        prog.append(rs)

        try:
            settings2 = self._byaddr[int(self._map.addr.settings2)]
            settings2.parse(HT1250_SETTINGS2)
            print("settings2", repr(settings2._memobj.settings2))
            rs = RadioSetting("radiopassword", "Radio Password",
                RadioSettingValueInteger(0, 9999,
                    settings2._memobj.settings2.radiopassword))
            prog.append(rs)
        except (InvalidValueError, KeyError):
            pass

        for val in tuning.walk():
            val[0].set_mutable(False)
        for val in fdb.walk():
            val[0].set_mutable(False)
        for val in prog.walk():
            val[0].set_mutable(False)

        return RadioSettings(tuning, fdb, prog)

    @classmethod
    def match_model(cls, filedata, filename):
        return filedata.startswith(b'\x02\x80') and len(filedata) != 0x300 or \
            filename.endswith('.mot')


# Motorola Waris Tuning only
# It is assumed the user will want to perform tuning and programming
# independently, so this separate tuning driver is provided.
@directory.register
class WarisTuningRadio(WarisBase, chirp_common.CloneModeRadio):
    MODEL = "Waris Tuning"
    _memsize = 0x300

    def sync_out(self):
        self.update_checksums()
        do_upload(self, start=0)

    def get_memory(self, number):
        mem = chirp_common.Memory()
        mem.number = number
        mem.empty = True
        return mem

    def get_settings(self):
        self._tuning_items = (
            (self._memobj.vcoattn25,127,False),
            (self._memobj.modbalattn,63,True),
            (self._memobj.kvalues,256,True),
            (self._memobj.mvalues,256,True),
            (self._memobj.frontendfilter,127,False),
            (self._memobj.squelch12,63,False),
            (self._memobj.squelch20,63,False),
            (self._memobj.squelch25,63,False))
        self._Offer_Autoconvert()
        return RadioSettings(self.get_tuning_settings(),
                             self.get_fdb_settings())

    def set_settings(self, settings):
        for setting in settings:
            if not isinstance(setting, RadioSetting):
                self.set_settings(setting)
                continue
            if not setting.changed():
                continue

            name = setting.get_name()
            if "/" in name:
                name, index = name.split("/", 1)
                obj = getattr(self._tuning, name)[int(index)]
            else:
                obj = self._tuning

            print("Setting %s = %s" % (name, setting.value))
            if setting.has_apply_callback():
                setting.run_apply_callback()
            else:
                setattr(obj, name, setting.value)

    @classmethod
    def match_model(cls, filedata, filename):
        return filedata.startswith("\x02\x80") and len(filedata) == 0x300


@directory.register
class HT1250Radio(WarisRadio, chirp_common.CloneModeRadio):
    """Motorola HT1250"""
    MODEL = "HT1250"
    _programming_layout = {
        'CODEPLUG_VERSION_AND_DATE':    0,
        'HT1250_SETTINGS':              1,
        'ZONE_NAMES':                   3,
        'HT1250_SETTINGS2':             4,
        'SCAN_LIST_MEMBERS':            9,
        'CHANNELS':                     21,
        # 'BUTTON_ASSIGNMENTS':           22,
        'CHANNEL_NAMES':                23,
    }


@directory.register
class CDM1250Radio(WarisRadio, chirp_common.CloneModeRadio):
    """Motorola CDM1250"""
    MODEL = "CDM1250"
    _programming_layout = {
        'CODEPLUG_VERSION_AND_DATE':    0,
        'HT1250_SETTINGS':              1,
        'ZONE_NAMES':                   3,
        # 4: Control 1 On
        'SCAN_LIST_MEMBERS':            9,
        'CHANNELS':                     20,
        'CHANNEL_NAMES':                22,
    }


@directory.register
class PR860Radio(WarisRadio, chirp_common.CloneModeRadio):
    """Motorola PR860"""
    MODEL = "PR860"
    _programming_layout = {
        'CODEPLUG_VERSION_AND_DATE':    0,
        'CHANNELS':                     9,
        'CHANNEL_NAMES':                10,
    }


@directory.register
class SrecFile(WarisRadio, chirp_common.FileBackedRadio):
    """Motorola srec files"""
    MODEL = "srec file"
    FILE_EXTENSION = "srec"

    def __init__(self, filename):
        self._mmap = None
        self.pipe = None
        self.load_mmap(filename)

    def load_mmap(self, filename):
        try:
            import bincopy
        except ImportError as e:
            raise errors.RadioError(str(e))

        b = bincopy.BinFile()
        with open(filename, "rb") as f:
            self._header = f.read(0x322)
            b.add_srec(f.read())
            self._sheader = b.as_binary()[:5]
        # Add fake tuning + fdb header:
            fake_hdr = "\x02\x80" + "\xff\xff\xff\xff\x07" + "\x00" * 0x279 + str(b.as_binary())[5:]
            self._mmap = memmap.MemoryMapBytes(bitwise.string_straight_encode(fake_hdr))
        self.process_mmap()

    def save_mmap(self, filename):
        try:
            import bincopy
        except ImportError as e:
            raise errors.RadioError(str(e))

        self.update_checksums()

        b = bincopy.BinFile()
        b.add_binary(self._mmap.get_packed())
        with open(filename, "wb") as f:
            f.write(self._header)
            f.write(self._shreader)
            f.write(b.as_srec())

    @classmethod
    def match_model(cls, filedata, filename):
        return filename.endswith(".srec")
