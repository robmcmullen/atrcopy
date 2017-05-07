from collections import defaultdict

import numpy as np

from errors import *
from segments import SegmentData, EmptySegment, ObjSegment
from diskimages import DiskImageBase
from utils import to_numpy

import logging
log = logging.getLogger(__name__)


# From atari800 source
known_cart_types = [
# (note: all size units in KB)
# atari800 index number
# name
# total size
# static size
# static offset
# static address
# banked size
# banked offset (for bank zero)
# banked address
    (0,  "", 0,),
    (57, "Standard 2 KB", 2, 2, 0, 0xb800),
    (58, "Standard 4 KB", 4, 4, 0, 0xb000),
    (59, "Right slot 4 KB", 4, 4, 0, 0, 0x9000),
    (1,  "Standard 8 KB", 8, 8, 0, 0xa000),
    (21, "Right slot 8 KB", 8,),
    (2,  "Standard 16 KB", 16, 16, 0, 0x8000),
    (44, "OSS 8 KB", 8,),
    (15, "OSS one chip 16 KB", 16,),
    (3,  "OSS two chip (034M) 16 KB", 16, 4, 12, 0xb000, 4, 0, 0xa000),
    (45, "OSS two chip (043M) 16 KB", 16, 4, 12, 0xb000, 4, 0, 0xa000),
    (12, "XEGS 32 KB", 32,  8, 24, 0xa000, 8, 0, 0x8000),
    (13, "XEGS (banks 0-7) 64 KB", 64, 8, 56, 0xa000, 8, 0, 0x8000),
    (67, "XEGS (banks 8-15) 64 KB", 64, 8, 56, 0xa000, 8, 0, 0x8000),
    (14, "XEGS 128 KB", 128, 8, 120, 0xa000, 8, 0, 0x8000),
    (23, "XEGS 256 KB", 256, 8, 248, 0xa000, 8, 0, 0x8000),
    (24, "XEGS 512 KB", 512, 8, 504, 0xa000, 8, 0, 0x8000),
    (25, "XEGS 1 MB", 1024, 8, 1016, 0xa000, 8, 0, 0x8000 ),
    (33, "Switchable XEGS 32 KB", 32,  8, 24, 0xa000, 8, 0, 0x8000),
    (34, "Switchable XEGS 64 KB", 64,  8, 56, 0xa000, 8, 0, 0x8000),
    (35, "Switchable XEGS 128 KB", 128, 8, 120, 0xa000, 8, 0, 0x8000),
    (36, "Switchable XEGS 256 KB", 256, 8, 248, 0xa000, 8, 0, 0x8000),
    (37, "Switchable XEGS 512 KB", 512, 8, 504, 0xa000, 8, 0, 0x8000),
    (38, "Switchable XEGS 1 MB", 1024, 8, 1016, 0xa000, 8, 0, 0x8000 ),
    (22, "Williams 32 KB", 32,),
    (8,  "Williams 64 KB", 64,),
    (9,  "Express 64 KB", 64,),
    (10, "Diamond 64 KB", 64,),
    (11, "SpartaDOS X 64 KB", 64,),
    (43, "SpartaDOS X 128 KB", 128,),
    (17, "Atrax 128 KB", 128,),
    (18, "Bounty Bob 40 KB", 40,),
    (26, "MegaCart 16 KB", 16,),
    (27, "MegaCart 32 KB", 32,),
    (28, "MegaCart 64 KB", 64,),
    (29, "MegaCart 128 KB", 128,),
    (30, "MegaCart 256 KB", 256,),
    (31, "MegaCart 512 KB", 512,),
    (32, "MegaCart 1 MB", 1024,),
    (39, "Phoenix 8 KB", 8,),
    (46, "Blizzard 4 KB", 4,),
    (40, "Blizzard 16 KB", 16, 16, 0, 0x8000),
    (60, "Blizzard 32 KB", 32,),
    (41, "Atarimax 128 KB Flash", 128,),
    (42, "Atarimax 1 MB Flash", 1024,),
    (47, "AST 32 KB", 32,),
    (48, "Atrax SDX 64 KB", 64,),
    (49, "Atrax SDX 128 KB", 128,),
    (50, "Turbosoft 64 KB", 64,),
    (51, "Turbosoft 128 KB", 128,),
    (52, "Ultracart 32 KB", 32,),
    (53, "Low bank 8 KB", 8, 8, 0, 0x8000),
    (5,  "DB 32 KB", 32,),
    (54, "SIC! 128 KB", 128,),
    (55, "SIC! 256 KB", 256,),
    (56, "SIC! 512 KB", 512,),
    (61, "MegaMax 2 MB", 2048,),
    (62, "The!Cart 128 MB", 128*1024,),
    (63, "Flash MegaCart 4 MB", 4096,),
    (64, "MegaCart 2 MB", 2048,),
    (65, "The!Cart 32 MB", 32*1024,),
    (66, "The!Cart 64 MB", 64*1024,),
    (20, "Standard 4 KB 5200", 4, 4, 0, 0x8000),
    (19, "Standard 8 KB 5200", 8, 8, 0, 0x8000),
    (4,  "Standard 32 KB 5200", 32, 32, 0, 0x4000),
    (16, "One chip 16 KB 5200", 16,),
    (6,  "Two chip 16 KB 5200", 16,),
    (7,  "Bounty Bob 40 KB 5200", 40,),
]

known_cart_type_map = {c[0]:i for i, c in enumerate(known_cart_types)}


def get_known_carts():
    grouped = defaultdict(list)
    for c in known_cart_types[1:]:
        size = c[2]
        grouped[size].append(c)
    return grouped


def get_cart(cart_type):
    try:
        return known_cart_types[known_cart_type_map[cart_type]]
    except KeyError:
        raise InvalidDiskImage("Unsupported cart type %d" % cart_type)


class A8CartHeader(object):
    # Atari Cart format described by https://sourceforge.net/p/atari800/source/ci/master/tree/DOC/cart.txt  NOTE: Big endian!
    format = np.dtype([
        ('magic', '|S4'),
        ('format', '>u4'),
        ('checksum', '>u4'),
        ('unused','>u4')
        ])
    file_format = "Cart"

    def __init__(self, bytes=None, create=False):
        self.image_size = 0
        self.cart_type = -1
        self.cart_name = ""
        self.cart_size = 0
        self.crc = 0
        self.unused = 0
        self.header_offset = 0
        self.num_banks = 0
        self.banks = []
        self.bank_size = 0
        self.bank_origin = 0
        self.main_size = 0
        self.main_offset = 0
        self.main_origin = 0
        self.possible_types = set()
        if create:
            self.header_offset = 16
            self.check_size(0)
        if bytes is None:
            return

        if len(bytes) == 16:
            values = bytes.view(dtype=self.format)[0]
            if values[0] != 'CART':
                raise InvalidCartHeader
            self.cart_type = int(values[1])
            self.crc = int(values[2])
            self.header_offset = 16
            self.set_type(self.cart_type)
        else:
            raise InvalidCartHeader

    def __str__(self):
        return "%s Cartridge (atari800 type=%d size=%d, %d banks, crc=%d)" % (self.cart_name, self.cart_type, self.cart_size, self.bank_size, self.crc)

    def __len__(self):
        return self.header_offset

    def to_array(self):
        raw = np.zeros([16], dtype=np.uint8)
        values = raw.view(dtype=self.format)[0]
        values[0] = 'CART'
        values[1] = self.cart_type
        values[2] = self.crc
        values[3] = 0
        return raw

    def set_type(self, cart_type):
        self.cart_type = cart_type
        c = get_cart(cart_type)
        self.cart_name = c[1]
        self.cart_size = c[2]
        self.main_size = self.cart_size
        if len(c) >= 6:
            self.main_size, self.main_offset, self.main_origin = c[3:6]
        if len(c) >= 9:
            self.banks = []
            self.bank_size, offset, self.bank_origin = c[6:9]
            s = self.cart_size - self.main_size
            while s > 0:
                self.banks.append(offset)
                offset += self.bank_size
                s -= self.bank_size

    def check_size(self, size):
        self.possible_types = set()
        k, r = divmod(size, 1024)
        if r == 0 or r == 16:
            for i, t in enumerate(known_cart_types):
                valid_size = t[0]
                if k == valid_size:
                    self.possible_types.add(i)


class AtariCartImage(DiskImageBase):
    def __init__(self, rawdata, cart_type, filename=""):
        self.cart_type = cart_type
        DiskImageBase.__init__(self, rawdata, filename)

    def __str__(self):
        return str(self.header)

    def read_header(self):
        bytes = self.bytes[0:16]
        try:
            self.header = A8CartHeader(bytes)
        except InvalidCartHeader:
            self.header = A8CartHeader()
            self.header.set_type(self.cart_type)

    def strict_check(self):
        if self.header.cart_type != self.cart_type:
            raise InvalidDiskImage("Cart type doesn't match type defined in header")

    def relaxed_check(self):
        if self.header.cart_type != self.cart_type:
            # force the header to be the specified cart type
            self.header = A8CartHeader()
            self.header.set_type(self.cart_type)

    def check_size(self):
        if self.header is None:
            return
        k, rem = divmod((len(self) - len(self.header)), 1024)
        c = get_cart(self.cart_type)
        if _dbg: log.debug("checking type=%d, k=%d, rem=%d for %s, %s" % (self.cart_type, k, rem, c[1], c[2]))
        if rem > 0:
            raise InvalidDiskImage("Cart not multiple of 1K")
        if k != c[2]:
            raise InvalidDiskImage("Image size %d doesn't match cart type %d size %d" % (k, self.cart_type, c[2]))

    def parse_segments(self):
        r = self.rawdata
        i = self.header.header_offset
        if i > 0:
            self.segments.append(ObjSegment(r[0:i], 0, 0, 0, i, name="Cart Header"))
        self.segments.extend(self.get_main_segment())
        self.segments.extend(self.get_banked_segments())

    def get_main_segment(self):
        r = self.rawdata
        start = self.header.header_offset + self.header.main_offset * 1024
        end = start + (self.header.main_size * 1024)
        s = ObjSegment(r[start:end], 0, 0, self.header.main_origin, name="Main Bank")
        return [s]

    def get_banked_segments(self):
        segments = []
        r = self.rawdata
        for i, offset in enumerate(self.header.banks):
            start = self.header.header_offset + offset * 1024
            end = start + (self.header.bank_size * 1024)
            s = ObjSegment(r[start:end], 0, 0, self.header.bank_origin, name="Bank #%d" % (i + 1))
            segments.append(s)
        return segments


def add_cart_header(bytes):
    header = A8CartHeader(create=True)
    header.check_size(len(bytes))
    hlen = len(header)
    data = np.empty([hlen + len(bytes)], dtype=np.uint8)
    data[0:hlen] = header.to_array()
    data[hlen:] = bytes
    return data
