"""
Routes and views for the flask application.
"""

from datetime import datetime
from flask import render_template, request
from FlaskWebProject1 import app
import os
import pip

try:
 import pylast
 from pylast import NetworkError, WSError
except:
 package = 'pylast'
 pip.main(['install', '--user', package])
 raise ImportError('Restarting')
try:
 from flask_wtf import FlaskForm
except:
 package = 'flask_wtf'
 pip.main(['install', '--user', package])
 raise ImportError('Restarting')
try:
 from wtforms import DateField, SelectField, validators, ValidationError
except:
 package = 'wtforms'
 pip.main(['install', '--user', package])
 raise ImportError('Restarting')

try:
  import requests
  from requests.packages.urllib3.util.retry import Retry
  from requests.adapters import HTTPAdapter, ConnectionError
except:
 package = 'requests'
 pip.main(['install', '--user', package])
 raise ImportError('Restarting')









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

    if input_time>datetime.today():
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
                 "radio":my_json["schedule"]["service"]["key"]
                 }
            )
        return json.dumps(list_of_data)


class LastFMDataGetter():

    def __init__(self):
        doc = get_secret_dict()




        self.network = pylast.LastFMNetwork(api_key=doc["api_key"],
                                    api_secret=doc["api_secret"],
                                    username=doc["username"],
                                    password_hash=doc["password_hash"])

    def derive_track_dict(self,jsonstring,index):
        data_list = json.loads(jsonstring)
        data_dict = data_list[int(index)]

        print(data_dict["radio"])
        if data_dict["radio"]=="bbcone":
            radio = "BBCRadio1"
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



@app.route('/', methods=['post', 'get'])
@app.route('/home')
def home():
    form = DateForm()
    form2 = BBCStationList()




    index = request.form.get('webmenu', None)
    if index is not None:
        hiddenjson = request.form.get('hiddentype', None)
        try:
            last_fm_getter = LastFMDataGetter()
            tracklist = last_fm_getter.derive_track_dict(hiddenjson,index)
            #print(str(select))
            #print(hiddenjson)

            song_tuples = list()
            for i,track in enumerate(tracklist):
                try:
                    album = pylast.Album(artist=track.track.artist,
                                         title=track.track.title,
                                         network = last_fm_getter.network)
                    print(album)
                    image = album.get_cover_image(0)
                except WSError:
                    image = ""

                song_tuples.append((i,track.track.title,image))
            print(song_tuples[0][2])
        except NetworkError:
            song_tuples = [(1,"testsong","static/content/cover1.jpg"), (2,"testsong2","static/content/cover2.jpg")]

        songlist_form_hidden_data = ""
        songlist_form_data= song_tuples
        """Renders the home page."""
        return render_template(
            'index.html',
            title='Home Page',
            year=datetime.now().year,
            form=form,
            form2=form2,
            songlist_form_data=songlist_form_data,
            episodes=list()
        )

    elif form.is_submitted():
        if form.validate_on_submit():
            my_getter = GetterOfIt()
            imagelist, hiddenjson = my_getter.get_bbc_json(datestring=form.dt.data.strftime('%x'),
                                            radiostation_name=form2.radiostation.data)

            print(hiddenjson)

            return render_template(
                'index.html',
                title='Home Page',
                year=datetime.now().year,
                form=form,
                form2 = form2,
                episodes= imagelist,
                hiddendata = str(hiddenjson)
            )

    """Renders the home page."""
    return render_template(
        'index.html',
        title='Home Page',
        year=datetime.now().year,
        form=form,
        form2=form2,
        episodes=list()
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
