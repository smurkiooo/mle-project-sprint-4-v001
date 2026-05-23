import sys
import time
import requests

def test_cold_user():
    """тест для пользователя без персональных рекомендаций, то есть должны вернуться дефолтные (топ-популярные)"""
    resp = requests.post("http://127.0.0.1:8000/recommendations",params={"user_id": 999999999, "k": 5})
    assert resp.status_code == 200
    recs = resp.json()["recs"]
    assert len(recs) > 0
    print(f"Тест 1 (нет перс. рек.): {recs}")


def test_warm_user_no_history():
    """тест для пользователя с персональными рекомендациями, но без онлайн-истории. должны вернуться офлайнрекомендации"""
    resp = requests.post("http://127.0.0.1:8000/recommendations",params={"user_id": 4, "k": 5})
    assert resp.status_code == 200
    recs = resp.json()["recs"]
    assert len(recs) > 0
    print(f"Тест 2 : {recs}")


def test_warm_user_with_history():
    """тест для пользователя с персональными рекомендациями и онлайн-историей. Должны вернуться смешанные рекомендации"""
    requests.post("http://127.0.0.1:8000/put_event", params={"user_id": 4, "item_id": 99262})
    resp = requests.post("http://127.0.0.1:8000/recommendations", params={"user_id": 4, "k": 10})
    assert resp.status_code == 200
    recs = resp.json()["recs"]
    assert len(recs) > 0
    print(f"Тест 3 (перс. рек. + история): {recs}")


if __name__ == "__main__":
    test_cold_user()
    test_warm_user_no_history()
    test_warm_user_with_history()
    print("Все тесты  успешно прошлись")
