#! /usr/bin/env python

"""Report on cumulative time for a customer project.

Usage::

  report_hours.py              -- report on hours.txt
  report_hours.py <filename>   -- report on <filename>

Switches::

    -c, -comments   -- show the text after "--" on recorded hours lines
    -g, -graph      -- show a "graph" of balance-of-hours plus/minus for
                       the project so far, down the right hand side
    -doctest        -- run the doctests. This ignores any filename.

Defaults to reading a file called "hours.txt" in the same directory as
this script.

Lines in the text file may be:

    * :year <year>
    * :days <number-of-days>
    * :expect <day-name>=<hours>[, <day-name>=hours> ...]
    * <day-name> <day> <month> <hours> [-- <text>]
    * <day-name> <day> <month> for <timespan> [<timespan> ...] [-- <text>]

where:

    * <year> is a year
    * <number-of-days> is the number of days for a project (PO)
    * <day-name> is a three-letter day mnemonic (case doesn't matter)
    * <month> is a three-letter month mnemonic (case doesn't matter)
    * <timespan> is of the form <hh>:<mm>..<hh>:<mm> (<hh> may be 1 or 2
      digits)

Anything after a '#' is ignored, and empty lines are ignored.

So a typical file might look like::

    :year 2013
    # The initial PO is for 20 7.5-hour days, i.e., 150 hours
    :days 20
    :expect Mon=6.5, Tue=7.5, Wed=7.5, Thu=6.0, Fri=7.5

    Tue  3 Sep  6.5     -- initial discussions, etc.
    Wed  4 Sep  8.5     -- my laptop, exploring, notebook
    Thu  5 Sep  for 9:00..12:00 12:30..18:00
    Fri  6 Sep  for 9:30..12:00 12:30..17:00

Date records must be in the correct order (ascending date), but there is no
requirement to specify hours for every day.

There is no intent to support multiple projects in a single file. My normal
use is to have both report_hours.py and hours.txt in a Dropbox folder, which
is specific to the customer.

XXX Add the ability to specify new (continuation) POs with an extra :days
XXX line. This should report hours per PO, in case the *actual* hours
XXX worked overlap the boundary,

For what it is worth, this is (c) copyright Tibs, but to be honest you may
use it as you wish, although I provide no support.
"""

from __future__ import division
from __future__ import print_function

import os
import sys
import re
import datetime

class GiveUp(Exception):
    pass

MONTHS = {'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4, 'May':5, 'Jun':6,
          'Jul':7, 'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12}

MONTH_NAME = {1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun',
              7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}

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
        self.project_days = None

        self.colon_methods = {':year': self.set_year,
                              ':expect': self.set_hours,
                              ':days': self.set_project_days}

    def report_hours_per_day(self, with_caption=True):
        """Report on the current setting of hours-per-day, Mon..Sun

            >>> r = Report()
            >>> r.report_hours_per_day()
            Hours per day: 7.5, 7.5, 7.5, 7.5, 7.5, 0.0, 0.0
            >>> r.report_hours_per_day(False)
            7.5, 7.5, 7.5, 7.5, 7.5, 0.0, 0.0
        """
        if with_caption:
            print('Hours per day:', end=' ')
        print('{0}, {1}, {2}, {3}, {4}, {5}, {6}'.format(
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
            GiveUp: 'fred' is not <day-name>=<hours>

            >>> r.set_hours('mon')
            Traceback (most recent call last):
            ...
            GiveUp: 'mon' is not <day-name>=<hours>

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
                raise GiveUp('{!r} is not <day-name>=<hours>'.format(part, text))
            day_name = elements[0]
            if day_name.capitalize() not in self.hours_per_day:
                raise GiveUp('{!r} is not a recognised day name'.format(day_name))
            try:
                hours = float(elements[1])
            except ValueError:
                raise GiveUp('{!r} is not a floating point number of hours'.format(elements[1]))
            self.hours_per_day[day_name.capitalize()] = hours

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

    def set_project_days(self, text):
        """Set how many days the project should run.

            >>> r = Report()
            >>> print(r.project_days)
            None
            >>> r.set_project_days('5')
            >>> print(r.project_days)
            5
            >>> r.set_project_days('Fred')
            Traceback (most recent call last):
            ...
            GiveUp: 'Fred' is not an integer number of days
        """
        try:
            self.project_days = int(text.strip())
        except ValueError:
            raise GiveUp('{!r} is not an integer number of days'.format(text))

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

        For instance:

            >>> r = Report()
            >>> r.set_year('2013')
            >>> r.parse_hours_line('Thu 12 Sep 8.0  -- a comment')
            (datetime.date(2013, 9, 12), 'Thu', 8.0, 'a comment')
            >>> r.set_year('2003')
            >>> r.set_hours('Mon=7.0')
            >>> r.parse_hours_line(' Wed 3 Sep  19.0   --  we  trim  edge  whitespace')
            (datetime.date(2003, 9, 3), 'Wed', 19.0, 'we  trim  edge  whitespace')
            >>> r.parse_hours_line('Thu 4 Sep for 09:00..12:00 12:30..17:30 -- time spans')
            (datetime.date(2003, 9, 4), 'Thu', 8.0, 'time spans')
            >>> r.parse_hours_line('Fri 12 Sep for 8:30..9:30 -- 8:30, not 08:30')
            (datetime.date(2003, 9, 12), 'Fri', 1.0, '8:30, not 08:30')
            >>> r.parse_hours_line('Fri 12 Sep holiday -- today')
            (datetime.date(2003, 9, 12), 'Fri', 7.5, 'today')
            >>> r.parse_hours_line('Fri 12 Sep pubhol -- today')
            (datetime.date(2003, 9, 12), 'Fri', 7.5, 'today')
            >>> r.parse_hours_line('Fri 12 Sep sick -- today')
            (datetime.date(2003, 9, 12), 'Fri', 7.5, 'today')

        but

            >>> r.parse_hours_line('Something something something -- fred')
            Traceback (most recent call last):
            ...
            GiveUp: Expecting "<day-name> <day> <month> <hours>"
            or "<day-name> <day> <month> for <timespan> [<timespan> ...]"
            not: 'Something something something'

            >>> r.parse_hours_line('Something 3 Sep 2.0 -- not a day name')
            Traceback (most recent call last):
            ...
            GiveUp: Expected 3 letter day name, not 'Something'

            >>> r.parse_hours_line('Wed pardon Sep 2.0 -- not a date')
            Traceback (most recent call last):
            ...
            GiveUp: Expected integer day (day of month), not 'pardon'

            >>> r.parse_hours_line('Wed 3 Wednesday 2.0 -- not a month')
            Traceback (most recent call last):
            ...
            GiveUp: Expected 3 letter month name, not 'Wednesday'

            >>> r.parse_hours_line('Wed 3 Sep aagh -- silly hours')
            Traceback (most recent call last):
            ...
            GiveUp: Expected floating point hours, not 'aagh'

            >>> r.set_year('2013')
            >>> r.parse_hours_line('Fri 12 Sep 9.0 -- wrong day of week')
            Traceback (most recent call last):
            ...
            GiveUp: 12 Sep 2013 should be Thu, not Fri

            >>> r.parse_hours_line('Thu 12 Sep for fred -- too few ..')
            Traceback (most recent call last):
            ...
            GiveUp: Timespan 'fred' is not <hh>:<mm>..<hh>:<mm>

            >>> r.parse_hours_line('Thu 12 Sep for 9:30..12:30..13:00 -- too many ..')
            Traceback (most recent call last):
            ...
            GiveUp: Timespan '9:30..12:30..13:00' is not <hh>:<mm>..<hh>:<mm>

            >>> r.parse_hours_line('Thu 12 Sep for 999..09:30 -- no :')
            Traceback (most recent call last):
            ...
            GiveUp: Timespan '999..09:30' is not <hh>:<mm>..<hh>:<mm>

            >>> r.parse_hours_line('Thu 12 Sep for 09:30..fred -- no :')
            Traceback (most recent call last):
            ...
            GiveUp: Timespan '09:30..fred' is not <hh>:<mm>..<hh>:<mm>

            >>> r.parse_hours_line('Thu 12 Sep for 09:30..08:30 -- backwards')
            Traceback (most recent call last):
            ...
            GiveUp: Timespan '09:30..08:30' is not a positive timespan
        """
        parts = line.split('--')
        data = parts[0].rstrip()
        comment = ' '.join(parts[1:]).lstrip()

        spec = data.split()
        if len(spec) < 4 or (len(spec) > 4 and spec[3] not in ('for', 'holiday')):
            raise GiveUp('Expecting "<day-name> <day> <month> <hours>"\n'
                         'or "<day-name> <day> <month> for <timespan> [<timespan> ...]"\n'
                         'or "<day-name> <day> <month> holiday"\n'
                         'or "<day-name> <day> <month> pubhol"\n'
                         'or "<day-name> <day> <month> sick"\n'
                         'not: {!r}'.format(data))

        day_name = spec[0]
        day = spec[1]
        month = spec[2]

        if day_name.capitalize() not in self.hours_per_day:
            raise GiveUp('Expected 3 letter day name, not {!r}'.format(day_name))
        day_name = day_name.capitalize()

        if month.capitalize() not in MONTHS:
            raise GiveUp('Expected 3 letter month name, not {!r}'.format(month))
        month = month.capitalize()

        try:
            day = int(day)
        except ValueError:
            raise GiveUp('Expected integer day (day of month), not {!r}'.format(day))

        date = datetime.date(self.year, MONTHS[month], day)
        if DAYS[date.weekday()] != day_name:
            raise GiveUp('{} {} {} should be {}, not {}'.format(day, month, self.year,
                         DAYS[date.weekday()], day_name))

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
        elif spec[3] in ('holiday', 'pubhol', 'sick'):
            hours = self.hours_per_day[day_name]
        else:
            hours = spec[3]
            try:
                hours = float(hours)
            except ValueError:
                # Make a crude check for a possible common mistake
                if '..' in hours and ':' in hours:
                    raise GiveUp('Expected floating point hours, not {!r}'
                                 ' - did you mean "for {}"?'.format(hours, hours))
                else:
                    raise GiveUp('Expected floating point hours, not {!r}'.format(hours))

        return date, day_name, hours, comment

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
            (datetime.date(2013, 9, 12), 'Thu', 8.0, 'a comment')
            None
            None
            (datetime.date(2003, 9, 3), 'Wed', 19.0, 'we  trim  edge  whitespace')
            (datetime.date(2003, 9, 4), 'Thu', 8.0, 'time spans')
            (datetime.date(2003, 9, 12), 'Fri', 1.0, '8:30, not 08:30')

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
            ...          ':expect Mon=7.0',
            ...          ':year 2003',
            ...          'Wed 3 Sep  19.0  -- a comment',
            ...          ':year 2013',
            ...          'Thu 12 Sep 8.0  -- a comment']
            >>> for data in r.parse_lines(lines):
            ...    print(data)
            (datetime.date(2003, 9, 3), 'Wed', 19.0, 'a comment')
            (datetime.date(2013, 9, 12), 'Thu', 8.0, 'a comment')

        but:

            >>> lines = [':year 2013',
            ...          'Thu 12 Sep 8.0  -- a comment',
            ...          ':year 2003',
            ...          'Wed 3 Sep  19.0  -- a comment']
            >>> for data in r.parse_lines(lines):
            ...    print(data)
            Traceback (most recent call last):
            ...
            GiveUp: Records out of order, 2003-09-03 comes before 2013-09-12
        """
        lineno = 0
        prev = None
        for line in line_source:
            lineno += 1
            try:
                data = self.parse_line(line)
            except GiveUp as e:
                raise GiveUp('Error in line {}\n{}'.format(lineno, e))

            if data:
                if prev and data < prev:
                    raise GiveUp('Records out of order, {} comes before {}'.format(
                        data[0].isoformat(), prev[0].isoformat()))
                prev = data
                yield data

    def show_hours(self, day, hours, width=11):
        """Return a picture of the hours for this day.
        """
        BASE = '*'
        EXTR = '^'
        MISS = '`'

        base = int(hours*2)
        norm = int(self.hours_per_day[day]*2)
        width = width*2

        parts = []

        if base == norm:
            parts.append(BASE*base)

        elif base < norm:
            parts.append(BASE*base)
            parts.append(MISS*(norm-base))

        else:
            parts.append(BASE*norm)
            parts.append(EXTR*(base-norm))

        picture = ''.join(parts)

        desc = '{{:{:d}s}}|'.format(width)
        return desc.format(picture)

    def show_balance(self, day, balance, before=4, after=15):
        """Return a picture of the balance of hours for this day.

        'before' is the number of hours we can show on the left (negative)
        side of the "zero" bar.

        'after' is the number of hours we can show on the right (positive)
        side.

        If 'before' is too small, then the "zero" bar will get wobbly.

        If 'after' is too small, then anything after this "picture" will
        be wobbly.
        """
        EXTR = '+'
        LESS = '-'
        SPAC = ' '

        count = int(2*balance)
        before = int(2*before)
        after = int(2*after)
        if balance < 0:
            left = (before - -count)*SPAC + -count*LESS
            right = after*SPAC
        else:
            left = before*SPAC
            right = count*EXTR + (after - count)*SPAC
        return '%s:%s'%(left, right)

    def report_lines(self, line_source, show_comments=False, with_graph=False):
        """Report on the information from our reader.

        If 'show_comments' is True, then we show the extra text after any '--'
        on the hours lines.

        For instance:

            >>> r = Report()
            >>> lines = ['# a more realistic example',
            ...          ':expect Mon=6.0, Tue=6.0, Wed=6.0, Thu=6.0, Fri=6.0',
            ...          ':days 20',
            ...          ':year 2013',
            ...          'Mon  2 Sep  4.0     -- first day',
            ...          'Tue  3 Sep  6.5     -- initial discussions, etc.',
            ...          'Wed  4 Sep  8.5     -- my laptop, exploring, notebook',
            ...          'Thu  5 Sep  6.5',
            ...          'Fri  6 Sep  8.5     -- setting up the two computers',
            ...          'Mon  9 Sep  7.0     -- inc. Kynesim lunch',
            ...          'Tue 10 Sep  7.5',
            ...          'Wed 11 Sep  for 9:00..12:00  12:30..17:30 # i.e., 3 + 5 = 8',
            ...          'Thu 12 Sep  for 9:30..12:00  12:30..15:30 # i.e., 2.5 + 3 = 5.5',
            ...          'Fri 13 Sep  0.0     -- not at this work today',
            ...         ]
            >>> r.report_lines(lines, False, True)
            2013
            -Mon  2 Sep  4.0 |********````          |  -2.0 |    ----:
             Tue  3 Sep  6.5 |************^         |  -1.5 |     ---:
             Wed  4 Sep  8.5 |************^^^^^     |   1.0 |        :++
             Thu  5 Sep  6.5 |************^         |   1.5 |        :+++
             Fri  6 Sep  8.5 |************^^^^^     |   4.0 |        :++++++++
            -Mon  9 Sep  7.0 |************^^        |   5.0 |        :++++++++++
             Tue 10 Sep  7.5 |************^^^       |   6.5 |        :+++++++++++++
             Wed 11 Sep  8.0 |************^^^^      |   8.5 |        :+++++++++++++++++
             Thu 12 Sep  5.5 |***********`          |   8.0 |        :++++++++++++++++
             Fri 13 Sep  0.0 |````````````          |   0.0 |        :
            <BLANKLINE>
            Summary for 2013-09-02 to 2013-09-13:
             Worked 62.0 hours over 9 days
                    62.0 hours is   8.3 (7.5-hour) days
                    or 41% of the project total 20 days (150.0 hours)
                       leaving 88.0 hours, or 11.7 (7.5-hour) days, to do
             Hours per week is currently set to 30.0
             with hours-per-day (Mon-Sun) as 6.0, 6.0, 6.0, 6.0, 6.0, 0.0, 0.0
             Using the hours-per-day currently set, expected 54.0 hours
             Giving a balance +8.0 hours, +1.1 days
            >>> r.report_lines(lines, True, True)
            2013
            -Mon  2 Sep  4.0 |********````          |  -2.0 |    ----:                               (first day)
             Tue  3 Sep  6.5 |************^         |  -1.5 |     ---:                               (initial discussions, etc.)
             Wed  4 Sep  8.5 |************^^^^^     |   1.0 |        :++                             (my laptop, exploring, notebook)
             Thu  5 Sep  6.5 |************^         |   1.5 |        :+++
             Fri  6 Sep  8.5 |************^^^^^     |   4.0 |        :++++++++                       (setting up the two computers)
            -Mon  9 Sep  7.0 |************^^        |   5.0 |        :++++++++++                     (inc. Kynesim lunch)
             Tue 10 Sep  7.5 |************^^^       |   6.5 |        :+++++++++++++
             Wed 11 Sep  8.0 |************^^^^      |   8.5 |        :+++++++++++++++++
             Thu 12 Sep  5.5 |***********`          |   8.0 |        :++++++++++++++++
             Fri 13 Sep  0.0 |````````````          |   0.0 |        :                               (not at this work today)
            <BLANKLINE>
            Summary for 2013-09-02 to 2013-09-13 (1 week):
             Worked 62.0 hours over 9 days
                    62.0 hours is   8.3 (7.5-hour) days
                    or 41% of the project total 20 days (150.0 hours)
                       leaving 88.0 hours, or 11.7 (7.5-hour) days, to do
             Hours per week is currently set to 30.0
             with hours (Mon-Sun) as 6.0, 6.0, 6.0, 6.0, 6.0, 0.0, 0.0
             Given the hours-per-day currently set, expected 54.0 hours, balance +8.0
            >>> r.report_lines(lines, False, False)
            2013
            -Mon  2 Sep  4.0 |********````          |
             Tue  3 Sep  6.5 |************^         |
             Wed  4 Sep  8.5 |************^^^^^     |
             Thu  5 Sep  6.5 |************^         |
             Fri  6 Sep  8.5 |************^^^^^     |  34.0
            -Mon  9 Sep  7.0 |************^^        |
             Tue 10 Sep  7.5 |************^^^       |
             Wed 11 Sep  8.0 |************^^^^      |
             Thu 12 Sep  5.5 |***********`          |
             Fri 13 Sep  0.0 |````````````          |  28.0
            <BLANKLINE>
            Summary for 2013-09-02 to 2013-09-13 (1 week):
             Worked 62.0 hours over 9 days
                    62.0 hours is   8.3 (7.5-hour) days
                    or 41% of the project total 20 days (150.0 hours)
                       leaving 88.0 hours, or 11.7 (7.5-hour) days, to do
             Hours per week is currently set to 30.0
             with hours-per-day (Mon-Sun) as 6.0, 6.0, 6.0, 6.0, 6.0, 0.0, 0.0
             Using the hours-per-day currently set, expected 54.0 hours
             Giving a balance +8.0 hours, +1.1 days
        """
        year = None
        total = 0.0
        total_expected = 0.0
        total_extra = 0.0
        first = last = None
        days_worked = 0
        week_total = 0.0
        for date, day, hours, comment in self.parse_lines(line_source):

            if date.year != year:
                print('{}'.format(date.year))
                year = date.year

            expected = self.hours_per_day[day]
            extra = hours - expected

            picture1 = self.show_hours(day, hours)

            # We assume that zero length days are holiday, or weekend,
            # and are thus to be ignored (or it all goes very strange)
            if hours:
                days_worked += 1
                total += hours
                total_expected += expected
                total_extra += extra
                picture2 = self.show_balance(day, total_extra)
            else:
                picture2 = self.show_balance(day, 0)

            parts = []
            parts.append('{}{} {:2d} {}'.format(
                '-' if day == 'Mon' else
                '~' if day in ('Sat', 'Sun') else ' ',
                day, date.day, MONTH_NAME[date.month]))

            parts.append('{:4.1f} |{}'.format(hours, picture1))

            if with_graph:
                if hours:
                    parts.append('{:5.1f} |{}'.format(total_extra, picture2))
                else:
                    parts.append('{:5.1f} |{}'.format(0.0, picture2))
            else:
                week_total += hours
                # Treating Friday as the end-of-week for reporting week totals
                # does mean that if I ever work Saturday or Sunday for a
                # project it will get reported the next week, which may be a
                # bit odd - but worry about that if/when it becomes a concern
                if day == 'Fri':
                    parts.append('{:5.1f}'.format(week_total))
                    week_total = 0.0

            if show_comments and comment:
                parts.append('({})'.format(comment))

            # If we're not printing comments, we'll have trailing spaces
            # from picture2, so just strip them away
            print(' '.join(parts).rstrip())

            if not first:
                first = date
            last = date

        print()

        if not with_graph and last and last.weekday() != 4:    # i.e., Friday
            print('Week so far {:.1f} hours'.format(week_total))

        first_day = first.toordinal()
        last_day = last.toordinal()
        elapsed = last_day - first_day + 1
        weeks = elapsed // 7

        print('Summary for {} to {} ({} week{}):'.format(
            first.isoformat(), last.isoformat(), weeks, '' if weeks == 1 else 's'))

        print(' Worked {:.1f} hour{} over {} day{}'.format(
            total, '' if total == 1 else 's',
            days_worked, '' if days_worked==1 else 's'))

        virtual_days = total / 7.5
        print('        {:.1f} hour{} is   {:.1f} (7.5-hour) day{}'.format(
            total, '' if total == 1 else 's',
            virtual_days, '' if virtual_days==1 else 's'))
        if self.project_days:
            print('        or {:.0%} of the project total {} day{} ({:.1f} hours)'.format(
                total / (self.project_days * 7.5),
                self.project_days, '' if self.project_days == 1 else 's',
                self.project_days*7.5))
            hours_left = self.project_days * 7.5 - total
            full_days_left = self.project_days - virtual_days
            print('           leaving {:.1f} hour{}, or {:.1f} (7.5-hour)'
                  ' day{}, to do'.format(
                hours_left,
                '' if hours_left == 1 else 's',
                full_days_left,
                '' if full_days_left == 1 else 's'))

        print(' Hours per week is currently set to {:.1f}'.format(
            sum(self.hours_per_day.values())))
        print(' with hours-per-day (Mon-Sun) as', end=' ')
        self.report_hours_per_day(False)

        print(' Using the hours-per-day currently set, expected {:.1f}'
              ' hours'.format(total_expected))

        if total_extra > 7.5:
            print(' Giving a balance of {:+.1f} hour{}, {:+.1f} days'.format(total_extra,
                '' if abs(total_extra)==1.0 else 's', total_extra/7.5))
        else:
            print(' Giving a balance of {:+.1f} hour{}'.format(total_extra,
                '' if abs(total_extra)==1.0 else 's'))

def report_file(filename, show_comments=False, with_graph=False):
    """Report on the hours described in the given filename.

    If 'show_comments' is True, then we show the extra text after any '--'
    on the hours lines.
    """

    r = Report()
    with open(filename) as fd:
        r.report_lines(fd, show_comments, with_graph)

def report(args):
    filename = None
    show_comments = False
    with_graph = False
    while args:
        word = args.pop(0)
        if word in ('-h', '-help', '--help', '/?', '/help'):
            print(__doc__)
            return
        elif word in ('-g', '-graph'):
            with_graph = True
        elif word in ('-c', '-comments'):
            show_comments = True
        elif word == '-doctest':
            import doctest
            failures, tests = doctest.testmod()
            if failures:
                raise GiveUp('The light is RED')
            else:
                print('The light is GREEN')
            return
        elif word[0] == '-' and not os.path.exists(word):
            raise GiveUp('Unexpected switch {!r}'.format(word))
        elif not filename:
            filename = word
        else:
            raise GiveUp('Unexpected argument {!r} (already got'
                         ' filename {!r}'.format(word. filename))

    if not filename:
        this_file = __file__
        this_dir = os.path.split(this_file)[0]
        filename = os.path.join(this_dir, 'hours.txt')

    try:
        report_file(filename, show_comments, with_graph)
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
