from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Create the FastAPI app
app = FastAPI()

# Setting up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # frontend server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# test
@app.get("/api/hello")
def read_root():
    return {"message": "Hello from FastAPI!"}
