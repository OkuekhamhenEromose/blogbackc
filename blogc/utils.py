
from django.core.mail import send_mail
from django.conf import settings

def SendMail(email):
    subject = "Welcome to blog website"
    message = f'''
                This is we saying a big welcome to you
                Thanks for registering.
                '''

    send_mail(
    subject,
    message,
    settings.EMAIL_HOST_USER,
    [email],
    fail_silently=False,
)