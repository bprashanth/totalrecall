#!/usr/bin/env python3
import json,sys,urllib.request
URL='http://127.0.0.1:33167/call'; TOKEN='f7f3902124fe1210980993780b895dcc4900c925ffcd3dad'
payload={'skill':sys.argv[1],'args':json.loads(sys.argv[2]) if len(sys.argv)>2 else {}}
req=urllib.request.Request(URL,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+TOKEN})
print(urllib.request.urlopen(req,timeout=300).read().decode())
