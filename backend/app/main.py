from fastapi import FastAPI

app = FastAPI(
    title="Referly API", 
    description="Sistem Referal Berbasis Collaborative Filtering",
    version="1.0.0"
)

@app.get("/")
def health_check():
    return {"status": "Referly Backend is up and running!"}