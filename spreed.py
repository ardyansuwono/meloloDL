import requests
import pandas as pd

url = "https://api.short.io/api/links?domain_id=1131756&limit=150"

headers = {
    "accept": "application/json",
    "authorization": "JWT eyJhbGciOiJFUzUxMiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiItcTZubndXUm1lWC16Xy1wdmVLS2wiLCJpZCI6Ii1xNm5ud1dSbWVYLXpfLXB2ZUtLbCIsInVzZXJfaWQiOjEzNjM3NDcsImxuZyI6bnVsbCwic3ViIjoxMzYzNzQ3LCJsb2dpbkhpc3RvcnlJZCI6ImFkOTAwY2Y5LTAyZTEtNDFmNS05ZmRjLTM4YjExYzUxMjVhZSIsImltcGVyc29uYXRlIjpmYWxzZSwiaWF0IjoxNzczMTUzODcwLCJleHAiOjE3NzU3NDU4NzAsImF1ZCI6ImF1dGgifQ.AZh7R9Wp2B_9l7W5tHf58wxFtDVNkMTUE40cQ2vrrGtxX1SQvrhWYA2UlFeM4dqsh3QN-ehppR8GAlTrgYgdXITRAX1o5HC7teIPjnM1sfuBR-VPea8ZFbsKb0gMAoZoVCxZVzVEKDB5fHtvr_6czbj9qhlB2Lp-WHVbCAXxaVmUXQXx"
}

response = requests.get(url, headers=headers)
data = response.json()

# biasanya list link ada di field 'links'
links = data.get("links", data)

df = pd.json_normalize(links)

df.to_csv("shortio_links.csv", index=False)

print("CSV berhasil dibuat: shortio_links.csv")