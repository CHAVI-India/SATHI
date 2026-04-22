Installation
============

Complete guide for installing SATHI on Linux servers.

.. contents:: Table of Contents
   :local:
   :depth: 2

Prerequisites
-------------

**System Requirements:**

- Ubuntu 20.04+ or Debian-based Linux
- 4GB RAM minimum (8GB recommended)
- Python 3.13+
- PostgreSQL 14+
- Domain name (for SSL)

**Required Software:**

.. code-block:: bash

    sudo apt update && sudo apt install -y \
        python3.13 python3.13-venv python3.13-dev \
        postgresql postgresql-contrib libpq-dev \
        nginx supervisor memcached git \
        build-essential libssl-dev python3-magic

Development Installation
------------------------

Quick Setup
~~~~~~~~~~~

.. code-block:: bash

    # 1. Clone repository
    git clone https://github.com/your-org/chavi-prom.git
    cd chavi-prom
    
    # 2. Create virtual environment
    python3.13 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    
    # 3. Setup PostgreSQL
    sudo -u postgres psql -c "CREATE DATABASE chaviprom;"
    sudo -u postgres psql -c "CREATE USER chaviprom_user WITH PASSWORD 'password';"
    sudo -u postgres psql -c "GRANT ALL ON DATABASE chaviprom TO chaviprom_user;"
    
    # 4. Configure environment
    cp sampleenv.txt .env
    # Edit .env with your settings
    
    # 5. Run migrations
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py collectstatic --noinput
    
    # 6. Start server
    python manage.py runserver

Production Installation
-----------------------

Step 1: System Setup
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Install all dependencies
    sudo apt update && sudo apt install -y \
        python3.13 python3.13-venv postgresql nginx \
        supervisor memcached certbot python3-certbot-nginx
    
    # Create system user
    sudo useradd -m -s /bin/bash sathi
    sudo usermod -aG www-data sathi

Step 2: Database Setup
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    sudo -u postgres psql << EOF
    CREATE DATABASE chaviprom_prod;
    CREATE USER chaviprom_prod WITH PASSWORD 'strong_password';
    GRANT ALL ON DATABASE chaviprom_prod TO chaviprom_prod;
    EOF

Step 3: Application Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    sudo su - sathi
    git clone https://github.com/your-org/chavi-prom.git
    cd chavi-prom
    python3.13 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Create .env file with production settings
    nano .env

**Production .env:**

.. code-block:: bash

    DJANGO_SECRET_KEY=your-secret-key
    DJANGO_DEBUG=False
    DJANGO_ALLOWED_HOSTS=yourdomain.com
    DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com
    DJANGO_DATABASE_ENGINE=django.db.backends.postgresql_psycopg2
    DJANGO_DATABASE_NAME=chaviprom_prod
    DJANGO_DATABASE_USER=chaviprom_prod
    DJANGO_DATABASE_PASSWORD=strong_password
    DJANGO_SECURED_FIELDS_KEY=your-encryption-key
    DJANGO_ENVIRONMENT=production

Step 4: Gunicorn Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``/home/sathi/chavi-prom/gunicorn_config.py``:

.. code-block:: python

    import multiprocessing
    
    bind = "127.0.0.1:8000"
    workers = multiprocessing.cpu_count() * 2 + 1
    accesslog = "/home/sathi/chavi-prom/logs/gunicorn_access.log"
    errorlog = "/home/sathi/chavi-prom/logs/gunicorn_error.log"
    loglevel = "info"
    timeout = 120

Step 5: Supervisor Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create ``/etc/supervisor/conf.d/sathi.conf``:

.. code-block:: ini

    [program:sathi]
    command=/home/sathi/chavi-prom/venv/bin/gunicorn \
            --config /home/sathi/chavi-prom/gunicorn_config.py \
            chaviprom.wsgi:application
    directory=/home/sathi/chavi-prom
    user=sathi
    autostart=true
    autorestart=true
    stdout_logfile=/home/sathi/chavi-prom/logs/supervisor.log

.. code-block:: bash

    sudo supervisorctl reread
    sudo supervisorctl update
    sudo supervisorctl start sathi

Step 6: Nginx Configuration (HTTP Only - Before SSL)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create initial HTTP-only configuration at ``/etc/nginx/sites-available/sathi``:

.. code-block:: nginx

    upstream sathi_app {
        server 127.0.0.1:8000 fail_timeout=0;
    }
    
    server {
        listen 80;
        listen [::]:80;
        server_name yourdomain.com www.yourdomain.com;
        
        client_max_body_size 100M;
        
        access_log /var/log/nginx/sathi_access.log;
        error_log /var/log/nginx/sathi_error.log;
        
        location /static/ {
            alias /home/sathi/chavi-prom/staticfiles/;
            expires 30d;
            add_header Cache-Control "public, immutable";
        }
        
        location /media/ {
            alias /home/sathi/chavi-prom/media/;
            expires 7d;
            add_header Cache-Control "public";
        }
        
        location / {
            proxy_pass http://sathi_app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_redirect off;
            
            proxy_connect_timeout 120s;
            proxy_send_timeout 120s;
            proxy_read_timeout 120s;
        }
    }

Enable the site and test configuration:

.. code-block:: bash

    sudo ln -s /etc/nginx/sites-available/sathi /etc/nginx/sites-enabled/
    sudo rm /etc/nginx/sites-enabled/default  # Remove default site
    sudo nginx -t
    sudo systemctl restart nginx

**Verify HTTP access:** Visit http://yourdomain.com to ensure the site loads.

Step 7: Obtain SSL Certificate with Let's Encrypt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Prerequisites:**

- Domain name must point to your server's IP address
- Port 80 must be accessible (for Let's Encrypt verification)
- Nginx must be running with HTTP configuration

**Obtain and Install Certificate:**

.. code-block:: bash

    # Run Certbot with Nginx plugin
    sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

**Certbot will:**

1. Verify domain ownership via HTTP challenge
2. Generate SSL certificates
3. **Automatically modify your Nginx configuration** to:
   
   - Add SSL certificate paths
   - Configure SSL protocols and ciphers
   - Set up HTTP to HTTPS redirect
   - Add security headers

4. Reload Nginx with new configuration

**During the process, Certbot will ask:**

- Your email address (for renewal notifications)
- Agreement to Terms of Service
- Whether to redirect HTTP to HTTPS (choose **Yes**)

**Verify SSL Configuration:**

.. code-block:: bash

    # Check certificate was installed
    sudo certbot certificates
    
    # Test Nginx configuration
    sudo nginx -t
    
    # Verify HTTPS works
    curl -I https://yourdomain.com

**Test Automatic Renewal:**

.. code-block:: bash

    # Dry run to test renewal process
    sudo certbot renew --dry-run

**Certificate Auto-Renewal:**

Certbot automatically creates a systemd timer for renewal. Verify it's active:

.. code-block:: bash

    # Check timer status
    sudo systemctl status certbot.timer
    
    # View timer schedule
    sudo systemctl list-timers | grep certbot

Certificates will auto-renew when they have 30 days or less remaining.

**Manual Renewal (if needed):**

.. code-block:: bash

    sudo certbot renew
    sudo systemctl reload nginx

Step 8: Firewall Setup
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    sudo ufw allow OpenSSH
    sudo ufw allow 'Nginx Full'
    sudo ufw enable

Maintenance
-----------

Updating Application
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    sudo su - sathi
    cd chavi-prom
    git pull
    source venv/bin/activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py collectstatic --noinput
    exit
    sudo supervisorctl restart sathi

Viewing Logs
~~~~~~~~~~~~

.. code-block:: bash

    # Application logs
    tail -f /home/sathi/chavi-prom/logs/gunicorn_error.log
    
    # Nginx logs
    tail -f /var/log/nginx/sathi_error.log
    
    # Supervisor status
    sudo supervisorctl status

Troubleshooting
---------------

**Service not starting:**

.. code-block:: bash

    sudo supervisorctl status sathi
    sudo supervisorctl tail sathi stderr

**Database connection errors:**

.. code-block:: bash

    # Test PostgreSQL connection
    psql -U chaviprom_prod -d chaviprom_prod -h localhost

**SSL certificate issues:**

.. code-block:: bash

    sudo certbot certificates
    sudo certbot renew --force-renewal
