# OAuth Redirect URI Error - Quick Fix

## The Problem
```
The redirect_uri is not associated with this application.
```

## The Solution (5 Steps)

### 1. Find Your Redirect URI

Your app sends this redirect URI to OAuth providers:

**For Development:**
- GitHub: `http://localhost:18000/api/v1/auth/oauth/github/callback`
- Google: `http://localhost:18000/api/v1/auth/oauth/google/callback`
- GitLab: `http://localhost:18000/api/v1/auth/oauth/gitlab/callback`

**For Production:**
Replace `localhost:18000` with your domain:
- `https://yourdomain.com/api/v1/auth/oauth/{provider}/callback`

### 2. Update GitHub OAuth App

1. Go to: https://github.com/settings/developers
2. Click your OAuth App
3. Set **Authorization callback URL** to: `http://localhost:18000/api/v1/auth/oauth/github/callback`
4. Click **Update application**

### 3. Update Google OAuth App

1. Go to: https://console.cloud.google.com/apis/credentials
2. Click your OAuth 2.0 Client ID
3. Under **Authorized redirect URIs**, add: `http://localhost:18000/api/v1/auth/oauth/google/callback`
4. Click **SAVE**

### 4. Update GitLab OAuth App

1. Go to: https://gitlab.com/-/profile/applications
2. Set **Redirect URI** to: `http://localhost:18000/api/v1/auth/oauth/gitlab/callback`
3. Click **Save application**

### 5. Restart & Test

```bash
# Restart your backend server
# Then try OAuth login again
```

## ⚠️ Important Notes

- **Must match EXACTLY** - no trailing slashes, correct port (18000), correct path
- **Wait a few seconds** after updating - OAuth providers need time to propagate changes
- **Check backend logs** - they now show the redirect URI being used

## Still Not Working?

Check backend logs for a line like:
```
OAuth redirect URI for github: http://localhost:18000/api/v1/auth/oauth/github/callback
```

Make sure this EXACTLY matches what's registered in your OAuth provider.

See [full troubleshooting guide](./oauth_redirect_uri_fix.md) for more details.
