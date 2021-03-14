try:
    from pip import main as pipmain
except:
    from pip._internal import main as pipmain
try:
    from PIL import Image, ImageFont, ImageDraw
except:
    pipmain(['install','pillow'])
    from PIL import Image, ImageFont, ImageDraw
try:
    import textwrap
except:
    pipmain(['install','textwrap'])
    import textwrap
import ics
try:
    import arrow
except:
    pipmain(['install','arrow'])
    import arrow
import requests
import re
import random
import calendar
import os

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
        titles = ['Priest', 'Virgin', 'Pope', 'Bishop', 'Martyr', 'Religious', 'Doctor', 'Abbot', 'Apostle', 'Evangelist' 'Deacon']

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
            feast = O_antiphons[feast]

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
        hourly_events  = [event for event in self.cal_feed if event.begin <= dt.ceil('day') and event.end >= dt.floor('day')]
        # Sort by first start date (then by last end date if two events start simultaneously)
        hourly_events = sorted(hourly_events, key=lambda event: (event.begin, event.end.timestamp*-1))

        # Combine events
        events = all_day_events + hourly_events

        # Turn into printable stings
        event_strs = [self.make_printable(event) for event in events]

        # Break into various lines for each event string
        event_strs = [textwrap.wrap(e_str, width=self.fmt['char_width']) for e_str in event_strs]

        # Start pixel adders
        bar_px = 0
        txt_px = 0

        ## Draw bar for event background ##
        for e, lines in zip(events, event_strs):
            for line in lines:
                # Horizontal line, so y is constant. Determine y
                y = loc[1] + self.fmt['font'].size/2 + bar_px

                # end_x depends on if event continues into next day. Calculate
                end_x = loc[0] + self.fmt['day_width'] - 1
                if e.end.replace(days=-2) > dt:
                    end_x = end_x + self.fmt['bar_width']

                # Draw line
                draw.line(((loc[0], y), (end_x, y)), fill=self.fmt['color'], width=self.fmt['font'].size+4)

                # Move down
                bar_px = bar_px + self.fmt['font'].size

        ## Draw text for event background ##
        for lines in event_strs:
            for line in lines:
                # Draw text
                draw.text((loc[0] + self.fmt['offset'], loc[1] + txt_px - 1), line, fill='white', font=self.fmt['font'])

                # Move down
                txt_px = txt_px + self.fmt['font'].size



def populate_day(draw, cal_feed, n, wr_day, offset, bar_width, day_width, event_start_height, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width, first_day, px = 0):
    to_edit = set()
    # Iterate through the OrgSync Feed
    for item in cal_feed:

        if item.all_day:
            if item.begin.date() <= wr_day.date() and item.end.date() > wr_day.date():
                to_edit.add(item)
                px = draw_event(draw, item, n, px, wr_day, offset, bar_width, day_width, event_start_height, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width, first_day)
        elif item.begin <= wr_day.ceil('day') and item.end > wr_day.floor('day').replace(seconds=1):
        # ((item.begin >= wr_day.floor('day') and item.end < wr_day.replace(days=1)) or
        #     (item.all_day and (item.begin <= wr_day and item.end > wr_day.replace(days=1) )) or
        #     (item.begin.day != item.end.day and not item.all_day and (item.begin < wr_day.replace(days=1) and item.end >= wr_day))):
            to_edit.add(item)
            px = draw_event(draw, item, n, px, wr_day, offset, bar_width, day_width, event_start_height, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width, first_day)
    return to_edit

def next_weekday(d, weekday): # 0 = Monday, 1=Tuesday, 2=Wednesday...
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0: # Target day already happened this week
        days_ahead += 7
    return d.replace(days=days_ahead)

def lighten(color):
    return tuple(list(color)+[125])

def draw_event(draw, item, n, px, wr_day, offset, bar_width, day_width, event_start_height, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width, first_day):
    if not item.transparent:# and ((not item.all_day) or (item.begin <= wr_day.replace(days=1) and item.end >= wr_day)):
        # Create event string
        to_draw = ('' if item.all_day else make_date(item)) + item.name
        # Use textwrap to make sure line doesn't exceed calendar day
        px_adder = 0

        print(item.name, item.all_day)

        if item.all_day:
            for line in textwrap.wrap(to_draw, width=text_width):
                draw.line([((day_width+bar_width)*n,event_start_height+event_text_size/2+px+px_adder), ((day_width+bar_width)*n+day_width+(0 if item.end.replace(days=-2) <= wr_day else bar_width)-1,event_start_height+event_text_size/2+px+px_adder)], fill=(128,128,128), width=event_text_height+1) #(0,0,0)
                px_adder = px_adder + event_text_height
            if wr_day.weekday() == first_day or item.begin >= wr_day.replace(days=-1):
                px_adder = 0
                for line in textwrap.wrap(to_draw, width=text_width):
                    draw.text((offset+(day_width+bar_width)*n, event_start_height+px+px_adder),line,'white',font=all_day)
                    px_adder = px_adder + event_text_height
        elif item.begin.day != item.end.day:
            for line in textwrap.wrap(to_draw, width=text_width):
                draw.line([((day_width+bar_width)*n,event_start_height+event_text_size/2+px+px_adder), ((day_width+bar_width)*n+day_width+(0 if item.end.replace(days=-1) <= wr_day else bar_width)-1,event_start_height+event_text_size/2+px+px_adder)], fill=(165,44,38), width=event_text_height+1)
                px_adder = px_adder + event_text_height
            px_adder = 0
            for line in textwrap.wrap(to_draw, width=text_width):
                if wr_day.weekday() == first_day or item.begin >= wr_day:
                    draw.text((offset+(day_width+bar_width)*n, event_start_height+px+px_adder),line,'white',font=all_day)
                    px_adder = px_adder + event_text_height
        else:
            if "(Live)" not in to_draw and "(Zoom)" not in to_draw and "SEEK Day" not in to_draw: # For all dark events
                for line in textwrap.wrap(to_draw, width=text_width):
                    draw.line([((day_width+bar_width)*n,event_start_height+event_text_size/2+px+px_adder), ((day_width+bar_width)*n+day_width+(0 if item.end.replace(days=-1) <= wr_day else bar_width)-1,event_start_height+event_text_size/2+px+px_adder)], fill=(165,44,38), width=event_text_height+1)
                    px_adder = px_adder + event_text_height
                px_adder = 0
                for line in textwrap.wrap(to_draw, width=text_width):
                    if wr_day.weekday() == first_day or item.begin >= wr_day:
                        draw.text((offset+(day_width+bar_width)*n, event_start_height+px+px_adder),line,'white',font=all_day)
                        px_adder = px_adder + event_text_height
            else:
                for line in textwrap.wrap(to_draw, width=text_width):
                    draw.text((offset+(day_width+bar_width)*n, event_start_height+px+px_adder),line,(165,44,38),font=event)
                    px_adder = px_adder + event_text_height
        return px_adder + draw_desc(draw, item, n, px, wr_day, offset, bar_width, day_width, event_start_height, event_text_height, desc_text_height, desc, desc_width)
    else:
        return px

def week_at_a_glance(cal_feed, adj_week, start_time = arrow.now().floor('day'), spec_title = False):
    # Image constants
    day_width = 160
    bar_width = day_width/40
    offset = day_width/20
    event_text_size = 12
    text_width = 23
    desc_width = 23
    desc_text_size = 11
    event_text_height = round(1.25*event_text_size)
    desc_text_height = round(1.25*desc_text_size)
    event_start_height = 216
    feast_fmt = {'char_width': 21,
                 'lines': 2,
                 'color': (128,128,128),
                 'font': ImageFont.truetype("fonts\\Roboto-Regular.ttf", 11)}
    event_fmt = {'char_width': 23,
                 'color': (165,44,38),
                 'font': ImageFont.truetype("fonts\\Roboto-Bold.ttf", 12),
                 'day_width': 160,
                 'bar_width': 160/40,
                 'offset': 160/20}

    lit_cal = liturgical_calendar(feast_fmt)

    cal_link = 'https://calendar.google.com/calendar/ical/stmonicayoungadults%40gmail.com/public/basic.ics'
    event_cal = event_calendar(cal_link, event_fmt)

    # Get Monday after start_time at midnight
    first_day = start_time.replace(months=1).floor('month') # Change month here

    # Pull image from template
    img = Image.open("templates/glance.png").convert('RGBA')
    draw = ImageDraw.Draw(img)

    # Initialize Fonts
    title = ImageFont.truetype("fonts\\Carme-Regular.ttf", 88)
    day_font = ImageFont.truetype("fonts\\Roboto-Black.ttf", 22)
    all_day = ImageFont.truetype("fonts\\Roboto-Bold.ttf", event_text_size)
    event = ImageFont.truetype("fonts\\Roboto-Regular.ttf", event_text_size)

    # Draw Title
    #draw.text((offset, 20),spec_title if spec_title else week_str,(255, 222, 118),font=title)

    to_edit = set()
    # Loop through the 7 days of the week
    # for n in range(7):
    #     # Increment days
    #     wr_day = next_monday.replace(days=n)
    #     # Draw calendar date onto calendar
    #     draw.text((offset+(day_width+bar_width)*n, 198), str(wr_day.day), (0,0,0), font=day_font)
    #     # Draw Saint day onto calendar (max 2 lines)
    #     lines = textwrap.wrap(get_saints_day(wr_day, lit_cal), width=20)
    #     for ndx, line in enumerate(lines[:2]):
    #         draw.text((offset+30+(day_width+bar_width)*n, 198+desc_text_size*ndx), line + ('...' if ndx == 1 and len(lines) > 2 else ''), 'black', font=desc)
    #     to_edit.update(populate_day(draw, cal_feed, n, wr_day, offset, bar_width, day_width, event_start_height, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width, 0))
    # Loop through the 7 days of the week
    for day in range(calendar.monthrange(first_day.year,first_day.month)[1]):
        # Increment days
        wr_day = first_day.replace(days=day)
        week = wr_day.isocalendar()[1] - first_day.isocalendar()[1] + (0 if wr_day.weekday() == 6 else -1) + 1           # Calendar offset goes here
        if week < 0:
            week = week + 52
        n = [1,2,3,4,5,6,0][wr_day.weekday()]
        # Draw calendar date onto calendar
        draw.text((offset+(day_width+bar_width)*n, 189+week*102), str(wr_day.day), (0,0,0), font=day_font)
        #print(day, week, str(wr_day.day))
        # Draw Saint day onto calendar
        lit_cal(draw, wr_day.date(), (offset+30+(day_width+bar_width)*n, 189+week*102))

        # Draw Events of day onto calendar
        # loc[0] = (day_width+bar_width)*n
        # loc[1] = event_start_height
        event_cal(draw, wr_day, ((day_width+bar_width)*n, event_start_height+week*102))

        # to_edit.update(populate_day(draw, cal_feed, n, wr_day, offset, bar_width, day_width, event_start_height, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width, 0))
        #to_edit.update(populate_day(draw, cal_feed, n, wr_day, offset, bar_width, day_width, event_start_height+102*week, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width, 6))
    # Save finalized image
    img.save(directory + '\\' + months[first_day.month-1] + '.png')
    return directory + '\\' + months[first_day.month-1] + '.png', sorted(list(to_edit), key=lambda event: (event.begin, event.end.timestamp*-1))
