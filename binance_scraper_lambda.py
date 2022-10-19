import json
import random
import string
import time
import logging
import requests

def fetch_binance_announcements(categoryId : int):
    # Generate random query/params to help prevent caching
    rand_page_size = random.randint(1, 1)
    letters = string.ascii_letters
    random_string = "".join(random.choice(letters) for i in range(random.randint(10, 20)))
    random_number = random.randint(1, 99999999999999999999)
    queries = [
        "type=1",
        f"catalogId={categoryId}",
        "pageNo=1",
        f"pageSize={str(rand_page_size)}",
        f"rnd={str(time.time())}",
        f"{random_string}={str(random_number)}",
    ]
    random.shuffle(queries)
    request_url = (
        f"https://www.binance.com/gateway-api/v1/public/cms/article/list/query"
        f"?{queries[0]}&{queries[1]}&{queries[2]}&{queries[3]}&{queries[4]}&{queries[5]}"
    )

    latest_announcement = requests.get(request_url, timeout=0.3)
    if latest_announcement.status_code == 200:
        try:
            cache_hit = True
        except KeyError:
            # No X-Cache header was found - great news, we're hitting the source.
            pass

        latest_announcement = latest_announcement.json()
        news = latest_announcement["data"]["catalogs"][0]["articles"][0]
        news['cache_hit'] = cache_hit
        return news
    else:
        return None
    
coms['result'] = fetch_binance_announcements(body.get('category_id', 48))