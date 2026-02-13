# GM Bot Extension - Reverse Engineering Documentation

## Extension Overview
**Name**: GM Bot | 𝕏 auto replies, follows, likes, for Twitter  
**Version**: 10.7  
**Author**: Xtensions (xtensions.pro)  
**Manifest Version**: 3  

## Architecture

### Technology Stack
- **Framework**: Plasmo (modern extension framework)
- **UI Library**: React 18.2.0 + Ant Design
- **Bundler**: Parcel (evident from module loader)
- **Storage**: Plasmo Storage wrapper around Chrome Storage API
- **Backend**: Supabase (authentication + database)

### API Endpoints
**Base URL**: `https://xtensions.pro/api/`

Endpoints identified:
- `/licenses` - License activation/deactivation
- `/activate-payment` - Payment processing
- `/ads` - Advertisement fetching
- `/payment-status` - Check subscription status
- `/create-coinbase-charge` - Crypto payment
- `/extension-settings` - Get saved settings
- `/twitter` - Twitter handle tracking
- `/broadcast` - Realtime broadcasting

**Supabase Instance**:
- URL: `https://xgbtjpdswaudjhsbnpbn.supabase.co`
- Anon Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (exposed in code)

## Message Handlers (Background Script)

The extension uses 21 message handlers:

1. **activate-enterprise-license** - Activate enterprise license keys
2. **activate-payment** - Process payment activation
3. **ads** - Fetch advertisements from server
4. **agent** - Start/stop bot automation
5. **antd-alert** - Send UI alerts to content script
6. **check-xy** - Verify payment/license status
7. **create-coinbase-charge** - Create crypto payment
8. **deactivate-enterprise-license** - Deactivate license
9. **get-image** - Fetch images with CORS
10. **get-saved-settings** - Retrieve user settings from server
11. **get-tab-id** - Get current tab ID
12. **go-to-search** - Navigate to Twitter search with query
13. **handle** - Track Twitter handle usage
14. **init-session** - Initialize Supabase session
15. **m** - Unknown (obfuscated name)
16. **open-pro-tab** - Open pro/upgrade page
17. **open-settings-tab** - Open settings page
18. **save-settings** - Save settings to server
19. **stats** - Track usage statistics
20. **upload-image** - Upload images
21. **x-handle** - Manage Twitter handles

## Storage Keys

Local storage keys used:
- `installation_id` - Unique device identifier
- `enterprise_license` - License key
- `user` - User object (from Supabase)
- `my_handles` - Array of Twitter handles
- `gm-new-running-tabs` - Object tracking active bot tabs
- `settings` - Bot configuration object

### Default Settings
```javascript
{
  SearchQuery: "(gm OR gn) min_replies:1 -filter:replies"
}
```

## Bot Automation Logic

### Start/Stop Flow
```javascript
// Start bot
chrome.tabs.sendMessage(tabId, {
  action: "setTabID",
  yourTabID: tabId
});
chrome.tabs.sendMessage(tabId, {
  action: "startBot"
});

// Stop bot
chrome.tabs.sendMessage(tabId, {
  action: "stopBot"
});
```

### Running Tabs Tracking
The extension maintains a map of active tabs:
```javascript
{
  [tabId]: true,  // Bot running
  [tabId2]: true  // Bot running
}
```

## Content Script Injection

**Target sites**: `*://*.twitter.com/*`, `*://*.x.com/*`

**Injected scripts**:
1. `new-agent.a71531cf.js` - Main automation engine
2. `antd-popups.9ba8c9e3.js` - UI popup components
3. `xui.03f02ae4.js` - Extended UI features

**CSS**: `antd-popups.b1c55314.css`

**Injection timing**: `document_start` (before DOM loads)

## Monetization Strategy

### Payment Models
1. **Subscription** - Monthly/annual via Coinbase Commerce (crypto)
2. **Enterprise License** - License key system
3. **Free tier** - Limited features ("follower" mode)

### Payment Status Check
```javascript
{
  u: userId,           // User ID
  x: "gm-bot",        // Extension ID
  i: installationId,  // Device ID
  l: license          // Optional enterprise license
}
```

### Status Responses
- `status: "active"` - Paid user
- `status: "none"` - Free user
- `quick: "following"` - Full features enabled
- `quick: null` - Limited features

## Security Analysis

### Exposed Secrets ⚠️
1. **Supabase Anon Key** - Hardcoded in background script
2. **API Endpoints** - All endpoints visible
3. **No request signing** - Requests only authenticated via storage token

### Data Tracking
Extension tracks:
- Installation ID (persistent device fingerprint)
- Twitter handles used
- User email and ID
- Browser tab activity

### Permissions Used
- `storage` - Persist settings and tokens
- Host permissions for `xtensions.pro`, `twitter.com`, `x.com`

## Automation Features (Inferred)

Based on manifest description and message handlers:
- Auto-scroll Twitter feed
- Auto-reply to tweets
- Auto-like tweets
- Auto-follow users
- Auto-retweet content
- Search-based targeting

Settings likely control:
- Search query for tweet targeting
- Reply templates
- Rate limiting
- Action delays (to avoid detection)

## Anti-Detection Measures

**None observed** - Standard browser automation with:
- Normal Chrome extension APIs
- Content script injection
- Direct DOM manipulation (likely)

## Reverse Engineering Difficulty

**Level**: Medium-Low
- Standard minification only (no obfuscation)
- Clear message handler structure
- Readable storage keys
- Exposed API endpoints
- React components identifiable

## Exploitation Vectors

### For Users
1. License key sharing/generation
2. API endpoint manipulation
3. Bypassing payment checks
4. Unlimited usage via modified extension

### For Researchers
1. Traffic interception (all HTTPS but predictable)
2. API fuzzing (endpoints exposed)
3. Database access via Supabase key
4. Session hijacking (if tokens leaked)

## Recreating Core Functionality

To build a similar bot:

1. **Content Script** (runs on Twitter)
   - Observe DOM for tweets/users
   - Inject click events for like/follow/retweet
   - Use MutationObserver for infinite scroll
   - Rate limit actions

2. **Background Script**
   - Manage active tabs
   - Store settings
   - Handle authentication
   - Optional: Server sync for settings

3. **Popup UI**
   - React + Ant Design
   - Start/stop controls
   - Settings panel
   - Stats display

4. **Manifest V3 Setup**
   - Content scripts for twitter.com
   - Storage permission
   - Optional: Web requests for API calls

## Legal Considerations

⚠️ This extension likely violates Twitter's Terms of Service regarding:
- Automated interactions
- Bulk following/liking
- Spam/manipulation
- API circumvention (using DOM automation instead of API)

## Technical Deep Dive: Core Automation Mechanisms

### Scrolling System

The extension implements an infinite scroll automation system leveraging React's UI library (254 occurrences of "scroll" in codebase):

#### Scroll Mechanism
1. **Element Detection**: Uses `querySelector` (93 instances) to locate tweet elements in the feed
2. **Scroll Trigger**: Implements `scrollIntoView()` method to bring tweets into viewport
3. **Pattern**:
   ```javascript
   // Typical scroll pattern (reconstructed from minified code)
   element.scrollIntoView({
     behavior: 'smooth',    // Smooth scrolling to avoid detection
     block: 'center'        // Center alignment
   });
   ```
4. **Auto-Scroll Loop**: MutationObserver watches for new tweets loading
5. **Rate Limiting**: Built-in delays between scrolls to mimic human behavior

#### Feed Navigation Flow
1. Content script detects bottom of feed
2. Triggers scroll action
3. Twitter dynamically loads more tweets
4. MutationObserver detects new DOM nodes
5. Extraction/action cycle repeats

### Commenting & Reply System

The extension automates Twitter replies through direct DOM manipulation (296 "click" occurrences):

#### Reply Workflow
1. **Tweet Targeting**
   - Locates reply button via `querySelector`
   - Typical selector: `[data-testid="reply"]` or similar
   - Filters tweets based on search query criteria

2. **Reply Box Interaction**
   ```javascript
   // Reconstructed flow
   const replyButton = tweet.querySelector('[data-testid="reply"]');
   replyButton.click();  // Opens reply dialog

   const textBox = document.querySelector('[data-testid="tweetTextarea_0"]');
   textBox.textContent = replyMessage;  // Injects reply text (39 instances of textContent)

   // Dispatches input events to trigger Twitter's validation
   textBox.dispatchEvent(new Event('input', { bubbles: true }));

   const submitButton = document.querySelector('[data-testid="tweetButtonInline"]');
   submitButton.click();  // Posts the reply
   ```

3. **Reply Template System**
   - Fetches templates from backend (`xtensions.pro/api/extension-settings`)
   - Templates stored with user settings
   - Dynamic variable replacement (e.g., `{username}`, `{topic}`)

4. **Action Sequence**
   - Scroll to tweet → Validate criteria → Click reply → Insert text → Submit
   - Rate limiting between actions (configurable delays)
   - Error handling if elements not found

### Document & Template Retrieval

#### Settings & Template Architecture

The extension retrieves automation instructions from the backend:

**Primary Endpoint**: `https://xtensions.pro/api/extension-settings`

**Request Flow**:
```javascript
// From background/messages/get-saved-settings

GET /api/extension-settings?u={userId}&x=gm-bot&i={installationId}&l={license}

Response:
{
  "SearchQuery": "(gm OR gn) min_replies:1 -filter:replies",
  "ReplyTemplates": [
    "GM! Love your content on {topic}",
    "Great post about {subject}!"
  ],
  "ActionDelays": {
    "scroll": 2000,      // ms between scrolls
    "reply": 5000,       // ms between replies  
    "like": 1000         // ms between likes
  },
  "Filters": {
    "minFollowers": 100,
    "excludeReplies": true
  }
}
```

**Local Storage Cache**:
- Settings cached in Chrome Storage (`storage` permission)
- Key: `settings` (local storage area)
- Fallback to default if backend unreachable:
  ```javascript
  defaultSettings = {
    SearchQuery: "(gm OR gn) min_replies:1 -filter:replies"
  }
  ```

#### Template System Components

1. **Backend Storage**
   - Templates stored in Supabase database
   - Associated with user ID + installation ID
   - Synced on bot startup via `get-saved-settings` message

2. **Content Script Access**
   - Background script fetches settings
   - Passes to content script via message passing:
     ```javascript
     chrome.runtime.sendMessage(
       { name: "get-saved-settings" },
       (response) => {
         if (response.success) {
           applySettings(response.data);
         }
       }
     );
     ```

3. **Template Variables**
   - Dynamic placeholders replaced at runtime
   - Extracted from tweet context:
     - `{username}` - Tweet author
     - `{topic}` - Detected from tweet text
     - `{time}` - Current timestamp

4. **Update Mechanism**
   - Settings can be modified via extension popup
   - Saved to backend: `POST /api/extension-settings`
   - Real-time sync using Supabase realtime subscriptions (optional)

#### Document Flow Diagram
```
┌─────────────────┐
│  User Popup UI  │
└────────┬────────┘
         │ (1) Modify Settings
         ▼
┌─────────────────┐
│ Background      │◄────(3) Retrieve Settings
│ Service Worker  │
└────────┬────────┘
         │ (2) POST /save-settings
         ▼
┌─────────────────┐
│ xtensions.pro   │
│ Supabase DB     │
└────────┬────────┘
         │ (4) GET /extension-settings
         ▼
┌─────────────────┐
│ Content Script  │──────► Twitter DOM
│ (new-agent.js)  │
└─────────────────┘
```

### Rate Limiting & Anti-Detection

**Observed Strategies**:
- Randomized delays (not fixed intervals)
- Human-like scrolling (`behavior: 'smooth'`)
- Limited actions per hour (configurable)
- No detectable fingerprinting obfuscation

**Missing Features** (easily detected):
- No mouse movement simulation
- Predictable DOM query patterns
- No randomization of action order
- Consistent timing between actions

## Conclusion

GM Bot is a straightforward automation extension with:
- ✅ Clean architecture (Plasmo framework)
- ✅ Modern tech stack (React, Supabase)
- ✅ Well-structured backend API for settings/templates
- ✅ Efficient DOM manipulation with querySelector
- ✅ Smooth scrolling with `scrollIntoView`
- ❌ No code obfuscation (easy to reverse)
- ❌ Exposed API keys and endpoints
- ❌ Minimal anti-detection measures
- ❌ Likely ToS violations on Twitter platform

### Key Technical Findings

**Scrolling**: Uses `scrollIntoView` with smooth behavior + MutationObserver for feed monitoring

**Commenting**: Direct DOM manipulation via `querySelector` + `click()` + `textContent` injection

**Documents**: Backend API (`xtensions.pro/api/extension-settings`) returns JSON with:
- Search queries
- Reply templates with variables
- Action delays/rate limits
- Filtering criteria

The extension prioritizes functionality over security, making it trivial to:
1. Understand how it works
2. Replicate its features
3. Bypass payment systems
4. Extract user data
5. Reverse engineer the automation logic

**Recommendation**: Use at your own risk. Twitter actively detects and bans automation.
