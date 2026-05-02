"""
Gunicorn Production Configuration for ARS Backend
Optimized for AWS EC2 t3.micro (1 vCPU, 1GB RAM)
"""

import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
# For t3.micro: 2-4 workers (CPU cores + 1)
workers = multiprocessing.cpu_count() + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 5

# Process naming
proc_name = "ars-backend"

# Logging
accesslog = "/var/log/ars-backend/access.log"
errorlog = "/var/log/ars-backend/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Server mechanics
daemon = False
pidfile = "/run/gunicorn-ars-backend.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if needed, disable for Nginx to handle)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print("🚀 ARS Backend starting with Gunicorn...")

def when_ready(server):
    """Called just after the server is started."""
    print(f"✅ ARS Backend ready. Workers: {workers}")

def on_exit(server):
    """Called just before the server stops."""
    print("⛔ ARS Backend shutting down...")

# Application
application = None
wsgi_app = None

# Server mechanics - limits
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# SSL context - for direct HTTPS (optional)
# ssl_version = ssl.PROTOCOL_TLSv1_2
# cert_reqs = ssl.CERT_NONE
# ca_certs = None
# suppress_ragged_eof = True
# do_handshake_on_connect = True
# ciphers = 'HIGH:!aNULL:!MD5'
