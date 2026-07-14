import requests, json
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0IiwiZXhwIjoxNzg0MDk4MzE1LCJpYXQiOjE3ODQwMTE5MTV9.sV1usIhHBKBXa_kgQEto2HwM84bHfz4b0Mq1Lz1u0Sw"
h = {"Authorization": f"Bearer {token}"}

body = {
    "trip_id": 0,
    "origin_city": "北京",
    "destination_city": "南京",
    "start_date": "2026-07-20",
    "end_date": "2026-07-23",
    "people_count": "2",
    "budget_total": "5000",
    "interests": "历史文化、美食、自然风光",
    "hotel_level": "四星级",
    "transport_preference": "高铁",
    "pace": "轻松"
}
r = requests.post("http://localhost:8000/api/trip-plans/generate", json=body, headers=h, timeout=120)
print(f"status: {r.status_code}")
data = r.json()
print(f"plan_id={data['id']} trip_id={data['trip_id']}")
print(f"origin={data['origin_city']} dest={data['destination_city']}")
print(f"interests={data['interests']}")
lv = data.get("latest_version", {})
pj = lv.get("plan_json", {})
if isinstance(pj, dict):
    print(f"title: {pj.get('title', '')}")
