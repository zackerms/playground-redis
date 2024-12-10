from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import json
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# CORSの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Redisクライアントの設定
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)

class User(BaseModel):
    name: str
    email: str

@app.get("/")
async def read_root():
    return FileResponse('static/index.html')

@app.post("/users/")
async def create_user(user: User):
    redis_client.set(f"user:{user.email}", json.dumps(user.dict()))
    return {"message": "User created successfully"}

@app.get("/users/{email}")
async def get_user(email: str):
    user_data = redis_client.get(f"user:{email}")
    if user_data is None:
        raise HTTPException(status_code=404, detail="User not found")
    return json.loads(user_data)

@app.get("/users")
async def get_all_users():
    users = []
    for key in redis_client.keys("user:*"):
        user_data = redis_client.get(key)
        if user_data:
            users.append(json.loads(user_data))
    return users