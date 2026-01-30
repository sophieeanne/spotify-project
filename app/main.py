from fastapi import FastAPI

app = FastAPI(title="Music Recommendation API")

@app.get("/")
def root():
    return {"status": "API is running 🚀"}
