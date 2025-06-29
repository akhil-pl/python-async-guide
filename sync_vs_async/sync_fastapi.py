from fastapi import FastAPI
import requests

app = FastAPI()

@app.get("/data")
def get_data():
    response = requests.get("https://httpbin.org/delay/1")
    return {"message": response.json()}
