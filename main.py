from threads import ThreadPool
from twitter import search_twitter, upload_twitpic
import ConfigParser
from pymongo import Connection, DESCENDING
from datetime import datetime
from webshots import create_local_webshot
import sys
import platform
import pycurl
import re
from StringIO import StringIO
import traceback

TWITTER_DATETIME_FORMAT = "%a, %d %b %Y %H:%M:%S +0000"

def get_config():
	config = ConfigParser.RawConfigParser()
	config.add_section("proxy")
	config.add_section("runtime")
	config.set("proxy", "http", "")
	config.read("no404.config")
	
	local = True if platform.mac_ver()[0] else False
	config.set("runtime", "platform", "local" if local else "server")
	suffix = "_" + config.get("runtime", "platform")
	
	for section in config.sections():
		for name, value in config.items(section):
			if name.endswith(suffix):
				config.set(section, name.split(suffix)[0], value)
	
	return config

def subdict(dict, keys):
	ret = {}
	for key in keys:
		ret[key] = dict[key]
	return ret

def read_tweet(pool, db, config, tweet_id):
	tweet = db.twitter_tweets.find_one({"id":tweet_id})
	webshots = db.webshots
	for url_set in tweet["urls"]:
		url = url_set["expanded_url"]
		if webshots.find_one({"urls":url}): # duplicate
			continue
		
		same_urls = [url, ]
		depth_limit = 10
		index = 1
		while True:
			if index > depth_limit: return
			c = pycurl.Curl()
			c.setopt(c.URL, url.encode("utf8"))
			c.setopt(c.NOBODY, True)
			buffer = StringIO()
			c.setopt(c.HEADER, True)
			c.setopt(c.WRITEFUNCTION, buffer.write)
			c.perform()
			index += 1
			try:
				new_url = re.findall(r'''(?mi)(?<=^Location:\s).+$''', buffer.getvalue())[0].strip()
				same_urls.append(new_url)
				url = new_url
			except IndexError:
				break
				
		print "Taking webshot at (%s)" % (", ".join(same_urls))
		result = create_local_webshot(config, url)
		if result["status"] == "succeeded":
			timestamp = datetime.now()
			image_url = upload_twitpic(config, result["path"], u"%s @%s" % (result["title"], tweet["from_user"]))
			webshot = {
				"urls":same_urls, 
				"image_url":image_url, 
				"original_tweet" : tweet_id,
				"created_at" : timestamp, 
				}
			webshots.insert(webshot)
			print "Webshot<%s> taken at (%s)" % (image_url, ", ".join(same_urls))
		else:
			print result

def _main():
	config = get_config()
	pool = ThreadPool(4)
	
	connection = Connection(config.get("mongodb", "host"), config.getint("mongodb", "port"))
	db = connection[config.get("mongodb", "db")]
	
	searches = db.twitter_searches
	tweets = db.twitter_tweets
	for keyword in config.get("twitter", "keywords").split(":"):
		last_searches = searches.find({"keyword":keyword})
		if last_searches.count():
			since_id = last_searches.sort("created_at", DESCENDING).limit(1)[0]["max_id"]
		else:
			since_id = 0
		
		response = search_twitter(config, keyword, since_id=str(since_id))
		
		new_search = subdict(response, ["max_id", "since_id"])
		new_search["keyword"] = keyword
		new_search["created_at"] = datetime.now()
		
		searches.insert(new_search)
		
		print "Found %d results on %s" % (len(response["results"]), keyword)
		
		for result in response["results"]:
			if result["from_user"] == "no404bot": continue
			urls_list = result["entities"].get("urls", None)
			if not urls_list: continue
			tweet = subdict(result, ["from_user", "from_user_id", "text", "iso_language_code", "id"])
			tweet["created_at"] = datetime.strptime(result["created_at"], TWITTER_DATETIME_FORMAT)
			tweet["urls"] = urls_list
			tweets.insert(tweet)
			pool.add_task(read_tweet, pool, db, config, tweet["id"])
			
	pool.wait_completion()
	

if __name__ == '__main__':
	reload(sys)	
	sys.setdefaultencoding("utf8")
	_main()
