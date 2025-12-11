# OAuth Redirect URI Error - Troubleshooting Guide

## Error Message
```
The redirect_uri is not associated with this application.
The application might be misconfigured or could be trying to redirect you to a website you weren't expecting.
```

## What This Means

This error occurs when the redirect URI your application sends to the OAuth provider (GitHub, Google, GitLab) doesn't match what's registered in the OAuth app settings.

## How the Redirect URI is Built

Your application automatically builds the redirect URI using this logic:

1. **Base URI**: From `AUTH_OAUTH_REDIRECT_URI` environment variable (default: `http://localhost:3000/auth/callback`)
2. **Backend Conversion**: The code converts this to the backend callback URL:
   - If `localhost:3000` is detected → converts to `localhost:18000`
   - Otherwise, extracts the base URL
3. **Final Redirect URI**: `{backend_base}/api/v1/auth/oauth/{provider}/callback`

### Example for Development:
- Input: `AUTH_OAUTH_REDIRECT_URI=http://localhost:3000/auth/callback`
- Output for GitHub: `http://localhost:18000/api/v1/auth/oauth/github/callback`
- Output for Google: `http://localhost:18000/api/v1/auth/oauth/google/callback`

## Step-by-Step Fix

### Step 1: Determine What Redirect URI Your App is Sending

The redirect URI depends on your `AUTH_OAUTH_REDIRECT_URI` setting:

**For Development (localhost:3000):**
- GitHub: `http://localhost:18000/api/v1/auth/oauth/github/callback`
- Google: `http://localhost:18000/api/v1/auth/oauth/google/callback`
- GitLab: `http://localhost:18000/api/v1/auth/oauth/gitlab/callback`

**For Production:**
- If `AUTH_OAUTH_REDIRECT_URI=https://yourdomain.com/auth/callback`
- Then redirect URI will be: `https://yourdomain.com/api/v1/auth/oauth/{provider}/callback`

### Step 2: Update OAuth Provider Settings

#### GitHub

1. Go to: https://github.com/settings/developers
2. Click on your OAuth App (or create a new one)
3. Find **"Authorization callback URL"**
4. Set it to EXACTLY: `http://localhost:18000/api/v1/auth/oauth/github/callback`
   - ⚠️ **Must match exactly** - no trailing slashes, correct port, correct path
5. Click **"Update application"**
6. Wait a few seconds for changes to propagate

#### Google

1. Go to: https://console.cloud.google.com/apis/credentials
2. Click on your OAuth 2.0 Client ID (or create a new one)
3. Under **"Authorized redirect URIs"**, click **"ADD URI"**
4. Add EXACTLY: `http://localhost:18000/api/v1/auth/oauth/google/callback`
   - ⚠️ **Must match exactly** - case sensitive, no trailing slashes
5. Click **"SAVE"**
6. Wait a few seconds for changes to propagate

#### GitLab

1. Go to: https://gitlab.com/-/profile/applications (or your GitLab instance)
2. Find your application (or create a new one)
3. Set **"Redirect URI"** to EXACTLY: `http://localhost:18000/api/v1/auth/oauth/gitlab/callback`
4. Click **"Save application"**

### Step 3: Verify Your Environment Variables

Check your backend `.env` file or environment:

```bash
# Check what redirect URI is configured
echo $AUTH_OAUTH_REDIRECT_URI

# Should be (for development):
# AUTH_OAUTH_REDIRECT_URI=http://localhost:3000/auth/callback
```

### Step 4: Restart Your Backend

After updating OAuth provider settings, restart your backend server:

```bash
# Stop your backend
# Then restart it to ensure it picks up any environment changes
```

### Step 5: Test the OAuth Flow

1. Try logging in with OAuth again
2. If it still fails, check the browser's Network tab to see the exact redirect URI being sent
3. Compare it with what's registered in your OAuth provider

## Common Mistakes

### ❌ Wrong Port
- Registered: `http://localhost:3000/api/v1/auth/oauth/github/callback`
- Should be: `http://localhost:18000/api/v1/auth/oauth/github/callback`

### ❌ Missing Path Segments
- Registered: `http://localhost:18000/callback`
- Should be: `http://localhost:18000/api/v1/auth/oauth/github/callback`

### ❌ Trailing Slash
- Registered: `http://localhost:18000/api/v1/auth/oauth/github/callback/`
- Should be: `http://localhost:18000/api/v1/auth/oauth/github/callback` (no trailing slash)

### ❌ Wrong Protocol
- Registered: `https://localhost:18000/api/v1/auth/oauth/github/callback`
- Should be: `http://localhost:18000/api/v1/auth/oauth/github/callback` (for localhost)

### ❌ Wrong Provider Name
- Registered: `http://localhost:18000/api/v1/auth/oauth/github/callback`
- But trying to use Google → should be: `http://localhost:18000/api/v1/auth/oauth/google/callback`

## Debugging: See What Redirect URI is Being Sent

To see exactly what redirect URI your application is sending, you can:

1. **Check Backend Logs**: The OAuth service logs the redirect URI being used
2. **Browser Network Tab**: 
   - Open DevTools → Network tab
   - Click the OAuth login button
   - Look for the request to the OAuth provider
   - Check the `redirect_uri` parameter in the URL

3. **Add Temporary Logging** (if needed):
   ```python
   # In backend/omoi_os/services/oauth_service.py
   redirect_uri = self._build_redirect_uri(provider_name)
   logger.info(f"Using redirect URI for {provider_name}: {redirect_uri}")
   ```

## Production Setup

For production, you'll need:

1. **Update Environment Variable**:
   ```bash
   AUTH_OAUTH_REDIRECT_URI=https://yourdomain.com/auth/callback
   ```

2. **Update OAuth Provider Settings**:
   - GitHub: `https://yourdomain.com/api/v1/auth/oauth/github/callback`
   - Google: `https://yourdomain.com/api/v1/auth/oauth/google/callback`
   - GitLab: `https://yourdomain.com/api/v1/auth/oauth/gitlab/callback`

3. **Use HTTPS**: OAuth providers require HTTPS in production

## Quick Checklist

- [ ] Identified which provider is failing (GitHub/Google/GitLab)
- [ ] Calculated the correct redirect URI based on `AUTH_OAUTH_REDIRECT_URI`
- [ ] Updated the OAuth provider's callback URL to match exactly
- [ ] Verified no trailing slashes or typos
- [ ] Waited a few seconds for changes to propagate
- [ ] Restarted the backend server
- [ ] Tested the OAuth flow again

## Still Not Working?

If you've verified everything above and it's still not working:

1. **Double-check the exact redirect URI** in your OAuth provider settings
2. **Check browser console** for any additional error messages
3. **Verify environment variables** are loaded correctly in your backend
4. **Check backend logs** for any OAuth-related errors
5. **Try creating a new OAuth app** with the correct redirect URI from the start

## Need Help?

If you're still stuck, provide:
- Which OAuth provider (GitHub/Google/GitLab)
- Your `AUTH_OAUTH_REDIRECT_URI` value
- What redirect URI is registered in the OAuth provider
- Any error messages from backend logs
