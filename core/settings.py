import os
import socket  # ADD THIS IMPORT
from pathlib import Path
from urllib.parse import urlparse  # ADD THIS IMPORT

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-lv8fl)y_or9qgb___%xb#o&k7b#@!1+0)7i-6z(ys-^g$yu_fg"

# =============================================
# ENVIRONMENT-BASED CONFIGURATION
# =============================================

# Check if we're in production mode (set DJANGO_ENV=production)
DJANGO_ENV = os.environ.get('DJANGO_ENV', 'development')

if DJANGO_ENV == 'production':
    DEBUG = False
    # In production, use your domain - MUST BE SET via environment variable
    SITE_URL = os.environ.get('SITE_URL', '')
    if not SITE_URL:
        raise ValueError("SITE_URL environment variable must be set in production mode")
    
    ALLOWED_HOSTS = [
        'localhost',
        '127.0.0.1',
        'signalry.com',
        'www.signalry.com',
    ]
    # Also allow any subdomain of the SITE_URL
    parsed = urlparse(SITE_URL)
    if parsed.netloc:
        ALLOWED_HOSTS.append(parsed.netloc)
        # Add without www if applicable
        if parsed.netloc.startswith('www.'):
            ALLOWED_HOSTS.append(parsed.netloc[4:])
        # Add the hostname without port
        hostname = parsed.hostname
        if hostname:
            ALLOWED_HOSTS.append(hostname)
    
    EMAIL_FROM_NAME = 'Signalry'
else:
    # Development/Testing mode
    DEBUG = True
    
    # Check if SITE_URL is provided via environment variable
    SITE_URL = os.environ.get('SITE_URL', '')
    
    if not SITE_URL:
        # Get current IP dynamically for testing
        try:
            # Try to get the actual server IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            SERVER_IP = s.getsockname()[0]
            s.close()
        except:
            SERVER_IP = '127.0.0.1'
        
        # Use dynamic SITE_URL based on current IP
        SITE_URL = f'http://{SERVER_IP}:8000'
        ALLOWED_HOSTS = [
            SERVER_IP,
            'localhost',
            '127.0.0.1',
            f'{SERVER_IP}:8000',  # Add with port for runserver
        ]
    else:
        # Use the provided SITE_URL
        parsed = urlparse(SITE_URL)
        ALLOWED_HOSTS = [
            'localhost',
            '127.0.0.1',
        ]
        if parsed.netloc:
            ALLOWED_HOSTS.append(parsed.netloc)
            # Add the hostname without port
            hostname = parsed.hostname
            if hostname:
                ALLOWED_HOSTS.append(hostname)
    
    EMAIL_FROM_NAME = 'Signalry (Development)'

# Validate SITE_URL is set
if not SITE_URL:
    raise ValueError("SITE_URL must be configured either via environment variable or automatic detection")

# Add the server IP to ALLOWED_HOSTS for development
if DJANGO_ENV != 'production':
    try:
        # Try to get server IP if not already in ALLOWED_HOSTS
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        server_ip = s.getsockname()[0]
        s.close()
        
        # Add IP if not already in ALLOWED_HOSTS
        if server_ip not in ALLOWED_HOSTS and f'{server_ip}:8000' not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.extend([server_ip, f'{server_ip}:8000'])
    except:
        pass

# For ALL platforms, also allow all hosts in development for flexibility
if DEBUG:
    ALLOWED_HOSTS.extend(['*', '0.0.0.0', '192.168.190.171', '192.168.190.171:8000'])

AUTH_USER_MODEL = "users.User"

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "core",
    "users",
    "plans",
    "smtp",
    "campaigns",
    "message_system",
    "tracking",
    "queues",
    "analytics",
    "monitoring",
    "deliverability",
    "django_extensions",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Custom context processor
                "core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =============================================
# ADDED SETTINGS FOR EMAIL FUNCTIONALITY
# =============================================

SITE_NAME = 'Signalry'

# Email Configuration
# For DEVELOPMENT/TESTING - shows emails in console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# For PRODUCTION - use real SMTP (uncomment and configure)
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'  # or your SMTP server
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'your-app-password'
# DEFAULT_FROM_EMAIL = 'your-email@gmail.com'

# Django's default email settings (used as fallback)
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'campaigns.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'campaigns': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'message_system': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

# Create logs directory if it doesn't exist
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)