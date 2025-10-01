"""
Gunicorn configuration file for handling large file uploads
"""
import os
import multiprocessing
from pathlib import Path

# Get the project base directory
BASE_DIR = Path(__file__).resolve().parent

# Gunicorn server socket binding
bind = "unix:/var/www/chavi-prom/chavi-prom.sock"

# Gunicorn configuration
workers = 5 # as using 2 cpus  
worker_class = "gthread"
threads = 2 # 
timeout = 1000  
max_requests = 1000  
max_requests_jitter = 50  
keepalive=150
worker_connections = 1000

# Additional timeout settings for long-running requests
graceful_timeout = 3600  # 1 hour graceful shutdown
worker_tmp_dir = '/var/www/chavi-prom/tmp'  # Changed from /dev/shm to /tmp to save memory


# Create logs directory if it doesn't exist
log_dir = os.path.join(BASE_DIR, 'logs')
os.makedirs(log_dir, exist_ok=True)

# Log settings
accesslog = os.path.join(log_dir, "gunicorn-access.log")
errorlog = os.path.join(log_dir, "gunicorn-error.log")
loglevel = "info"

# Django logging integration
disable_redirect_access_to_syslog = True
capture_output = True


# Process naming for easier monitoring
proc_name = "chavi_prom_gunicorn"

# Logging format for gunicorn logs
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Ensure Django logging configuration is used
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'generic': {
            'format': '%(asctime)s [%(process)d] [%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'class': 'logging.Formatter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'generic',
        },
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/www/chavi-prom/logs/gunicorn_error.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'generic',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'error_file'],
    },
    'loggers': {
        'gunicorn.error': {
            'level': 'INFO',
            'handlers': ['error_file'],
            'propagate': False,
        },
        'gunicorn.access': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    }
}