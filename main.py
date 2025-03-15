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


@app.get("/register/form", response_class=HTMLResponse)
def get_users(request: Request):
    template = templates.get_template("registration_form.html")
    return template.render(request=request)


@app.post("/registration",response_class=HTMLResponse)
def registeration_form(
    request: Request,
    username:str =Form(...),
    email:str = Form(...),
    password:str = Form(...),
    user_type:str = Form(...)
):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        query = "INSERT INTO library.users(username, email, password , user_type) VALUES (%s, %s, %s , %s)"
        cursor.execute(query, (username, email, password, user_type))
        connection.commit()
        template = templates.get_template("success.html")
        return template.render(request=request, username=username, email=email, password=password , user_type=user_type)
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Error inserting data into the database")
    finally:
        cursor.close()
        connection.close()


@app.get("/usersdata", response_class=HTMLResponse)
def movies_page(request: Request):
    users = users_data_from_db()
    template = templates.get_template("users.html")
    return template.render(request=request, users=users)

@app.get("/",response_class=HTMLResponse)
def get_registeration_form(request:Request):
    categories = fetch_user_categories()
    template = templates.get_template("login_form.html")
    return template.render(request=request, categories=categories)


@app.post("/login" ,response_class=HTMLResponse)
def login_form(
  request:Request,
  email:str = Form(...),
  password:str = Form(...),
  category: str = Form(...),
  other_category: str = Form(None)
):
    if category == "other" and other_category:
        new_category_id = insert_new_movie_category(other_category)
        category = new_category_id

    users = authenticate_user(email, password)
    if users:
        session_token = serializer.dumps(users['user_id'])  # Creating a session token
        response = RedirectResponse(url="/bookslist", status_code=303)
        response.set_cookie(key="session_token", value=session_token, httponly=True, secure=True, samesite="Lax", max_age=3600)  # Storing session token in an HTTP-only, secure cookie
        return response
    template = templates.get_template("login_form.html")
    return template.render(request=request, error="Invalid credentials!")

@app.get("/logout")
def logout(response: Response):
    response = RedirectResponse(url="/")
    response.delete_cookie("session_token")  # Removing session token
    return response



def fetch_books_data_from_db(order="ASC"):
    connection = get_db_connection()
    if not connection:
        return {"message": "Database connection not done"}
    try:
        cur = connection.cursor(dictionary=True)
        query = "SELECT * FROM library.books"
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

#fetching categorires
def fetch_user_categories(order="ASC"):
    connection = get_db_connection()
    if not connection:
        return {"message": "Database connection not done"}

    try:
        cur = connection.cursor(dictionary=True)
        query = f"select * from library.categories ORDER by id {order}"
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


#To insert the new category
def insert_new_movie_category(user_type: str):
  connection = get_db_connection()
  if not connection:
    return {"message": "Database connection not done"}  
  try:
    cursor = connection.cursor()
    query = "INSERT INTO library.categories(user_type) VALUES(%s)"
    cursor.execute(query, (user_type,))
    connection.commit()
    lastid = cursor.lastrowid
    return lastid
  except Error as e:
    print(f"Error insert category data: {e}")
    return []  
  finally:
    if connection.is_connected():
      cursor.close()
      connection.close()            

@app.get("/books/form" , response_class=HTMLResponse)
def books(request: Request):
    template = templates.get_template("books_form.html")
    return template.render(request=request)

@app.post("/books" , response_class=HTMLResponse)
def number_of_books(
    request: Request,
    bookname:str =Form(...),
    author:str = Form(...),
    quantity:str = Form(...),
    price:str = Form(...),
    availability:str = Form(...)
):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        query = "INSERT INTO library.books(bookname,author,quantity,price,availability) VALUES (%s, %s, %s ,%s ,%s)"
        cursor.execute(query, (bookname,author,quantity,price,availability))
        connection.commit()
        template = templates.get_template("books_success.html")
        return template.render(request=request,bookname=bookname , author=author , quantity=quantity , price=price , availability=availability )
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Error inserting data into the database")
    finally:
        cursor.close()
        connection.close()


@app.get("/bookslist", response_class=HTMLResponse)
def movies_page(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/")
    books = fetch_books_data_from_db()
    template = templates.get_template("books.html")
    return template.render(request=request, books=books)

def get_current_user(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    try:
        user_id = serializer.loads(session_token)  # Decoding the session token to get user ID
        return user_id
    except:
        return None

def users_data_from_db(order="ASC"):
    connection = get_db_connection()
    if not connection:
        return {"message": "Database connection not done"}
    try:
        cur = connection.cursor(dictionary=True)
        query = "SELECT users.user_id , users.username , users.email , users.password , categories.user_type as user_type FROM library.users INNER JOIN library.categories ON library.users.user_type = library.categories.id"
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
