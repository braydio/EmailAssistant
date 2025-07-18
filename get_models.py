import requests
from display import console

list_models_endpoint = "http://192.168.1.239:5150/v1/internal/model/info"

response = requests.get(list_models_endpoint)
console.print(response.json())
