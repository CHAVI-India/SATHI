# CHAVI-PROM Production Deployment Guide

Complete guide for deploying the CHAVI-PROM Django application on Ubuntu Server with Nginx, Gunicorn, Supervisor, and PostgreSQL.

---

## Table of Contents

1. [Server Setup](#1-server-setup)
2. [System Dependencies](#2-system-dependencies)
3. [PostgreSQL Database Setup](#3-postgresql-database-setup)
4. [Application Setup](#4-application-setup)
5. [Tailwind CSS Build](#5-tailwind-css-build)
6. [Gunicorn Configuration](#6-gunicorn-configuration)
7. [Supervisor Setup](#7-supervisor-setup)
8. [Nginx Configuration](#8-nginx-configuration)
9. [SSL/TLS Setup](#9-ssltls-setup-lets-encrypt)
10. [Final Steps & Maintenance](#10-final-steps--maintenance)

---

## 1. Server Setup

### 1.1 Initial Server Configuration

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Set timezone
sudo timedatectl set-timezone Asia/Kolkata

# Create application user (recommended for security)
sudo adduser --system --group --home /var/www/chavi-prom chaviprom

# Add your SSH key for the chaviprom user (optional)
sudo mkdir -p /var/www/chavi-prom/.ssh
sudo cp ~/.ssh/authorized_keys /var/www/chavi-prom/.ssh/
sudo chown -R chaviprom:chaviprom /var/www/chavi-prom/.ssh
sudo chmod 700 /var/www/chavi-prom/.ssh
sudo chmod 600 /var/www/chavi-prom/.ssh/authorized_keys
```

### 1.2 Firewall Configuration

```bash
# Install UFW (if not already installed)
sudo apt install ufw -y

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

---

## 2. System Dependencies

### 2.1 Install Required Packages

```bash
# Python and development tools
sudo apt install -y python3 python3-venv python3-dev python3-pip

# PostgreSQL if you wish to install the database in the same VPS
sudo apt install -y postgresql postgresql-contrib libpq-dev

# Nginx
sudo apt install -y nginx

# Supervisor
sudo apt install -y supervisor

# NPM (for Tailwind CSS)
sudo apt install -y npm

# Additional dependencies
sudo apt install -y git build-essential libssl-dev libffi-dev
sudo apt install -y libmagic1  # For python-magic

# Verify installations
python3 --version
node --version
npm --version
psql --version # If Postgres installed in the same machine.
nginx -v
```

---

## 3. PostgreSQL Database Setup
Note that the database can be setup in the same virtual machine or server or in a seperate server. Alternatively a managed database solution can also be used.

### 3.1 Create Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE chaviprom;
CREATE USER chaviprom_user WITH PASSWORD 'your_secure_password_here';
ALTER ROLE chaviprom_user SET client_encoding TO 'utf8';
ALTER ROLE chaviprom_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE chaviprom_user SET timezone TO 'Asia/Kolkata';
GRANT ALL PRIVILEGES ON DATABASE chaviprom TO chaviprom_user;

# Grant schema permissions (PostgreSQL 15+)
\c chaviprom
GRANT ALL ON SCHEMA public TO chaviprom_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO chaviprom_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO chaviprom_user;

# Exit PostgreSQL
\q
```

### 3.2 Configure PostgreSQL for Local Connections

```bash
# Edit pg_hba.conf (adjust path for your PostgreSQL version)
sudo nano /etc/postgresql/17/main/pg_hba.conf

# Add or modify this line for local connections:
# local   all             chaviprom_user                          md5

# Restart PostgreSQL
sudo systemctl restart postgresql
sudo systemctl enable postgresql
```

---

## 4. Application Setup

### 4.1 Clone Repository

```bash
# Switch to application user
sudo su - chaviprom

# Clone the repository
cd /var/www
git clone https://github.com/CHAVI-India/SATHI.git
cd chavi-prom
```

### 4.2 Create Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### 4.3 Install Python Dependencies

```bash
# Install requirements
pip install -r requirements.txt

# Verify installation
pip list
```

### 4.4 Environment Configuration

```bash
# Create .env file from sample
cp sampleenv.txt .env

# Edit .env file with production settings
nano .env
```

**Important `.env` settings for production:**

**Note:**
You can generate a django secret key with the command `python manage.py generate_key`. Alternatively you can go to https://djecre.me/ to generate a secret key.

Remember to replace the values in the .env file with your actual values. Specially look at the language setting and the database password.

The encrypted fields key is different from the django secret key. The django secret key is used for general security purposes while the encrypted fields key is used for encrypting sensitive data in the database. This is a Fernet key and can be generated with the command `python manage.py generate_key`. Save this key in a safe place. You can generate multiple keys and add them to the .env file separated by commas to enable key rotation. Alternatively the key can be generated at https://8gwifi.org/fernet.jsp

Remember that the = sign at the end is not a typo. It is required to separate the key from the value.

```bash
# Security
DJANGO_SECRET_KEY=your_very_long_random_secret_key_here_generate_with_django
DJANGO_DEBUG=False
DJANGO_DEBUG_TOOLBAR_ENABLED=False

# Hosts (replace with your actual domain)
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,your_server_ip
DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Database
DJANGO_DATABASE_ENGINE=django.db.backends.postgresql_psycopg2
DJANGO_DATABASE_NAME=chaviprom
DJANGO_DATABASE_USER=chaviprom_user
DJANGO_DATABASE_PASSWORD=your_secure_password_here
DJANGO_DATABASE_HOST=localhost
DJANGO_DATABASE_PORT=5432

# Generate secured fields key
# Run: python manage.py generate_key
DJANGO_SECURED_FIELDS_KEY=your_generated_key_here

# Language & Time Zone
DJANGO_LANGUAGE_CODE=en-gb
DJANGO_TIME_ZONE=Asia/Kolkata
DJANGO_LANGUAGES=en-gb:English,bn:Bangla,hi:Hindi

# Font configuration
DJANGO_LANGUAGE_FONTS=en-gb:Roboto,bn:Noto+Sans+Bengali,hi:Noto+Sans+Devanagari
DJANGO_DEFAULT_FONT=Roboto

# Parler settings
PARLER_DEFAULT_LANGUAGE=en-gb
PARLER_LANGUAGES=en-gb,bn,hi
PARLER_HIDE_UNTRANSLATED=False

# Email settings (configure with your SMTP provider)
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_EMAIL_HOST=smtp.gmail.com
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_HOST_USER=your_email@gmail.com
DJANGO_EMAIL_HOST_PASSWORD=your_app_password
DJANGO_EMAIL_USE_TLS=True
DJANGO_DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Environment
DJANGO_ENVIRONMENT=production

# Security settings
DJANGO_SECURE_HSTS_SECONDS=31536000

# Email verification
DJANGO_ACCOUNT_EMAIL_VERIFICATION=mandatory

```

### 4.5 Generate Django Secret Key

```bash
# Generate a secure secret key
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Copy the output and add it to your .env file as DJANGO_SECRET_KEY
```

### 4.6 Generate Secured Fields Key

```bash
# Activate virtual environment if not already active
source /var/www/chavi-prom/app/venv/bin/activate

# Generate key
python manage.py generate_key

# Copy the output and add it to your .env file as DJANGO_SECURED_FIELDS_KEY
```

### 4.7 Database Migrations

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Create necessary directories
mkdir -p logs media item_media tmp
```

---

## 5. Tailwind CSS Build

This project uses Tailwind CSS v4 compiled locally for production-ready performance. See [TAILWIND_CSS_SETUP.md](./TAILWIND_CSS_SETUP.md) for detailed information.

### 5.1 Install Node Dependencies

```bash
# Make sure you're in the project directory
cd /var/www/chavi-prom/app

# Install npm packages
npm install

# Verify Tailwind is installed
npm list tailwindcss
```

### 5.2 Build Tailwind CSS

```bash
# Build production CSS
npm run tailwind:build

# Verify output.css was created
ls -lh static/src/output.css
```

**Important**: The `static/src/output.css` file must be built before collecting static files!

### 5.3 Collect Static Files

```bash
# Collect all static files
python manage.py collectstatic --noinput

# Verify static files
ls -lh staticfiles/
```

### 5.4 Set Permissions

```bash
# Exit from chaviprom user if logged in
exit

# Set proper ownership
sudo chown -R chaviprom:chaviprom /var/www/chavi-prom/app

# Set permissions for static and media files
sudo chmod -R 755 /var/www/chavi-prom/app/staticfiles
sudo chmod -R 755 /var/www/chavi-prom/app/media
sudo chmod -R 755 /var/www/chavi-prom/app/item_media
sudo chmod 600 /var/www/chavi-prom/app/.env
```

---

## 6. Gunicorn Configuration

The project includes a pre-configured `gunicorn.conf.py` file optimized for handling large file uploads.

### 6.1 Test Gunicorn

```bash
# Switch to application user
sudo su - chaviprom
cd /var/www/chavi-prom/app
source venv/bin/activate

# Test gunicorn
gunicorn -c gunicorn.conf.py chaviprom.wsgi:application

# If successful, press Ctrl+C to stop
# Exit back to your user
exit
```

---

## 7. Supervisor Setup

Supervisor will manage the Gunicorn process, ensuring it starts on boot and restarts if it crashes.

### 7.1 Create Supervisor Configuration

```bash
sudo nano /etc/supervisor/conf.d/chavi-prom.conf
```

**Add the following configuration:**

```ini
[program:chavi-prom]
command=/var/www/chavi-prom/app/venv/bin/gunicorn -c /var/www/chavi-prom/app/gunicorn.conf.py chaviprom.wsgi:application
directory=/var/www/chavi-prom/app
user=chaviprom
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/www/chavi-prom/app/logs/supervisor-stdout.log
stderr_logfile=/var/www/chavi-prom/app/logs/supervisor-stderr.log
environment=PATH="/var/www/chavi-prom/app/venv/bin"
```

### 7.2 Update Supervisor

```bash
# Reread configuration
sudo supervisorctl reread

# Update supervisor
sudo supervisorctl update

# Start the application
sudo supervisorctl start chavi-prom

# Check status
sudo supervisorctl status chavi-prom

# View logs
sudo tail -f /var/www/chavi-prom/app/logs/supervisor-stdout.log
```

### 7.3 Supervisor Management Commands

```bash
# Start application
sudo supervisorctl start chavi-prom

# Stop application
sudo supervisorctl stop chavi-prom

# Restart application
sudo supervisorctl restart chavi-prom

# View status
sudo supervisorctl status
```

---

## 8. Nginx Configuration

### 8.1 Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/chavi-prom
```

**Add the following configuration:**

```nginx
# Upstream Gunicorn server
upstream chavi_prom_server {
    server unix:/var/www/chavi-prom/app/chavi-prom.sock fail_timeout=0;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Allow Let's Encrypt verification
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Server Configuration
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (will be configured by certbot)
    # ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Client body size (for file uploads)
    client_max_body_size 100M;
    client_body_timeout 300s;

    # Timeouts
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # Logs
    access_log /var/log/nginx/chavi-prom-access.log;
    error_log /var/log/nginx/chavi-prom-error.log;

    # Static files
    location /static/ {
        alias /var/www/chavi-prom/app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /var/www/chavi-prom/app/media/;
        expires 7d;
    }

    # Item media files
    location /item_media/ {
        alias /var/www/chavi-prom/app/item_media/;
        expires 7d;
    }

    # Favicon
    location = /favicon.ico {
        alias /var/www/chavi-prom/app/staticfiles/favicon.ico;
        access_log off;
    }

    # Django application
    location / {
        proxy_pass http://chavi_prom_server;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_http_version 1.1;
    }
}
```

### 8.2 Enable Nginx Site

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/chavi-prom /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# If test passes, reload Nginx
sudo systemctl reload nginx
sudo systemctl enable nginx
```

---

## 9. SSL/TLS Setup (Let's Encrypt)

### 9.1 Install Certbot

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx
```

### 9.2 Obtain SSL Certificate

**Before running certbot:**
1. Ensure your domain DNS points to your server IP
2. Ensure ports 80 and 443 are open in your firewall

```bash
# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Follow the prompts:
# - Enter your email address
# - Agree to terms of service
# - Choose whether to redirect HTTP to HTTPS (recommended: yes)
```

### 9.3 Auto-Renewal Setup

```bash
# Certbot auto-renewal is set up automatically
# Test renewal process
sudo certbot renew --dry-run

# Check renewal timer
sudo systemctl status certbot.timer
```

---

## 10. Final Steps & Maintenance

### 10.1 Set Up Log Rotation

```bash
sudo nano /etc/logrotate.d/chavi-prom
```

Add:
```
/var/www/chavi-prom/app/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 chaviprom chaviprom
    sharedscripts
    postrotate
        supervisorctl restart chavi-prom > /dev/null 2>&1 || true
    endscript
}
```

### 10.2 Application Updates

```bash
# Switch to application user
sudo su - chaviprom
cd /var/www/chavi-prom/app
source venv/bin/activate

# Pull latest code
git pull origin main

# Install/update dependencies
pip install -r requirements.txt --upgrade

# Rebuild Tailwind CSS
npm install
npm run tailwind:build

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Exit and restart services
exit
sudo supervisorctl restart chavi-prom
sudo systemctl reload nginx
```

### 10.3 Viewing Logs

```bash
# Gunicorn logs
sudo tail -f /var/www/chavi-prom/app/logs/gunicorn-error.log

# Supervisor logs
sudo tail -f /var/www/chavi-prom/app/logs/supervisor-stdout.log

# Nginx logs
sudo tail -f /var/log/nginx/chavi-prom-error.log
```

### 10.4 Common Issues

#### Issue: 502 Bad Gateway

```bash
# Check Gunicorn status
sudo supervisorctl status chavi-prom

# Restart Gunicorn
sudo supervisorctl restart chavi-prom

# Check logs
sudo tail -f /var/www/chavi-prom/app/logs/gunicorn-error.log
```

#### Issue: Static files not loading

```bash
# Rebuild Tailwind CSS
cd /var/www/chavi-prom/app
source venv/bin/activate
npm run tailwind:build

# Collect static files
python manage.py collectstatic --noinput

# Check permissions
sudo chmod -R 755 /var/www/chavi-prom/app/staticfiles
```

### 10.5 Deployment Checklist

- [ ] Server updated and secured
- [ ] All dependencies installed
- [ ] PostgreSQL configured
- [ ] `.env` file configured with production settings
- [ ] `DEBUG=False` in production
- [ ] Secret keys generated
- [ ] Database migrations completed
- [ ] Tailwind CSS built successfully
- [ ] Static files collected
- [ ] Gunicorn tested
- [ ] Supervisor configured and running
- [ ] Nginx configured
- [ ] SSL certificate installed
- [ ] Firewall enabled
- [ ] Log rotation configured

---

## Additional Resources

- **Tailwind CSS Setup**: See [TAILWIND_CSS_SETUP.md](./TAILWIND_CSS_SETUP.md) for detailed Tailwind configuration
- **Django Documentation**: https://docs.djangoproject.com/
- **Gunicorn Documentation**: https://docs.gunicorn.org/
- **Nginx Documentation**: https://nginx.org/en/docs/
- **Let's Encrypt**: https://letsencrypt.org/docs/

---

**Last Updated**: January 2025  
**System Version**: CHAVI-PROM Django Application
