
"""
Flask App for BBC After Scrobbler

author: Sebastian Wolf
description: This is the view file generating the substantial
    view from the index.html File

Steps of the workflow:

    * Check if the user is logged in
    * Login the user via last.fm and put session_key into session
    * Check if a songlist was sent
    ** Scrobble songs from list
    * Check if an episode was sent
    ** Get the songs of this episode and display them
    * Check if a BBC Radio station and time were sent
    ** Generate a list of episodes to be displayed in a form
"""
__author__ = "Sebastian Wolf"
__copyright__ = "Copyright 2017, BBCAfterSCrobbler"
__license__ = "https://www.apache.org/licenses/LICENSE-2.0"
__version__ = "0.0.1"
__maintainer__ = "Sebastian Wolf"
__email__ = "sebastian@mail-wolf.de"
__status__ = "Production"


from datetime import datetime
from flask import render_template, request, session
from FlaskWebProject1 import app
import os
import json
from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, ValidationError, TextAreaField
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter, ConnectionError
import pylast
from pylast import NetworkError, WSError
import yaml
import re

def get_secret_dict(secrets_file="FlaskWebProject1/static/content/test_pylast.yaml"):
    if os.path.isfile(secrets_file):
        with open(secrets_file, "r") as f:  # see example_test_pylast.yaml
            doc = yaml.load(f)
    else:
        return dict()
    return doc

def validate_it(form, chain):
    """ Function to validate if no future date was sent

    :param form: Any Flaskform from the app
    :type form: FlaskForm

    :param chain: Data of the flaskform in a chained format

    :return: Raise Validationerror if date is in the future
    """

    input_time = datetime.strptime(chain.raw_data[0], chain.format)

    if input_time > datetime.today():
        raise ValidationError("Please do not use a date in the future")


class Textfield(FlaskForm):

    input_text = TextAreaField("TextList")

class DateForm(FlaskForm):
    """ Generate a dateform in american date format

    This generates a date selecter that will be rendered
    by Jquery UI as a DatePicker later on (see static/templates/index.html)

    """
    dt = DateField("datepick", format="%m/%d/%Y", validators=[validate_it])


class BBCStationList(FlaskForm):
    """BBC Station List Dropdown Form

    This generates a select field were a single BBC Station
    can be selected by the user

    Names of BBC stations can be found at:

        https://github.com/duckduckgo/zeroclickinfo-spice/blob/master/lib/DDG/Spice/BBC.pm
    """

    radiostation = SelectField(
        'Radio Station',
        choices=[("radio1", "BBC Radio 1 London"),
                 ("radio2", "BBC Radio2"),
                 ("radio3", "BBC Radio3"),
                 ("6music", "BBC6 Music"),
                 ("1xtra", "BBC 1xtra")]
    )


class GetterOfIt(object):
    """Class to access BBC Stations API

    """
    def get_bbc_json(self, datestring, radiostation_name):
        """Accessing a JSON file provided by the BBC API as
        described at

        http://www.bbc.co.uk/blogs/radiolabs/2008/05/helping_machines_play_with_pro.shtml

        :param datestring: A string providing a date in "%m/%d/%y" format

        :type datestring: str

        :param radiostation_name: A BBC Radio Station name in short format
            as it can be used by the API

        :return: imagelist, hidden_content

            imagelist: A List of episodes pid, title and subtitle
                Each episode is a dictionary with these fields

            hidden_content: A string of the list of data which contains dictionaries with the following fields
                per dictionary:

                * title = Name of the episode
                * subtitle = Subtitle of the episode
                * start = Starting time
                * end = Ending time
                * radio = radio station name
        """

        # Parse the datestring
        datestring_new = datetime.strptime(datestring, "%m/%d/%y").strftime('%Y/%m/%d')

        # start requests session
        s = requests.Session()


        # Define a Retry Element to have the possibility to
        retries = Retry(total=1,
                        backoff_factor=0.1,
                        status_forcelist=[ 500, 502, 503, 504])

        s.mount('http://', HTTPAdapter(max_retries=retries))


        # Get the json from the specific radiostation by using the
        # BBC API
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

        # Parse a short list of station information
        imagelist = self._receive_images(my_json)

        # Get a large list of the stations information

        hidden_content = self._receive_hidden(my_json)

        # Return both lists as strings (json.dumps)
        return imagelist, hidden_content

    def _receive_images(self, my_json):
        """ Derive a short dictionary with BBC Episode information

        :param my_json: Dictionary of the JSON Provided by the BBC Station API

        :return: imagelist

            A List of episodes pid, title and subtitle

            Each episode is a dictionary with these fields
        """

        my_images=list()
        for episode in my_json["schedule"]["day"]["broadcasts"]:

            my_images.append(
                [episode["programme"]["image"]["pid"],
                 episode["programme"]["display_titles"]["title"],
                 episode["programme"]["display_titles"]["subtitle"]
                 ])

        return my_images

    def _receive_hidden(self, my_json):
        """ Read out essential data for each episode in a BBC JSON

        :param my_json: Dictionary containing a JSON from the BBC API

        :return: json.dumps(list_of_data)

            A string of the list of data which contains dictionaries with the following fields
            per dictionary:

                * title = Name of the episode
                * subtitle = Subtitle of the episode
                * start = Starting time
                * end = Ending time
                * radio = radio station name
        """
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


class TextParser():

    def deparse_txt(self,list_of_artist_track,splittype,
                    exceptions=None):
        if not exceptions:
            exceptions = ["Remix", "Reprise", "Edit","Mix","Dubplate"]

        flatten = lambda l: [item for sublist in l for item in sublist]

        list_of_artist_track = re.sub(u'\u2013','-',list_of_artist_track)
        list_of_artist_track = re.sub(u'\xe2','-',list_of_artist_track)
        list_of_artist_track = re.sub(u'\u2019',"'",list_of_artist_track)

        list_of_artist_track=list_of_artist_track.decode('utf-8').replace(u'\xe2', '-').encode('ascii', 'replace').encode('utf-8')

        list_of_artist_track = list_of_artist_track.replace("by Robert Luis","by Robert Luis (Tru Thoughts)")

        list_of_artist_track = list_of_artist_track.splitlines()

        if splittype:

            list_of_artist_track = [element.split("-") for element in list_of_artist_track]

        else:

            list_of_artist_track = [element for element in list_of_artist_track if not element == '' or not element == " "]

            for splitter in ["-","\xe2"]:

                if isinstance(list_of_artist_track,str):
                    list_of_artist_track = list_of_artist_track.split(splitter)
                else:
                    list_of_artist_track = flatten([line_file.split(splitter) for line_file in list_of_artist_track])


            for entry in exceptions:
                pattern = "".join(["(?:", entry, ")(\))"])
                out_pat = "".join([entry,"|)"])
                list_of_artist_track = [re.sub(pattern, out_pat, entry) for entry in list_of_artist_track]


            list_of_artist_track = flatten([re.split("(?<!\|)(\))", entry) for entry in list_of_artist_track])


            # Delete ending brackets
            list_of_artist_track = [element for element in list_of_artist_track if element != ")"]

            list_of_artist_track = [
                [list_of_artist_track[i].strip().strip("|"),
                 "".join(list_of_artist_track[i+1].strip().split("(")[
                     0:list_of_artist_track[i+1].count("(")
                 ]).strip().replace("|","").strip(")")]
                   for i in range(0, len(list_of_artist_track)-1, 2)]


            list_of_artist_track = [var for var in list_of_artist_track if len(var)>0]



        song_tuples = [(i," -+- ".join([track[0],track[1]]))
                                   for i,track in enumerate(list_of_artist_track)]

        songlist_form_hidden_data = [{"title":track[1],
                                   "artist":track[0]}
                                                 for track in list_of_artist_track]
        return song_tuples, songlist_form_hidden_data

class LastFMDataGetter():
    """ A class to derive basic connectivities with
    the last.fm API

    On init it connects to the last.fm API with a session key

    Without a session key it will cause a WSError
    """

    def __init__(self):
        doc = get_secret_dict()

        self.network = pylast.LastFMNetwork(api_key=doc["api_key"],
                                    api_secret=doc["api_secret"],
                                            session_key=session.get(
                                                'session_key','notset'))

    def derive_track_dict(self,
                          jsonstring,
                          index):
        """Derive a list of tracks played by a specific BBC radio station
        in a specific time range

        Tasks:
            * Get the episode information
            * Convert the timestrings
            * Convert the radio station name to last.fm user account name
            * Derive the tracks by using pylast.get_recent_tracks

        :param jsonstring: A dictionary of BBC radio station episode information
            containing dictinaries. It is normally produced by
            :func:`GetterOfIt._receive_hidden`

        :param index: The number of the element of the list in the jsonstring that
            shall be used for calling the API

        :type index: int

        :return: tracks

            A list of last.fm PlayedTracks (pylast.Track) elements
            that were played in the time range of the defined
            episode

        :rtype: list
        """

        data_list = json.loads(jsonstring)
        data_dict = data_list[int(index)]

        # Rename the radio station to BBC user Names

        if data_dict["radio"]=="bbcone":
            radio = "BBCRadio1"
        elif data_dict["radio"]=="radio3":
            radio = "BBCRadio3"
        else:
            radio = "".join(["bbc",data_dict["radio"]])

        # Convert the datestrings of start and end of the episode to UTC

        start = datetime.strptime(data_dict["start"], "%Y-%m-%dT%H:%M:%SZ")
        end = datetime.strptime(data_dict["end"], "%Y-%m-%dT%H:%M:%SZ")
        import calendar
        utc_start = calendar.timegm(start.utctimetuple())
        utc_end = calendar.timegm(end.utctimetuple())

        # Derive the tracks from pylast
        lastfm_user = self.network.get_user(radio)
        tracks = lastfm_user.get_recent_tracks(time_from=utc_start,
                                               time_to=utc_end,limit=1000)

        return tracks

    def derive_episode_text(self,jsonstring, index):
        """ Derive a string for the name of the episode plus the time
        it was played at to be displayed in the app

        :param jsonstring: A dictionary of BBC radio station episode information
            containing dictinaries. It is normally produced by
            :func:`GetterOfIt._receive_hidden`

        :param index: The number of the element of the list in the jsonstring that
            shall be used for calling the API

        :type index: int

        :return: An information string for the episode

            Like "Jamie Cullum - Friday Night show - Friday, March 20 2016 20:00"
        """
        data_list = json.loads(jsonstring)
        data_dict = data_list[int(index)]
        return " ".join([data_dict["title"]," - ",
                           data_dict["subtitle"]," on ",
                           str(datetime.strptime(data_dict["start"],
                                              "%Y-%m-%dT%H:%M:%SZ").strftime(
                               '%A, %d %b %Y %H:%M'))])

    def derive_form_data(self, hiddenjson, index):
        """ From basic BBC Episode information + an index of the episode
        derive the songs played in two formats and the name+Playtime

        Tasks:

            * Derive a list of tracks of the episode by pylast
            * In case the list is not empty generate a list with
            ** title
            ** artist
            ** timestamp
            * and another list with
            ** counter(i), "artist - title"

            The first list shall go in the hidden content of a flaskform. The second list
            is displayed to the user to select songs

            * Derive the name of the episode which songs are displayed

        :param hiddenjson: A dictionary of BBC radio station episode information
            containing dictinaries. It is normally produced by
            :func:`GetterOfIt._receive_hidden`

        :param index: The number of the element of the list in the jsonstring that
            shall be used for calling the API

        :type index: int

        :return: song_tuples, songlist_form_hidden_data, episode_string

        """
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

    def scrobble_from_json(self, jsonstring="", indeces=list(), has_timestamp=True):
        """From a json of Songs and a list of indeces scrobble songs to the last.fm API

        This uses pylast.scrobble_many to simply scrobbe a list of songs from a jsonstring
        that contains these songs and a list of indeces which songs to take from that list

        :param jsonstring: A json put into a string. the json was compiled by :func:`songlist_form_hidden_data

        :param indeces: A list of integers telling which elements to take from the songlist and scrobble them

        :return: The list of songs as "Artist - Title - Timestamp" to be displayed in the app
        """
        data_list = json.loads(jsonstring)

        try:
            data_list[indeces[0]]["timestamp"]
        except KeyError:
            has_timestamp = False

        if has_timestamp:
            tracklist = [{"title":data_list[index]["title"],
                          "artist":data_list[index]["artist"],
                          "timestamp":data_list[index]["timestamp"]}
                         for index in indeces]
        else:
            tracklist = [{"title":data_list[index]["title"],
                          "artist":data_list[index]["artist"],
                          "timestamp":datetime.now()}
                         for index in indeces]
        try:
            self.network.scrobble_many(tracks=tracklist)

            if has_timestamp:
                scrobbling_list = [" - ".join([
                    data_list[index]["artist"],
                    data_list[index]["title"],
                    datetime.fromtimestamp(int(
                        data_list[index]["timestamp"])
                    ).strftime('%Y-%m-%d %H:%M')
                ]) for index in indeces]
            else:
                scrobbling_list = [" - ".join([
                    data_list[index]["artist"],
                    data_list[index]["title"]]) for index in indeces]
        except (WSError, NetworkError,KeyError) as d:
            print(d)
            scrobbling_list = False

        return scrobbling_list

class LoginCheck(object):
    """ Class to perform Login at the last.fm API

    This class just carries one function that checks if a login
    has to be performed or already was performed.

    """
    def check(self,the_session_key, lastfm_token):
        """ Depending on the existence of a session key or lastfm_token
        tell the app if the user is logged in or not

        :param the_session_key: A session key derived by pylast.SessionKeyGenerator

        :param lastfm_token: A token derived by calling the last.fm API as
            on http://www.last.fm/api/webauth

        :return: True (user is logged in) | False (user not logged in)
        """

        # Derive secret API key and API secret form yaml file
        doc = get_secret_dict()

        # If a session_key is there
        if the_session_key is not None:
            # try to connect at last.fm
            try:
                network=pylast.LastFMNetwork(api_key=doc["api_key"],
                                        api_secret=doc["api_secret"],
                                                session_key=the_session_key)
                logged_in = True
            except:
                logged_in = False

            return logged_in
        else:
            # If a token was provided
            if lastfm_token is not None:

                network = pylast.LastFMNetwork(api_key=doc["api_key"],
                                            api_secret=doc["api_secret"],
                                            username=doc["username"])

                # Create a session key by using pylast
                try:
                    sk_gen = pylast.SessionKeyGenerator(network)
                    session_key = sk_gen.get_web_auth_session_key(url=None,
                                                                  token=lastfm_token)
                except WSError:
                    return False

                session["session_key"] = session_key

                return True

            else:
                return False


@app.route('/', methods=['post', 'get'])
@app.route('/home')
def home():

    logged_in = False

    # Generate a starting formula using WTF Forms
    form = DateForm()
    form2 = BBCStationList()
    form3 = Textfield()

    index_of_episode = request.form.get('webmenu', None)

    indeces_of_songs = request.form.getlist('songs',None)

    lastfm_token = request.args.get('token',None)

    the_session_key = session.get("session_key", None)

    logout = request.form.get('logout', None)

    if logout:
        session["session_key"] = None
        the_session_key = None

    # Check if the user generated a login session key
    login_checker = LoginCheck()

    logged_in = login_checker.check(the_session_key, lastfm_token)

    # In case the user is logged in already
    if logged_in:

        # If a BBC episode was sent via POST
        if index_of_episode is not None:

            # get the hidden data of the BBC episode
            hiddenjson = request.form.get('hiddentype', None)
            last_fm_getter = LastFMDataGetter()

            # Derive the songs of the BBC episode
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
                    logged_in=logged_in,
                    set_tab="songchoose"
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
        # Check if a list of songs was selected by
        # the user and send via POST
        elif len(indeces_of_songs) > 0:
            # convert indeces to integer
            indeces_of_songs = [int(song) for song in indeces_of_songs]

            # Get the hiddenjson containing song infos
            hiddenjson = request.form.get('hiddensongs', None)


            if hiddenjson is not None:

                # Connect to last.fm and scrobble songs
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

        # Check if a date and BBC Radio station were selected and
        # send via POST
        elif form.is_submitted() and form.dt.data:
            form.validate_on_submit()
            print(form.dt.data is not None)


            print("mygetter")
            my_getter = GetterOfIt()
            imagelist, hiddenjson = my_getter.get_bbc_json(datestring=form.dt.data.strftime('%x'),
                                            radiostation_name=form2.radiostation.data)


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

        elif form3.is_submitted() and form3.input_text.data:


            text=form3.input_text.data
            text_parser = TextParser()
            checkit = request.form.get("hackbox",False)
            checkit = bool(checkit)
            if checkit:
                hackbox = "checked"
            else:
                hackbox = None
            song_tuples, songlist_form_hidden_data = text_parser.deparse_txt(text,checkit)
            if len(song_tuples)<1:
                return render_template(
                    'index.html',
                    title='BBC last.fm - ',
                    year=datetime.now().year,
                    superstring="No Songs found in your list",
                    logged_in=logged_in,
                    set_tab="songchoose",
                    hackbox=hackbox,
                    no_bbc="True"
                )
            else:
                form3.input_text.data = text
                """Renders the BBC last.fm - ."""
                return render_template(
                    'index.html',
                    title='BBC last.fm - ',
                    year=datetime.now().year,
                    form3=form3,
                    songlist_episode="Your parse songs:",
                    songlist_form_data=song_tuples,
                    songlist_hidden_data=json.dumps(songlist_form_hidden_data),
                    logged_in=logged_in,
                    set_tab="songchoose",
                    no_bbc="True",
                    hackbox=hackbox
                )

        else:
            return render_template(
                'index.html',
                title='BBC last.fm - ',
                year=datetime.now().year,
                form=form,
                form2=form2,
                form3=form3,
                episodes=list(),
                logged_in=logged_in
            )
    # Not logged in
    else:
        """Renders the BBC last.fm - ."""
        return render_template(
            'index.html',
            title='BBC last.fm - ',
            year=datetime.now().year,
            episodes=list(),
            superstring="Please login first",
            supersubstring="explain",
            no_bbc="True"
        )
