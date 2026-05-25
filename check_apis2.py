import urllib.request, urllib.error

urls = [
    'http://localhost:8000/api/analytics/hot-questions?limit=10',
    'http://localhost:8000/api/analytics/spot-heatmap',
]

for url in urls:
    name = url.split('/')[-1].split('?')[0]
    try:
        r = urllib.request.urlopen(url)
        print(f'200  {name}: {r.read().decode()[:200]}')
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:600]
        print(f'{e.code}  {name}: {body}')
