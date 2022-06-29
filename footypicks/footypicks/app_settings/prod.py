from .base import *
from dotenv import load_dotenv
load_dotenv()

DEBUG = False

ALLOWED_HOSTS = ['footypicks.com', 'footypicks.pythonanywhere.com', 'localhost', ]

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'footypicksuk@gmail.com'
EMAIL_HOST_PASSWORD = str(os.getenv('GMAIL_KEY'))
EMAIL_USE_TLS = True

SECRET_KEY = str(os.getenv('SECRET_KEY'))
