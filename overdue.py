from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mysql.connector

# Gmail SMTP settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
GMAIL_USER = "nsrivigna3@gmail.com"
GMAIL_APP_PASSWORD = "Sri2003"

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="Srivign@143",
        database="library"
    )

def send_overdue_notifications():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT u.email, u.username, b.book_id, bk.bookname, b.due_date
            FROM borrow b
            INNER JOIN users u ON b.user_id = u.user_id
            INNER JOIN books bk ON b.book_id = bk.book_id
            WHERE b.return_date IS NULL AND b.due_date < %s
        """, (datetime.now(),))

        overdue_users = cursor.fetchall()
        penalty_per_day = 5  # ₹5 per day

        for user in overdue_users:
            due_date = user["due_date"]
            days_overdue = (datetime.now() - due_date).days
            penalty = days_overdue * penalty_per_day
            receiver_email = user["email"]
            subject = "Book Return Reminder"
            text = f"""\
Hi {user["username"]},
This is a reminder that the book "{user["bookname"]}" was due on {due_date.strftime('%Y-%m-%d')}.
As of today, your penalty is ₹{penalty}.
Please return it as soon as possible to avoid further charges.
"""

            html = f"""\
<html>
  <body>
    <p>Hi {user["username"]},<br><br>
       This is a <strong>reminder</strong> that the book <em>"{user["bookname"]}"</em> was due on <strong>{due_date.strftime('%Y-%m-%d')}</strong>.<br>
       <strong>As of today, your penalty is ₹{penalty}.</strong><br>
       Please return it as soon as possible to avoid further charges.<br><br>
       Regards,<br>
       Library Team
    </p>
  </body>
</html>
"""

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = GMAIL_USER
            message["To"] = receiver_email

            message.attach(MIMEText(text, "plain"))
            message.attach(MIMEText(html, "html"))

            try:
                with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                    server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                    server.sendmail(GMAIL_USER, receiver_email, message.as_string())
                print(f"Notification sent to {receiver_email}")
            except Exception as email_error:
                print(f"Failed to send email to {receiver_email}: {email_error}")

    except Exception as db_error:
        print(f"Database error: {db_error}")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    send_overdue_notifications()

def update_penalties_for_overdue_books():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        penalty_per_day = 5
        cursor.execute("""
            SELECT borrow_id, due_date
            FROM borrow
            WHERE return_date IS NULL AND due_date < %s
        """, (datetime.now(),))
        
        overdue_records = cursor.fetchall()

        for record in overdue_records:
            days_overdue = (datetime.now() - record['due_date']).days
            penalty = days_overdue * penalty_per_day
            cursor.execute("""
                UPDATE borrow
                SET penalty = %s
                WHERE borrow_id = %s
            """, (penalty, record['borrow_id']))

        connection.commit()
        print(f"Updated penalties for {len(overdue_records)} overdue books.")

    except Exception as e:
        print(f"Error updating penalties: {e}")
    finally:
        cursor.close()
        connection.close()

# Optional trigger
if __name__ == "__main__":
    update_penalties_for_overdue_books()
