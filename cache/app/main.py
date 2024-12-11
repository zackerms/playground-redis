from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mysql.connector
import redis
import json
from typing import List
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# MySQL接続設定
db_config = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': os.getenv('MYSQL_PORT', 3306),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', 'password'),
    'database': os.getenv('MYSQL_DATABASE', 'testdb')
}

# Redis接続設定
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=os.getenv('REDIS_PORT', 6379),
    db=0,
    decode_responses=True
)

# キャッシュの有効期限（秒）
CACHE_EXPIRATION = 60 * 30


class User(BaseModel):
    name: str
    email: str


def init_db():
    # MySQLへの接続とテーブル作成
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE
    )
    """)
    conn.commit()
    cursor.close()
    conn.close()


@app.on_event("startup")
async def startup_event():
    # アプリケーション起動時にDBを初期化
    init_db()

@app.get("/")
async def read_root():
    return FileResponse('static/index.html')


@app.post("/users/")
async def create_user(user: User):
    """
    ユーザー作成
    """
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            (user.name, user.email)
        )
        conn.commit()
        # キャッシュを削除（ユーザー一覧の更新）
        redis_client.delete("all_users")
        return {"message": "User created successfully"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=str(err))
    finally:
        cursor.close()
        conn.close()

@app.put("/users/{email}")
async def update_user_name(email: str, name: str):
    """
    ユーザー名更新
    """
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET name = %s WHERE email = %s",
            (name, email)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
            
        # 関連するキャッシュを削除
        redis_client.delete(f"user:{email}")
        redis_client.delete("all_users")
        return {"message": "User updated successfully"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=str(err))
    finally:
        cursor.close()
        conn.close()


@app.get("/users/{email}")
async def get_user(email: str):
    """
    メールアドレスでユーザーを検索
    """
    # Redisからキャッシュを確認
    cache_key = f"user:{email}"
    cached_user = redis_client.get(cache_key)

    if cached_user:
        return json.loads(cached_user)

    # DBから検索
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT name, email FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        # キャッシュに保存
        redis_client.setex(
            cache_key,
            CACHE_EXPIRATION,
            json.dumps(user)
        )
        return user
    finally:
        cursor.close()
        conn.close()


@app.get("/users")
async def get_all_users() -> List[dict]:
    """
    全ユーザーを取得
    """
    # Redisからキャッシュを確認
    cached_users = redis_client.get("all_users")
    if cached_users:
        return json.loads(cached_users)

    # DBから全ユーザーを取得
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT name, email FROM users")
        users = cursor.fetchall()

        # キャッシュに保存
        redis_client.setex(
            "all_users",
            CACHE_EXPIRATION,
            json.dumps(users)
        )
        return users
    finally:
        cursor.close()
        conn.close()

@app.post("/db/users/")
async def create_user_to_db(user: User):
    """
    ユーザー作成（DBにのみ）
    """
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email) VALUES (%s, %s)",
            (user.name, user.email)
        )
        conn.commit()
        return {"message": "User created successfully"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=str(err))
    finally:
        cursor.close()
        conn.close()

@app.put("/db/users/{email}")
async def update_user_name_to_db(email: str, name: str):
    """
    ユーザー名更新（DBにのみ）
    """
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET name = %s WHERE email = %s",
            (name, email)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "User updated successfully"}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=400, detail=str(err))
    finally:
        cursor.close()
        conn.close()

@app.get("/db/users/{email}")
async def get_user_from_db(email: str):
    """
    メールアドレスでユーザーを検索（DBからのみ）
    """
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT name, email FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    finally:
        cursor.close()
        conn.close()

@app.get("/db/users")
async def get_all_users_from_db() -> List[dict]:
    """
    全ユーザーを取得（DBからのみ）
    """
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT name, email FROM users")
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()