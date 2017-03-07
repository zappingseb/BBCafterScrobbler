"""
Routes and views for the flask application.
"""

from datetime import datetime
from flask import render_template, request, session
from FlaskWebProject1 import app
import os
import pip
import json

import six
from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, validators, ValidationError
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter, ConnectionError
import pylast
from pylast import NetworkError, WSError
import yaml



def get_secret_dict(secrets_file="FlaskWebProject1/static/content/test_pylast.yaml"):
    if os.path.isfile(secrets_file):
        import yaml  # pip install pyyaml
        with open(secrets_file, "r") as f:  # see example_test_pylast.yaml
            doc = yaml.load(f)
    else:
        return dict()
    return doc

def validate_it(form, chain):

    input_time = datetime.strptime(chain.raw_data[0], chain.format)

    if input_time > datetime.today():
        raise ValidationError("Please do not use a date in the future")


class DateForm(FlaskForm):
    dt = DateField('Pick a date', format="%m/%d/%Y", validators=[validate_it])


class BBCStationList(FlaskForm):
    # https://github.com/duckduckgo/zeroclickinfo-spice/blob/master/lib/DDG/Spice/BBC.pm
    radiostation = SelectField(
        'Radio Station',
        choices=[("radio1", "BBC Radio 1 London"),
                 ("radio2", "BBC Radio2"),
                 ("radio3", "BBC Radio3"),
                 ("6music", "BBC6 Music"),
                 ("1xtra", "BBC 1xtra")]
    )


class GetterOfIt(object):
    def get_bbc_json(self, datestring, radiostation_name):

        print("WENT TO BBC FUNCTION")

        s = requests.Session()

        datestring_new = datetime.strptime(datestring, "%m/%d/%y").strftime('%Y/%m/%d')

        retries = Retry(total=1,
                        backoff_factor=0.1,
                        status_forcelist=[ 500, 502, 503, 504])

        s.mount('http://', HTTPAdapter(max_retries=retries))
        if radiostation_name=="radio4":
            try:
                request = s.get("".join([
                    "http://www.bbc.co.uk/",
                    str(radiostation_name),
                    "/programmes/schedules/fm/",
                    datestring_new,
                    ".json"
                ]),)
                my_json = json.loads(request.text)
            except ConnectionError:
                 my_json = json.load(open("FlaskWebProject1/static/tests/yesterday.json"))
        elif radiostation_name in ["radio2","radio3","6music","1xtra"]:
            try:
                request = s.get("".join([
                    "http://www.bbc.co.uk/",
                    str(radiostation_name),
                    "/programmes/schedules/",
                    datestring_new,
                    ".json"
                ]),)
                my_json = json.loads(request.text)
            except ConnectionError:
                 my_json = json.load(open("FlaskWebProject1/static/tests/yesterday.json"))
        elif radiostation_name=="radio1":
            radiostation_name="bbcone"
            try:
                request = s.get("".join([
                    "http://www.bbc.co.uk/",
                    str(radiostation_name),
                    "/programmes/schedules/london/",
                    datestring_new,
                    ".json"
                ]),)
                my_json = json.loads(request.text)
            except ConnectionError:
                 my_json = json.load(open("FlaskWebProject1/static/tests/yesterday.json"))

        print("GOT JSON")

        imagelist = self._receive_images(my_json)

        hidden_content = self._receive_hidden(my_json)

        return imagelist, hidden_content

    def _receive_images(self,my_json):

        my_images=list()
        for episode in my_json["schedule"]["day"]["broadcasts"]:
            print(episode["programme"]["display_titles"]["title"])
            print("".join(["sub:",episode["programme"]["display_titles"]["subtitle"]]))
            # my_images.append(
            #    "".join(["<image pid=\"",
            #             episode["programme"]["image"]["pid"],
            #             "\" template_url=\"http://ichef.bbci.co.uk/images/ic/16x16/",
            #             episode["programme"]["image"]["pid"],
            #             ".jpg\" />"])
            # )
            my_images.append(
                [episode["programme"]["image"]["pid"],
                 episode["programme"]["display_titles"]["title"],
                 episode["programme"]["display_titles"]["subtitle"]
                 ])

        print(my_images.__len__())

        return my_images

    def _receive_hidden(self,my_json):
        list_of_data = list()
        for episode in my_json["schedule"]["day"]["broadcasts"]:
            list_of_data.append(
                {"title":episode["programme"]["display_titles"]["title"],
                 "subtitle":episode["programme"]["display_titles"]["subtitle"],
                 "end":episode["end"],
                 "start":episode["start"],
                 "radio":my_json["schedule"]["service"]["key"],
                 }
            )

        return json.dumps(list_of_data)


class LastFMDataGetter():

    def __init__(self):
        doc = get_secret_dict()

        self.network = pylast.LastFMNetwork(api_key=doc["api_key"],
                                    api_secret=doc["api_secret"],
                                            session_key=session.get(
                                                'session_key','notset'))

    def derive_track_dict(self,
                          jsonstring,
                          index):
        data_list = json.loads(jsonstring)
        data_dict = data_list[int(index)]

        print(data_dict["radio"])
        if data_dict["radio"]=="bbcone":
            radio = "BBCRadio1"
        elif data_dict["radio"]=="radio3":
            radio = "BBCRadio3"
        else:
            radio = "".join(["bbc",data_dict["radio"]])

        lastfm_user = self.network.get_user(radio)

        start = datetime.strptime(data_dict["start"], "%Y-%m-%dT%H:%M:%SZ")
        end = datetime.strptime(data_dict["end"], "%Y-%m-%dT%H:%M:%SZ")
        import calendar
        utc_start = calendar.timegm(start.utctimetuple())
        utc_end = calendar.timegm(end.utctimetuple())

        # Act
        tracks = lastfm_user.get_recent_tracks(time_from=utc_start,
                                               time_to=utc_end,limit=1000)

        return tracks

    def derive_episode_text(self,jsonstring, index):
        data_list = json.loads(jsonstring)
        data_dict = data_list[int(index)]
        return " ".join([data_dict["title"]," - ",
                           data_dict["subtitle"]," on ",
                           str(datetime.strptime(data_dict["start"],
                                              "%Y-%m-%dT%H:%M:%SZ").strftime(
                               '%A, %d %b %Y %H:%M'))])

    def derive_form_data(self, hiddenjson, index):
        tracklist = self.derive_track_dict(hiddenjson, index)

        try:
            if len(tracklist)>0:
                for i,track in enumerate(tracklist):

                    song_tuples = [(i," - ".join([track.track.artist.name,
                                                  track.track.title]))
                                   for i,track in enumerate(tracklist)]

                    songlist_form_hidden_data = [{"title":track.track.title,
                                   "artist":track.track.artist.name,
                                   "timestamp":track.timestamp}
                                                 for track in tracklist]
            else:
                song_tuples=[]
                songlist_form_hidden_data=""
        except NetworkError:
            song_tuples = [(1,"testsong"),
                               (2,"testsong2")]

            songlist_form_hidden_data = ""

        return song_tuples, songlist_form_hidden_data, \
               self.derive_episode_text(hiddenjson,index)

    def scrobble_from_json(self, jsonstring="", indeces=list()):

        data_list = json.loads(jsonstring)

        tracklist = [{"title":data_list[index]["title"],
                      "artist":data_list[index]["artist"],
                      "timestamp":data_list[index]["timestamp"]}
                     for index in indeces]
        print("in_scrobble")
        self.network.scrobble_many(tracks=tracklist)

        scrobbling_list = [" - ".join([
            data_list[index]["artist"],
            data_list[index]["title"],
            datetime.fromtimestamp(int(
                data_list[index]["timestamp"])
            ).strftime('%Y-%m-%d %H:%M')
        ])]

        return scrobbling_list

class LoginCheck(object):
    def check(self,the_session_key, lastfm_token):
        doc = get_secret_dict()
        if the_session_key is not None:

            try:
                network=pylast.LastFMNetwork(api_key=doc["api_key"],
                                        api_secret=doc["api_secret"],
                                                session_key=the_session_key)

                logged_in = True
            except:
                logged_in = False

            return logged_in
        else:
            if lastfm_token is not None:

                network = pylast.LastFMNetwork(api_key=doc["api_key"],
                                            api_secret=doc["api_secret"],
                                            username=doc["username"])

                sk_gen = pylast.SessionKeyGenerator(network)
                session_key = sk_gen.get_web_auth_session_key(url=None,
                                                              token=lastfm_token)

                session["session_key"] = session_key

                return True

            else:
                return False


@app.route('/', methods=['post', 'get'])
@app.route('/home')
def home():

    form = DateForm()
    form2 = BBCStationList()

    index_of_episode = request.form.get('webmenu', None)

    indeces_of_songs = request.form.getlist('songs',None)

    lastfm_token = request.args.get('token',None)

    the_session_key = session.get("session_key", None)



    login_checker = LoginCheck()

    logged_in = login_checker.check(the_session_key, lastfm_token)

    if logged_in:

        if index_of_episode is not None:
            hiddenjson = request.form.get('hiddentype', None)
            last_fm_getter = LastFMDataGetter()

            song_tuples, songlist_form_hidden_data, songlist_episode = \
                last_fm_getter.derive_form_data(hiddenjson,index_of_episode)

            if len(song_tuples)<1:
                return render_template(
                    'index.html',
                    title='BBC last.fm - ',
                    year=datetime.now().year,
                    form=form,
                    form2=form2,
                    superstring="No Songs found on last.fm",
                    logged_in=logged_in
                )
            else:
                """Renders the BBC last.fm - ."""
                return render_template(
                    'index.html',
                    title='BBC last.fm - ',
                    year=datetime.now().year,
                    form=form,
                    form2=form2,
                    songlist_episode=songlist_episode,
                    songlist_form_data=song_tuples,
                    songlist_hidden_data=json.dumps(songlist_form_hidden_data),
                    logged_in=logged_in,
                    set_tab="songchoose"
                )

        elif len(indeces_of_songs) > 0:
            indeces_of_songs = [int(song) for song in indeces_of_songs]
            hiddenjson = request.form.get('hiddensongs', None)
            if hiddenjson is not None:
                last_fm_getter = LastFMDataGetter()
                scrobbling_list = last_fm_getter.scrobble_from_json(hiddenjson,
                                                                    indeces_of_songs)
                if scrobbling_list:
                    return render_template(
                        'index.html',
                        title='BBC last.fm - ',
                        year=datetime.now().year,
                        form=form,
                        form2 = form2,
                        superstring = "Successfully Scrobbled",
                        scrobbling_list = scrobbling_list,
                        logged_in=logged_in
                    )
                else:
                    return render_template(
                        'index.html',
                        title='BBC last.fm - ',
                        year=datetime.now().year,
                        form=form,
                        form2 = form2,
                        superstring = "Problems scrobbling, click Refresh",
                        logged_in=logged_in
                    )
        elif form.validate_on_submit():

            print("mygetter")
            my_getter = GetterOfIt()
            imagelist, hiddenjson = my_getter.get_bbc_json(datestring=form.dt.data.strftime('%x'),
                                            radiostation_name=form2.radiostation.data)

            print(hiddenjson)

            return render_template(
                'index.html',
                title='BBC last.fm - ',
                year=datetime.now().year,
                form=form,
                form2 = form2,
                episodes= imagelist,
                hiddendata = str(hiddenjson),
                logged_in=logged_in,
                set_tab="episodefinder"
            )
        else:
            return render_template(
                'index.html',
                title='BBC last.fm - ',
                year=datetime.now().year,
                form=form,
                form2=form2,
                episodes=list(),
                logged_in=logged_in
            )
    else:
        """Renders the BBC last.fm - ."""
        return render_template(
            'index.html',
            title='BBC last.fm - ',
            year=datetime.now().year,
            form=form,
            form2=form2,
            episodes=list(),
            superstring="Please login first"
        )

@app.route('/contact')
def contact():
    """Renders the contact page."""
    return render_template(
        'contact.html',
        title='Contact',
        year=datetime.now().year,
        message='Your contact page.'
    )

@app.route('/about')
def about():
    """Renders the about page."""
    return render_template(
        'about.html',
        title='About',
        year=datetime.now().year,
        message='Your application description page.'
    )
