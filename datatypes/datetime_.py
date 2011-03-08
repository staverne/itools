# -*- coding: UTF-8 -*-
# Copyright (C) 2004-2008 Juan David Ibáñez Palomar <jdavid@itaapy.com>
# Copyright (C) 2005 Piotr Macuk <piotr@macuk.pl>
# Copyright (C) 2007 Hervé Cauwelier <herve@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from the Standard Library
from time import mktime
from datetime import date, datetime, time, timedelta, tzinfo
from email.utils import parsedate_tz, mktime_tz, formatdate

# Import from itools
from itools.core import utc
from base import DataType


###########################################################################
# Parsing the wide family of date formats in Internet protocols
###########################################################################

class HTTPDate(DataType):
    """This datatype is named "HTTPDate" for historical reasons, but supports
    many of the date formats used in Internet protocols.
    """
    # TODO As specified by RFC 1945 (HTTP 1.0), should check HTTP 1.1

    @staticmethod
    def decode(data):
        """Decode dates in formats RFC 1123 (inc. 822), RFC-850, ANSI C's
        asctime() format, and non-standard formats sent by some HTTP
        clients.
        """
        parts = parsedate_tz(data)
        if parts is None:
            raise ValueError, 'date "%s" is not supported' % data
#        has_tz = parts[-1] is None
        timestamp = mktime_tz(parts)

        return datetime.fromtimestamp(timestamp)


    @staticmethod
    def encode(value):
        """Encode a datetime object to RFC 1123 format: ::

            Day, DD Month YYYY HH:MM:SS GMT

        "Day" and "Month" are the English names abbreviated.
        """
        # The given "value" must be a naive datetime object, we consider it
        # represents a local time.  Transform it to Unix time (always UTC).
        parts = value.timetuple()
        timestamp = mktime(parts)

        # Transform the Unix time to a string in RFC 2822 format (with "GMT"
        # instead of "-0000").
        return formatdate(timestamp, usegmt=True)



###########################################################################
# ISO 8601 (http://en.wikipedia.org/wiki/ISO_8601)
###########################################################################

# XXX Python dates (the datetime.date module) require the month and day,
# they are not able to represent lower precission dates as ISO 8601 does.
# In the long run we will need to replace Python dates by something else.

class ISOCalendarDate(DataType):
    """Extended formats (from max. to min. precission): %Y-%m-%d, %Y-%m, %Y

    Basic formats: %Y%m%d, %Y%m, %Y
    """

    @staticmethod
    def decode(data):
        if not data:
            return None

        # The year
        year = int(data[:4])
        data = data[4:]
        if not data:
            return date(year, 1, 1)

        # Extended format
        if data[0] == '-':
            data = data[1:]
            month = int(data[:2])
            data = data[2:]
            if not data:
                return date(year, month, 1)
            # The day
            day = int(data[1:])
            return date(year, month, day)

        # Basic format
        month = int(data[:2])
        data = data[2:]
        if not data:
            return date(year, month, 1)
        # The day
        day = int(data)
        return date(year, month, day)


    @staticmethod
    def encode(value):
        # We choose the extended format as the canonical representation
        if value is None:
            return ''
        return value.strftime('%Y-%m-%d')


# TODO ISOWeekDate
# TODO ISOOrdinalDate



class FixedOffset(tzinfo):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, sign, offset_h, offset_m):
        if sign == '+':
            fact = 1
        else:
            fact = -1
        minutes = fact * (offset_h * 60 + offset_m)
        self.__offset = timedelta(minutes=minutes)
        if offset_m:
            self.__name = '%c%.2d:%.2d' % (sign, offset_h, offset_m)
        else:
            self.__name = '%c%.2d:00' % (sign, offset_h)


    def utcoffset(self, dt):
        return self.__offset


    def tzname(self, dt):
        return self.__name


    def dst(self, dt):
        return timedelta(0)



class ISOTime(DataType):
    """Extended formats (from max. to min. precission): %H:%M:%S, %H:%M

    Basic formats: %H%M%S, %H%M, %H
    """


    @staticmethod
    def decode(data):
        if not data:
            return None

        # Timezone
        if data[-1] == 'Z':
            data = data[:-1]
            tzinfo = utc
        else:
            p_pos = data.find('+')
            m_pos = data.find('-')
            pos = m_pos * p_pos
            if pos > 0:
                tzinfo = None
            else:
                pos = -pos
                sign = data[pos]
                offset = data[pos+1:]
                if ':' in offset:
                    offset = offset.split(':')
                else:
                    offset = [offset[0:2], offset[2:]]
                o_h = int(offset[0])
                o_m = int(offset[1]) if offset[1] else 0
                data = data[:pos]
                tzinfo = FixedOffset(sign, o_h, o_m)

        # Extended formats
        if ':' in data:
            parts = data.split(':')
            n = len(parts)
            if n > 3:
                raise ValueError, 'unexpected time value "%s"' % data
            hour = int(parts[0])
            minute = int(parts[1])
            if n == 2:
                return time(hour, minute, tzinfo=tzinfo)
            second = int(parts[2])
            return time(hour, minute, second, tzinfo=tzinfo)

        # Basic formats
        hour = int(data[:2])
        data = data[2:]
        if not data:
            return time(hour, tzinfo=tzinfo)
        # Minute
        minute = int(data[:2])
        data = data[2:]
        if not data:
            return time(hour, minute, tzinfo=tzinfo)
        # Second
        second = int(data)
        return time(hour, minute, second, tzinfo=tzinfo)


    @staticmethod
    def encode(value):
        # We choose the extended format as the canonical representation
        if value is None:
            return ''
        fmt = '%H:%M:%S'
        if value.tzinfo is not None:
            suffixe = '%Z'
        else:
            suffixe = ''
        return value.strftime(fmt + suffixe)



class ISODateTime(DataType):

    @staticmethod
    def decode(value):
        if not value:
            return None
        date, time = value.split('T')
        date = ISOCalendarDate.decode(date)
        time = ISOTime.decode(time)

        return datetime.combine(date, time)


    @staticmethod
    def encode(value):
        if value is None:
            return ''
        fmt = '%Y-%m-%dT%H:%M:%S'
        if value.tzinfo is not None:
            fmt += '%z'
        return value.strftime(fmt)
