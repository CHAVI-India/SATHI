import multiprocessing
import os

# ============================================================================
# GUNICORN CONFIGURATION FOR DJANGO APPLICATION WITH DATABASE OPTIMIZATION
# ============================================================================
# This configuration is optimized for Django applications that perform
# multiple database queries per request. Adjust settings based on your
# server resources and application requirements.
#
# USAGE:
# To run your Django application with this configuration, use:
#   gunicorn -c gunicorn.conf.py chaviprom.wsgi:application
#
# Alternative commands:
#   gunicorn -c gunicorn.conf.py chaviprom.wsgi  (if application is the default)
#   gunicorn --config gunicorn.conf.py chaviprom.wsgi:application  (long form)
#
# The application module format is: <project_name>.wsgi:application
# Where 'chaviprom' is your Django project name.

# ============================================================================
# SERVER SOCKET CONFIGURATION
# ============================================================================
# bind: Interface and port to bind to
# - Use "0.0.0.0:8000" to accept connections from any IP
# - Use "127.0.0.1:8000" to only accept local connections
# - For production behind a reverse proxy, consider "unix:/tmp/gunicorn.sock"
bind = "0.0.0.0:8000"

# backlog: Maximum number of pending connections
# - Higher values for high-traffic applications
# - Default is usually sufficient for most applications
backlog = 2048

# ============================================================================
# WORKER PROCESS CONFIGURATION
# ============================================================================
# WORKER COUNT OPTIMIZATION:
# Formula: (2 x CPU cores) + 1
# - For CPU-bound apps: Use CPU core count
# - For I/O-bound apps (like database-heavy Django): Use (2 x CPU cores) + 1
# - For mixed workloads: Start with (2 x CPU cores) + 1 and monitor
# - Maximum recommended: 2 x CPU cores + 1
# 
# MONITORING GUIDELINES:
# - Monitor CPU usage: Should be 80-90% under load
# - Monitor memory usage: Each worker uses ~50-200MB
# - Monitor database connections: Ensure you don't exceed DB connection limits
# - If CPU usage is low but response times are high, increase workers
# - If memory usage is too high, decrease workers or increase server RAM
workers = multiprocessing.cpu_count() * 2 + 1

# WORKER CLASS SELECTION:
# - "sync": Best for CPU-bound and database-heavy applications (DEFAULT)
# - "gevent": For I/O-bound applications with many concurrent connections
# - "eventlet": Alternative async worker, similar to gevent
# - "gthread": Threaded workers, can be memory efficient but with GIL limitations
worker_class = "sync"

# worker_connections: Only relevant for async workers (gevent/eventlet)
# - For sync workers, this setting is ignored
# - For async workers, increase based on concurrent connection needs
worker_connections = 1000

# WORKER RECYCLING:
# max_requests: Number of requests a worker handles before restarting
# - Prevents memory leaks and connection pool issues
# - Lower values (500-1000) for applications with potential memory leaks
# - Higher values (2000-5000) for stable applications
# - Set to 0 to disable worker recycling
max_requests = 1000

# max_requests_jitter: Random jitter to prevent all workers restarting simultaneously
# - Should be 10-50% of max_requests
# - Helps distribute worker restarts over time
max_requests_jitter = 50

# ============================================================================
# TIMEOUT CONFIGURATION (CRITICAL FOR DATABASE APPLICATIONS)
# ============================================================================
# timeout: Worker timeout for handling requests
# - Default: 30 seconds (too low for database-heavy applications)
# - Database applications: 60-120 seconds
# - Long-running queries: 120-300 seconds
# - If you get "Worker timeout" errors, increase this value
# - Monitor slow queries and optimize them instead of just increasing timeout
timeout = 120

# keepalive: Seconds to wait for requests on a Keep-Alive connection
# - Helps reduce connection overhead
# - Too high values can tie up workers unnecessarily
# - 2-5 seconds is usually optimal
keepalive = 2

# graceful_timeout: Timeout for graceful worker restarts
# - Time given to finish current requests during restart
# - Should be less than timeout but sufficient for current requests
# - 30 seconds allows most requests to complete gracefully
graceful_timeout = 30

# ============================================================================
# MEMORY MANAGEMENT
# ============================================================================
# preload_app: Load application before forking workers
# - Pros: Reduces memory usage through copy-on-write, faster startup
# - Cons: Code changes require full restart, not just worker restart
# - Recommended: True for production, False for development
preload_app = True

# max_worker_memory: Maximum memory per worker in KB
# - Workers exceeding this limit will be gracefully restarted
# - Helps prevent memory leaks from accumulating
# - Monitor actual memory usage and adjust accordingly
# - Typical Django worker: 100-300MB (100000-300000 KB)
max_worker_memory = 200000  # 200MB per worker

# ============================================================================
# SECURITY SETTINGS
# ============================================================================
# Request size limits to prevent DoS attacks
# - limit_request_line: Maximum size of HTTP request line (0 = unlimited)
# - limit_request_fields: Maximum number of header fields
# - limit_request_field_size: Maximum size of header field (0 = unlimited)
limit_request_line = 0
limit_request_fields = 32768
limit_request_field_size = 0

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
# accesslog: Access log file path
# - "-" logs to stdout (good for containerized deployments)
# - "/path/to/access.log" for file logging
# - None to disable access logging
accesslog = "-"

# errorlog: Error log file path
# - "-" logs to stderr (good for containerized deployments)
# - "/path/to/error.log" for file logging
errorlog = "-"

# loglevel: Logging level
# - "debug": Very verbose, includes all requests and responses
# - "info": Standard logging level for production
# - "warning": Only warnings and errors
# - "error": Only errors
loglevel = "info"

# access_log_format: Custom format for access logs
# - %(h)s: Remote address
# - %(t)s: Time of request
# - %(r)s: Request line
# - %(s)s: Status code
# - %(b)s: Response length
# - %(D)s: Request time in microseconds (useful for performance monitoring)
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ============================================================================
# PROCESS MANAGEMENT
# ============================================================================
# proc_name: Process name for easier identification in process lists
proc_name = "chaviprom_django"

# daemon: Run as daemon (background process)
# - False: Run in foreground (recommended for containerized deployments)
# - True: Run as daemon (traditional server deployments)
daemon = False

# pidfile: File to store process ID
# - Useful for process management and monitoring
pidfile = "/tmp/gunicorn.pid"

# user/group: Run workers as specific user/group
# - None: Run as current user
# - "www-data": Common web server user
# - Ensure the user has necessary permissions for your application
user = None
group = None

# tmp_upload_dir: Directory for temporary files during uploads
# - None: Use system default
# - "/tmp": Explicit temporary directory
tmp_upload_dir = None

# ============================================================================
# SSL/TLS CONFIGURATION (OPTIONAL)
# ============================================================================
# Uncomment and configure if serving HTTPS directly (not recommended behind reverse proxy)
# keyfile = "/path/to/private.key"
# certfile = "/path/to/certificate.crt"
# ca_certs = "/path/to/ca_bundle.crt"  # For client certificate verification
# cert_reqs = 0  # SSL client certificate requirements (0=none, 1=optional, 2=required)

# ============================================================================
# ENVIRONMENT VARIABLES
# ============================================================================
# Environment variables to pass to worker processes
# - Essential for Django settings module
# - Add any other environment variables your application needs
raw_env = [
    'DJANGO_SETTINGS_MODULE=chaviprom.settings',
    # Add more environment variables as needed:
    # 'DATABASE_URL=postgresql://user:pass@localhost/db',
    # 'REDIS_URL=redis://localhost:6379/0',
]

# ============================================================================
# WORKER LIFECYCLE HOOKS - DATABASE OPTIMIZATION
# ============================================================================
# These hooks are critical for Django applications with database connections.
# They ensure proper database connection handling across worker processes.

def when_ready(server):
    """
    Called when the server is ready to accept connections.
    - Good place for one-time setup tasks
    - Runs in the master process
    - Use for initializing shared resources
    """
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    """
    Called when a worker receives SIGINT or SIGQUIT signal.
    - Opportunity for graceful cleanup
    - Worker is about to terminate
    """
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    """
    Called just before a worker is forked.
    - Runs in the master process
    - Use for setup that should happen before forking
    """
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """
    Called just after a worker has been forked.
    - Runs in the master process after fork
    - Limited utility compared to post_worker_init
    """
    server.log.info("Worker spawned (pid: %s)", worker.pid)
    
def pre_exec(server):
    """
    Called just before a new master process is forked.
    - Useful for cleaning up master process resources
    """
    server.log.info("Forked child, re-executing")

def worker_abort(worker):
    """
    Called when a worker receives SIGABRT signal.
    - Worker crashed or was forcefully terminated
    - Opportunity to log crash information
    """
    worker.log.info("worker received SIGABRT signal")

# ============================================================================
# DATABASE CONNECTION OPTIMIZATION HOOKS
# ============================================================================
# CRITICAL: These hooks prevent database connection sharing between processes,
# which can cause "connection already closed" errors and connection pool exhaustion.

def post_worker_init(worker):
    """
    Called just after a worker has been forked and initialized.
    
    IMPORTANT FOR DATABASE APPLICATIONS:
    - Closes all database connections inherited from the master process
    - Each worker gets its own fresh connection pool
    - Prevents "connection already closed" errors
    - Essential for applications using connection pooling
    
    PERFORMANCE IMPACT:
    - Slight delay during worker startup
    - Prevents connection-related crashes and timeouts
    - Enables proper connection pooling per worker
    """
    from django.db import connections
    connections.close_all()
    worker.log.info("Closed database connections in worker %s", worker.pid)

def worker_exit(server, worker):
    """
    Called just after a worker has been exited.
    
    DATABASE CLEANUP:
    - Ensures all database connections are properly closed
    - Prevents connection leaks when workers are recycled
    - Important for databases with connection limits
    
    MONITORING:
    - Log worker exits for debugging
    - Track worker lifecycle for performance optimization
    """
    from django.db import connections
    connections.close_all()
    server.log.info("Worker %s exited, closed database connections", worker.pid)

# ============================================================================
# RESOURCE OPTIMIZATION GUIDELINES
# ============================================================================
#
# MONITORING YOUR APPLICATION:
# 1. Database Connections:
#    - Monitor active connections: SELECT count(*) FROM pg_stat_activity; (PostgreSQL)
#    - Ensure connections don't exceed your database's max_connections
#    - Each worker may use 1-10 connections depending on your connection pooling
#
# 2. Memory Usage:
#    - Monitor with: ps aux | grep gunicorn
#    - Each worker should use 50-300MB typically
#    - If memory usage grows continuously, investigate memory leaks
#
# 3. CPU Usage:
#    - Target 80-90% CPU utilization under load
#    - If CPU is low but response times are high, increase workers
#    - If CPU is maxed out, optimize your code or scale horizontally
#
# 4. Response Times:
#    - Monitor the %(D)s field in access logs (microseconds)
#    - Database queries should be optimized if response times are consistently high
#
# SCALING RECOMMENDATIONS:
# - Start with current settings and monitor
# - Increase workers if you have available CPU and memory
# - Consider async workers (gevent) if you have many concurrent idle connections
# - Use a reverse proxy (nginx) for static files and SSL termination
# - Consider connection pooling solutions like pgbouncer for PostgreSQL 