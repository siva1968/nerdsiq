# Google Drive Setup for NerdsIQ

## Option A: OAuth 2.0 User Credentials (Recommended for Restricted Orgs)

Use this method if your organization blocks service account key creation.

### Step 1: Create OAuth Client ID

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Google Drive API**:
   - Go to "APIs & Services" → "Enable APIs and Services"
   - Search for "Google Drive API" → Enable it

4. Configure OAuth Consent Screen:
   - Go to "APIs & Services" → "OAuth consent screen"
   - Choose **Internal** (for org users) or **External** (for testing)
   - Fill in App name: `NerdsIQ`
   - Add your email as support email
   - Click "Save and Continue"
   - **Add Scopes** (Important!):
     - Click "Add or Remove Scopes"
     - In the filter box, search for `drive.readonly`
     - Check the box for `https://www.googleapis.com/auth/drive.readonly`
     - Or manually enter: `https://www.googleapis.com/auth/drive.readonly`
     - Click "Update" then "Save and Continue"
   - Add test users if using External consent screen
   - Click "Save and Continue" to finish

5. Create OAuth Client ID:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: **Web application**
   - Name: `nerdsiq-web`
   - Under "Authorized redirect URIs", add:
     - `https://nerdsiq.getinstantleads.in/oauth/callback`
   - Click "Create"
   - Download the JSON file (click the download icon)

### Step 2: Save Credentials & Authenticate

Save the downloaded JSON file as:
```
backend/credentials/oauth-client.json
```

Run the authentication script (one-time):
```bash
docker exec -it nerdsiq-api python scripts/authenticate_drive.py
```

The script will:
1. Display an authorization URL - open it in your browser
2. Sign in with your Google account and authorize access
3. You'll be redirected to a URL (may show error page - that's OK)
4. Copy the **full redirect URL** and paste it back in the terminal
5. The refresh token is saved for future use

### Step 3: Share Google Drive Folder

1. Open Google Drive
2. Create or select a folder with your documents
3. Your authenticated user must have access to this folder
4. Copy the **Folder ID** from the URL:
   - URL looks like: `https://drive.google.com/drive/folders/1ABC123xyz`
   - Folder ID is: `1ABC123xyz`

### Step 4: Update Environment

Add to your `backend/.env`:
```
GOOGLE_OAUTH_CLIENT_FILE=./credentials/oauth-client.json
GOOGLE_OAUTH_TOKEN_FILE=./credentials/oauth-token.json
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here
```

---

## Option B: Service Account (If Allowed)

Use this method if your organization allows service account key creation.

### Step 1: Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Google Drive API**

4. Create a Service Account:
   - Go to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Name: `nerdsiq-drive-reader`
   - Click "Create and Continue"
   - Skip granting roles (not needed for Drive)
   - Click "Done"

5. Create a Key:
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose **JSON** format
   - Download the file

### Step 2: Save Credentials

Save the downloaded JSON file as:
```
backend/credentials/google-service-account.json
```

### Step 3: Share Google Drive Folder

1. Open Google Drive
2. Create or select a folder with your documents
3. Right-click the folder → "Share"
4. Add the service account email (looks like: `nerdsiq-drive-reader@your-project.iam.gserviceaccount.com`)
5. Give it "Viewer" access
6. Copy the **Folder ID** from the URL

### Step 4: Update Environment

Add to your `backend/.env`:
```
GOOGLE_SERVICE_ACCOUNT_FILE=./credentials/google-service-account.json
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-here
```

---

## Step 5: Index Documents

Run:
```bash
docker exec nerdsiq-api python scripts/index_documents.py
```

## Supported Document Types
- Google Docs
- PDF files
- Text files (.txt, .md)
- Word documents (.docx)
