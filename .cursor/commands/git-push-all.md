# Git Push All

## Description
Stages all changes, commits them, and pushes to the remote repository.

## Command

```bash
#!/bin/bash

# Stage all changes
git add .

# Check if there are any changes to commit
if git diff --staged --quiet; then
    echo "No changes to commit."
    exit 0
fi

# Show status
echo "Staged changes:"
git status --short

# Get commit message from user or use AI-generated message
# If using Cursor's AI, generate a commit message based on staged changes
# Otherwise, prompt for a message
if [ -z "$COMMIT_MESSAGE" ]; then
    echo ""
    echo "Enter commit message (or press Enter for AI-generated message):"
    read -r COMMIT_MESSAGE
    
    if [ -z "$COMMIT_MESSAGE" ]; then
        # Use git's default editor or a simple default message
        COMMIT_MESSAGE="Update: $(git diff --staged --name-only | head -3 | tr '\n' ', ' | sed 's/,$//')"
        if [ ${#COMMIT_MESSAGE} -gt 100 ]; then
            COMMIT_MESSAGE="${COMMIT_MESSAGE:0:97}..."
        fi
    fi
fi

# Commit changes
git commit -m "$COMMIT_MESSAGE"

# Get current branch
BRANCH=$(git branch --show-current)

# Push to remote
echo "Pushing to origin/$BRANCH..."
git push origin "$BRANCH"

echo "✅ Successfully pushed to origin/$BRANCH"
```

## Usage

Execute this command via Cursor's command palette or chat interface.

**Example:**
```
@git-push-all
```

Or with a custom commit message:
```
COMMIT_MESSAGE="Fix: Enhanced heartbeat protocol implementation" @git-push-all
```

## Safety Features

- Checks for staged changes before committing
- Shows what will be committed
- Prompts for commit message if not provided
- Uses current branch for push (prevents accidental pushes to wrong branch)
