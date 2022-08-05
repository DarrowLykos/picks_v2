#from .base_settings import *
from dotenv import load_dotenv
import os
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Turn off debug
DEBUG = False

ALLOWED_HOSTS = ['footypicks.com', 'footypicks.pythonanywhere.com', 'localhost', ]

# GMAIL SMTP connection for outbound emails
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'footypicksuk@gmail.com'
EMAIL_HOST_PASSWORD = 'jodqwlpgmgniaxdl'
EMAIL_USE_TLS = True

# Get Secret Key from .env file
SECRET_KEY = str(os.getenv('SECRET_KEY'))

# Database on Python Anywhere
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'footypicks$default',
        'USER': 'footypicks',
        'PASSWORD': 'rigwaitlawny',
        'HOST': 'footypicks.mysql.pythonanywhere-services.com',
    }
}