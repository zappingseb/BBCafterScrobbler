# ![image](http://myfirstflask.azurewebsites.net/static/images/both_logos.png) BBC After Scrobbler

A tool to make you scrobble whole BBC Radio shows after the emisson to last.fm

This is a flask app including a virtual environment for the Azure Cloud. The
app is hosted at: http://myfirstflask.azurewebsites.net.

Installation of this app can simply be done by using the [Azure Continuousdeployment] (https://docs.microsoft.com/en-us/azure/app-service-web/web-sites-deploy#a-namecontinuousdeploymentadeploy-continuously-from-a-cloud-based-source-control-service). Just clone this app to your github repository and you can
simply use it on your system.
The documentation for a flask azure app can be found under in this [PDF](http://flask.pocoo.org/docs/0.10/)

## Python 2.7 dependencies

* Flask-WTF
* WTForms
* [pylast](https://github.com/pylast/pylast)
* requests
* json
* yaml

## Usage

To use the app four steps are needed.

1. Login to last.fm via the button

2. Select a radio station and a date to find all episodes of that station at
a certain day:

![Usage first](http://myfirstflask.azurewebsites.net/static/images/screen1.JPG)

3. Choose a radio station and get the scrobbles.

![Usage second](http://myfirstflask.azurewebsites.net/static/images/screen2.JPG)

4. Select the songs to scrobble and Send them to last.fm. They will be send
including the timestamp.

![Usage last](http://myfirstflask.azurewebsites.net/static/images/screen3.JPG)


