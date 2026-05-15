import requests

url = "https://himalayas.app/jobs/api"
params = {"search": "software", "worldwide": "true", "limit": 1000}
response = requests.get(url, params=params, timeout=15)
print("Status code:", response.status_code)
if response.status_code == 200:
    data = response.json()
    print(f"Jobs found: {len(data.get('jobs', []))}")
else:
    print("Response:", response.text)