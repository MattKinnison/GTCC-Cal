try:
    from pip import main as pipmain
except:
    from pip._internal import main as pipmain
import requests
import webbrowser
import os
try:
    import ics
except:
    pipmain(['install','ics'])
    import ics
try:
    from bottle import Bottle, run, request, static_file
except:
    pipmain(['install','bottle'])
    from bottle import Bottle, run, request, static_file
import cal_maker

webbrowser.open('http://localhost:8080',new=2)

from bottle import Bottle, run, request, static_file

directory = os.path.expanduser('~\\Pictures\\GTCC Calendars')
if not os.path.exists(directory):
    os.makedirs(directory)

app = Bottle()

def load_html(files):
    templates = {}
    for file in files:
        with open('html\\'+file+'.html') as f:
            templates[file] = f.read()
    return templates

templates = load_html(['home','template','accordion','weekGT', 'weekFB', 'weekend', 'big_cal'])

cal_feed = {}

def refresh_OrgSync():
    # Pull OrgSync calendar feed
    cal_feed = ics.Calendar(requests.get('https://calendar.google.com/calendar/ical/stmonicayoungadults%40gmail.com/public/basic.ics').text.encode('latin-1').decode('utf-8')).events #.replace(';X-RICAL-TZSOURCE=TZINFO','')
    for event in cal_feed:
        if not event.all_day: #(event.end - event.begin).total_seconds() < 66400:
            event.begin = event.begin.to('US/Central')#.replace(hours=-5)
            event.end = event.end.to('US/Central')#.replace(hours=-5)
    return sorted(cal_feed, key = lambda event: (event.begin, event.end.timestamp*-1))

def make_accord(editable, temp_id, ask_week):
    accord = ''
    for event in editable:
        anacc = templates['accordion'].format(id=event.uid,title=event.name,month=str(event.begin.month),day_=str(event.begin.day),description=event.description)
        accord = accord + anacc
    return '''
<div class="panel-group" id="accordion">
    <form action="/{address}" method="POST"><input type="hidden"  name="ask_week" value="{week}"/>
        {events}
        <br>
        <button type="submit" class="btn btn-default" name="save2" value="iii">Update</button>
    </form>
</div>'''.format(address=temp_id, week=ask_week, events=accord)

def update_accord(cal_feed, POST):
    POST.pop('save2', None)
    ids = set([key.split('+')[-1] for key in POST])
    features = {id: {key.split('+')[0]: POST[key] for key in POST if key.split('+')[-1] == id} for id in ids}
    for id in features:
        for event in cal_feed:
            if id == event.uid:
                event.transparent = not 'advert' in features[id]
                event.location = 'desc' if 'desc_on' in features[id] else ''
                event.name = features[id]['title']
                event.description = features[id]['description']
                break
    return cal_feed

@app.route('/images_temp/<filename:re:.*\.png>')
def send_image(filename):
    return static_file(filename, root=os.cwd()+'\\templates', mimetype='image/png')

@app.route('/images/<filename:re:.*\.png>')
def send_image(filename):
    return static_file(filename, root=directory, mimetype='image/png')

@app.route('/css/<filename:re:.*\.css>')
def send_image(filename):
    return static_file(filename, root='.\\', mimetype='text/css')

@app.route('/')
def home():
    return templates['template'].format(body=templates['home'],home_act='class="active"',prt_act='',GT_act='',week_act='',end_act='')

@app.route('/weekGT', method='GET')
def weekGT():
    return templates['template'].format(body=templates['weekGT'],home_act='',prt_act='',GT_act='class="active"',week_act='',end_act='').format(image='temp/template.png',accordion='')

@app.route('/weekGT', method='POST')
def weekGT():
    global cal_feed
    if 'ask_week' in request.POST:
        ask_week = int(request.POST.pop('ask_week'))
        cal_feed = update_accord(cal_feed, request.POST)
        active_glance, editable = cal_maker.week_at_a_glance(cal_feed, ask_week)
        return templates['template'].format(body=templates['weekGT'],home_act='',prt_act='',GT_act='class="active"',week_act='',end_act='').format(image=active_glance,accordion=make_accord(editable, 'weekGT', ask_week))
    else:
        cal_feed = refresh_OrgSync()
        ask_week = {'This Week': -1, 'Next Week': 0, '2 Weeks Ahead': 1, '3 Weeks Ahead': 2}[request.POST.weekSel.strip()]
        active_glance, editable = cal_maker.week_at_a_glance(cal_feed, ask_week)
        return templates['template'].format(body=templates['weekGT'],home_act='',prt_act='',GT_act='class="active"',week_act='',end_act='').format(image=active_glance,accordion=make_accord(editable, 'weekGT', ask_week))

# @app.route('/weekFB', method='GET')
# def weekFB():
#     return templates['template'].format(body=templates['weekFB'],home_act='',prt_act='',GT_act='',week_act='class="active"',end_act='').format(image='week.png',accordion='')
#
# @app.route('/weekFB', method='POST')
# def weekFB():
#     global cal_feed
#     if 'ask_week' in request.POST:
#         ask_week = int(request.POST.pop('ask_week'))
#         cal_feed = update_accord(cal_feed, request.POST)
#         active_glance, editable = cal_maker.this_week_at_GTCC(cal_feed, ask_week)
#         return templates['template'].format(body=templates['weekFB'],home_act='',prt_act='',GT_act='',week_act='class="active"',end_act='').format(image=active_glance,accordion=make_accord(editable, 'weekFB', ask_week))
#     else:
#         cal_feed = refresh_OrgSync()
#         ask_week = {'This Week': -1, 'Next Week': 0, '2 Weeks Ahead': 1, '3 Weeks Ahead': 2}[request.POST.weekSel.strip()]
#         active_glance, editable = cal_maker.this_week_at_GTCC(cal_feed, ask_week)
#         return templates['template'].format(body=templates['weekFB'],home_act='',prt_act='',GT_act='',week_act='class="active"',end_act='').format(image=active_glance,accordion=make_accord(editable, 'weekFB', ask_week))
#
# @app.route('/weekend', method='GET')
# def weekend():
#     return templates['template'].format(body=templates['weekend'],home_act='',prt_act='',GT_act='',week_act='',end_act='class="active"').format(image='temp/weekend.png',accordion='')
#
# @app.route('/weekend', method='POST')
# def weekend():
#     global cal_feed
#     if 'ask_week' in request.POST:
#         ask_week = int(request.POST.pop('ask_week'))
#         cal_feed = update_accord(cal_feed, request.POST)
#     else:
#         cal_feed = refresh_OrgSync()
#         ask_week = {'This Week': -1, 'Next Week': 0, '2 Weeks Ahead': 1, '3 Weeks Ahead': 2}[request.POST.weekSel.strip()]
#     active_glance, editable = cal_maker.this_weekend_at_GTCC(cal_feed, ask_week)
#     return templates['template'].format(body=templates['weekend'],home_act='',prt_act='',GT_act='',week_act='',end_act='class="active"').format(image=active_glance,accordion=make_accord(editable, 'weekend', ask_week))
#
# @app.route('/big_cal', method='GET')
# def big_cal():
#     return templates['template'].format(body=templates['big_cal'],home_act='',prt_act='class="active"',GT_act='',week_act='',end_act='').format(image='temp/monthCal.png',accordion='')
#
# @app.route('/big_cal', method='POST')
# def big_cal():
#     global cal_feed
#     if 'ask_week' in request.POST:
#         _ = request.POST.pop('ask_week')
#         cal_feed = update_accord(cal_feed, request.POST)
#         active_glance, editable = cal_maker.big_calendar(cal_feed)
#         return templates['template'].format(body=templates['big_cal'],home_act='',prt_act='class="active"',GT_act='',week_act='',end_act='').format(image=active_glance,accordion=make_accord(editable, 'big_cal', 0))
#     else:
#         cal_feed = refresh_OrgSync()
#         active_glance, editable = cal_maker.big_calendar(cal_feed)
#         return templates['template'].format(body=templates['big_cal'],home_act='',prt_act='class="active"',GT_act='',week_act='',end_act='').format(image=active_glance,accordion=make_accord(editable, 'big_cal', 0))

run(app, host='localhost', port=8080)
