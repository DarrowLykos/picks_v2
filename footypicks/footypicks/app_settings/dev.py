from .base import *


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '!+)p=ft^jr+$kni!c1w*9!xaj)*6)ir)4zh!(=b=8a8j!xf#b-'

ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'footypicks.com', '192.168.1.163', 'sjones187.ddns.net', ]

# Email backend

EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
EMAIL_FILE_PATH = os.path.join(BASE_DIR, 'sent-emails')

