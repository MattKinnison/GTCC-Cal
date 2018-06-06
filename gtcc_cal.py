from bottle import Bottle, run, request, static_file
import datetime
import requests
import xmltodict
import dateutil.parser
import pytz
import textwrap
import cal_maker
import pprint as pp

app = Bottle()

eastern = pytz.timezone('US/Eastern')

def load_html(files):
    templates = {}
    for file in files:
        with open('html\\'+file+'.html') as f:
            templates[file] = f.read()
    return templates

templates = load_html(['home','template','accordion','weekGT','accordion_all_day', 'weekFB'])

cal_feed = {}

def d_to_dt(d):
    return eastern.localize(datetime.datetime.combine(d,datetime.time.min))

def refresh_OrgSync():
    # Pull OrgSync calendar feed
    feed = xmltodict.parse(requests.get('https://api.orgsync.com/api/v3/portals/137015/events.rss?key=dxtLPV3wbG0wDsb2iUmu5ImQFhUQpH_CsBHPl_CH9gs&per_page=100&upcoming=true').text)['rss']['channel']['item']
    # Reformat dates
    for item in feed:
        item['event:startdate'] = dateutil.parser.parse(item['event:startdate']).astimezone(eastern)
        item['event:enddate'] = dateutil.parser.parse(item['event:enddate']).astimezone(eastern)
        item['isallday'] = (item['event:enddate']-item['event:startdate']).total_seconds() % 86400 == 0
        if item['isallday']:
            item['event:startdate'] = item['event:startdate'] + datetime.timedelta(4/24)
            item['event:enddate'] = item['event:enddate'] - datetime.timedelta(4/24)
    # Group By dates
    start = min([item['event:startdate'].date() for item in feed])
    last = max([item['event:enddate'].date() for item in feed])
    y = {'advert': 'on', 'desc_on': None}
    daily = {d_to_dt(datetime.timedelta(day) + start):
        [{**item, **y} for item in feed if item['event:startdate'] <= d_to_dt(datetime.timedelta(day+1) + start) and item['event:enddate'] >= d_to_dt(datetime.timedelta(day) + start) and not item['isallday']] for day in range((last - start).days)}
    y = {'advert': 'on'}
    all_day = [{**item, **y} for item in feed if item['isallday']]
    return {'daily': daily, 'all_day': all_day}

@app.route('/images/<filename:re:.*\.png>')
def send_image(filename):
    return static_file(filename, root='./', mimetype='image/png')

@app.route('/css/<filename:re:.*\.css>')
def send_image(filename):
    return static_file(filename, root='./', mimetype='text/css')

@app.route('/')
def home():
    return templates['template'].format(body=templates['home'],home_act='class="active"',prt_act='',GT_act='',week_act='',end_act='')

@app.route('/weekGT', method='GET')
def weekGT():
    return templates['template'].format(body=templates['weekGT'],home_act='',prt_act='',GT_act='class="active"',week_act='',end_act='').format(image='template.png',accordion='')

@app.route('/weekGT', method='POST')
def weekGT():
    global cal_feed
    if request.POST.save:
        cal_feed = refresh_OrgSync()
        ask_week = {'This Week': -1, 'Next Week': 0, '2 Weeks Ahead': 1, '3 Weeks Ahead': 2}[request.POST.weekSel.strip()]
        active_glance, editable = cal_maker.week_at_a_glance(cal_feed, ask_week)
        accord = ''
        for event in cal_feed['all_day']:
            if event['event:startdate'] < max(editable.keys()) and event['event:enddate'] >= min(editable.keys()):
                anacc = templates['accordion_all_day'].format(id=event['link'].split('/')[-1],title=event['title'],month=str(event['event:startdate'].month),day_=str(event['event:startdate'].day))
                accord = accord + anacc
        for day in editable:
            for event in editable[day]:
                anacc = templates['accordion'].format(id=event['link'].split('/')[-1],title=event['title'],month=str(day.month),day_=str(day.day),description='' if 'description' not in event else event['description'])
                accord = accord + anacc
        return templates['template'].format(body=templates['weekGT'],home_act='',prt_act='',GT_act='class="active"',week_act='',end_act='').format(image=active_glance,accordion='''<div class="panel-group" id="accordion">
    <form action="/weekGT" method="POST">'''+accord+
            '''            <br>
            <button type="submit" class="btn btn-default" name="save2" value="iii">Update</button>
    </form>
</div>''')
    elif request.POST.save2:
        request.POST.pop('save2', None)
        ids = set([key.split('-')[-1] for key in request.POST])
        features = {id: {key.split('-')[0]: request.POST[key] for key in request.POST if key.split('-')[-1] == id} for id in ids}
        for id in features:
            comp = False
            for event in cal_feed['all_day']:
                if id == event['link'].split('/')[-1]:
                    event['advert'] = 'on' if 'advert' in features[id] else 'off'
                    event['title'] = features[id]['title']
                    comp = True
                    break
            for day in cal_feed['daily']:
                if comp:
                    break
                else:
                    for event in cal_feed['daily'][day]:
                        if id == event['link'].split('/')[-1]:
                            event['advert'] = 'on' if 'advert' in features[id] else 'off'
                            event['desc_on'] = 'on' if 'desc_on' in features[id] else 'off'
                            event['title'] = features[id]['title']
                            event['description'] = features[id]['description']
                            break
                            break
        ask_week = 0
        active_glance, editable = cal_maker.week_at_a_glance(cal_feed, ask_week)
        accord = ''
        for event in cal_feed['all_day']:
            if event['event:startdate'] < max(editable.keys()) and event['event:enddate'] >= min(editable.keys()):
                anacc = templates['accordion_all_day'].format(id=event['link'].split('/')[-1],title=event['title'],month=str(event['event:startdate'].month),day_=str(event['event:startdate'].day))
                accord = accord + anacc
        for day in editable:
            for event in editable[day]:
                anacc = templates['accordion'].format(id=event['link'].split('/')[-1],title=event['title'],month=str(day.month),day_=str(day.day),description='' if 'description' not in event else event['description'])
                accord = accord + anacc
        return templates['template'].format(body=templates['weekGT'],home_act='',prt_act='',GT_act='class="active"',week_act='',end_act='').format(image=active_glance,accordion='''<div class="panel-group" id="accordion">
    <form action="/weekGT" method="POST">'''+accord+
            '''            <br>
            <button type="submit" class="btn btn-default" name="save2" value="iii">Update</button>
    </form>
</div>''')
    else:
        return templates['template'].format(body=templates['weekGT'],home_act='',prt_act='',GT_act='class="active"',week_act='',end_act='').format(image='template.png',accordion='')

@app.route('/weekFB', method='GET')
def weekFB():
    return templates['template'].format(body=templates['weekFB'],home_act='',prt_act='',GT_act='class="active"',week_act='',end_act='').format(image='week.png',accordion='')

@app.route('/weekFB', method='POST')
def weekFB():
    global cal_feed
    if request.POST.save:
        cal_feed = refresh_OrgSync()
        ask_week = {'This Week': -1, 'Next Week': 0, '2 Weeks Ahead': 1, '3 Weeks Ahead': 2}[request.POST.weekSel.strip()]
        active_glance, editable = cal_maker.week_at_a_glance(cal_feed, ask_week)
        accord = ''
        for event in cal_feed['all_day']:
            if event['event:startdate'] < max(editable.keys()) and event['event:enddate'] >= min(editable.keys()):
                anacc = templates['accordion_all_day'].format(id=event['link'].split('/')[-1],title=event['title'],month=str(event['event:startdate'].month),day_=str(event['event:startdate'].day))
                accord = accord + anacc
        for day in editable:
            for event in editable[day]:
                anacc = templates['accordion'].format(id=event['link'].split('/')[-1],title=event['title'],month=str(day.month),day_=str(day.day),description='' if 'description' not in event else event['description'])
                accord = accord + anacc
        return templates['template'].format(body=templates['weekGT'],home_act='',prt_act='',GT_act='class="active"',week_act='',end_act='').format(image=active_glance,accordion='''<div class="panel-group" id="accordion">
    <form action="/weekGT" method="POST">'''+accord+
            '''            <br>
            <button type="submit" class="btn btn-default" name="save2" value="iii">Update</button>
    </form>
</div>''')
    elif request.POST.save2:
        request.POST.pop('save2', None)
        ids = set([key.split('-')[-1] for key in request.POST])
        features = {id: {key.split('-')[0]: request.POST[key] for key in request.POST if key.split('-')[-1] == id} for id in ids}
        for id in features:
            comp = False
            for event in cal_feed['all_day']:
                if id == event['link'].split('/')[-1]:
                    event['advert'] = 'on' if 'advert' in features[id] else 'off'
                    event['title'] = features[id]['title']
                    comp = True
                    break
            for day in cal_feed['daily']:
                if comp:
                    break
                else:
                    for event in cal_feed['daily'][day]:
                        if id == event['link'].split('/')[-1]:
                            event['advert'] = 'on' if 'advert' in features[id] else 'off'
                            event['desc_on'] = 'on' if 'desc_on' in features[id] else 'off'
                            event['title'] = features[id]['title']
                            event['description'] = features[id]['description']
                            break
                            break
        ask_week = 0
        active_glance, editable = cal_maker.week_at_a_glance(cal_feed, ask_week)
        accord = ''
        for event in cal_feed['all_day']:
            if event['event:startdate'] < max(editable.keys()) and event['event:enddate'] >= min(editable.keys()):
                anacc = templates['accordion_all_day'].format(id=event['link'].split('/')[-1],title=event['title'],month=str(event['event:startdate'].month),day_=str(event['event:startdate'].day))
                accord = accord + anacc
        for day in editable:
            for event in editable[day]:
                anacc = templates['accordion'].format(id=event['link'].split('/')[-1],title=event['title'],month=str(day.month),day_=str(day.day),description='' if 'description' not in event else event['description'])
                accord = accord + anacc
        return templates['template'].format(body=templates['weekGT'],home_act='',prt_act='',GT_act='class="active"',week_act='',end_act='').format(image=active_glance,accordion='''<div class="panel-group" id="accordion">
    <form action="/weekGT" method="POST">'''+accord+
            '''            <br>
            <button type="submit" class="btn btn-default" name="save2" value="iii">Update</button>
    </form>
</div>''')
    else:
        return templates['template'].format(body=templates['weekGT'],home_act='',prt_act='',GT_act='class="active"',week_act='',end_act='').format(image='template.png',accordion='')

run(app, host='localhost', port=8080)
