from flask_mail import Message
from flask import current_app, render_template
from app import mail
from threading import Thread


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_notification_email(subject, recipients, html_body):
    """
    A reusable function to fire off emails in the background.
    """
    msg = Message(subject, 
                  sender=current_app.config.get('MAIL_USERNAME', 'noreply@safewatch.com'), 
                  recipients=recipients)
    
    msg.html = html_body
    
    
    Thread(target=send_async_email, args=(current_app._get_current_object(), msg)).start()
