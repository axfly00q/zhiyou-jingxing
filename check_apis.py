import urllib.request, urllib.error

urls = [
    'http://localhost:8000/api/analytics/overview?days=7',
    'http://localhost:8000/api/analytics/sentiment-trend?days=7',
    'http://localhost:8000/api/analytics/hot-questions?days=7',
    'http://localhost:8000/api/analytics/spot-heatmap?days=7',
    'http://localhost:8000/api/analytics/suggestions?days=7',
    'http://localhost:8000/api/analytics/hourly-traffic?days=7',
    'http://localhost:8000/api/analytics/question-categories?days=7',
    'http://localhost:8000/api/analytics/avatar-preference?days=7',
]

for url in urls:
    name = url.split('/')[-1].split('?')[0]
    try:
        r = urllib.request.urlopen(url)
        print(f'200  {name}')
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:400]
        print(f'{e.code}  {name}: {body}')
