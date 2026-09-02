import requests
import urllib.parse
q = urllib.parse.quote('SPY OR "S&P 500"')
url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={q}&mode=TimelineVol&format=json&startdatetime=20190101000000&enddatetime=20190331235959&sourcelang=eng"
r = requests.get(url, timeout=10)
print("Status:", r.status_code)
print("Text:", r.text[:300])
