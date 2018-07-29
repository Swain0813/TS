import requests
print ("downloading with requests")
url = 'https://cdn-1-lt.cdnpan.com/hls/2018/07/22/bzjeAH24/out004.ts'
r = requests.get(url)
with open("demo3.ts", "wb") as code:
     code.write(r.content)