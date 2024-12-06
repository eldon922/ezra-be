# Installation

1. run `sudo apt install pandoc ffmpeg ffprobe`
2. create link for ffmpeg & ffprobe in `ezra-be/venv/bin/` from `usr/bin/`
    ```
    ln -s /usr/bin/ffmpeg /root/ezra-be/venv/bin/ffmpeg
    ln -s /usr/bin/ffprobe /root/ezra-be/venv/bin/ffprobe
    ```

# Deployment Resources

- https://www.digitalocean.com/community/developer-center/deploying-a-next-js-application-on-a-digitalocean-droplet

- https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-22-04

- https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-20-04

- https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu

- https://www.digitalocean.com/community/tutorials/ufw-essentials-common-firewall-rules-and-commands

# Linux Snippets

```shell
# DEPLOY FRONTEND ########################################################################

cd /var/www/ezra-fe
git checkout main
git pull
npm install --legacy-peer-deps
npm run build
pm2 restart ezra-fe
pm2 logs

------------------------------------------------------------------------------------------

pm2 logs

# DEPLOY BACKEND #########################################################################

cd /root/ezra-be
git checkout main
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ezra-be
sleep 5
sudo systemctl status ezra-be

------------------------------------------------------------------------------------------

journalctl -e -u ezra-be
htop

------------------------------------------------------------------------------------------

cd /root/ezra-be
source venv/bin/activate

------------------------------------------------------------------------------------------

curl http://localhost:5000/login

curl -H "Content-type: application/json" -d '{
    "username": "eldon",
    "password": "eldon444"
}' 'http://localhost:5000/login'

# COPY/CUT/REMOVE/RENAME/LINK FILES ######################################################

cp -r /usr/bin/ffmpeg /root/ezra-be/venv/bin/ffmpeg
scp root@104.248.159.174:/root/ezra-be/txt/eldon/2455-10minutes.txt .
mv ezra-be /home/ezra_user/
ln -s /usr/bin/ffprobe /root/ezra-be/venv/bin/ffprobe

# DATABASE ###############################################################################

sudo -u ezra_user psql ezra

# NGINX FRONTEND #########################################################################

sudo nano /etc/nginx/sites-available/transcript.griibandung.org

------------------------------------------------------------------------------------------

server {
  listen 80;
  server_name transcript.griibandung.org www.transcript.griibandung.org;
  location / {
    proxy_pass http://localhost:3000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_cache_bypass $http_upgrade;
  }
}

------------------------------------------------------------------------------------------

sudo nginx -t
sudo systemctl restart nginx

sudo ln -s /etc/nginx/sites-available/transcript.griibandung.org /etc/nginx/sites-enabled/

# NGINX BACKEND ##########################################################################

sudo nano /etc/nginx/sites-available/ezra-be

------------------------------------------------------------------------------------------

server {
    listen 5000;
    server_name localhost;

    allow 127.0.0.1;
    deny all;

    location / {
        include proxy_params;
        proxy_pass http://unix:/root/ezra-be/ezra-be.sock;
    }
}

------------------------------------------------------------------------------------------

sudo nginx -t
sudo systemctl restart nginx

sudo ln -s /etc/nginx/sites-available/ezra-be /etc/nginx/sites-enabled

# GUNICORN BACKEND SERVICE ###############################################################

sudo nano /etc/systemd/system/ezra-be.service

------------------------------------------------------------------------------------------

[Unit]
Description=Gunicorn instance to serve ezra-be
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/root/ezra-be
Environment="PATH=/root/ezra-be/venv/bin"
ExecStart=/root/ezra-be/venv/bin/gunicorn --timeout 0 --threads 9 --workers 9 --bind unix:ezra-be.sock -m 007 wsgi:app

# Memory management
MemoryAccounting=yes
MemoryHigh=6G

CPUQuota=80%

[Install]
WantedBy=multi-user.target

------------------------------------------------------------------------------------------

[Unit]
Description=Gunicorn instance to serve ezra-be
After=network.target

[Service]
User=ezra_be
Group=www-data
WorkingDirectory=/home/ezra_user/ezra-be
Environment="PATH=/home/ezra_user/ezra-be/venv/bin"
ExecStart=/home/ezra_user/ezra-be/venv/bin/gunicorn --workers 3 --bind unix:ezra-be.sock -m 007 wsgi:app

[Install]
WantedBy=multi-user.target

------------------------------------------------------------------------------------------

sudo systemctl daemon-reload
sudo systemctl stop ezra-be
sudo systemctl start ezra-be
sudo systemctl restart ezra-be
sudo systemctl enable ezra-be
sudo systemctl status ezra-be

# SSL #####################################################################################

sudo certbot --nginx -d transcript.griibandung.org -d www.transcript.griibandung.org
```