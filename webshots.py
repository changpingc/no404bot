import subprocess
from tempfile import mktemp
from PIL import Image
from BeautifulSoup import BeautifulSoup
import urllib2
import os.path

def create_local_webshot(config, url):
	bin = config.get("wkhtmltoimage", "bin")
	args = config.get("wkhtmltoimage", "args")
	format = config.get("wkhtmltoimage", "format")
	tmp = config.get("wkhtmltoimage", "tmp")
	
	output_path = mktemp(dir=tmp, suffix="."+format, prefix="")
	
	command = " ".join([bin, args, "-f", format, "'%s'" % url, output_path])
	
	p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	(stdout, stderr) = p.communicate()
	retcode = p.poll()
	
	result = {}
	result["url"] = url
	result["path"] = output_path
	if retcode != 0 or os.path.getsize(output_path) < 5000:
		result["stdout"] = stdout
		result["stderr"] = stderr
		result["retcode"] = retcode
		result["status"] = "failed"
	else:
		im = Image.open(output_path)
		if im.size[0] < 100 or im.size[1] < 100:
			result["status"] = "failed"
			result["message"] = "Image too small"
		else:
			soup = BeautifulSoup(urllib2.urlopen(url))
			result["title"] = soup.title.string
			result["status"] = "succeeded"
	return result

if __name__ == "__main__":
	from main import get_config
	import sys
	config = get_config()
	
	print create_local_webshot(config, sys.argv[1])

