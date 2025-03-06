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


@app.get("/",response_class=HTMLResponse)
def get_registeration_form(request:Request):
    template = templates.get_template("login_form.html")
    return template.render(request=request)

@app.get("/register/form", response_class=HTMLResponse)
def get_users(request: Request):
    template = templates.get_template("registeration_form.html")
    return template.render(request=request)

@app.post("/registeration",response_class=HTMLResponse)
def new_users(
    request: Request,
    username:str =Form(...),
    email:str = Form(...),
    password:str = Form(...),
    category:str = Form(...),
    other_category = Form(None)
):
    connection = get_db_connection()
    cursor = connection.cursor()
    try: 
        # if category =='other':
        #     category = insert_new_users_category(other_category)
        query = "INSERT INTO users(username,email,password,category) VALUES(%s , %s , %s , %s)" 
        cursor.execute(query,(username,email,password,category))
        connection.commit()
        template = templates.get_template("success.html")
        return template.render(request=request , username=username , email=email ,password=password , category=category )
    except Error as e:
        print(f"Error:{e}")
    finally:
        cursor.close()
        connection.close()

def users_data_from_db(order="ASC"):
    connection = get_db_connection()
    if not connection:
        return {"message": "Database connection not done"}
    try:
        cur = connection.cursor(dictionary=True)
        query = "SELECT * FROM library.users"
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