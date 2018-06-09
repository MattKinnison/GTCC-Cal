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
    return tuple(list(color)+[178])

def make_date(item):
    return (str(((item['event:startdate'].hour-1) % 12)+1) +
                ('' if item['event:startdate'].minute == 0 else (':'+str(item['event:startdate'].minute))) +
                '-' + str(((item['event:enddate'].hour-1) % 12)+1) +
                ('' if item['event:enddate'].minute == 0 else (':'+str(item['event:enddate'].minute))) +
                ('AM' if item['event:enddate'].hour < 12 else 'PM') +
                ' | ')

def week_at_a_glance(cal_feed, adj_week, start_time = datetime.date.today(), spec_title = False):
    # Image constants
    day_width = 166
    event_text_height = 20
    desc_text_height = 14

    # Get Monday after start_time at midnight
    next_monday = d_to_dt(next_weekday(start_time+datetime.timedelta(adj_week*7), 0))
    # Make title date range
    week_str = (months[next_monday.month - 1] + ' ' +
                str(next_monday.day) + ' - ' +
                months[(next_monday + datetime.timedelta(6)).month - 1] + ' ' +
                str((next_monday + datetime.timedelta(6)).day))
    # Pull image from template
    img = Image.open("template.png").convert('RGBA')
    draw = ImageDraw.Draw(img)

    # Initialize Fonts
    title = ImageFont.truetype("Carme-Regular.ttf", 88)
    day_font = ImageFont.truetype("Roboto-Black.ttf", 22)
    all_day = ImageFont.truetype("Roboto-Bold.ttf", 16)
    event = ImageFont.truetype("Roboto-Regular.ttf", 16)
    desc = ImageFont.truetype("Roboto-Regular.ttf", 12)

    # Draw Title
    draw.text((10, 20),spec_title if spec_title else week_str,(255, 222, 118),font=title)

    to_edit = {}
    # Loop through the 7 days of the week
    for n in range(7):
        # Increment days
        wr_day = next_monday + datetime.timedelta(n)
        # Draw calendar date onto calendar
        draw.text((10+day_width*n, 198), str(wr_day.day), (0,0,0), font=day_font)
        holy_day = get_saints_day(wr_day, lit_cal)
        m = 0
        for line in textwrap.wrap(holy_day, width=20):
            draw.text((40+day_width*n, 198+12*m), line, (0,0,0), font=desc)
            m = m + 1
        to_edit[wr_day] = []
        # mth row to write text on
        m = 0
        # Iterate through the OrgSync Feed
        for item in cal_feed['all_day']:
            if item['advert'] == 'on' and item['event:startdate'] < wr_day + datetime.timedelta(1) and item['event:enddate'] >= wr_day:
                # Create event string
                to_draw = item['title']
                # Use textwrap to make sure line doesn't exceed calendar day
                for line in textwrap.wrap(to_draw, width=19):
                    draw.line([(day_width*n,238+event_text_height*m),(day_width*(n+1),238+event_text_height*m)],fill=colors[item['event:type'] if item['event:type'] in colors.keys() else 'Other'],width=event_text_height)
                    if wr_day.weekday() == 0 or not (item['event:startdate'] < wr_day):
                        draw.text((10+day_width*n, 230+event_text_height*m),line,(255,255,255),font=all_day)
                    #o = draw.textsize(line,font=event)[0]
                    m = m + 1
        m1 = 0
        if wr_day in cal_feed['daily']:
            for item in cal_feed['daily'][wr_day]:
                to_edit[wr_day].append(item)
                if item['advert'] == 'on':
                    if 'Apologetics' in item['title'] or 'Theology of the Body' in item['title'] or 'Scripture Study' in item['title']:
                        to_d = (item['title'].split(':')[0])
                    else:
                        to_d = item['title']
                    # Create event string
                    to_draw = make_date(item) + to_d
                    # Use textwrap to make sure line doesn't exceed calendar day
                    for line in textwrap.wrap(to_draw, width=19):
                        draw.text((10+day_width*n, 230+event_text_height*m+desc_text_height*m1),line,colors[item['event:type'] if item['event:type'] in colors.keys() else 'Other'],font=event)
                        # Increment line by 1 once written
                        m = m + 1
                    if 'desc_on' in item and item['desc_on'] == 'on' and item['description']:
                        lines = textwrap.wrap(item['description'], width=22)
                        draw.rectangle([(10+day_width*n,230+event_text_height*m+desc_text_height*m1),(150+day_width*n,230+event_text_height*m+desc_text_height*(m1+len(lines)))],fill=lighten(colors[item['event:type'] if item['event:type'] in colors.keys() else 'Other']), outline=(0,0,0))
                        for line in lines:
                            (w, h) = draw.textsize(line,font=desc)
                            draw.text((10+day_width*n+(140-w)/2, 230+event_text_height*m+desc_text_height*m1),line,(0,0,0),font=desc)
                            m1 = m1 + 1
    # Save finalized image
    img.save(week_str + '.png')
    return week_str + '.png', to_edit

def this_week_at_GTCC(cal_feed, adj_week, start_time = datetime.date.today(), spec_title = False):
    # Image constants
    day_width = 164
    start_height = 115
    event_text_height = 20
    desc_text_height = 14

    # Get Monday after start_time at midnight
    next_monday = d_to_dt(next_weekday(start_time+datetime.timedelta(adj_week*7), 0))
    # Make title date range
    week_str = (months[next_monday.month - 1] + ' ' +
                str(next_monday.day) + ' - ' +
                months[(next_monday + datetime.timedelta(4)).month - 1] + ' ' +
                str((next_monday + datetime.timedelta(4)).day))
    # Pull image from template
    img = Image.open("week.png").convert('RGBA')
    draw = ImageDraw.Draw(img)

    # Initialize Fonts
    title = ImageFont.truetype("Carme-Regular.ttf", 88)
    day_font = ImageFont.truetype("Roboto-Black.ttf", 22)
    all_day = ImageFont.truetype("Roboto-Bold.ttf", 16)
    event = ImageFont.truetype("Roboto-Regular.ttf", 16)
    desc = ImageFont.truetype("Roboto-Regular.ttf", 12)

    to_edit = {}
    # Loop through the 7 days of the week
    for n in range(5):
        # Increment days
        wr_day = next_monday + datetime.timedelta(n)
        # Draw calendar date onto calendar
        draw.text((5+day_width*n, 85), str(wr_day.day), (255,255,255), font=day_font)
        to_edit[wr_day] = []
        # mth row to write text on
        m = 0
        # Iterate through the OrgSync Feed
        for item in cal_feed['all_day']:
            if item['advert'] == 'on' and item['event:startdate'] < wr_day + datetime.timedelta(1) and item['event:enddate'] >= wr_day:
                # Create event string
                to_draw = item['title']
                # Use textwrap to make sure line doesn't exceed calendar day
                for line in textwrap.wrap(to_draw, width=19):
                    draw.line([(day_width*n,start_height+event_text_height*(m+0.5)),(day_width*(n+1),start_height+event_text_height*(m+0.5))],fill=colors[item['event:type'] if item['event:type'] in colors.keys() else 'Other'],width=event_text_height)
                    if wr_day.weekday() == 0 or not (item['event:startdate'] < wr_day):
                        draw.text((5+day_width*n, start_height+event_text_height*m),line,(255,255,255),font=all_day)
                    #o = draw.textsize(line,font=event)[0]
                    m = m + 1
        m1 = 0
        if wr_day in cal_feed['daily']:
            for item in cal_feed['daily'][wr_day]:
                to_edit[wr_day].append(item)
                if item['advert'] == 'on':
                    if 'Apologetics' in item['title'] or 'Theology of the Body' in item['title'] or 'Scripture Study' in item['title']:
                        to_d = (item['title'].split(':')[0])
                    else:
                        to_d = item['title']
                    # Create event string
                    to_draw = make_date(item) + to_d
                    # Use textwrap to make sure line doesn't exceed calendar day
                    for line in textwrap.wrap(to_draw, width=19):
                        draw.text((5+day_width*n, start_height+event_text_height*m+desc_text_height*m1),line,colors[item['event:type'] if item['event:type'] in colors.keys() else 'Other'],font=event)
                        # Increment line by 1 once written
                        m = m + 1
                    if 'desc_on' in item and item['desc_on'] == 'on' and item['description']:
                        lines = textwrap.wrap(item['description'], width=22)
                        draw.rectangle([(5+day_width*n,start_height+event_text_height*m+desc_text_height*m1),(150+day_width*n,start_height+event_text_height*m+desc_text_height*(m1+len(lines)))],fill=lighten(colors[item['event:type'] if item['event:type'] in colors.keys() else 'Other']), outline=(0,0,0))
                        for line in lines:
                            (w, h) = draw.textsize(line,font=desc)
                            draw.text((10+day_width*n+(140-w)/2, start_height+event_text_height*m+desc_text_height*m1),line,(0,0,0),font=desc)
                            m1 = m1 + 1
    # Save finalized image
    img.save(week_str + '.png')
    return week_str + '.png', to_edit
