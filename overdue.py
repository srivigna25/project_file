from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mysql.connector
import logging

# Gmail SMTP settings
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
GMAIL_USER = "nsrivigna3@gmail.com"
GMAIL_APP_PASSWORD = "Sri2003"  # Consider storing this securely!
PENALTY_PER_DAY = 5

# ---------- LOGGING SETUP ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",
        password="Srivign@143",
        database="library"
    )

# ---------- PENALTY UPDATE FUNCTION ----------
def update_penalties_for_overdue_books():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT borrow_id, due_date
            FROM borrow
            WHERE return_date IS NULL AND due_date < %s
        """, (datetime.now(),))

        overdue_records = cursor.fetchall()
        logging.info(f"Found {len(overdue_records)} overdue borrow records.")

        for record in overdue_records:
            days_overdue = (datetime.now() - record['due_date']).days
            penalty = days_overdue * PENALTY_PER_DAY
            cursor.execute("""
                UPDATE borrow
                SET penalty = %s
                WHERE borrow_id = %s
            """, (penalty, record['borrow_id']))

        connection.commit()
        logging.info("Penalty updates committed to the database.")

    except Exception as e:
        logging.error(f"Error updating penalties: {e}")
    finally:
        cursor.close()
        connection.close()

# ---------- EMAIL NOTIFICATION FUNCTION ----------
def send_overdue_notifications():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT u.email, u.username, bk.bookname, b.due_date
            FROM borrow b
            INNER JOIN users u ON b.user_id = u.user_id
            INNER JOIN books bk ON b.book_id = bk.book_id
            WHERE b.return_date IS NULL AND b.due_date < %s
        """, (datetime.now(),))

        overdue_users = cursor.fetchall()
        logging.info(f"Sending emails to {len(overdue_users)} overdue users.")

        for user in overdue_users:
            due_date = user["due_date"]
            days_overdue = (datetime.now() - due_date).days
            penalty = days_overdue * PENALTY_PER_DAY

            subject = "Library Book Overdue Reminder"
            receiver_email = user["email"]
            plain_text = f"""\
Hi {user["username"]},
This is a reminder that the book "{user["bookname"]}" was due on {due_date.strftime('%Y-%m-%d')}.
Your current penalty is ₹{penalty}.
Please return it as soon as possible to avoid more charges.
"""

            html_content = f"""\
<html>
  <body>
    <p>Hi {user["username"]},<br><br>
       This is a <strong>reminder</strong> that the book <em>"{user["bookname"]}"</em> was due on <strong>{due_date.strftime('%Y-%m-%d')}</strong>.<br>
       Your current penalty is <strong>₹{penalty}</strong>.<br><br>
       Please return it soon to avoid further charges.<br><br>
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
            message.attach(MIMEText(plain_text, "plain"))
            message.attach(MIMEText(html_content, "html"))

            try:
                with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                    server.starttls()
                    server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                    server.sendmail(GMAIL_USER, receiver_email, message.as_string())
                logging.info(f"Email sent to {receiver_email}")
            except Exception as email_error:
                logging.error(f"Failed to send email to {receiver_email}: {email_error}")

    except Exception as db_error:
        logging.error(f"Database error: {db_error}")
    finally:
        cursor.close()
        connection.close()

# ---------- MAIN ----------
if __name__ == "__main__":
    logging.info("Running overdue check and notifications...")
    update_penalties_for_overdue_books()
    send_overdue_notifications()
    logging.info("Done.")