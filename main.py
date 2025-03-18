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
            print("Database connection established")
            return connection
    except Error as e:
        print(f"Database Connection Error: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")

def authenticate_user(email: str, password: str , user_type:str):
    connection = get_db_connection()   
    if not connection:
        print("Database connection failed")
        return None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM library.users WHERE email=%s AND password=%s AND user_type=%s" ,(email, password,user_type))
        user = cursor.fetchone()
        return user
    except Error as e:
        print(f"Error: {e}")
        return None
    finally:
        cursor.close()
        connection.close()


def users_data_from_db(order="ASC"):
    connection = get_db_connection()
    if not connection:
        return {"message": "Database connection not done"}
    try:
        cur = connection.cursor(dictionary=True)
        query = "SELECT users.user_id , users.username , users.email , users.password , categories.category as user_type FROM library.users INNER JOIN library.categories ON library.users.user_type = library.categories.id"
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
        query = f"SELECT * FROM library.categories ORDER BY id {order}"
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
def get_login_form(request:Request):
    categories = fetch_user_categories()
    if isinstance(categories, dict) and "message" in categories:
        categories = [] # Ensures empty categories if fetching fails
    template = templates.get_template("login_form.html")
    return template.render(request=request, categories=categories)




@app.post("/login", response_class=HTMLResponse)
def login_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    category: str = Form(...),
    other_category: str = Form(None)
):
    
    if category == "other" and other_category:
        new_category_id = insert_new_movie_category(other_category)
        category = new_category_id  # Correcting category assignment

    users = authenticate_user(email, password, category)  # Corrected variable usage
    if users:
        session_token = serializer.dumps(users['user_id'])
        response = RedirectResponse(url="/bookslist", status_code=303)
        response.set_cookie( key="session_token", value=session_token, httponly=True,secure=True, samesite="Lax", max_age=3600)
        return response
    return RedirectResponse(url="/", status_code=303)
    


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



#To insert the new category
def insert_new_movie_category(category: str):
  connection = get_db_connection()
  if not connection:
    return {"message": "Database connection not done"}  
  try:
    cursor = connection.cursor()
    query = "INSERT INTO library.categories(category) VALUES(%s)"
    cursor.execute(query, (category,))
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

# Frontend route to show form for creating data
@app.get("/books/new", response_class=HTMLResponse)
def show_books_form(request: Request):
    categories_data = fetch_user_categories()
    template = templates.get_template("books_form.html")
    return template.render(request=request, categories=categories_data)

@app.post("/books" , response_class=HTMLResponse)
def number_of_books(
    request: Request,
    bookname:str =Form(...),
    author:str = Form(...),
    quantity:str = Form(...),
    price:str = Form(...),
    availability:str = Form(...)
):
     # Check if the user is an admin
    if not is_admin_user(request):
        raise HTTPException(status_code=403, detail="Permission denied. Only admins can delete books.")    
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        query = "INSERT INTO library.books(bookname,author,quantity,price,availability) VALUES (%s, %s, %s ,%s ,%s)"
        cursor.execute(query, (bookname,author,quantity,price,availability))
        connection.commit()
        template = templates.get_template("books_success.html")
        return template.render(request=request,bookname=bookname , author=author , quantity=quantity , price=price , availability=availability )
    except Error as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        connection.close()


@app.get("/bookslist", response_class=HTMLResponse)
def users_page(request: Request):
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

# Frontend route to show movie form with existing data

@app.get("/books/edit/{book_id}", response_class=HTMLResponse)
def edit_book_form(request: Request, book_id: int):
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection error")
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM library.books WHERE book_id = %s", (book_id,))
        book = cursor.fetchone()
        categories_data = fetch_user_categories()
        template = templates.get_template("books_form.html")
        return template.render(request=request, book=book, categories=categories_data)
    except Error as e:
        print(f"Error fetching book data: {e}")
        raise HTTPException(status_code=500, detail="Error fetching book data")
    finally:
        cursor.close()
        connection.close()





@app.post("/books/borrow/{book_id}", response_class=HTMLResponse)
async def borrow_book(book_id: int):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT quantity FROM library.books WHERE book_id = %s", (book_id,))
        book = cursor.fetchone()

        if not book:
            raise HTTPException(status_code=404, detail="Book not found")

        if book['quantity'] <= 0:
            raise HTTPException(status_code=400, detail="Book is out of stock")

        cursor.execute("UPDATE library.books SET quantity = quantity - 1 WHERE book_id = %s", (book_id,))
        connection.commit()

        return HTMLResponse(content="<h3>Book borrowed successfully!</h3>")
    except Error as e:
        print(f"Error borrowing book: {e}")
        raise HTTPException(status_code=500, detail="Error borrowing book")
    finally:
        cursor.close()
        connection.close()


        

# Only admins can delete books
@app.post("/books/delete/{book_id}", response_class=HTMLResponse)
async def delete_book(book_id: int, request: Request):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM library.books WHERE book_id = %s", (book_id,))
        connection.commit()
        return RedirectResponse(url="/bookslist", status_code=303)
    except Error as e:
        print(f"Error deleting book: {e}")
        raise HTTPException(status_code=500, detail="Error deleting the book.")
    finally:
        cursor.close()
        connection.close()
