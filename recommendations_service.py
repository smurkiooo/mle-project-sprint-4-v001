import logging
import pandas as pd
from fastapi import FastAPI
logger = logging.getLogger("uvicorn.error")










app = FastAPI(title="сервис для рекомендации треков")









class Recommendations:
    """Класс управляет оффлайн рекомендациями: Отранжированными CatBoost и дефолтные Топ-популярных треков"""

    def __init__(self):
        self._recs = {"personal": None, "default": None}
        self._stats = {
            "request_personal_count": 0,
            "request_default_count": 0,
        }

    def load(self, type: str, path: str, **kwargs):
        logger.info(f"загрузка рекомендаций, тип: {type}")
        self._recs[type] = pd.read_parquet(path, **kwargs)
        if type == "personal":
            self._recs[type] = self._recs[type].set_index("user_id")
        logger.info(f"Loaded {type} recommendations")

    def get(self, user_id: int, k: int = 100):
        try:
            recs = self._recs["personal"].loc[[user_id]]
            recs = recs.sort_values("rank")["item_id"].tolist()[:k]
            self._stats["request_personal_count"] += 1
        except KeyError:
            recs = self._recs["default"]["item_id"].tolist()[:k]
            self._stats["request_default_count"] += 1
        except Exception:
            logger.error("никаких рекомендаций не найдено")
            recs = []
        return recs

    def stats(self):
        logger.info("Recommendation stats:")
        for name, value in self._stats.items():
            logger.info(f"  {name:<30} {value}")


class SimilarItems:
    """Класс находит и рекомендует похожие айтемы (треки)в зависимоти от истории действий пользователя"""

    def __init__(self):
        self._similar = None

    def load(self, path: str, **kwargs):
        logger.info("загрузка похожих айтемов")
        self._similar = pd.read_parquet(path, **kwargs).set_index("item_id_1")
        logger.info("готово")

    def get(self, item_id: int, k: int = 10) -> list:
        try:
            rows = self._similar.loc[[item_id]]
            return rows.sort_values("score", ascending=False)["item_id_2"].tolist()[:k]
        except KeyError:
            return []


class EventStore:
    """хранит недавние онлайн пользовательские взаимодействия"""

    def __init__(self, max_events_per_user: int = 10):
        self._events: dict = {}
        self._max_events = max_events_per_user

    def put(self, user_id: int, item_id: int):
        events = self._events.setdefault(user_id, [])
        events.append(item_id)
        self._events[user_id] = events[-self._max_events :]

    def get(self, user_id: int) -> list:
        return list(self._events.get(user_id, []))


rec_store = Recommendations()
similar_items_store = SimilarItems()
events_store = EventStore(max_events_per_user=10)


@app.on_event("startup")
async def startup():
    # загрузка персональных ALS рекомендаций, отранжированных катбустом
    rec_store.load("personal","recsys/recommendations/recommendations.parquet",columns=["user_id", "item_id", "rank"],)

    #Дефолтные рекомендации - топ100 популярных треков
    default_df = pd.read_parquet("recsys/recommendations/top_popular.parquet",columns=["track_id", "popularity"])
    default_df = (default_df.rename(columns={"track_id": "item_id"}).sort_values("popularity", ascending=False).reset_index(drop=True))
    rec_store._recs["default"] = default_df

    # похожие треки для онлайн рекомендаций
    similar_items_store.load("recsys/recommendations/similar.parquet", columns=["item_id_1", "item_id_2", "score"])


@app.post("/put_event")
async def put_event(user_id: int, item_id: int):
    """функция записывает в хранилище пользовательские действия онлайн"""
    events_store.put(user_id, item_id)
    return {"status": "ok", "user_id": user_id, "item_id": item_id}


@app.post("/recommendations")
async def recommendations(user_id: int, k: int = 100):
    """функция возвращает к рекомендаций для пользователя (смешивая онлайн и офлайн сигналы)

    стратегия смешивания такая:
   Берём последние треки, которые пользователь прослушал (из текущей сессии),
    и для каждого из них находим похожие треки через матрицу ALS item-item similarity.
      Чем недавнее событие  тем выше его треки в списке. Дубликаты убираем.
   Офлайн-часть: Если у пользователя есть персональная модель, то берём его рекомендации,
     отранжированные CatBoost. Если про пользователя ничего неизвестно,
       даём просто топ самых популярных треков.
 Итоговый список: Сначала идут онлайн-рекомендации (самые релевантные), 
 потом офлайн заполняют оставшиеся места до k.
  Треки, уже попавшие в онлайн часть , еще раз не добавляются.
    """
    # онлайн 
    history = events_store.get(user_id)
    seen: set = set()
    online_recs: list = []
    for item_id in reversed(history):   # сначала последние события
        for sim_item in similar_items_store.get(item_id, k=k):
            if sim_item not in seen:
                seen.add(sim_item)
                online_recs.append(sim_item)

    # офлайн
    offline_recs = rec_store.get(user_id, k=k)

    # смешанные рекомендации
    blended = list(online_recs)
    for item in offline_recs:
        if item not in seen:
            seen.add(item)
            blended.append(item)
        if len(blended) >= k:
            break

    return {"recs": blended[:k]}


@app.get("/health")
async def health():
    """возвращает ОК когда все ланные загружены"""
    ready = all(v is not None for v in rec_store._recs.values())
    return {"status": "ok" if ready else "loading"}


@app.get("/stats")
async def stats():
    """возвращает счетчик на запросы рекомендаций разных типов от пользователя"""
    rec_store.stats()
    return rec_store._stats
