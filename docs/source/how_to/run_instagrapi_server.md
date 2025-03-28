# InstagrAPI Server

The instagram API Extractor requires a running instance of the InstagrAPI server. 
We have a lightweight script with the endpoints required for our Instagram API Extractor module which you can run locally, or via Docker.

To run this you need to install some additional requirements.

## Setup

Although there is an option to run the server in a Docker container, the authentication is usually rejected without an additional session file, which can be created by running the server locally first.

⚠️ Warning: Remember that it's best not to use your own personal account for archiving. [Here's why](../installation/authentication.md#recommendations-for-authentication).

## Overview: How the Setup Works

1. You enter your Instagram credentials in a local `.env` file
2. You run the server **once locally** to generate a session file
3. After that, you can choose to run the server again locally or inside Docker without needing to log in again

---

## 1. One-Time Local Setup 

This generates a session file using your login details so Instagram recognises your login. 
This will be reused automatically by the script, and can also be passed to the Docker container.

### 🔧 Step-by-step:

1. **Navigate to the server folder (and stay there for the rest of this guide)**:
   ```bash
   cd scripts/instagrapi_server
   ```

2. **Create a `secrets/` folder** (if it doesn't already exist in `scripts/instagrapi_server`):
   ```bash
   mkdir -p secrets
   ```

3. **Create a `.env` file** inside `secrets/` with your Instagram credentials:
   ```dotenv
   INSTAGRAM_USERNAME="your_username"
   INSTAGRAM_PASSWORD="your_password"
   ```

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

The server should now be running within that session, and accessible at  http://127.0.0.1:8000 

You can set this in the orchestration.yaml file like this:
```yaml
instagram_api_extractor:
  api_endpoint: http://127.0.0.1:8000
```

Or to run it in a Docker container, you can pass the session file to it now.
**Stop the server** (`Ctrl+C`).

📅 Your session has now been saved to `secrets/instagrapi_session.json`.

---

## 2. Running the Server Again

Once the session file is created, you should be able to run the server without logging in again.

### To run it locally (from scripts/instagrapi_server):
```bash
poetry run uvicorn src.instgrapinstance.instaserver:app --port 8000
```

---

## 3. Running via Docker (After Setup to create the session file)

Once the session file exists, you can pass this to docker Docker and it should authenticate successfully.

### 🔨 Build the Docker image:
```bash
docker build -t instagrapi-server .
```

### ▶️ Run the container:
```bash
docker run -d \
  --env-file secrets/.env \
  -v "$(pwd)/secrets:/app/secrets" \
  -p 8000:8000 \
  --name ig-instasrv \
  instagrapi-server
```

This passes the /secrets/ directory to docker, so it can use your saved session file and credentials.

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

- You only need to run the server **locally once** to generate a session.
- Never share your `.env` or `instagrapi_session.json` — these contain sensitive login data. 
- If you want to reset your session, simply delete the `secrets/instagrapi_session.json` file and re-run the local server.
