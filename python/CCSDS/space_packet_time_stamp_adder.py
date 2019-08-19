#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2019 Athanasios Theocharis <athatheoc@gmail.com>
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

import numpy
from gnuradio import gr
from datetime import datetime
from datetime import date
import pmt
import array
import space_packet

class space_packet_time_stamp_adder(gr.basic_block):
    """
    Time Stamp Adder (CCSDS 301.0-B-4)
    --- The user should study the time code formats book and fill only the necessary fields.

    --- On another note, the space packet parser, in case of a time stamp addition, will only display information
    if a PField is used, since metadata are crucial to the parsing of the time stamp.

    --- The user, in general, should check the code of the preferred time format and confirm that the behavior is
    the wanted one. Great care should be taken on the variability of the size. (E.g. in ASCII A time format,
    the user should define the size of the decimal fraction of the second subfield and should change the finalHeader array.)

    --- Automated time only prints a timestamp down to microseconds

    --- When defining an epoch, the user should check that it fits into the bytes that were assigned to hold the difference.
        E.g. If the epoch "0001 January 1" is defined in CDS, then it will not be able to fit today's date into a 16-bit
        DAYS part.
    """
    def __init__(self, input_manual_automatic, time_format, pfield, pfield_extension, time_code_identification_cuc,
                 epoch_year_cuc, epoch_month_cuc, epoch_day_cuc, basic_time_num_octets_cuc, fractional_time_num_octets_cuc, pfield_extension_appended,
                 additional_octets_basic_time_cuc, additional_octets_fractional_time_cuc, rsvd_cuc,
                 time_code_identification_cds, epoch_identification_cds, epoch_year_cds, epoch_month_cds, epoch_day_cds,
                 length_of_day_cds,
                 length_of_submillisecond_cds, time_code_identification_ccs, calendar_variation_ccs,
                 number_of_subsecond_ccs, year, month, day, hour, minute, second, microsecond, picosecond):
        gr.basic_block.__init__(self,
            name="space_packet_time_stamp_adder",
            in_sig=[],
            out_sig=[])

        ##################################################
        # Parameters
        ##################################################
        self.input_manual_automatic = input_manual_automatic
        self.time_format = time_format
        self.pfield = pfield #Checks if the P-Field will be used
        self.pfield_extension = pfield_extension #Checks if the PField will be appended
        self.time_code_identification_cuc = time_code_identification_cuc
        self.epoch_year_cuc = epoch_year_cuc
        self.epoch_month_cuc = epoch_month_cuc
        self.epoch_day_cuc = epoch_day_cuc
        self.basic_time_num_octets_cuc = basic_time_num_octets_cuc
        self.fractional_time_num_octets_cuc = fractional_time_num_octets_cuc
        self.pfield_extension_appended = pfield_extension_appended #Checks if the PField Extension will be appended
        self.additional_octets_basic_time_cuc = additional_octets_basic_time_cuc
        self.additional_octets_fractional_time_cuc = additional_octets_fractional_time_cuc
        self.rsvd_cuc = rsvd_cuc
        self.time_code_identification_cds = time_code_identification_cds
        self.epoch_identification_cds = epoch_identification_cds
        self.epoch_year_cds = epoch_year_cds
        self.epoch_month_cds = epoch_year_cds
        self.epoch_day_cds = epoch_day_cds
        self.length_of_day_cds = length_of_day_cds
        self.length_of_submillisecond_cds = length_of_submillisecond_cds
        self.time_code_identification_ccs = time_code_identification_ccs
        self.calendar_variation_ccs = calendar_variation_ccs
        self.number_of_subsecond_ccs = number_of_subsecond_ccs
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second
        self.microsecond = microsecond
        self.picosecond = picosecond
        ##################################################
        # Blocks
        ##################################################
        self.message_port_register_in(pmt.intern('in'))
        self.set_msg_handler(pmt.intern('in'), self.handle_msg)
        self.message_port_register_out(pmt.intern('out'))

    def handle_msg(self, msg_pmt):
        msg = pmt.cdr(msg_pmt)
        if not pmt.is_u8vector(msg):
            print
            "[ERROR] Received invalid message type. Expected u8vector"
            return
        packet = pmt.u8vector_elements(msg)

        mask = 0b11111111 #Use this to take the last 8 bits of a number

        if self.input_manual_automatic == 1:
            self.now = datetime.utcnow()
            self.year = self.now.year
            self.month = self.now.month
            self.day = self.now.day
            self.hour = self.now.hour
            self.minute = self.now.minute
            self.second = self.now.second
            self.microsecond = self.now.microsecond
            if self.length_of_submillisecond_cds >= 2:
                self.length_of_submillisecond_cds = 1
        else:
            self.now = datetime(self.year, self.month, self.day, self.hour, self.minute, self.second, self.microsecond)
        finalHeader = numpy.zeros(20, dtype=int).tolist()
        if self.time_format == 0: #CUC
            if self.pfield == 0:
                if self.pfield_extension == 0:
                    basic_time = 1 + self.basic_time_num_octets_cuc + self.additional_octets_basic_time_cuc
                    fractional_time = 1 + self.fractional_time_num_octets_cuc + self.additional_octets_fractional_time_cuc
                    size = basic_time + fractional_time + 2 #For the 2 pfields
                else:
                    basic_time = 1 + self.basic_time_num_octets_cuc
                    fractional_time = 1 + self.fractional_time_num_octets_cuc
                    size = basic_time + fractional_time + 1 #For the 1 pfeild

                finalHeader = numpy.zeros(size, dtype=int).tolist()
                finalHeader[0] = (self.pfield_extension << 7) + (self.time_code_identification_cuc << 4) + (self.basic_time_num_octets_cuc << 2) + (self.fractional_time_num_octets_cuc)
                finalHeader.append(array.array('B', self.secondsSinceEpoch().to_bytes(basic_time, 'big')).tolist())

            else:
                print "Agency should define unsegmented code"
        elif self.time_format == 1: #CDS
            if self.pfield == 0:
                temp_size = 0
                if self.length_of_submillisecond_cds == 1 or self.length_of_submillisecond_cds == 2:
                    temp_size = self.length_of_submillisecond_cds
                finalHeader = numpy.zeros(7 + 1*self.length_of_day_cds + 2*temp_size, dtype=int).tolist()
                finalHeader[0] = (self.pfield_extension << 7) + (self.time_code_identification_cds << 4) + (self.epoch_identification_cds << 3) + (self.length_of_day_cds << 2) + (self.length_of_submillisecond_cds)
                if self.length_of_day_cds == 0:
                    finalHeader.append(array.array('B', self.daysSinceEpoch().to_bytes(2, 'big')).tolist())
                    finalHeader.append(array.array('B', self.msOfTheDay().to_bytes(4, 'big')).tolist())
                    if temp_size == 1:
                        finalHeader.append(array.array('B', self.microsecond.to_bytes(2, 'big')).tolist())
                    elif temp_size == 2:
                        finalHeader.append(array.array('B', self.picosecond.to_bytes(4, 'big')).tolist())
                else:
                    finalHeader.append(array.array('B', self.daysSinceEpoch().to_bytes(3, 'big')).tolist())
                    finalHeader.append(array.array('B', self.msOfTheDay().to_bytes(4, 'big')).tolist())
                    if temp_size == 1:
                        finalHeader.append(array.array('B', self.microsecond.to_bytes(2, 'big')).tolist())
                    elif temp_size == 2:
                        finalHeader.append(array.array('B', self.picosecond.to_bytes(4, 'big')).tolist())
            else:
                print "Behavior should be defined by the user"
        elif self.time_format == 2: #CCS
            if self.pfield == 0:
                finalHeader = numpy.zeros(8 + self.number_of_subsecond_ccs, dtype=int).tolist()
                finalHeader[0] = (self.pfield_extension << 7) + (self.time_code_identification_ccs << 4) + (self.calendar_variation_ccs << 3) + (self.number_of_subsecond_ccs)
                finalHeader[1] = self.year >> 8
                finalHeader[2] = self.year & mask
                if self.calendar_variation_ccs == 0:
                    finalHeader[3] = self.month
                    finalHeader[4] = self.day
                else:
                    finalHeader[3] = (30*self.month + self.day) >> 8
                    finalHeader[4] = (30*self.month + self.day) & mask
                finalHeader[5] = self.hour
                finalHeader[6] = self.minute
                finalHeader[7] = self.second
                if self.number_of_subsecond_ccs >= 1:
                    finalHeader[8] = self.microsecond/10000
                if self.number_of_subsecond_ccs >= 2:
                    finalHeader[9] = (self.microsecond/100) % 100
                if self.number_of_subsecond_ccs >= 3:
                    finalHeader[10] = self.microsecond % 100
                if self.number_of_subsecond_ccs >= 4:
                    finalHeader[11] = (self.picosecond % 1000000)/10000
                if self.number_of_subsecond_ccs >= 5:
                    finalHeader[12] = (self.picosecond % 10000)/100
                if self.number_of_subsecond_ccs >= 6:
                    finalHeader[13] = self.microsecond % 100

            else:
                print "Behavior should be defined by the user"
        elif self.time_format == 3: #ASCII A
            finalHeader = numpy.zeros(17, dtype=int).tolist()
            finalHeader[0] = ord(str(self.year/1000))
            finalHeader[1] = ord(str(self.year/100 % 10))
            finalHeader[2] = ord(str(self.year/10 % 10))
            finalHeader[3] = ord(str(self.year % 10))
            finalHeader[4] = ord(str(self.month / 10))
            finalHeader[5] = ord(str(self.month % 10))
            finalHeader[6] = ord(str(self.day / 10))
            finalHeader[7] = ord(str(self.day % 10))
            finalHeader[8] = ord('T')
            finalHeader[9] = ord(str(self.hour / 10))
            finalHeader[10] = ord(str(self.hour % 10))
            finalHeader[11] = ord(str(self.minute/10))
            finalHeader[12] = ord(str(self.minute % 10))
            finalHeader[13] = ord(str(self.second/10))
            finalHeader[14] = ord(str(self.second % 10))
            finalHeader[15] = ord(str(self.microsecond/100000))
            finalHeader[16] = ord('Z')
        elif self.time_format == 4: #ASCII B
            finalHeader = numpy.zeros(16, dtype=int).tolist()
            finalHeader[0] = ord(str(self.year / 1000))
            finalHeader[1] = ord(str(self.year / 100 % 10))
            finalHeader[2] = ord(str(self.year / 10 % 10))
            finalHeader[3] = ord(str(self.year % 10))
            dayOfYear = self.month*30 + self.day
            finalHeader[4] = ord(str(dayOfYear / 100))
            finalHeader[5] = ord(str((dayOfYear / 10) % 10))
            finalHeader[6] = ord(str(dayOfYear % 10))
            finalHeader[7] = ord('T')
            finalHeader[8] = ord(str(self.hour / 10))
            finalHeader[9] = ord(str(self.hour % 10))
            finalHeader[10] = ord(str(self.minute / 1000))
            finalHeader[11] = ord(str(self.minute / 1000))
            finalHeader[12] = ord(str(self.second / 1000))
            finalHeader[13] = ord(str(self.second / 1000))
            finalHeader[14] = ord(str(self.microsecond / 100000))
            finalHeader[15] = ord('Z')
        else:
            print "Time Format Unknown"
        x = 0
        # for i in finalHeader:
        #     if i > 255:
        #         print i
        #         print x
        #         x = x + 1
        #     else:
        #         x = x+1

        finalPacket = numpy.append(finalHeader, packet)
        finalPacket = array.array('B', finalPacket[:])
        finalPacket = pmt.cons(pmt.PMT_NIL, pmt.init_u8vector(len(finalPacket), finalPacket))
        self.message_port_pub(pmt.intern('out'), finalPacket)

    def daysSinceEpoch(self):
        if self.epoch_identification_cds == 0:
            self.epoch_year_cds = 1958
            self.epoch_month_cds = 1
            self.epoch_day_cds = 1
        timestamp = (self.now.toordinal() - date(self.epoch_year_cds, self.epoch_month_cds, self.epoch_day_cds).toordinal())
        return timestamp

    def msOfTheDay(self):
        return self.hour*60*60*1000 + self.minute*60*1000 + self.second * 1000

    def secondsSinceEpoch(self):
        if self.time_code_identification_cuc == 1:
            self.epoch_year_cuc = 1958
            self.epoch_month_cuc = 1
            self.epoch_day_cuc = 1

        timestamp = (self.now.toordinal() - date(year = self.epoch_year_cuc, month = self.epoch_month_cuc, day = self.epoch_day_cuc).toordinal())*86400
        return timestamp