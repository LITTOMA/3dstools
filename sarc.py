#!/usr/bin/python
import argparse
import os
import os.path
import struct
import sys

import zlib

SARC_HEADER_LEN = 0x14
SFAT_HEADER_LEN = 0x0c
SFNT_HEADER_LEN = 0x08

SARC_MAGIC = 'SARC'
SFAT_MAGIC = 'SFAT'
SFNT_MAGIC = 'SFNT'

READ_AMOUNT = 1024
DECOMP_AMOUNT = 512

STATE_SARC = 0
STATE_SFAT = 1
STATE_SFNT = 2
STATE_DATA = 3


class Sarc:
    invalid = False

    def __init__(self, filename, compressed=False, verbose=False):
        self.file = open(filename, 'rw')
        self.compressed = compressed
        self.verbose = verbose

        if os.path.exists(filename):
            if compressed:
                self.file_size = struct.unpack('>I', self.file.read(4))[0]
            else:
                self.file_size = os.stat(filename).st_size

    def save(self):
        pass

    def read(self):
        if self.compressed:
            z = zlib.decompressobj()
        state = STATE_SARC

        partial_data = ''
        eof = False
        get_more = True

        while not eof:
            read_data = self.file.read(READ_AMOUNT)
            eof = len(read_data) == 0

            if get_more:
                if self.compressed:
                    partial_data += z.decompress(z.unconsumed_tail + read_data, DECOMP_AMOUNT)
                else:
                    partial_data += read_data
                get_more = False

            if state == STATE_SARC:
                if len(partial_data) >= SARC_HEADER_LEN:
                    self._parse_header(partial_data[:SARC_HEADER_LEN])
                    if self.invalid:
                        return
                    partial_data = partial_data[SARC_HEADER_LEN:]
                    state = STATE_SFAT
                else:
                    get_more = True
            elif state == STATE_SFAT:
                if len(partial_data) >= SFAT_HEADER_LEN:
                    self._parse_fat_header(partial_data[:SFAT_HEADER_LEN])
                    if self.invalid:
                        return
                    partial_data = partial_data[SFAT_HEADER_LEN:]
                    state = STATE_SFNT
                else:
                    get_more = True
            elif state == STATE_SFNT:
                if len(partial_data) >= SFNT_HEADER_LEN:
                    self._parse_fnt_header(partial_data[:SFNT_HEADER_LEN])
                    if self.invalid:
                        return
                    partial_data = partial_data[SFNT_HEADER_LEN:]
                    state = STATE_DATA
                else:
                    get_more = True
            elif state == STATE_DATA:
                pass

    def _parse_header(self, data):
        magic, header_len, bom, file_len, data_offset, unknown = struct.unpack('=4s2H3I', data)

        order = None

        if bom == 0xFFFE:
            order = '>'
        elif bom == 0xFEFF:
            order = '<'

        if magic != SARC_MAGIC:
            print('Invalid SARC magic bytes: %s (expected "%s")' % (magic, SARC_MAGIC))
            self.invalid = True
            return

        if header_len != SARC_HEADER_LEN:
            print('Invalid SARC header length: %d (expected %d)' % (header_len, SARC_HEADER_LEN))
            self.invalid = True
            return

        if order is None:
            print('Invalid byte-order marker: 0x%x (expected either 0xFFFE or 0xFEFF)' % bom)
            self.invalid = True
            return

        if file_len != self.file_size:
            print('Invalid file size: %d (expected %d)' % (file_len, self.file_size))
            self.invalid = True
            return

        if data_offset > file_len or data_offset < SARC_HEADER_LEN + SFAT_HEADER_LEN + SFNT_HEADER_LEN:
            print('Invalid data offset: %d (outside of file)' % data_offset)
            self.invalid = True
            return

        if self.verbose:
            print('SARC Magic: %s' % magic)
            print('SARC Header length: %d' % header_len)
            print('SARC Byte order: %s' % order)
            print('SARC File size: %d' % file_len)
            print('SARC Data offset: %d' % data_offset)

            print('\nSARC Unknown: 0x%x' % unknown)

    def _parse_fat_header(self, data):
        pass

    def _parse_fnt_header(self, data):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SARC Archive Tool')
    parser.add_argument('-v', '--verbose', help='print more data when working', action='store_true', default=False)
    parser.add_argument('-z', '--zlib', help='use ZLIB to compress or decompress the archive', action='store_true',
                        default=False)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-x', '--extract', help='extract the SARC', action='store_true', default=False)
    group.add_argument('-c', '--create', help='create a SARC', action='store_true', default=False)
    group.add_argument('-t', '--list', help='list contents', action='store_true', default=False)
    parser.add_argument('-f', '--archive', metavar='archive', help='the SARC filename', default=None, required=True)
    parser.add_argument('file', help='files to add to an archive', nargs='*')
    args = parser.parse_args()

    archive_exists = os.path.exists(args.archive)

    if archive_exists and args.create:
        print('File exists: %s' % args.archive)
        answer = None
        while answer not in ('y', 'n'):
            if answer is not None:
                print('Please answer "y" or "n"')
            answer = raw_input('Overwrite existing file? (y/N) ').lower()

            if len(answer) == 0:
                answer = 'n'

        if answer == 'n':
            print('Aborted.')
            sys.exit(1)

    if not archive_exists and (args.extract or args.list):
        print('File not found!')
        print(args.archive)
        sys.exit(1)

    sarc = Sarc(args.archive, compressed=args.zlib, verbose=args.verbose)

    if args.extract or args.list:
        sarc.read()
