# Ezra Backend Service

This repository contains the backend API for **Ezra**, a web service that accepts YouTube or Google Drive audio links, transcribes the content, and returns text/word documents to authenticated users. The service includes an administrative interface for managing users, prompts, and system settings. 

---

## 🚀 Features

- **User authentication** with JWT tokens
- Audio retrieval from Google Drive or YouTube (via `gdown`/`yt-dlp`)
- Optional trimming of audio using FFmpeg
- Asynchronous processing with `flask_executor`
- Transcription & proofreading logic (via external services)
- File download endpoints (TXT, MD, Word)
- Admin routes for managing users, prompts, transcriptions, and settings
- PostgreSQL database managed with SQLAlchemy
- Lightweight Flask app easily containerized or deployed with Gunicorn & Nginx

---

## 🛠️ Tech Stack

- Python 3.11+ (tested)
- Flask
- Flask-JWT-Extended
- Flask-SQLAlchemy
- Flask-Executor
- PostgreSQL
- `yt-dlp`, `ffmpeg`, `pandoc`

---

## 📁 Repository Structure

```
admin_routes.py
app.py                 # Main Flask application
database.py            # SQLAlchemy initialization
models.py              # ORM models
pandoc_service.py      # Converts documents via Pandoc
proofreading_service.py
transcription_service.py
password.py            # helper functions for password generation
wsgi.py                # Gunicorn entrypoint
migrations/            # SQL migration scripts
readme.md              # You are here
requirements.txt
Dockerfile
```

---

## ⚙️ Configuration

### Environment Variables

| Variable                   | Description                                                    | Example                                      |
|----------------------------|----------------------------------------------------------------|----------------------------------------------|
| `DATABASE_URL`             | SQLAlchemy database URI                                        | `postgresql://user:pass@host/db`            |
| `JWT_SECRET_KEY`           | Secret key for signing JWT tokens                              | `a-very-secret-value`                        |
| `DEEPSEEK_BASE_URL`        | Base URL for Deepseek API                                      | `https://api.deepseek.com`                 |
| `DEEPSEEK_API_KEY`         | API key for Deepseek service                                   | `sk-xxxxxxxxxxxx`                           |
| `TRANSCRIBE_API_KEY`       | API key used by transcription microservice                     | `Jsh2Y-KlsHSKhAg7K...`                    |
| `TRANSCRIBE_API_URL`       | Endpoint for transcription service                             | `https://eldon922--ezra-inference-process.modal.run` |
| `GET_RESULT_TRANSCRIBE_API_URL` | Endpoint to fetch transcription results                     | `https://eldon922--ezra-inference-get-transcription-result.modal.run` |

Load them via a `.env` file or your deployment environment. You can use the included `.env` template if available.

---

## 📝 Installation (local development)

1. **Clone the repository**
   ```bash
   git clone <repo-url> ezra-be
   cd ezra-be
   ```

2. **Create & activate a Python virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables** (via `.env` or export):
   ```bash
   export DATABASE_URL="postgresql://..."
   export JWT_SECRET_KEY="change-this"
   ```

5. **Run migrations** (if using):
   ```bash
   python migrations/migrate.py
   ```

6. **Start the application**
   ```bash
   python app.py
   # or with Flask
   export FLASK_APP=app.py
   flask run
   ```

Open `http://localhost:5000/` and test the `/login` endpoint.

---

## 📡 API Endpoints

### Authentication

- `POST /login` – body `{username, password}` → JWT access token

### User Routes (require `Authorization: Bearer <token>`)

- `POST /process` – submit a transcription request (form data: `drive_link`, optional `start_time`, `end_time`)
- `GET /transcriptions` – list current user's transcriptions
- `GET /download/{txt|md|word}/{id}` – download a completed file

### Admin Routes (JWT token of a user with `is_admin=true`)

Under `/admin` prefix:

- `GET /users`, `POST /users`, `DELETE /users/{id}`
- `GET /transcriptions`, `DELETE /transcriptions/{id}`
- `GET /logs`
- Prompt management (`/transcribe-prompts`, `/proofread-prompts`)
- Settings endpoints to select active prompts

> See `admin_routes.py` for full details and request/response shapes.

---

## 🗂 Database Schema

Tables defined by `models.py` include `User`, `Transcription`, `ErrorLog`, `TranscribePrompt`, `ProofreadPrompt`, `SystemSetting`, etc. Scripts in `migrations/` provide initial SQL.

---

## ⚠️ Deployment Tips

- Build a virtual environment and install dependencies.
- Use Gunicorn with `wsgi:app` and configure systemd (service file example in existing README).
- Serve behind Nginx as reverse proxy; ensure file permissions for user file directories.
- Install system packages: `pandoc`, `ffmpeg`, and keep `yt-dlp` up to date.

---

## 📦 Docker

A `Dockerfile` is included for container builds. Adapt as needed for production.

---

## 📚 Additional Resources

Links to DigitalOcean tutorials (e.g., Flask+Gunicorn+Nginx, PostgreSQL setup, firewall rules) are kept for reference.
- https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-22-04

- https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-20-04

- https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu

- https://www.digitalocean.com/community/tutorials/ufw-essentials-common-firewall-rules-and-commands

### Linux Snippets

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

---

## 🙌 Contributing

Feel free to submit issues or pull requests. Follow Python style guidelines and update tests when adding features.

---

## 📜 License

Specify the license for your project here (e.g. MIT, Apache 2.0).
