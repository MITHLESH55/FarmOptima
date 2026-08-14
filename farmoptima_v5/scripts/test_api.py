import requests
s='http://127.0.0.1:8000'
loc={'lat':18.5254,'lon':74.0150}
try:
    r=requests.get(f"{s}/api/satellite", params=loc, timeout=60)
    print('/api/satellite', r.status_code)
    print(r.text)
except Exception as e:
    print('sat err', e)
try:
    r=requests.post(f"{s}/api/recommend", json={'lat':loc['lat'],'lon':loc['lon']}, timeout=120)
    print('/api/recommend', r.status_code)
    print(r.text[:2000])
except Exception as e:
    print('rec err', e)
