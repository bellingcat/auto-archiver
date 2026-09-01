# InstagrAPI Server

The instagram API Extractor requires access to a running instance of the InstagrAPI server. 
We have a lightweight script with the endpoints required for our Instagram API Extractor module which you can run locally, or via Docker.



⚠️ Warning: Remember that it's best not to use your own personal account for archiving. [Here's why](../installation/authentication.md#recommendations-for-authentication).

🔐 Security: the server logs into your Instagram account, so every request it serves acts as that account. All routes require an API key: set `INSTAGRAPI_API_KEY` in `secrets/.env` (the Docker script generates one for you) and pass the same value as `access_token` in your orchestration file. Keep the server bound to localhost (the default) — if you must expose it remotely, put it behind an authenticated reverse proxy over HTTPS.
## Quick Start: Using Docker

We've provided a convenient shell script (`run_instagrapi_server.sh`) that simplifies the process of setting up and running the Instagrapi server in Docker. This script handles building the Docker image, setting up credentials, and starting the container.

### 🔧 Running the script:

Run this script either from the repository root or from within the `scripts/instagrapi_server` directory:

```bash
./scripts/instagrapi_server/run_instagrapi_server.sh
```

This script will:
- Prompt for your Instagram username and password.
- Create the necessary `.env` file, including a randomly generated `INSTAGRAPI_API_KEY`.
- Build the Docker image.
- Start the Docker container (published on `127.0.0.1:8000`, localhost only) and authenticate with Instagram, creating a session automatically.
- Print the generated API key, which you must set as `access_token` in your orchestration file (see below).

### ⏱ To run the server again later:
```bash
docker start ig-instasrv
```

### 🐛 Debugging:
View logs:
```bash
docker logs ig-instasrv
```


### Overview: How the Setup Works

1. You enter your Instagram credentials in a local `.env` file
2. You run the server **once locally** to generate a session file
3. After that, you can choose to run the server again locally or inside Docker without needing to log in again

---

## Optional: Manual / Local Setup

If you'd prefer to run the server manually (without Docker), you can follow these steps:


1. **Navigate to the server folder (and stay there for the rest of this guide)**:
   ```bash
   cd scripts/instagrapi_server
   ```

2. **Create a `secrets/` folder** (if it doesn't already exist in `scripts/instagrapi_server`):
   ```bash
   mkdir -p secrets
   ```

3. **Create a `.env` file** inside `secrets/` with your Instagram credentials and an API key (any long random secret, e.g. the output of `openssl rand -hex 32`):
   ```dotenv
   INSTAGRAM_USERNAME="your_username"
   INSTAGRAM_PASSWORD="your_password"
   INSTAGRAPI_API_KEY="a_long_random_secret"
   ```
   Restrict its permissions: `chmod 600 secrets/.env`

4. **Install dependencies** using the pyproject.toml file:
  
   ```bash
   poetry install --no-root
   ```

5. **Run the server locally**:
   ```bash
   poetry run uvicorn src.instaserver:app --port 8000
   ```

6. **Watch for the message**:
   ```
   Login successful, session saved.
   ```

✅ Your session is now saved to `secrets/instagrapi_session.json`.

### To run it again locally:
```bash
poetry run uvicorn src.instaserver:app --port 8000
```

---

## Adding the API Endpoint to Auto Archiver

The server should now be running within that session, and accessible at  http://127.0.0.1:8000 

You can set this in the Auto Archiver orchestration.yaml file like this (the `access_token` must match the `INSTAGRAPI_API_KEY` from `secrets/.env`):
```yaml
instagram_api_extractor:
  api_endpoint: http://127.0.0.1:8000
  access_token: a_long_random_secret
```


---

## 2. Running the Server Again

Once the session file is created, you should be able to run the server without logging in again.

### To run it locally (from scripts/instagrapi_server):
```bash
poetry run uvicorn src.instaserver:app --port 8000
```

---

## 3. Running via Docker (After Setup is Complete, either locally or via the script)

Once the `instagrapi_session.json` and `.env` files are set up, you can pass them Docker and it should authenticate successfully.

### 🔨 Build the Docker image manually:
```bash
docker build -t instagrapi-server .
```

### ▶️ Run the container:
```bash
docker run -d \
  --env-file secrets/.env \
  -v "$(pwd)/secrets:/app/secrets" \
  -p 127.0.0.1:8000:8000 \
  --name ig-instasrv \
  instagrapi-server
```

This passes the /secrets/ directory to docker as well as the environment variables from the `.env` file. Publishing with `127.0.0.1:8000:8000` keeps the server reachable from this machine only — do not publish it on all interfaces (`-p 8000:8000`), as anyone who can reach the port could query Instagram through your account.



---

## 4. Optional Cleanup

- **Stop the Docker container**:
  ```bash
  docker stop ig-instasrv
  ```

- **Remove the container**:
  ```bash
  docker rm ig-instasrv
  ```

- **Remove the Docker image**:
  ```bash
  docker rmi instagrapi-server
  ```

### ⏱ To run again later:
```bash
docker start ig-instasrv
```

---

##  Notes

- Never share your `.env` or `instagrapi_session.json` — these contain sensitive login data. 
- If you want to reset your session, simply delete the `secrets/instagrapi_session.json` file and re-run the local server.
