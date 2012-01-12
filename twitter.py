from twython import Twython
import twitpic
from yfrog import Uploader as YfrogUploader
import urllib
import httplib2
import sys

def post_twitter(config, message):
	username = config.get("twitter", "username")
	password = config.get("simpleauthtwitter", "key")

	http = httplib2.Http()
	http.add_credentials(username, password)
	response = http.request(
		"http://simpleauthtwitter.heroku.com/api/statuses/update.xml", 
		"POST", 
		urllib.urlencode({"status": message})
	)
	
	if response: return
	else: raise Exception("Twitter update failed <%s>" % message)

def get_twython(config):
	twitter = Twython(
		twitter_token = config.get("twitter", "consumer_key"),
		twitter_secret = config.get("twitter", "consumer_secret"),
		oauth_token = config.get("twitter", "access_token_key"),
		oauth_token_secret = config.get("twitter", "access_token_secret"),
		proxy = config.get("proxy", "http"),
	)
	return twitter

	# ef get_tweepy(config):
	# auth = tweepy.OAuthHandler(config.get("twitter", "consumer_key"), config.get("twitter", "consumer_secret"))
	# auth.set_access_token(config.get("twitter", "access_token_key"), config.get("twitter", "access_token_secret"))
	# api = tweepy.API(auth)
	# return api

def search_twitter(config, keyword, **kwargs):
	twitter = get_twython(config)
	return twitter.searchTwitter(include_entities="true", result_type="recent", rpp=100, q=keyword, **kwargs)

def upload_twitpic(config, file, message):
	twit = twitpic.TwitPicAPI(config.get("twitter", "username"), config.get("twitter", "password"))
	twitpic_url = twit.upload(file, message=message)
	if type(twitpic_url) == int:
		print "twitpic upload %s returned %d" % (file, twitpic_url)
		return None
	post_twitter(config, message + " " + twitpic_url)
	# api = get_tweepy(config)
	# api.update_status(message + " " + twitpic_url)
	return twitpic_url

def upload_yfrog(config, file, message):
	yfrog = YfrogUploader()
	result = yfrog.uploadFile(file, config.get("twitter", "username"), config.get("twitter", "password"), message=message, public=True, source="no404 bot")
	return result["url"]