# Django Resume Builder - Production Deployment Guide

This guide walks you through deploying a Django application to production on AWS EC2 with Nginx, Gunicorn, and SSL certificates.

## Prerequisites

- AWS EC2 instance running Ubuntu
- Domain name configured in Cloudflare
- Django application ready for deployment

## Project Structure

```
/home/ubuntu/django_resume_builder/
└── resume_builder/
    ├── manage.py
    ├── resume_builder/
    │   ├── settings.py
    │   ├── wsgi.py
    │   └── ...
    └── other_apps/
```

## 1. Django Production Configuration

### Update Settings

Edit `/home/ubuntu/django_resume_builder/resume_builder/settings.py`:

```python
# Add your domain to ALLOWED_HOSTS
ALLOWED_HOSTS = ['django.jimmyjohn.com', 'your-ec2-public-ip']

# Set DEBUG to False for production
DEBUG = False

# Configure static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Security settings (recommended)
SECURE_SSL_REDIRECT = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
```

### Collect Static Files

```bash
cd /home/ubuntu/django_resume_builder/resume_builder
python manage.py collectstatic
```

## 2. Install and Configure Gunicorn

```bash
# Install Gunicorn
pip install gunicorn

# Test Gunicorn (optional)
cd /home/ubuntu/django_resume_builder/resume_builder
gunicorn --workers 3 --bind 0.0.0.0:8000 resume_builder.wsgi:application
```

## 3. Install and Configure Nginx

### Install Nginx

```bash
sudo apt update
sudo apt install nginx
```

### Create Nginx Configuration

Create `/etc/nginx/sites-available/django`:

```nginx
server {
    listen 80;
    server_name django.jimmyjohn.com;
    
    location = /favicon.ico { 
        access_log off; 
        log_not_found off; 
    }
    
    location /static/ {
        root /home/ubuntu/django_resume_builder/resume_builder;
    }
    
    location /media/ {
        root /home/ubuntu/django_resume_builder/resume_builder;
    }
    
    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/django_resume_builder/resume_builder/django.sock;
    }
}
```

### Enable the Site

```bash
# Enable your site
sudo ln -s /etc/nginx/sites-available/django /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Start Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## 4. Create Systemd Service for Gunicorn

Create `/etc/systemd/system/django.service`:

```ini
[Unit]
Description=gunicorn daemon for Django Resume Builder
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/django_resume_builder/resume_builder
ExecStart=/home/ubuntu/django_resume_builder/venv/bin/gunicorn --workers 3 --bind unix:/home/ubuntu/django_resume_builder/resume_builder/django.sock resume_builder.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

**Note:** If you're not using a virtual environment, replace `/home/ubuntu/django_resume_builder/venv/bin/gunicorn` with just `gunicorn`.

### Start the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable django
sudo systemctl start django
```

## 5. AWS Security Group Configuration

In your AWS Console, configure your EC2 security group to allow:

- **HTTP (80)** from `0.0.0.0/0`
- **HTTPS (443)** from `0.0.0.0/0`
- **SSH (22)** from your IP address

## 6. Cloudflare DNS Configuration

In your Cloudflare dashboard:

1. Go to DNS settings
2. Add an **A record**:
   - **Name**: `django`
   - **Content**: Your EC2 instance's public IP address
   - **Proxy status**: Orange (proxied) for additional security

## 7. SSL Certificate with Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d django.jimmyjohn.com

# Test automatic renewal
sudo certbot renew --dry-run
```

## 8. Running the Application

### Start Everything

```bash
# Start Gunicorn service
sudo systemctl start django

# Start Nginx
sudo systemctl start nginx

# Check status
sudo systemctl status django
sudo systemctl status nginx
```

### Access Your Application

Visit `https://django.jimmyjohn.com` in your browser!

## 9. Monitoring and Troubleshooting

### Check Service Status

```bash
# Check Gunicorn service
sudo systemctl status django

# Check Nginx status
sudo systemctl status nginx
```

### View Logs

```bash
# Gunicorn logs
sudo journalctl -u django -f

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Nginx access logs
sudo tail -f /var/log/nginx/access.log
```

### Restart Services

```bash
# Restart Gunicorn (after code changes)
sudo systemctl restart django

# Restart Nginx (after config changes)
sudo systemctl restart nginx
```

## 10. Updating Your Application

When you make changes to your Django code:

```bash
# Navigate to your project
cd /home/ubuntu/django_resume_builder/resume_builder

# Pull latest changes (if using git)
git pull origin main

# Collect static files (if static files changed)
python manage.py collectstatic --noinput

# Apply database migrations (if any)
python manage.py migrate

# Restart Gunicorn
sudo systemctl restart django
```

## 11. Common Issues and Solutions

### Permission Issues
```bash
# Fix socket permissions
sudo chmod 755 /home/ubuntu/django_resume_builder/resume_builder/django.sock
sudo chown ubuntu:www-data /home/ubuntu/django_resume_builder/resume_builder/django.sock
```

### Static Files Not Loading
```bash
# Ensure correct permissions for static files
sudo chown -R ubuntu:www-data /home/ubuntu/django_resume_builder/resume_builder/staticfiles/
sudo chmod -R 755 /home/ubuntu/django_resume_builder/resume_builder/staticfiles/
```

### 502 Bad Gateway Error
- Check if Gunicorn service is running: `sudo systemctl status django`
- Check if the socket file exists: `ls -la /home/ubuntu/django_resume_builder/resume_builder/django.sock`
- Check Nginx error logs: `sudo tail -f /var/log/nginx/error.log`

## 12. Security Recommendations

- Keep your server updated: `sudo apt update && sudo apt upgrade`
- Configure a firewall: `sudo ufw enable`
- Regular backups of your database and code
- Monitor your logs regularly
- Keep Django and dependencies updated

## Environment Variables (Optional)

For sensitive information, consider using environment variables:

```python
# In settings.py
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD')
```

Create a `.env` file in your project root and add it to `.gitignore`.

---

## Quick Commands Reference

```bash
# Check all services
sudo systemctl status django nginx

# View all logs
sudo journalctl -u django -f &
sudo tail -f /var/log/nginx/error.log

# Restart everything
sudo systemctl restart django nginx

# Test configuration
sudo nginx -t
python manage.py check --deploy
```

Your Django Resume Builder should now be live at `https://django.jimmyjohn.com`!