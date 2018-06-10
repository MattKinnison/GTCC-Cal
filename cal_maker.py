from PIL import Image, ImageFont, ImageDraw
import datetime
import dateutil.parser
import pytz
import textwrap
import ics
import arrow
import requests
import re
import random
import calendar
import os

directory = os.path.expanduser('~/Pictures/GTCC Calendars')

eastern = pytz.timezone('US/Eastern')

months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

lit_cal = ics.Calendar(requests.get('http://www.universalis.com/vcalendar.ics').text.encode('latin-1').decode('utf-8')).events

# Set Category colors
colors = {  "Faith Formation": (136,40,136),
            "Community Life": (57,83,164),
            "Freshmen Events": (57,83,164),
            "Liturgy": (225,72,154),
            "Outreach": (12,128,64),
            "Knights of Columbus": (237,31,36),
            "Graduate Student Events": (246,133,32),
            "FOCUS": (2,147,140),
            "Other": (0,0,0)
          }

gt_order = {"Faith Formation": 4,
            "Community Life": 5,
            "Freshmen Events": 5,
            "Liturgy": 1,
            "Outreach": 2,
            "Knights of Columbus": 0,
            "Graduate Student Events": 3,
            "FOCUS": 0,
            "Other": 0
          }

def d_to_dt(d):
    return eastern.localize(datetime.datetime.combine(d,datetime.time.min))

def is_interesting(event):
    if 'Saint' in event:
        return True
    if 'Sunday' in event:
        return True
    elif 'Ordinary Time' in event:
        return False
    elif 'Lent' in event:
        return False
    elif 'Advent' in event:
        return False
    elif 'after' in event:
        return False
    elif 'of Easter' in event:
        return False
    elif 'of Christmas' in event:
        return False
    elif 'January' in event:
        return False
    elif 'December' in event:
        return False
    elif'Saturday memorial' in event:
        return False
    else:
        return True

def is_not_title(word):
    if 'First' in word:
        return True
    elif 'Mary' in word:
        return True
    elif 'Corpus' in word:
        return True
    elif 'Priest' in word:
        return False
    elif 'Virgin' in word:
        return False
    elif 'Pope' in word:
        return False
    elif 'Bishop' in word:
        return False
    elif 'Martyr' in word:
        return False
    elif 'Religious' in word:
        return False
    elif 'Doctor' in word:
        return False
    elif 'Abbot' in word:
        return False
    elif 'Apostle' in word:
        return False
    elif 'Evangelist' in word:
        return False
    elif 'Deacon' in word:
        return False
    else:
        return True

def get_saints_day(wr_day, lit_cal):
    day_string = [holy_day.name for holy_day in lit_cal if holy_day.begin.date() == wr_day.date()][0]
    day_events = [event for event in re.split(',\n or |,\n \(commemoration of ',day_string) if is_interesting(event)]
    if day_events:
        word = ' '.join([word.strip() for word in random.choice(day_events).split(', ') if is_not_title(word)])
        return word if word[-1] != ')' and '(' not in word else word[:-1]
    else:
        return ''

def next_weekday(d, weekday): # 0 = Monday, 1=Tuesday, 2=Wednesday...
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0: # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)

def lighten(color):
    return tuple(list(color)+[125])

def make_date(item):
    return (str(((item['event:startdate'].hour-1) % 12)+1) +
                ('' if item['event:startdate'].minute == 0 else (':'+str(item['event:startdate'].minute).zfill(2))) +
                (('AM' if item['event:startdate'].hour < 12 else 'PM') if ('AM' if item['event:startdate'].hour < 12 else 'PM') != ('AM' if item['event:enddate'].hour < 12 else 'PM') else '') +
                '-' + str(((item['event:enddate'].hour-1) % 12)+1) +
                ('' if item['event:enddate'].minute == 0 else (':'+str(item['event:enddate'].minute).zfill(2))) +
                ('AM' if item['event:enddate'].hour < 12 else 'PM') +
                ' | ')

def draw_desc(draw, item, n, px, wr_day, offset, bar_width, day_width, event_start_height, event_text_height, desc_text_height, desc, desc_width):
    if 'desc_on' in item and item['desc_on'] == 'on' and item['description'] and wr_day - item['event:startdate'] < datetime.timedelta(1):
        px = px + offset
        lines = [l2 for l1 in item['description'].split('\n') for l2 in textwrap.wrap(l1, width=desc_width, drop_whitespace=False)]
        draw.rectangle([(offset+(day_width+bar_width)*n,event_start_height+px),((day_width+bar_width)*(n)+day_width-1-offset,event_start_height+desc_text_height*len(lines)+px)],fill=lighten(colors.get(item['event:type'], 'black')))
        for line in lines:
            (w, h) = draw.textsize(line,font=desc)
            draw.text(((day_width+bar_width)*n+(day_width-1-w)/2, event_start_height+px),line,'black',font=desc)
            px = px + desc_text_height
        px = px + offset
    return px

def draw_event(draw, item, n, px, wr_day, offset, bar_width, day_width, event_start_height, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width):
    if item['advert'] == 'on' and ((not item['isallday']) or (item['event:startdate'] < wr_day + datetime.timedelta(1) and item['event:enddate'] >= wr_day)):
        # Create event string
        to_draw = ('' if item['isallday'] else make_date(item)) + item['title']
        # Use textwrap to make sure line doesn't exceed calendar day
        for line in textwrap.wrap(to_draw, width=text_width):
            if item['isallday']:
                draw.line([((day_width+bar_width)*n,event_start_height+event_text_size/2+px), ((day_width+bar_width)*n+day_width+(0 if item['event:enddate'] - datetime.timedelta(1) <= wr_day else bar_width)-1,event_start_height+event_text_size/2+px)], fill=colors.get(item['event:type'], 'black'), width=event_text_height)
                if wr_day.weekday() == 0 or item['event:startdate'] >= wr_day:
                    draw.text((offset+(day_width+bar_width)*n, event_start_height+px),line,'white',font=all_day)
            else:
                draw.text((offset+(day_width+bar_width)*n, event_start_height+px),line,colors.get(item['event:type'], 'black'),font=event)
            px = px + event_text_height
        return draw_desc(draw, item, n, px, wr_day, offset, bar_width, day_width, event_start_height, event_text_height, desc_text_height, desc, desc_width)
    else:
        return px

def populate_day(draw, cal_feed, n, wr_day, offset, bar_width, day_width, event_start_height, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width, px = 0):
    to_edit = []
    # Iterate through the OrgSync Feed
    for item in cal_feed['all_day']:
        px = draw_event(draw, item, n, px, wr_day, offset, bar_width, day_width, event_start_height, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width)
    for item in cal_feed['daily'][wr_day]:
        to_edit.append(item)
        px = draw_event(draw, item, n, px, wr_day, offset, bar_width, day_width, event_start_height, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width)
    return to_edit

def week_at_a_glance(cal_feed, adj_week, start_time = datetime.date.today(), spec_title = False):
    # Image constants
    day_width = 160
    bar_width = day_width/40
    offset = day_width/20
    event_text_size = 16
    text_width = 19
    desc_text_size = 12
    desc_width = 23
    event_text_height = round(1.25*event_text_size)
    desc_text_height = round(1.25*desc_text_size)
    event_start_height = 230

    # Get Monday after start_time at midnight
    next_monday = d_to_dt(next_weekday(start_time+datetime.timedelta(adj_week*7), 0))
    # Make title date range
    week_str = (months[next_monday.month - 1] + ' ' +
                str(next_monday.day) + ' - ' +
                months[(next_monday + datetime.timedelta(6)).month - 1] + ' ' +
                str((next_monday + datetime.timedelta(6)).day))
    # Pull image from template
    img = Image.open("templates/glance.png").convert('RGBA')
    draw = ImageDraw.Draw(img)

    # Initialize Fonts
    title = ImageFont.truetype("Carme-Regular.ttf", 88)
    day_font = ImageFont.truetype("Roboto-Black.ttf", 22)
    all_day = ImageFont.truetype("Roboto-Bold.ttf", event_text_size)
    event = ImageFont.truetype("Roboto-Regular.ttf", event_text_size)
    desc = ImageFont.truetype("Roboto-Regular.ttf", desc_text_size)

    # Draw Title
    draw.text((offset, 20),spec_title if spec_title else week_str,(255, 222, 118),font=title)

    to_edit = {}
    # Loop through the 7 days of the week
    for n in range(7):
        # Increment days
        wr_day = next_monday + datetime.timedelta(n)
        # Draw calendar date onto calendar
        draw.text((offset+(day_width+bar_width)*n, 198), str(wr_day.day), (0,0,0), font=day_font)
        # Draw Saint day onto calendar (max 2 lines)
        lines = textwrap.wrap(get_saints_day(wr_day, lit_cal), width=20)
        for ndx, line in enumerate(lines[:2]):
            draw.text((offset+30+(day_width+bar_width)*n, 198+desc_text_size*ndx), line + ('...' if ndx == 1 and len(lines) > 2 else ''), 'black', font=desc)
        to_edit[wr_day] = populate_day(draw, cal_feed, n, wr_day, offset, bar_width, day_width, event_start_height, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width)
    # Save finalized image
    img.save(directory + '/' + week_str + '.png')
    return directory + '/' + week_str + '.png', to_edit

def this_week_at_GTCC(cal_feed, adj_week, start_time = datetime.date.today(), spec_title = False):
    # Image constants
    day_width = 160
    bar_width = day_width/40
    offset = day_width/20
    event_text_size = 16
    text_width = 19
    desc_text_size = 12
    desc_width = 23
    event_text_height = round(1.25*event_text_size)
    desc_text_height = round(1.25*desc_text_size)
    event_start_height = 130

    # Get Monday after start_time at midnight
    next_monday = d_to_dt(next_weekday(start_time+datetime.timedelta(adj_week*7), 0))
    # Make title date range
    week_str = (months[next_monday.month - 1] + ' ' +
                str(next_monday.day) + ' - ' +
                months[(next_monday + datetime.timedelta(4)).month - 1] + ' ' +
                str((next_monday + datetime.timedelta(4)).day))
    # Pull image from template
    img = Image.open("templates/week.png").convert('RGBA')
    draw = ImageDraw.Draw(img)

    # Initialize Fonts
    all_day = ImageFont.truetype("Roboto-Bold.ttf", event_text_size)
    event = ImageFont.truetype("Roboto-Regular.ttf", event_text_size)
    desc = ImageFont.truetype("Roboto-Regular.ttf", desc_text_size)

    dofw = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY']

    to_edit = {}
    # Loop through the 7 days of the week
    for n in range(5):
        # Increment days
        wr_day = next_monday + datetime.timedelta(n)
        # Draw calendar date onto calendar
        day_string = dofw[n] + ' ' + str(wr_day.month) + '.' + str(wr_day.day)
        (w, h) = draw.textsize(day_string,font=event)
        draw.text(((day_width+bar_width)*n+(day_width-1-w)/2, 80), day_string, 'white', font=event)
        # Draw Saint day onto calendar (max 2 lines)
        lines = textwrap.wrap(get_saints_day(wr_day, lit_cal), width=25)
        if lines:
            draw.rectangle([(n*(day_width+bar_width),106),(n*(day_width+bar_width)+day_width-1,125)], fill=(255, 222, 118))
            (w, h) = draw.textsize(lines[0] + ('...' if len(lines) > 1 else ''),font=desc)
            draw.text(((day_width+bar_width)*n+(day_width-1-w)/2, event_start_height-22), lines[0] + ('...' if len(lines) > 1 else ''), 'black', font=desc)
        to_edit[wr_day] = populate_day(draw, cal_feed, n, wr_day, offset, bar_width, day_width, event_start_height, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width)
    # Save finalized image
    img.save(directory + '/' + week_str + '.png')
    return directory + '/' + week_str + '.png', to_edit

def this_weekend_at_GTCC(cal_feed, adj_week, start_time = datetime.date.today(), spec_title = False):
    # Image constants
    day_width = 320
    bar_width = day_width/40
    offset = day_width/20
    event_text_size = 24
    text_width = 26
    desc_text_size = 18
    desc_width = 33
    event_text_height = round(1.25*event_text_size)
    desc_text_height = round(1.25*desc_text_size)
    event_start_height = 172

    # Get Monday after start_time at midnight
    next_friday = d_to_dt(next_weekday(start_time+datetime.timedelta(adj_week*7), 4))
    # Make title date range
    week_str = (months[next_friday.month - 1] + ' ' +
                str(next_friday.day) + ' - ' +
                months[(next_friday + datetime.timedelta(2)).month - 1] + ' ' +
                str((next_friday + datetime.timedelta(2)).day))
    # Pull image from template
    img = Image.open("templates/weekend.png").convert('RGBA')
    draw = ImageDraw.Draw(img)

    # Initialize Fonts
    day_font = ImageFont.truetype("Roboto-Regular.ttf", 32)
    all_day = ImageFont.truetype("Roboto-Bold.ttf", event_text_size)
    event = ImageFont.truetype("Roboto-Regular.ttf", event_text_size)
    desc = ImageFont.truetype("Roboto-Regular.ttf", desc_text_size)

    dofw = ['FRIDAY', 'SATURDAY', 'SUNDAY']

    to_edit = {}
    # Loop through the 7 days of the week
    for n in range(3):
        # Increment days
        wr_day = next_friday + datetime.timedelta(n)
        # Draw calendar date onto calendar
        day_string = dofw[n] + ' ' + str(wr_day.month) + '.' + str(wr_day.day)
        (w, h) = draw.textsize(day_string,font=day_font)
        draw.text(((day_width+bar_width)*n+(day_width-1-w)/2, 95), day_string, 'white', font=day_font)
        # Draw Saint day onto calendar (max 2 lines)
        lines = textwrap.wrap(get_saints_day(wr_day, lit_cal), width=36)
        if lines:
            draw.rectangle([(n*(day_width+bar_width),134),(n*(day_width+bar_width)+day_width-1,172)], fill=(255, 222, 118))
            (w, h) = draw.textsize(lines[0] + ('...' if len(lines) > 1 else ''),font=desc)
            draw.text(((day_width+bar_width)*n+(day_width-1-w)/2, event_start_height-30), lines[0] + ('...' if len(lines) > 1 else ''), 'black', font=desc)
        to_edit[wr_day] = populate_day(draw, cal_feed, n, wr_day, offset, bar_width, day_width, event_start_height, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width, px = offset)
    # Save finalized image
    img.save(directory + '/' + week_str + '.png')
    return directory + '/' + week_str + '.png', to_edit

def big_calendar(cal_feed, start_time = datetime.date.today(), spec_title = False):
    # Image constants
    day_width = 2040
    bar_width = 20
    offset = day_width/20
    event_text_size = 144
    text_width = 28
    desc_text_size = 108
    desc_width = 35
    event_text_height = round(1.25*event_text_size)
    desc_text_height = round(1.25*desc_text_size)
    event_start_height = 3200

    # Get Monday after start_time at midnight
    first_day = d_to_dt(start_time.replace(day=1,month=(start_time.month%12)+1,year=start_time.year+int(start_time.month/12)))
    # Pull image from template
    img = Image.open("templates/monthCal.png").convert('RGBA')
    draw = ImageDraw.Draw(img)

    # Initialize Fonts
    day_font = ImageFont.truetype("Roboto-Black.ttf", 250)
    all_day = ImageFont.truetype("Roboto-Bold.ttf", event_text_size)
    event = ImageFont.truetype("Roboto-Regular.ttf", event_text_size)
    desc = ImageFont.truetype("Roboto-Regular.ttf", desc_text_size)

    to_edit = {}
    # Loop through the 7 days of the week
    for day in range(calendar.monthrange(first_day.year,first_day.month)[1]):
        # Increment days
        wr_day = first_day + datetime.timedelta(day)
        week = wr_day.isocalendar()[1] - first_day.isocalendar()[1] - 1 + (1 if wr_day.weekday() == 6 else 0)
        n = [1,2,3,4,5,6,0][wr_day.weekday()]
        # Draw calendar date onto calendar
        draw.text((offset+(day_width+bar_width)*n, 2900+week*1588), str(wr_day.day), (0,0,0), font=day_font)
        # Draw Saint day onto calendar (max 2 lines)
        lines = textwrap.wrap(get_saints_day(wr_day, lit_cal), width=28)
        for ndx, line in enumerate(lines[:2]):
            draw.text((offset+400+(day_width+bar_width)*n, 2915+week*1588+desc_text_size*ndx), line + ('...' if ndx == 1 and len(lines) > 2 else ''), 'black', font=desc)
        to_edit[wr_day] = populate_day(draw, cal_feed, n, wr_day, offset, bar_width, day_width, event_start_height+1588*week, event_text_size, event_text_height, desc_text_height, all_day, event, desc, text_width, desc_width)
    # Save finalized image
    img.save(directory + '/' + months[first_day.month-1] + '.png')
    return directory + '/' + months[first_day.month-1] + '.png', to_edit
