#! /usr/bin/env python

"""Report on cumulative time

For what it is worth, this is (c) copyright Tony Ibbs, but to be honest you
may use it as you wish, although I provide no support. It is intended purely
to make it easier for me to make sure that I am not working too few hours for
the particular customer to whom this particular version of the software has
been customised.
"""

from __future__ import division
from __future__ import print_function

import sys
import datetime
import re

class GiveUp(Exception):
    pass

MONTHS = {'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'May':5, 'Jun':6,
          'Jul':7, 'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12}

DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')

timespan_re = re.compile(r'(\d|\d\d):(\d\d)\.\.(\d|\d\d):(\d\d)')

class Report(object):

    # Sensible defaults for the number of hours I expect to work each day
    hours_per_day = {'Mon': 7.5,
                     'Tue': 7.5,
                     'Wed': 7.5,
                     'Thu': 7.5,
                     'Fri': 7.5,
                     'Sat': 0.0,
                     'Sun': 0.0}

    def __init__(self):
        self.hours_per_day = Report.hours_per_day.copy()
        self.year = datetime.date.today().year

        self.colon_methods = {':year': self.set_year,
                              ':expect': self.set_hours}

    def report_hours_per_day(self):
        """Report on the current setting of hours-per-day, Mon..Sun

            >>> r = Report()
            >>> r.report_hours_per_day()
            Hours per day: 7.5, 7.5, 7.5, 7.5, 7.5, 0.0, 0.0
        """
        print('Hours per day: {0}, {1}, {2}, {3}, {4}, {5}, {6}'.format(
            self.hours_per_day['Mon'],
            self.hours_per_day['Tue'],
            self.hours_per_day['Wed'],
            self.hours_per_day['Thu'],
            self.hours_per_day['Fri'],
            self.hours_per_day['Sat'],
            self.hours_per_day['Sun']))

    def set_hours(self, text):
        """Given text of the form 'Mon=7.0, Tue=6.0', amend the expected hours

        Note that whitespace after commas is optional, the case of the day
        mnemonics is ignored, and the ordering of the days is not relevant.

        For instance:

            >>> r = Report()
            >>> r.report_hours_per_day()
            Hours per day: 7.5, 7.5, 7.5, 7.5, 7.5, 0.0, 0.0
            >>> r.set_hours('Mon=6.0, tue=7.5, WED=7.5,thu=5.5, sat=1.0, fri=3.0,sun=4.0')
            >>> r.report_hours_per_day()
            Hours per day: 6.0, 7.5, 7.5, 5.5, 3.0, 1.0, 4.0
            >>> r.set_hours('Mon=0.0')
            >>> r.report_hours_per_day()
            Hours per day: 0.0, 7.5, 7.5, 5.5, 3.0, 1.0, 4.0

        but:

            >>> r.set_hours('fred')
            Traceback (most recent call last):
            ...
            GiveUp: 'fred' is not <day>=<hours>

            >>> r.set_hours('mon')
            Traceback (most recent call last):
            ...
            GiveUp: 'mon' is not <day>=<hours>

            >>> r.set_hours('fred=99')
            Traceback (most recent call last):
            ...
            GiveUp: 'fred' is not a recognised day name

            >>> r.set_hours('mon=awkward')
            Traceback (most recent call last):
            ...
            GiveUp: 'awkward' is not a floating point number of hours

            >>> r.set_hours('mon=9 tue=8')
            Traceback (most recent call last):
            ...
            GiveUp: 'mon=9 tue=8' contains whitespace - is there a missing comma?
        """
        parts = text.split(',')
        parts = [x.strip() for x in parts]
        for part in parts:
            if ' ' in part:
                raise GiveUp('{!r} contains whitespace - is there a missing comma?'.format(part))
            elements = part.split('=')
            if len(elements) != 2:
                raise GiveUp('{!r} is not <day>=<hours>'.format(part, text))
            day = elements[0]
            if day.capitalize() not in self.hours_per_day:
                raise GiveUp('{!r} is not a recognised day name'.format(day))
            try:
                hours = float(elements[1])
            except ValueError:
                raise GiveUp('{!r} is not a floating point number of hours'.format(elements[1]))
            self.hours_per_day[day.capitalize()] = hours

    def set_year(self, text):
        """Set the year, given it as text.

            >>> r = Report()
            >>> r.set_year('2003')
            >>> r.year
            2003
            >>> r.set_year('Fred')
            Traceback (most recent call last):
            ...
            GiveUp: 'Fred' is not an integer year
        """
        try:
            self.year = int(text.strip())
        except ValueError:
            raise GiveUp('{!r} is not an integer year'.format(text))

    def parse_colon_text(self, colon_word, rest):
        """Parse words from a line starting with a colon

        For example:

            >>> r = Report()
            >>> r.set_year('2013')
            >>> r.parse_colon_text(':year', '2003')
            >>> r.year
            2003
            >>> r.parse_colon_text(':expect', 'Mon=6.0')
            >>> r.report_hours_per_day()
            Hours per day: 6.0, 7.5, 7.5, 7.5, 7.5, 0.0, 0.0

        but:

            >>> r.parse_colon_text(':fred', '')
            Traceback (most recent call last):
            ...
            GiveUp: Unrecognised colon-command ':fred'
        """
        try:
            fn = self.colon_methods[colon_word]
            fn(rest)
        except KeyError:
            raise GiveUp('Unrecognised colon-command {!r}'.format(colon_word))

    def parse_hours_line(self, line):
        """Parse a line describing the hours for a day
        """
        parts = line.split('--')
        data = parts[0].rstrip()
        comment = ' '.join(parts[1:]).lstrip()

        spec = data.split()
        if len(spec) < 4 or (len(spec) > 4 and spec[3] != 'for'):
            raise GiveUp('Expecting "<day> <date> <month> <hours>"\n'
                         'or "<day> <date> <month> for <timespan> [<timespan> ...]"\n'
                         'not: {!r}'.format(data))

        day = spec[0]
        daynum = spec[1]
        month = spec[2]

        if day.capitalize() not in self.hours_per_day:
            raise GiveUp('Expected 3 letter day name, not {!r}'.format(day))
        day = day.capitalize()

        if month.capitalize() not in MONTHS:
            raise GiveUp('Expected 3 letter month name, not {!r}'.format(month))
        month = month.capitalize()

        try:
            daynum = int(daynum)
        except ValueError:
            raise GiveUp('Expected integer date (day of month), not {!r}'.format(daynum))

        date = datetime.date(self.year, MONTHS[month], daynum)
        if DAYS[date.weekday()] != day:
            raise GiveUp('{} {} {} should be {}, not {}'.format(daynum, month, self.year,
                         DAYS[date.weekday()], day))

        if spec[3] == 'for':
            spans = spec[4:]
            hours = 0
            for span in spans:
                match = re.match(timespan_re, span)
                if match is None or match.end() != len(span) or len(match.groups()) != 4:
                    raise GiveUp('Timespan {!r} is not <hh>:<mm>..<hh>:<mm>'.format(span))
                groups = match.groups()
                try:
                    start_time = datetime.timedelta(hours=int(groups[0]), minutes=int(groups[1]))
                except ValueError:
                    raise GiveUp('{}:{} is not a valid time, <hh>:<mm>'.format(groups[0], groups[1]))
                try:
                    end_time = datetime.timedelta(hours=int(groups[2]), minutes=int(groups[3]))
                except ValueError:
                    raise GiveUp('{}:{} is not a valid time'.format(groups[2], groups[3]))

                if start_time >= end_time:
                    raise GiveUp('Timespan {!r} is not a positive timespan'.format(span))

                delta = end_time - start_time
                delta_hours = delta.seconds / (60*60)
                hours += delta_hours
        else:
            hours = spec[3]
            try:
                hours = float(hours)
            except ValueError:
                raise GiveUp('Expected floating point hours, not {!r}'.format(hours))

        return day, daynum, month, self.year, hours, comment

    def parse_line(self, line):
        """Parse a line, returning None or a data tuple

        For instance:

            >>> r = Report()
            >>> lines = ['# a comment',
            ...          '',
            ...          ':year 2013',
            ...          'Thu 12 Sep 8.0  -- a comment',
            ...          ':expect Mon=7.0',
            ...          ':year 2003',
            ...          ' Wed 3 Sep  19.0   --  we  trim  edge  whitespace',
            ...          'Thu 4 Sep for 09:00..12:00 12:30..17:30 -- time spans',
            ...          'Fri 12 Sep for 8:30..9:30 -- 8:30, not 08:30']
            >>> for line in lines:
            ...    print(r.parse_line(line))
            None
            None
            None
            ('Thu', 12, 'Sep', 2013, 8.0, 'a comment')
            None
            None
            ('Wed', 3, 'Sep', 2003, 19.0, 'we  trim  edge  whitespace')
            ('Thu', 4, 'Sep', 2003, 8.0, 'time spans')
            ('Fri', 12, 'Sep', 2003, 1.0, '8:30, not 08:30')

        but:

            >>> r.parse_line('Something something something -- fred')
            Traceback (most recent call last):
            ...
            GiveUp: Expecting "<day> <date> <month> <hours>"
            or "<day> <date> <month> for <timespan> [<timespan> ...]"
            not: 'Something something something'

            >>> r.parse_line('Something 3 Sep 2.0 -- not a day name')
            Traceback (most recent call last):
            ...
            GiveUp: Expected 3 letter day name, not 'Something'

            >>> r.parse_line('Wed pardon Sep 2.0 -- not a date')
            Traceback (most recent call last):
            ...
            GiveUp: Expected integer date (day of month), not 'pardon'

            >>> r.parse_line('Wed 3 Wednesday 2.0 -- not a month')
            Traceback (most recent call last):
            ...
            GiveUp: Expected 3 letter month name, not 'Wednesday'

            >>> r.parse_line('Wed 3 Sep aagh -- silly hours')
            Traceback (most recent call last):
            ...
            GiveUp: Expected floating point hours, not 'aagh'

            >>> r.parse_line(':year 2013')
            >>> r.parse_line('Fri 12 Sep 9.0 -- wrong day of week')
            Traceback (most recent call last):
            ...
            GiveUp: 12 Sep 2013 should be Thu, not Fri

            >>> r.parse_line('Thu 12 Sep for fred -- too few ..')
            Traceback (most recent call last):
            ...
            GiveUp: Timespan 'fred' is not <hh>:<mm>..<hh>:<mm>

            >>> r.parse_line('Thu 12 Sep for 9:30..12:30..13:00 -- too many ..')
            Traceback (most recent call last):
            ...
            GiveUp: Timespan '9:30..12:30..13:00' is not <hh>:<mm>..<hh>:<mm>

            >>> r.parse_line('Thu 12 Sep for 999..09:30 -- no :')
            Traceback (most recent call last):
            ...
            GiveUp: Timespan '999..09:30' is not <hh>:<mm>..<hh>:<mm>

            >>> r.parse_line('Thu 12 Sep for 09:30..fred -- no :')
            Traceback (most recent call last):
            ...
            GiveUp: Timespan '09:30..fred' is not <hh>:<mm>..<hh>:<mm>

            >>> r.parse_line('Thu 12 Sep for 09:30..08:30 -- backwards')
            Traceback (most recent call last):
            ...
            GiveUp: Timespan '09:30..08:30' is not a positive timespan

        """
        line = line.strip()

        parts = line.split('#')
        text = parts[0]
        if not text:
            return None

        parts = text.split()
        if parts[0].startswith(':'):
            self.parse_colon_text(parts[0], text[len(parts[0]):])
        else:
            return self.parse_hours_line(text)

    def parse_lines(self, line_source):
        """Parse lines from reader, yielding tuples for actual hour reports.

        For instance:

            >>> r = Report()
            >>> lines = ['# a comment',
            ...          '',
            ...          ':year 2013',
            ...          'Thu 12 Sep 8.0  -- a comment',
            ...          ':expect Mon=7.0',
            ...          ':year 2003',
            ...          'Wed 3 Sep  19.0  -- a comment']
            >>> for data in r.parse_lines(lines):
            ...    print(data)
            ('Thu', 12, 'Sep', 2013, 8.0, 'a comment')
            ('Wed', 3, 'Sep', 2003, 19.0, 'a comment')
        """
        lineno = 0
        for line in line_source:
            lineno += 1
            try:
                data = self.parse_line(line)
            except GiveUp as e:
                raise GiveUp('Error in line {}\n{}'.format(lineno, e))
            if data:
                yield data

def report_file(filename):
    """Report on the hours described in the given filename.
    """

    r = Report()
    with open(filename) as fd:
        for data in r.parse_lines(fd):
            print(data)

def report(args):
    filename = None
    while args:
        word = args.pop(0)
        if word in ('-h', '-help', '--help', '/?', '/help'):
            print(__doc__)
            return
        elif word == '-doctest':
            import doctest
            failures, tests = doctest.testmod()
            if failures:
                raise GiveUp('The light is RED')
            else:
                print('The light is GREEN')
            return
        elif word[0] == '-' and not os.path.exists(word):
            raise GiveUp('Unexpected switch {:r}'.format(word))
        elif not filename:
            filename = word
        else:
            raise GiveUp('Unexpected argument {:r} (already got'
                         ' filename {:r}'.format(word. filename))

    if not filename:
        filename = 'hours.txt'

    try:
        report_file(filename)
    except GiveUp as e:
        raise GiveUp('Error reading file {!r}\n{}'.format(filename, e))

if __name__ == '__main__':
    args = sys.argv[1:]
    try:
        report(args)
    except GiveUp as e:
        print(e)
        sys.exit(1)

# vim: set tabstop=8 softtabstop=4 shiftwidth=4 expandtab:
