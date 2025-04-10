import overdue
from datetime import datetime, timedelta
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
        category = new_category_id  # Ensure category gets updated correctly

    users = authenticate_user(email, password, category)  # Ensure this function returns expected data

    if users and isinstance(users, dict) and 'user_type' in users:
        session_token = serializer.dumps(users.get('user_id', ''))
        user_type = users.get("user_type", "").strip().lower()
        print(f"DEBUG: User type is '{user_type}'")

        response = RedirectResponse(
            url="/bookslist" if user_type == "admin" or user_type == "1"  else "/books/details",
            status_code=303
        )
        response.set_cookie(key="session_token", value=session_token, httponly=True, secure=True)
        return response
    return RedirectResponse(url="/", status_code=303)
    


@app.get("/logout")
def logout(response: Response):
    response = RedirectResponse(url="/")
    response.delete_cookie("session_token")  # Removing session token
    return response


def fetch_books_data_from_db(search=None, order="ASC"):
    connection = get_db_connection()
    if not connection:
        return {"message": "Database connection not done"}
    try:
        cur = connection.cursor(dictionary=True)
        if search:
            query = "SELECT * FROM library.books WHERE bookname LIKE %s OR author LIKE %s"
            cur.execute(query, (f"%{search}%", f"%{search}%"))
        else:
            query = "SELECT * FROM library.books"
            cur.execute(query)
        results = cur.fetchall()
        return results
    except Error as e:
        print(f"Error fetching books: {e}")
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
    if not is_admin_user(request):
        raise HTTPException(status_code=403, detail="Permission denied. Only admins can add new books.")
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
    if not is_admin_user(request):
        raise HTTPException(status_code=403, detail="Permission denied. Only admins can add new books.") 
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
def users_page(request: Request,search:str = None):
    user_id = get_current_user(request)
    if not user_id:
        return RedirectResponse(url="/")
    if not is_admin_user(request):
        raise HTTPException(status_code=403, detail="Permission denied. Only admins can add new books.")   
    books = fetch_books_data_from_db(search)
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



def is_admin_user(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        return False
    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT categories.category FROM library.users "
                       "INNER JOIN library.categories ON library.users.user_type = library.categories.id "
                       "WHERE users.user_id = %s", (user_id,))
        user = cursor.fetchone()
        return user and user['category'].strip().lower() == 'admin'
    finally:
        cursor.close()
        connection.close()

def is_user_user(request: Request):
    user_id = get_current_user(request)
    if not user_id:
        return False    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT categories.category FROM library.users "
                       "INNER JOIN library.categories ON library.users.user_type = library.categories.id "
                       "WHERE users.user_id = %s", (user_id,))
        user = cursor.fetchone()
        return user and user['category'].strip().lower() == 'user'
    finally:
        cursor.close()
        connection.close()


# Frontend route to show movie form with existing data
@app.get("/books/edit/{book_id}", response_class=HTMLResponse)
def edit_book_form(request: Request, book_id: int):
    if not is_admin_user(request):
        raise HTTPException(status_code=403, detail="Permission denied. Only admins can edit book details.")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
      query = f"SELECT * from library.books WHERE book_id={book_id}"
      cursor.execute(query)
      book = cursor.fetchone()
      categoriesData = fetch_user_categories()
      template = templates.get_template("books_form.html")
      return template.render(request=request, book=book ,categories=categoriesData)
    except Error as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        connection.close()


        
# Frontend route to show movie form with existing data
@app.post("/books/update/{book_id}", response_class=HTMLResponse)
async def update_book(
    request: Request,
    book_id: int,
    bookname: str = Form(...),
    author: str = Form(...),
    quantity: int = Form(...),
    price: str = Form(...),
    availability: str = Form(...)
):
    connection = get_db_connection()
    if not connection:
        raise HTTPException(status_code=500, detail="Database connection error")

    cursor = connection.cursor()
    try:
        query = "UPDATE library.books SET bookname = %s, author = %s, quantity = %s, price = %s, availability = %s  WHERE book_id = %s"
        cursor.execute(query, (bookname, author, quantity, price, availability, book_id))
        connection.commit()  # Ensures changes are saved in the database

        print(f"Updated book {book_id}: {bookname}, {author}, Quantity: {quantity}, Price: {price}, Availability: {availability}")

        return RedirectResponse(url="/bookslist", status_code=303)

    except Exception as e:
        print(f"Error updating book: {e}")
        return HTMLResponse(f"Error: {e}", status_code=500)

    finally:
        cursor.close()
        connection.close()


@app.get("/books/details", response_class=HTMLResponse)
def show_book_details(request: Request , search :str=None):
    books = fetch_books_data_from_db(search)  # Assuming this fetches book data
    template = templates.get_template("details_book.html")
    return template.render(request=request, books=books)

@app.post("/books/borrow/{book_id}", response_class=HTMLResponse)
async def borrow_book(request: Request, book_id: int):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=403, detail="User not authenticated.")

    try:
        user_id = serializer.loads(session_token)  # Correctly extract the user ID
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID format.")

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        # Check if the book exists and has enough quantity
        cursor.execute("SELECT quantity FROM library.books WHERE book_id = %s", (book_id,))
        book = cursor.fetchone()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        if book['quantity'] <= 0:
            raise HTTPException(status_code=400, detail="Book is out of stock")

        # Insert borrow record
        borrow_date = datetime.now()
        due_date = datetime.now() + timedelta(days=14)  # 14 days borrowing period
        cursor.execute("INSERT INTO library.borrow (user_id, book_id, borrow_Date,due_date) VALUES (%s, %s, %s,%s)",
                       (user_id, book_id,borrow_date, due_date))

        # Reduce book quantity
        cursor.execute("UPDATE library.books SET quantity = quantity - 1 WHERE book_id = %s", (book_id,))
        # Get total books borrowed by user
        cursor.execute("SELECT COUNT(*) FROM library.borrow WHERE user_id = %s", (user_id,))
        total_borrowed = cursor.fetchone()["COUNT(*)"]

        connection.commit()

        return HTMLResponse(f"<h3>Book borrowed successfully on {borrow_date.strftime('%Y-%m-%d')}! Due date: {due_date.strftime('%Y-%m-%d')}<br>Total books borrowed: {total_borrowed}</h3>")
    
    except Error as e:
        print(f"Error borrowing book: {e}")
        raise HTTPException(status_code=500, detail="Error borrowing book")

    finally:
        cursor.close()
        connection.close()


@app.post("/books/return/{book_id}", response_class=HTMLResponse)
def return_book(request: Request, book_id: int):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=403, detail="User not authenticated.")

    try:
        user_id = serializer.loads(session_token)  # Extract user ID
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID format.")

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Check if the user actually borrowed the book
        cursor.execute("SELECT * FROM library.borrow WHERE book_id = %s AND user_id = %s AND return_date IS NULL",
                       (book_id, user_id))
        borrow_record = cursor.fetchone()
        if not borrow_record:
            raise HTTPException(status_code=400, detail="No active borrow record found.")

        # Step 2: Mark return request as pending (admin must approve it)
        cursor.execute("UPDATE library.borrow SET return_approved = FALSE WHERE book_id = %s AND user_id = %s AND return_date IS NULL",
                       (book_id, user_id))

        connection.commit()
        return HTMLResponse("<h3>Your return request has been submitted. Waiting for admin approval.</h3>")

    finally:
        cursor.close()
        connection.close()


from datetime import datetime

@app.get("/admin/pending-returns", response_class=HTMLResponse)
def view_pending_returns(request: Request):
    if not is_admin_user(request):
        raise HTTPException(status_code=403, detail="Admins only.")
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT b.borrow_id, u.username, bk.bookname, b.borrow_date, b.due_date
            FROM borrow b
            JOIN users u ON b.user_id = u.user_id
            JOIN books bk ON b.book_id = bk.book_id
            WHERE b.return_approved = FALSE AND b.return_date IS NULL
        """)
        returns = cursor.fetchall()

        # Convert borrow_date strings to datetime objects
        for item in returns:
            if isinstance(item['borrow_date'], str):
                item['borrow_date'] = datetime.strptime(item['borrow_date'], "%Y-%m-%d %H:%M:%S.%f")


        template = templates.get_template("admin_pending_returns.html")
        return template.render(request=request, returns=returns)
    finally:
        cursor.close()
        connection.close()



@app.post("/admin/approve-return/{borrow_id}")
def approve_return(borrow_id: int, request: Request):
    if not is_admin_user(request):
        raise HTTPException(status_code=403, detail="Admins only.")
    
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        return_date = datetime.now()

        # Update return_date, approve, increase quantity
        cursor.execute("""
            UPDATE borrow 
            SET return_date = %s, return_approved = TRUE 
            WHERE borrow_id = %s
        """, (return_date, borrow_id))

        cursor.execute("""
            UPDATE books 
            SET quantity = quantity + 1 
            WHERE book_id = (SELECT book_id FROM borrow WHERE borrow_id = %s)
        """, (borrow_id,))

        connection.commit()
        return RedirectResponse(url="/admin/pending-returns", status_code=303)
    finally:
        cursor.close()
        connection.close()

@app.get("/user/borrowed", response_class=HTMLResponse)
def get_borrowed_books(request: Request):
    user_id = request.cookies.get("session_token")
    if not user_id:
        raise HTTPException(status_code=403, detail="User not authenticated.")
    
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT books.bookname, books.author, borrow.borrow_date, borrow.due_date, borrow.return_date 
            FROM borrow 
            INNER JOIN books ON borrow.book_id = books.book_id
            WHERE borrow.user_id = %s
        """, (user_id,))
        borrowed_books = cursor.fetchall()
        template = templates.get_template("borrowed_books.html")
        return template.render(request=request, books=borrowed_books)
    finally:
        cursor.close()
        connection.close()    #explain the code why timedelta is used
    

# Only admins can delete books
@app.post("/books/delete/{book_id}", response_class=HTMLResponse)
async def delete_book(book_id: int, request: Request):
    if not is_admin_user(request):
        raise HTTPException(status_code=403, detail="Permission denied. Only admins can edit book details.")
    
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("DELETE FROM library.books WHERE book_id = %s", (book_id,))
        connection.commit()
        return RedirectResponse(url="/", status_code=303)
    except Error as e:
        print(f"Error deleting book: {e}")
        raise HTTPException(status_code=500, detail="Error deleting the book.")
    finally:
        cursor.close()
        connection.close()
