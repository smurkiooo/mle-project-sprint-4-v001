import numpy as np
import pandas as pd
from recommendations_service import Recommendations

rec_store = Recommendations()

rec_store.load(
    "personal",
    # ваш код здесь #,
    columns=["user_id", "item_id", "rank"],
)
rec_store.load(
    "default",
    # ваш код здесь #,
    columns=["item_id", "rank"],
)

rec_store.get(user_id=100, k=5)


@app.post("/recommendations")
async def recommendations(user_id: int, k: int = 100):
    """
    Возвращает список рекомендаций длиной k для пользователя user_id
    """

    recs = rec_store.get(user_id, k)

    return {"recs": recs}


import requests

recommendations_url = "http://127.0.0.1:8000"

headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
params = {"user_id": 1353637, 'k': 3}

resp = requests.post(recommendations_url + "/recommendations", headers=headers, params=params)
if resp.status_code == 200:
    recs = resp.json()
else:
    recs = []
    print(f"status code: {resp.status_code}")
    
print(recs)