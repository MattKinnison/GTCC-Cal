from PIL import Image, ImageFont, ImageDraw
import textwrap
import ics
import arrow
import requests
import re
import random
import calendar
import os
import sys

directory = os.path.expanduser('~\\Pictures\\St. Monica Calendars')
months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec']

class liturgical_calendar:
    # A custom wrapper for the universalis calendar.
    # Limits print to one saint per day (choosen at random).
    # Removes ordinary days (weekdays without a feast day).
    # Removes titles associated with certain saints (i.e. martyr, doctor, etc.)
    # Replaces december dates with the O Antiphons associated with that day.

    O_antiphon_map = {"17 December": "O Sapientia",#\n(O Wisdom)",
                      '18 December': 'O Adonai',#\n(O Lord)',
                      '19 December': 'O Radix Jesse',#\n(O Root of Jesse)',
                      '20 December': 'O Clavis David',#\n(O Key of David)',
                      '21 December': 'O Oriens',#\n(O Dayspring)',
                      '22 December': 'O Rex Gentium',#\n(O King of the Nations)',
                      '23 December': 'O Emmanuel',#\n(O With Us is God)',
                      '24 December': ""}

    def is_interesting(self, feast):
        # Determines if an feast is worth advertizing

        if any(ft in feast for ft in ['Saint', 'Sunday']):
            # If it is a Sunday or has a saint, definitely advertize
            return True
        elif any(ft in feast for ft in ['Ordinary Time', 'Lent', 'Advent', 'after', 'of Easter', 'of Christmas', 'January', 'Saturday memorial']):
            # If it is a weekday without a saint (i.e. just in a given liturgical season), do not advertize. ALso skip every Saturday BVM memorial.
            return False
        else:
            # Default to including it is its something else. Who knows, could be interested
            return True

    def is_title(self, str):
        # Determines if a string contains a Saint's title

        # This list may need to be expanded
        titles = ['Priest', 'Virgin', 'Pope', 'Bishop', 'Martyr', 'Religious', 'Doctor', 'Abbot', 'Apostle', 'Evangelist' 'Deacon', 'Missionary']

        if any((x in str) for x in ['First', 'Mary', 'Corpus']):
            # Mary deserves here titles, and First and Corpus Christi cause bugs
            return False
        elif any((x in str) for x in titles):
            return True
        else:
            return False

    def __init__(self, fmt):
        self.lit_cal = ics.Calendar(requests.get('http://www.universalis.com/vcalendar.ics').text.encode('latin-1').decode('utf-8')).events
        self.fmt = fmt

    def get_feast_from_date(self, date):
        # TODO

        # Filter calendar for our date
        feast_names = [ft.name for ft in self.lit_cal if ft.begin.date() == date]

        # If there are multiple feast days listed seperately (unusual), limit to just the first one listed. Else, bypass the rest of this function.
        if feast_names:
            feasts = feast_names[0]
        else:
            return ''

        # Multiple days can be listed in a single string. This breaks those up.
        feasts_list = re.split(',\n or |,\n \(commemoration of ', feasts)

        # Limit list to those feasts worth advertizing
        feasts_list = [ft for ft in feasts_list if self.is_interesting(ft)]

        # If there aren't any feasts to advertize, bypass the rest of this function
        if not feasts_list:
            return ''

        # If there are multiple advertizable feasts, pick one randomly
        feast = random.choice(feasts_list)

        # Remove any hanging parentheses
        if (feast[-1] == ')') and ('(' not in feast):
            feast = feast[:-1]

        # Replace any December date with the O Antiphon from that day
        if "December" in feast:
            feast = self.O_antiphon_map[feast]

        return feast

    def abbreviate_feast(self, feast):
        # Sometimes feast days are too long for all calendar. This does its best to shorten those

        # Remove "The" from feast day
        feast = re.sub(r"The ", "", feast)

        # Abbreviate "Saints" to "Sts."
        feast = re.sub(r'Saints','Sts.', feast)

        # Abbreviate "Saint" to "St."
        feast = re.sub(r'Saint','St.', feast)

        # Don't abbrevaite All Saints!! (Bug fix)
        if feast == "All Sts.":
            feast = "All Saints Day"

        # Remove special titles from each saint
        feast_parts = feast.split(', ')
        feast_parts = [part.strip() for part in feast_parts if not self.is_title(part)]
        feast = ' '.join(feast_parts)

        return feast

    def __call__(self, draw, date, loc):

        # Get feast name with helper function
        feast = self.get_feast_from_date(date)

        # Abbreviate feast to fit on calendar
        feast = self.abbreviate_feast(feast)

        ## Actually draw on image ##
        # Break text into lines
        lines = textwrap.wrap(feast, width=self.fmt['char_width'])

        # Draw to image, spaces lines one after another
        for ndx, line in enumerate(lines):
            # If you can't fit full title still, shorten with "..."
            if (ndx == self.fmt['lines'] - 1) and (len(lines) > self.fmt['lines']):
                line = line + "..."
            elif ndx > self.fmt['lines'] - 1:
                line = ""

            draw.text((loc[0], loc[1] + ndx * self.fmt['font'].size), line, self.fmt['color'], font=self.fmt['font'])

class event_calendar:
    # Convert a .ics link into events on the calendar.
    # Format the date correctly.

    def printable_time(self, dt):
        # Convert to 12 hour time
        h = str(((dt.hour-1) % 12) + 1)

        # Ignore minutes if 0
        if dt.minute == 0:
            m = ""
        else:
            m = ':'+str(dt.minute).zfill(2)

        # Get AM/PM
        _m = 'AM' if dt.hour < 12 else 'PM'

        return h + m + _m

    def printable_times(self, item):

        # Exception list - Events with no offical end time (may need to be modified over time)
        start_only_keywords = {'Formation', '(Live)', '(Zoom)'}

        # Get start time using helper function
        start_time = self.printable_time(item.begin)

        if any([exem in item.name for exem in start_only_keywords]):
            # If a start only date, print start and bypass
            return start_time + " | "
        else:
            # Get end time using helper function
            end_time = self.printable_time(item.end)

            # If starts and ends in same half of the day, abbreviate start time
            if end_time[-2:] == start_time[-2:]:
                start_time = start_time[:-2]

            return start_time + "-" + end_time + " | "

    def make_printable(self, event):
        # Add a time to the event name (if applicable)

        str = event.name

        # If hourly event, give times
        if not event.all_day and (event.end - event.begin).days == 0:
            str = self.printable_times(event) + str

        return str

    def __init__(self, cal_link, fmt):
        self.cal_feed = ics.Calendar(requests.get(cal_link).text.encode('latin-1').decode('utf-8')).events

        # Convert all events to the central time zone (except all day events as they're different)
        for event in self.cal_feed:
            if not event.all_day:
                event.begin = event.begin.to('US/Central')
                event.end = event.end.to('US/Central')

        self.fmt = fmt

    def __call__(self, draw, dt, loc):

        ## All Day Events ##
        # Filter for all day events on this date
        all_day_events = [event for event in self.cal_feed if event.all_day and event.begin.date() <= dt.date() and event.end.date() > dt.date()]
        # Sort by first start date (then by last end date if two events start simultaneously)
        all_day_events = sorted(all_day_events, key=lambda event: (event.begin, event.end.timestamp*-1))

        ## Hourly Events ##
        # Filter for shorter events on this date
        hourly_events  = [event for event in self.cal_feed if not event.all_day and event.begin <= dt.ceil('day') and event.end >= dt.floor('day')]
        # Sort by first start date (then by last end date if two events start simultaneously)
        hourly_events = sorted(hourly_events, key=lambda event: (event.begin, event.end.timestamp*-1))

        # Combine events
        events = all_day_events + hourly_events

        # Turn into printable stings
        event_strs = [self.make_printable(event) for event in events]

        # Isolate events that have signups (may need to be modified over time)
        signup_events = ['33 Days', 'Consoling the Heart', 'SEEK Day']

        # Determine which events are signup events
        is_signup = [any([(s_e in e_str) for s_e in signup_events]) for e_str in event_strs]

        # Break into various lines for each event string
        event_strs = [textwrap.wrap(e_str, width=self.fmt['char_width']) for e_str in event_strs]

        # Start pixel adders
        bar_px = 0
        txt_px = 0

        ## Draw bar for event background ##
        for e, signup, lines in zip(events, is_signup, event_strs):
            if not signup:
                for line in lines:
                    # Horizontal line, so y is constant. Determine y
                    y = loc[1] + self.fmt['font'].size/2 + bar_px

                    # end_x depends on if event continues into next day. Calculate
                    end_x = loc[0] + self.fmt['day_width'] - 1
                    if e.end.shift(days=-1) > dt:
                        end_x = end_x + self.fmt['bar_width']

                    # Differentiate all day events in a different color
                    if e.all_day:
                        color = self.fmt['ad_color']
                    else:
                        color = self.fmt['color']

                    # Draw line
                    draw.line(((loc[0], y), (end_x, y)), fill=color, width=self.fmt['font'].size + self.fmt['spacing'] + 1)

                    # Move down
                    bar_px = bar_px + self.fmt['font'].size + self.fmt['spacing'] + 1

        ## Draw text for event background ##
        for e, signup, lines in zip(events, is_signup, event_strs):
            for line in lines:
                # Draw text

                if signup:
                    draw.text((loc[0] + self.fmt['offset'], loc[1] + txt_px), line, fill=self.fmt['color'], font=self.fmt['signup_font'])
                else:
                    if (not e.all_day) or (dt.weekday() == 6) or (e.begin.date() == dt.date()):
                        # Only fill if hourly event, or Sunday, or first day of multiple
                        draw.text((loc[0] + self.fmt['offset'], loc[1] + txt_px - 1), line, fill='white', font=self.fmt['font'])

                # Move down
                txt_px = txt_px + self.fmt['font'].size + self.fmt['spacing'] + 1

def draw_calendar(month_offset=1, start_time = arrow.now().floor('day')):
    # Formatting constraints for feast days
    feast_fmt = {'char_width': 21,
                 'lines': 2,
                 'color': (128,128,128),
                 'font': ImageFont.truetype("fonts\\Roboto-Regular.ttf", 11)}

    # Formatting constraints for events
    event_fmt = {'char_width': 23,
                 'color': (165,44,38),
                 'ad_color': (128, 128, 128),
                 'font': ImageFont.truetype("fonts\\Roboto-Bold.ttf", 12),
                 'signup_font': ImageFont.truetype("fonts\\Roboto-Regular.ttf", 12),
                 'day_width': 160,
                 'bar_width': 160/40,
                 'offset': 160/20,
                 'spacing': 3}

    # Initialize feast day object
    lit_cal = liturgical_calendar(feast_fmt)

    # Initialize event calendar object
    cal_link = 'https://calendar.google.com/calendar/ical/stmonicayoungadults%40gmail.com/public/basic.ics'
    event_cal = event_calendar(cal_link, event_fmt)

    # Get Monday after start_time at midnight
    first_day = start_time.shift(months=month_offset).floor('month') # Change month here

    # Pull image from template
    img = Image.open("templates/glance.png").convert('RGBA')
    draw = ImageDraw.Draw(img)

    # Initialize Fonts
    title = ImageFont.truetype("fonts\\Carme-Regular.ttf", 68)
    day_font = ImageFont.truetype("fonts\\Roboto-Black.ttf", 22)

    # Draw Month name on top of calendar
    draw.text((30, 14), first_day.format('MMMM'), 'white', font=title)

    day_bar_wdt = event_fmt['day_width']+event_fmt['bar_width']

    to_edit = set()

    # Find start week
    start_week = first_day.isocalendar()[1]

    # If its a Sunday, the start of the week is actually the next week
    if first_day.weekday() == 6:
         start_week = start_week + 1

    # Get number of weeks in previous year
    last_yr_NoW = first_day.shift(years=-1).isocalendar()[1]

    for day in range(calendar.monthrange(first_day.year,first_day.month)[1]):
        # Increment days
        wr_day = first_day.shift(days=day)

        # default weekday func has monday as first day of week. Shift it to Sunday
        DoW = (wr_day.weekday() + 1) % 7

        # Find week of month
        WoM = wr_day.isocalendar()[1] - start_week

        # If its a Sunday, the start of the week is actually next week
        if DoW == 0:
            WoM = WoM + 1

        # If week is less than zero. Index from last week of last year
        if WoM < 0 and wr_day.month == 1:
                # In January, add count from last week of last year
                WoM = WoM + last_yr_NoW

        # Draw calendar date onto calendar
        draw.text((8+(day_bar_wdt)*DoW, 189+WoM*102), str(wr_day.day), (0,0,0), font=day_font)

        # Draw Saint day onto calendar
        lit_cal(draw, wr_day.date(), (38+(day_bar_wdt)*DoW, 189+WoM*102))

        # Draw Events of day onto calendar
        event_cal(draw, wr_day, ((day_bar_wdt)*DoW, 216+WoM*102))

    # Save finalized image
    img.save(directory + '\\' + first_day.format('YY-MM_MMM') + '.png')
    return directory + '\\' + months[first_day.month-1] + '.png', sorted(list(to_edit), key=lambda event: (event.begin, event.end.timestamp*-1))


if __name__ == "__main__":
   draw_calendar(int(sys.argv[1]))
