Report on cumulative time for a customer project.

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

For what it is worth, this is (c) copyright Tibs, but to be honest you may
use it as you wish, although I provide no support.

