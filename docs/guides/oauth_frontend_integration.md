# OAuth Frontend Integration Guide

This guide explains how to integrate the OAuth authentication system with the frontend application.

## Overview

The OAuth system supports multiple providers:
- **GitHub** - With repository access (read:user, user:email, repo, read:org scopes)
- **Google** - Basic profile and email
- **GitLab** - With support for self-hosted instances

## Setup

### 1. Environment Variables

Set the following environment variables in your backend:

```bash
# Required for GitHub OAuth
AUTH_GITHUB_CLIENT_ID=your_github_client_id
AUTH_GITHUB_CLIENT_SECRET=your_github_client_secret

# Optional for Google OAuth
AUTH_GOOGLE_CLIENT_ID=your_google_client_id
AUTH_GOOGLE_CLIENT_SECRET=your_google_client_secret

# Optional for GitLab OAuth
AUTH_GITLAB_CLIENT_ID=your_gitlab_client_id
AUTH_GITLAB_CLIENT_SECRET=your_gitlab_client_secret
AUTH_GITLAB_BASE_URL=https://gitlab.com  # or your self-hosted GitLab URL

# Frontend callback URL
AUTH_OAUTH_REDIRECT_URI=http://localhost:3000/auth/callback
```

### 2. Create OAuth App

#### GitHub
1. Go to GitHub Settings → Developer settings → OAuth Apps → New OAuth App
2. Set Authorization callback URL to: `http://localhost:18000/api/v1/auth/oauth/github/callback`
3. Copy the Client ID and Client Secret

#### Google
1. Go to Google Cloud Console → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID
3. Add authorized redirect URI: `http://localhost:18000/api/v1/auth/oauth/google/callback`
4. Copy the Client ID and Client Secret

#### GitLab
1. Go to GitLab → User Settings → Applications
2. Set Callback URL to: `http://localhost:18000/api/v1/auth/oauth/gitlab/callback`
3. Select scopes: `read_user`, `email`
4. Copy the Application ID and Secret

## Frontend Integration

### Starting OAuth Flow

The simplest way to start an OAuth flow is to redirect the user to the provider's authorization endpoint:

```typescript
const handleOAuth = (provider: "github" | "google" | "gitlab") => {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000"
  window.location.href = `${apiUrl}/api/v1/auth/oauth/${provider}`
}
```

### Alternative: Get URL First

If you need to track the state or handle the flow differently:

```typescript
import { api } from "@/lib/api/client"

interface AuthUrlResponse {
  auth_url: string
  state: string
}

async function getOAuthUrl(provider: string): Promise<AuthUrlResponse> {
  return api.get<AuthUrlResponse>(`/api/v1/auth/oauth/${provider}/url`, false)
}

// Usage
const handleOAuth = async (provider: string) => {
  try {
    const { auth_url, state } = await getOAuthUrl(provider)
    // Optionally store state in sessionStorage for verification
    sessionStorage.setItem("oauth_state", state)
    window.location.href = auth_url
  } catch (error) {
    console.error("Failed to get OAuth URL:", error)
  }
}
```

### OAuth Callback Page

The callback page (`/auth/callback`) handles the redirect from the OAuth provider. It:

1. Extracts tokens from URL parameters
2. Stores tokens in localStorage
3. Fetches user data
4. Updates auth context
5. Redirects to the main app

The callback page is already implemented at `frontend/app/(auth)/callback/page.tsx`.

### Handling OAuth Errors

Errors are passed as URL parameters to the callback page:

```typescript
// Common error codes
const errorMessages: Record<string, string> = {
  invalid_state: "Invalid security token. Please try again.",
  oauth_failed: "OAuth authentication failed. Please try again.",
  no_tokens: "No authentication tokens received.",
  auth_failed: "Failed to complete authentication.",
}
```

## API Endpoints

### List Available Providers

```typescript
GET /api/v1/auth/oauth/providers

Response:
{
  "providers": [
    { "name": "github", "enabled": true },
    { "name": "google", "enabled": false },
    { "name": "gitlab", "enabled": false }
  ]
}
```

### Get Authorization URL

```typescript
GET /api/v1/auth/oauth/{provider}/url

Response:
{
  "auth_url": "https://github.com/login/oauth/authorize?...",
  "state": "random_state_token"
}
```

### Start OAuth Flow (Redirect)

```typescript
GET /api/v1/auth/oauth/{provider}

// Redirects to provider's authorization page
```

### OAuth Callback

```typescript
GET /api/v1/auth/oauth/{provider}/callback?code=...&state=...

// Redirects to frontend with tokens:
// http://localhost:3000/auth/callback?access_token=...&refresh_token=...&provider=...
```

### List Connected Providers (Authenticated)

```typescript
GET /api/v1/auth/oauth/connected

Response:
{
  "providers": [
    { "provider": "github", "username": "octocat", "connected": true }
  ]
}
```

### Connect Additional Provider (Authenticated)

```typescript
POST /api/v1/auth/oauth/{provider}/connect

Response:
{
  "auth_url": "https://github.com/login/oauth/authorize?...",
  "state": "random_state_token"
}
```

### Disconnect Provider (Authenticated)

```typescript
DELETE /api/v1/auth/oauth/{provider}/disconnect

Response:
{
  "success": true,
  "message": "github disconnected successfully"
}
```

## GitHub Repository API

Once a user has connected their GitHub account, they can access their repositories:

### List Repositories

```typescript
GET /api/v1/github/repos?visibility=all&sort=updated&per_page=30&page=1

Response: Array of GitHubRepo objects
```

### Get Repository Details

```typescript
GET /api/v1/github/repos/{owner}/{repo}

Response: GitHubRepo object
```

### List Branches

```typescript
GET /api/v1/github/repos/{owner}/{repo}/branches

Response: Array of GitHubBranch objects
```

### Get File Content

```typescript
GET /api/v1/github/repos/{owner}/{repo}/contents/{path}?ref=main

Response: GitHubFile object with decoded content
```

### List Directory

```typescript
GET /api/v1/github/repos/{owner}/{repo}/directory?path=src&ref=main

Response: Array of DirectoryItem objects
```

### Get Repository Tree

```typescript
GET /api/v1/github/repos/{owner}/{repo}/tree?tree_sha=HEAD&recursive=true

Response: Array of TreeItem objects
```

### Create/Update File

```typescript
PUT /api/v1/github/repos/{owner}/{repo}/contents/{path}

Body:
{
  "content": "file content",
  "message": "commit message",
  "branch": "main"  // optional
}

Response: FileOperationResult
```

### Create Branch

```typescript
POST /api/v1/github/repos/{owner}/{repo}/branches

Body:
{
  "branch_name": "feature/new-feature",
  "from_sha": "abc123..."
}

Response: BranchCreateResult
```

### Create Pull Request

```typescript
POST /api/v1/github/repos/{owner}/{repo}/pulls

Body:
{
  "title": "Add new feature",
  "head": "feature/new-feature",
  "base": "main",
  "body": "Description...",  // optional
  "draft": false  // optional
}

Response: PullRequestCreateResult
```

## React Components Example

### OAuth Login Buttons

```tsx
import { Button } from "@/components/ui/button"
import { Github, Mail } from "lucide-react"

function OAuthButtons() {
  const handleOAuth = (provider: string) => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000"
    window.location.href = `${apiUrl}/api/v1/auth/oauth/${provider}`
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      <Button variant="outline" onClick={() => handleOAuth("github")}>
        <Github className="mr-2 h-4 w-4" />
        GitHub
      </Button>
      <Button variant="outline" onClick={() => handleOAuth("google")}>
        <Mail className="mr-2 h-4 w-4" />
        Google
      </Button>
    </div>
  )
}
```

### Connected Providers List

```tsx
import { useEffect, useState } from "react"
import { api } from "@/lib/api/client"

interface ConnectedProvider {
  provider: string
  username?: string
  connected: boolean
}

function ConnectedProviders() {
  const [providers, setProviders] = useState<ConnectedProvider[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const response = await api.get<{ providers: ConnectedProvider[] }>(
          "/api/v1/auth/oauth/connected"
        )
        setProviders(response.providers)
      } catch (error) {
        console.error("Failed to fetch providers:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchProviders()
  }, [])

  const handleDisconnect = async (provider: string) => {
    try {
      await api.delete(`/api/v1/auth/oauth/${provider}/disconnect`)
      setProviders(providers.filter(p => p.provider !== provider))
    } catch (error) {
      console.error("Failed to disconnect:", error)
    }
  }

  if (loading) return <div>Loading...</div>

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Connected Accounts</h3>
      {providers.length === 0 ? (
        <p className="text-muted-foreground">No connected accounts</p>
      ) : (
        <ul className="space-y-2">
          {providers.map(provider => (
            <li key={provider.provider} className="flex items-center justify-between">
              <span>
                {provider.provider.charAt(0).toUpperCase() + provider.provider.slice(1)}
                {provider.username && ` (@${provider.username})`}
              </span>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => handleDisconnect(provider.provider)}
              >
                Disconnect
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

### Repository List

```tsx
import { useEffect, useState } from "react"
import { api } from "@/lib/api/client"

interface GitHubRepo {
  id: number
  name: string
  full_name: string
  description?: string
  private: boolean
  html_url: string
  default_branch: string
  language?: string
}

function RepositoryList() {
  const [repos, setRepos] = useState<GitHubRepo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRepos = async () => {
      try {
        const response = await api.get<GitHubRepo[]>("/api/v1/github/repos")
        setRepos(response)
      } catch (err) {
        setError("Failed to load repositories. Make sure GitHub is connected.")
      } finally {
        setLoading(false)
      }
    }

    fetchRepos()
  }, [])

  if (loading) return <div>Loading repositories...</div>
  if (error) return <div className="text-destructive">{error}</div>

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Your Repositories</h3>
      <ul className="space-y-2">
        {repos.map(repo => (
          <li key={repo.id} className="p-4 border rounded-lg">
            <a
              href={repo.html_url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium hover:underline"
            >
              {repo.full_name}
            </a>
            {repo.description && (
              <p className="text-sm text-muted-foreground">{repo.description}</p>
            )}
            <div className="flex gap-2 mt-2 text-xs text-muted-foreground">
              {repo.language && <span>{repo.language}</span>}
              <span>{repo.private ? "Private" : "Public"}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
```

## Security Considerations

1. **State Parameter**: The OAuth flow uses a state parameter to prevent CSRF attacks. The state is verified on callback.

2. **Token Storage**: Tokens are stored in localStorage. For enhanced security in production, consider:
   - Using httpOnly cookies for refresh tokens
   - Implementing token rotation
   - Adding PKCE for public clients

3. **Scope Limitations**: GitHub OAuth requests the `repo` scope for full repository access. Consider requesting minimal scopes based on your needs.

4. **Token Refresh**: OAuth tokens may expire. Implement token refresh logic for long-running sessions.

## Troubleshooting

### Common Issues

1. **"Provider not configured"**
    - Ensure `AUTH_{PROVIDER}_CLIENT_ID` and `AUTH_{PROVIDER}_CLIENT_SECRET` are set

2. **"Invalid state"**
    - The OAuth state expired or was tampered with
    - Try the login flow again

3. **"GitHub not connected"**
    - User needs to authenticate with GitHub first
    - Check if `github_access_token` exists in user attributes

4. **Callback redirect fails**
    - Verify `AUTH_OAUTH_REDIRECT_URI` matches your frontend URL
    - Check CORS settings if frontend and backend are on different origins

### Debug Mode

Enable debug logging in development:

```python
# In your backend config
import logging
logging.getLogger("omoi_os.services.oauth_service").setLevel(logging.DEBUG)
```

## Production Checklist

- [ ] Set secure JWT secret key (`AUTH_JWT_SECRET_KEY`)
- [ ] Configure proper `AUTH_OAUTH_REDIRECT_URI` for production domain
- [ ] Use HTTPS for all OAuth callbacks
- [ ] Implement rate limiting on OAuth endpoints
- [ ] Set up Redis for OAuth state storage (instead of in-memory)
- [ ] Review and minimize requested OAuth scopes
- [ ] Implement proper error logging and monitoring
- [ ] Test all OAuth flows thoroughly
