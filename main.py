from typing import Union
from fastapi import FastAPI, Request, Form, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.exceptions import HTTPException
from mako.lookup import TemplateLookup
import mysql.connector
from mysql.connector import Error
from itsdangerous import URLSafeSerializer
import secrets
  
app = FastAPI()

#secret key for session handling
SECRET_KEY = secrets.token_hex(16)
serializer = URLSafeSerializer(SECRET_KEY)

#define Mako html templates path
templates = TemplateLookup(directories=["templates"])

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            port = 3306,
            user ="root",
            password ="Srivign@143",
            database ="library"
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error while connecting to database MySQL: {e}")
        return None

def authenticate_user(email: str, password: str):
    connection = get_db_connection()
    if not connection:
        return None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM library.users WHERE email=%s AND password=%s", (email, password))
        user = cursor.fetchone()
        return user
    except Error as e:
        print(f"Error: {e}")
        return None
    finally:
        cursor.close()
        connection.close()

@app.get("/",response_class=HTMLResponse)
def get_registeration_form(request:Request):
    template = templates.get_template("login_form.html")
    return template.render(request=request)

@app.get("/logout")
def logout(response: Response):
    response = RedirectResponse(url="/")
    response.delete_cookie("session_token")  # Removing session token
    return response


@app.get("/register/form", response_class=HTMLResponse)
def get_users(request: Request):
    template = templates.get_template("registration_form.html")
    return template.render(request=request)


@app.post("/registration",response_class=HTMLResponse)
def new_users(
    request: Request,
    username:str =Form(...),
    email:str = Form(...),
    password:str = Form(...)
):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        query = "INSERT INTO library.users(username, email, password) VALUES (%s, %s, %s)"
        cursor.execute(query, (username, email, password))
        connection.commit()
        template = templates.get_template("success.html")
        return template.render(request=request, username=username, email=email, password=password)
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Error inserting data into the database")
    finally:
        cursor.close()
        connection.close()


@app.post("/login" ,response_class=HTMLResponse)
def registeration_form(
  request:Request,
  username:str = Form(...),
  password:str = Form(...),
  category:str = Form(...),
  other_category = Form(None)
):
  users = authenticate_user(username, password)
  if users:
    session_token = serializer.dumps(users['user_id'])  # Creating a session token
    response = RedirectResponse(url="/login", status_code=303)
    response.set_cookie(key="session_token", value=session_token, httponly=True, secure=True, samesite="Lax", max_age=3600)  # Storing session token in an HTTP-only, secure cookie
    return response
  template = templates.get_template("login_form.html")
  return template.render(request=request, error="Invalid credentials!")


def users_data_from_db(order="ASC"):
    connection = get_db_connection()
    if not connection:
        return {"message": "Database connection not done"}
    try:
        cur = connection.cursor(dictionary=True)
        query = "SELECT * FROM library.users "
        cur.execute(query)
        results = cur.fetchall()
        return results
    except Error as e:
        print(f"Error fetching categories: {e}")
        return []
    finally:
        if connection.is_connected():
            cur.close()
            connection.close()
