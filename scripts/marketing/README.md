# Marketing Scripts

Scripts for automating OmoiOS marketing activities.

## Typefully Tweet Scheduler

Automatically schedules tweets to X.com via the Typefully API.

### Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Get your Typefully API key**:
   - Go to https://typefully.com/settings
   - Navigate to API section
   - Generate a new API key

3. **Set the environment variable**:
   ```bash
   export TYPEFULLY_API_KEY="your_api_key_here"
   ```

### Usage

```bash
# List connected accounts
python typefully_scheduler.py --list-accounts

# Preview week 1 schedule (dry run)
python typefully_scheduler.py --week 1 --dry-run

# Schedule week 1
python typefully_scheduler.py --week 1

# Schedule week 2
python typefully_scheduler.py --week 2

# Schedule both weeks
python typefully_scheduler.py --all

# With custom start date
python typefully_scheduler.py --all --start-date 2026-01-20

# With specific timezone
python typefully_scheduler.py --all --timezone "America/New_York"
```

### Schedule Overview

| Week | Posts | Threads | Days |
|------|-------|---------|------|
| Week 1 | 17 | 1 | Mon-Sun |
| Week 2 | 17 | 1 | Mon-Sun |
| **Total** | **34** | **2** | **14 days** |

### Posting Times

- **Weekdays**: 9 AM, 12 PM, 6 PM
- **Saturday**: 10 AM, 3 PM
- **Sunday**: 11 AM (thread day)

### Customization

To modify the tweets, edit the `WEEK_1_SCHEDULE` and `WEEK_2_SCHEDULE` lists in `typefully_scheduler.py`. Each entry is a tuple:

```python
(day_offset, "HH:MM", "tweet content", "source_file.md", is_thread)
```

- `day_offset`: 0 = Monday of week 1, 7 = Monday of week 2
- `is_thread`: True for multi-tweet threads (content is a list)

### Notes

- Drafts are created with `[Auto]` prefix in title
- Threads are automatically handled (list of tweets)
- The script respects Typefully rate limits
- All times use your specified timezone
