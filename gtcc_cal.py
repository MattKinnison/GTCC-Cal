from bottle import Bottle, run, request, static_file
from PIL import Image, ImageFont, ImageDraw
import datetime
import json
import requests
import xmltodict
import dateutil.parser
import pytz
import textwrap
import sys
import calendar
import os

app = Bottle()

eastern = pytz.timezone('US/Eastern')

months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

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

gt_order = {  "Faith Formation": 4,
            "Community Life": 5,
            "Freshmen Events": 5,
            "Liturgy": 1,
            "Outreach": 2,
            "Knights of Columbus": 0,
            "Graduate Student Events": 3,
            "FOCUS": 0,
            "Other": 0
          }

temp = '''<div class="panel panel-default">
<div class="panel-heading">
<h4 class="panel-title">
<a data-toggle="collapse" data-parent="#accordion" href="#collapse{id}">
{title} - {month}/{day_}</a>
</h4>
</div>
<div id="collapse{id}" class="panel-collapse collapse">
<div class="panel-body">
<div class="checkbox">
    <label><input type="checkbox" checked>Include event in graphic?</label>
</div>
<div class="form-group">
    <label for="email">Title:</label>
    <input type="text" class="form-control" id="title{id}" value ="{title}">
 </div>
 <div class="checkbox">
     <label><input type="checkbox">Include description in graphic?</label>
 </div>
 <div class="form-group">
  <label for="comment">Desciption:</label>
  <textarea class="form-control" rows="5" id="desciption{id}">{description}</textarea>
</div>
</div>
</div>
</div>
'''

def next_weekday(d, weekday): # 0 = Monday, 1=Tuesday, 2=Wednesday...
    days_ahead = weekday - d.weekday()
    if days_ahead <= 0: # Target day already happened this week
        days_ahead += 7
    return d + datetime.timedelta(days_ahead)

def d_to_dt(d):
    return eastern.localize(datetime.datetime.combine(d,datetime.time.min))

def refresh_OrgSync():
    # Pull OrgSync calendar feed
    feed = xmltodict.parse(requests.get('https://api.orgsync.com/api/v3/portals/137015/events.rss?key=dxtLPV3wbG0wDsb2iUmu5ImQFhUQpH_CsBHPl_CH9gs&per_page=100&upcoming=true').text)['rss']['channel']['item']
    # Reformat dates
    for item in feed:
        item['event:startdate'] = dateutil.parser.parse(item['event:startdate']).astimezone()
        item['event:enddate'] = dateutil.parser.parse(item['event:enddate']).astimezone()
        item['isallday'] = (item['event:enddate']-item['event:startdate']).total_seconds() % 86400 == 0
    # Group By dates
    start = min([item['event:startdate'].date() for item in feed])
    last = max([item['event:enddate'].date() for item in feed])
    cal_feed = {d_to_dt(datetime.timedelta(day) + start):
        {'All Day': [item for item in feed if item['event:startdate'] < d_to_dt(datetime.timedelta(day,hours=20) + start) and item['event:enddate'] >= d_to_dt(datetime.timedelta(day) + start - datetime.timedelta(hours=4)) and item['isallday']],
         'Short': [item for item in feed if item['event:startdate'] <= d_to_dt(datetime.timedelta(day+1) + start) and item['event:enddate'] >= d_to_dt(datetime.timedelta(day) + start) and item['event:enddate'] - item['event:startdate'] < datetime.timedelta(1)]} for day in range((last - start).days)}
    return cal_feed

def week_at_a_glance(cal_feed, adj_week, start_time = datetime.date.today(), spec_title = False):
    # Get Monday after start_time at midnight
    next_monday = d_to_dt(next_weekday(start_time+datetime.timedelta(adj_week*7), 0))
    # Make title date range
    week_str = (months[next_monday.month - 1] + ' ' +
                str(next_monday.day) + ' - ' +
                months[(next_monday + datetime.timedelta(6)).month - 1] + ' ' +
                str((next_monday + datetime.timedelta(6)).day))
    # Pull image from template
    img = Image.open("template.png")
    draw = ImageDraw.Draw(img)

    # Initialize Fonts
    title = ImageFont.truetype("Carme-Regular.ttf", 88)
    day_font = ImageFont.truetype("Roboto-Black.ttf", 22)
    all_day = ImageFont.truetype("Roboto-Bold.ttf", 16)
    event = ImageFont.truetype("Roboto-Regular.ttf", 16)

    # Draw Title
    draw.text((10, 20),spec_title if spec_title else week_str,(255, 222, 118),font=title)

    to_edit = {}
    # Loop through the 7 days of the week
    for n in range(7):
        # Increment days
        wr_day = next_monday + datetime.timedelta(n)
        # Draw calendar date onto calendar
        draw.text((10+166*n, 200), str(wr_day.day), (0,0,0), font=day_font)

        # mth row to write text on
        m = 0
        to_edit[wr_day] = {'All Day': [],'Short': []}
        # Iterate through the OrgSync Feed
        for item in cal_feed[wr_day]['All Day']:
            to_edit[wr_day]['All Day'].append(item)
            # Create event string
            if 'Apologetics' in item['title'] or 'Theology of the Body' in item['title'] or 'Scripture Study' in item['title']:
                to_draw = (item['title'].split(':')[0])
            else:
                to_draw = item['title']
            # Use textwrap to make sure line doesn't exceed calendar day
            m1 = m
            for line in textwrap.wrap(to_draw, width=16):
                draw.line([(166*n,233+20*m1),(166*(n+1),233+20*m1)],fill=colors[item['event:type'] if item['event:type'] in colors.keys() else 'Other'],width=20)
                #o = draw.textsize(line,font=event)[0]
                m1 = m1 + 1
            for line in textwrap.wrap(to_draw, width=16):
                if ((wr_day - datetime.timedelta(1)) in cal_feed and item not in cal_feed[wr_day - datetime.timedelta(1)]['All Day']) or wr_day.weekday() == 0:
                    draw.text((10+166*n, 225+20*m),line,(255,255,255),font=all_day)
                # Increment line by 1 once written
                m = m + 1
        for item in cal_feed[wr_day]['Short']:
            to_edit[wr_day]['Short'].append(item)
            if 'Apologetics' in item['title'] or 'Theology of the Body' in item['title'] or 'Scripture Study' in item['title']:
                to_d = (item['title'].split(':')[0])
            else:
                to_d = item['title']
            # Create event string
            to_draw = (str(((item['event:startdate'].hour-1) % 12)+1) +
                        ('' if item['event:startdate'].minute == 0 else (':'+str(item['event:startdate'].minute))) +
                        '-' + str(((item['event:enddate'].hour-1) % 12)+1) +
                        ('' if item['event:enddate'].minute == 0 else (':'+str(item['event:enddate'].minute))) +
                        ('AM' if item['event:enddate'].hour < 12 else 'PM') +
                        ' | ' + to_d)
            # Use textwrap to make sure line doesn't exceed calendar day
            for line in textwrap.wrap(to_draw, width=16):
                draw.text((10+166*n, 225+20*m),line,colors[item['event:type'] if item['event:type'] in colors.keys() else 'Other'],font=event)
                # Increment line by 1 once written
                m = m + 1
    # Save finalized image
    img.save(week_str + '.png')
    return week_str + '.png', to_edit

@app.route('/images/<filename:re:.*\.png>')
def send_image(filename):
    return static_file(filename, root='./', mimetype='image/png')

@app.route('/index.html')
def home():
    with open("index.html") as page:
        out = page.read()
    return out

@app.route('/weekGT.html', method='GET')
def weekGT():
    with open("weekGT.html") as page:
        out = page.read()
    return out

@app.route('/weekGT.html', method='POST')
def weekGT():
    if request.POST.save:
        cal_feed = refresh_OrgSync()
        ask_week = {'This Week': -1, 'Next Week': 0, '2 Weeks Ahead': 1, '3 Weeks Ahead': 2}[request.POST.weekSel.strip()]
        active_glance, editable = week_at_a_glance(cal_feed, ask_week)
        with open("weekGT.html") as page:
            out = page.read()
        out = out.replace('<!-- Preview Here -->','<img class="img-responsive" src="/images/'+active_glance+'" alt="/images/template.png">')
        accord = ''
        n = 0
        for day in editable:
            for event in editable[day]['All Day']:
                anacc = temp.format(id=str(n),title=event['title'],month=str(day.month),day_=str(day.day),description='' if 'description' not in event else event['description'])
                n = n + 1
                accord = accord + anacc
            for event in editable[day]['Short']:
                anacc = temp.format(id=str(n),title=event['title'],month=str(day.month),day_=str(day.day),description='' if 'description' not in event else event['description'])
                n = n + 1
                accord = accord + anacc
        out = out.replace('<!--Accordian Here-->','<div class="panel-group" id="accordion"><form action="/weekGT.html" method="POST">'+accord+
            '<p></p><button type="submit" class="btn btn-default" name="save2" value="save2">Update</button></form></div>')
        return out
    elif request.POST.save2:
        print(request.POST)
        cal_feed = refresh_OrgSync()
        active_glance, editable = week_at_a_glance(cal_feed, ask_week)
        with open("weekGT.html") as page:
            out = page.read()
        out = out.replace('<!-- Preview Here -->','<img class="img-responsive" src="/images/'+active_glance+'" alt="/images/template.png">')
        accord = ''
        n = 0
        for day in editable:
            for event in editable[day]['All Day']:
                anacc = temp.format(id=str(n),title=event['title'],month=str(day.month),day_=str(day.day),description='' if 'description' not in event else event['description'])
                n = n + 1
                accord = accord + anacc
            for event in editable[day]['Short']:
                anacc = temp.format(id=str(n),title=event['title'],month=str(day.month),day_=str(day.day),description='' if 'description' not in event else event['description'])
                n = n + 1
                accord = accord + anacc
        out = out.replace('<!--Accordian Here-->','<div class="panel-group" id="accordion"><form action="/weekGT.html" method="POST">'+accord+
            '<p></p><button type="submit" class="btn btn-default" name="save2" value="save2">Update</button></form></div>')
        return out
    else:
        with open("weekGT.html") as page:
            out = page.read()
        return out

run(app, host='localhost', port=8080)
