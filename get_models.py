import requests

list_models_endpoint = "http://192.168.1.239:5150/v1/internal/model/info"

response = requests.get(list_models_endpoint)
print(response.json())
