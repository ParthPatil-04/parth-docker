from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"msg": "Hey, it works!"}
