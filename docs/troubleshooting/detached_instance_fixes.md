# SQLAlchemy DetachedInstanceError Fixes

## Summary

Fixed multiple potential `DetachedInstanceError` issues throughout the codebase where SQLAlchemy model instances were being used outside their session context.

## Fixed Issues

### 1. OAuth Callback Route (`backend/omoi_os/api/routes/oauth.py`)

**Problem**: User object was created/updated in one session, then `user.id` was accessed in a different session context.

**Fix**: 
- Moved all user creation/update logic into the same session where tokens are generated
- Extract `user_id` while still in session (before it becomes detached)
- Added `session.expunge(user)` to prevent detached instance errors

### 2. OAuth Service `get_or_create_user` (`backend/omoi_os/services/oauth_service.py`)

**Problem**: Returns User object from within a session context manager, which closes when function returns.

**Fix**: Added `session.expunge(user)` before returning to detach the object from the session.

### 3. Auth Route - Login (`backend/omoi_os/api/routes/auth.py`)

**Problem**: `authenticate_user()` returns User from async session, then `user.id` is accessed.

**Fix**: Extract `user_id = user.id` before using it to create tokens.

### 4. Auth Route - Refresh Token (`backend/omoi_os/api/routes/auth.py`)

**Problem**: `get_user_by_id()` returns User from async session, then `user.id` is accessed.

**Fix**: Extract `user_id = user.id` before using it to create tokens.

### 5. Auth Route - Password Reset (`backend/omoi_os/api/routes/auth.py`)

**Problem**: `get_user_by_email()` returns User from async session, then `user.id` is accessed.

**Fix**: Extract `user_id = user.id` before using it to create reset token.

## Already Protected

### `get_current_user` (`backend/omoi_os/api/dependencies.py`)

✅ **Already safe**: Uses `session.expunge(user)` before returning.

## Best Practices Applied

1. **Extract needed values before session closes**: Always extract `user.id` or other needed attributes while the session is still open.

2. **Use `session.expunge()` for objects returned from sync sessions**: When returning model instances from functions that use sync session context managers, expunge them before returning.

3. **Async sessions are safer**: Async sessions in FastAPI typically stay open for the entire request lifecycle, but it's still safer to extract needed values early.

## Pattern to Follow

```python
# ❌ BAD - accessing user.id after session closes
with db.get_session() as session:
    user = session.get(User, user_id)
    # session closes here
access_token = create_token(user.id)  # DetachedInstanceError!

# ✅ GOOD - extract ID before session closes
with db.get_session() as session:
    user = session.get(User, user_id)
    user_id = user.id  # Extract while session is open
    session.expunge(user)  # Detach from session
access_token = create_token(user_id)  # Safe!
```

## Testing

All fixes have been applied. Test the following flows:
1. OAuth login (GitHub/Google)
2. Regular email/password login
3. Token refresh
4. Password reset request
