import fastapi
import numpy as np
import pandas as pd
import os
import logging as logger


class Recommendations:

    def __init__(self):

        self._recs = {"personal": None, "default": None}
        self._stats = {"request_personal_count": 0, "request_default_count": 0}

    def load(self, type, path, **kwargs):
        #загрузка рекомендаций типа type из паркет-файла

        logger.info(f"Loading recommendations, type: {type}")
        self._recs[type] = pd.read_parquet(path, **kwargs)
        if type == "personal":
            self._recs[type] = self._recs[type].set_index("user_id")
        logger.info(f"Loaded")

    def get(self, user_id: int, k: int=100):
        #для конкретного слушателя по user_id возвращается список рекомендаций для него
        try:
            recs = self._recs["personal"].loc[user_id]
            recs = recs["item_id"].to_list()[:k]
            self._stats["request_personal_count"] += 1
        except KeyError:
            recs = self._recs["default"]
            recs = recs["item_id"].to_list()[:k]
            self._stats["request_default_count"] += 1
        except:
            logger.error("No recommendations found")
            recs = []

        return recs

    def stats(self):

        logger.info("статистики по рекоммендациям")
        for name, value in self._stats.items():
            logger.info(f"{name:<30} {value} ")