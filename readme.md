# Installation

## Only if there is any error related to below dependencies

1. run `sudo apt install pandoc`

# Deployment Resources

- https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-22-04

- https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-20-04

- https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu

- https://www.digitalocean.com/community/tutorials/ufw-essentials-common-firewall-rules-and-commands

# Linux Snippets

```shell
# DEPLOY BACKEND #########################################################################

cd ~/ezra-be
git checkout main
git pull
source ~/ezra-be/venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ezra-be
sleep 5
sudo systemctl status ezra-be

------------------------------------------------------------------------------------------

journalctl -e -u ezra-be
htop

------------------------------------------------------------------------------------------

cd ~/ezra-be
source ~/ezra-be/venv/bin/activate

python3 -m venv venv
python3 app.py

------------------------------------------------------------------------------------------

curl http://149.248.36.65/login

curl -H "Content-type: application/json" -d '{
    "username": "eldon",
    "password": "eldon444"
}' 'http://149.248.36.65/login'

# COPY/CUT/REMOVE/RENAME/LINK FILES ######################################################

cp -r /usr/bin/ffmpeg /root/ezra-be/venv/bin/ffmpeg
scp root@104.248.159.174:/root/ezra-be/txt/eldon/2455-10minutes.txt .
scp -P 47903 C:/Users/AVOWS/Desktop/ASR/audio_files/3648.mp3 user@194.106.118.83:~/whisper/audio_files/3648.mp3
mv ezra-be /home/ezra_user/
ln -s /usr/bin/ffprobe /root/ezra-be/venv/bin/ffprobe

# DATABASE ###############################################################################

sudo -u ezra_user psql ezra

UPDATE system_settings SET setting_value = 'true' WHERE setting_key = 'transcribing_allowed';

psql 'postgres://avnadmin:[PASSWORD]@ezra-ezra.e.aivencloud.com:10744/ezra_be?sslmode=require'

# NGINX BACKEND ##########################################################################

sudo nano /etc/nginx/sites-available/ezra-be

------------------------------------------------------------------------------------------

server {
    listen 80;
    server_name _;

    # allow 127.0.0.1;
    # deny all;

    location / {
        include proxy_params;
        proxy_pass http://unix:/root/ezra-be/ezra-be.sock;
    }
}

------------------------------------------------------------------------------------------

sudo ln -s /etc/nginx/sites-available/ezra-be /etc/nginx/sites-enabled

cd /etc/nginx/sites-enabled
sudo rm default

sudo nginx -t
sudo systemctl restart nginx

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
ExecStart=/root/ezra-be/venv/bin/gunicorn --timeout 0 --threads 3 --workers 3 --bind unix:ezra-be.sock -m 007 wsgi:app

# Memory management
MemoryAccounting=yes
MemoryHigh=400M

CPUQuota=80%

[Install]
WantedBy=multi-user.target

------------------------------------------------------------------------------------------

sudo systemctl daemon-reload

sudo systemctl start ezra-be
sudo systemctl stop ezra-be
sudo systemctl restart ezra-be
sudo systemctl enable ezra-be
sudo systemctl status ezra-be

# SSL #####################################################################################

sudo certbot --nginx -d transcript.griibandung.org -d www.transcript.griibandung.org
```