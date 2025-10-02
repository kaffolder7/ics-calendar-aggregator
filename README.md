# ICS Calendar Aggregator

A Python service that scrapes event pages, downloads individual `.ics` calendar files, enriches them with event descriptions, and merges them into a single subscribable calendar feed.

## Features

- 🔄 **Automatic Aggregation** - Scrapes event listings and downloads ICS files
- 📝 **Description Enrichment** - Extracts event descriptions from web pages<!-- - 🗓️ **Date Filtering** - Only includes events from today onwards -->
- ⚡ **Parallel Processing** - Fast concurrent processing of multiple events
    - **Rate-Limited** - Built-in throttling prevents overwhelming the server
- 💾 **Smart Caching** - Avoids re-downloading unchanged events
- 🌐 **HTTP Server** - Serves merged calendar for subscription
- 🐳 **Docker Ready** - Easy deployment with Docker/Coolify

## Use Case

Perfect for aggregating events from websites that:
- Provide individual `.ics` files per event (e.g., Squarespace sites)
- Don't offer a consolidated calendar feed
- Have event descriptions on web pages but not in ICS files

This tool was built for [Noblesville Main Street Events](https://www.noblesvillemainstreet.org/events) but can be adapted for any similar event calendar.

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/kaffolder7/ics-calendar-aggregator.git
cd ics-calendar-aggregator

# Build and run
docker-compose up -d

# Calendar available at:
# http://localhost:8080/merged_calendar.ics
```

### Option 2: Python Direct

```bash
# Install dependencies
pip install -r requirements.txt

# Run the aggregator
python aggregator.py

# Serve the calendar
python -m http.server 8080
```

## Configuration

Edit the configuration variables at the top of `aggregator.py`:

```python
# Website with event listings
EVENTS_URL = "https://www.noblesvillemainstreet.org/events"

# Output filename
OUTPUT_ICS = "merged_calendar.ics"

# Database for caching
DB_FILE = "calendar_cache.db"

# Cache duration before re-checking events
CACHE_DURATION_HOURS = 6

# Number of parallel workers for processing
MAX_WORKERS = 5
```

## How It Works

1. **Scrapes Event Listings** - Fetches the main events page and extracts event URLs
2. **Downloads ICS Files** - For each event, downloads the `.ics` file (tries `?format=ics` pattern)
3. **Scrapes Descriptions** - Fetches each event page and extracts description text
4. **Enriches Events** - Adds descriptions and URLs to calendar events
5. **Filters by Date** - Removes events before today
6. **Merges Calendar** - Combines all events into single `.ics` file
7. **Caches Results** - Stores event data to avoid redundant downloads

## Subscribing to the Calendar

### In Google Calendar
1. Click the **+** next to "Other calendars"
2. Select **From URL**
3. Enter: `http://your-server:8080/merged_calendar.ics`
4. Click **Add calendar**

### In Apple Calendar
1. **File** → **New Calendar Subscription**
2. Enter the URL
3. Set refresh frequency (recommended: hourly)
4. Click **Subscribe**

### In Outlook
1. **Add calendar** → **Subscribe from web**
2. Paste the URL
3. Name the calendar
4. Click **Import**

### In Thunderbird
1. Right-click **Calendar** → **New Calendar**
2. Select **On the Network**
3. Choose **iCalendar (ICS)**
4. Enter the URL

## Deployment

### Deploy to Coolify

1. Create a new **Docker Compose** service in Coolify
2. Paste the contents of `docker-compose.yml` (or `docker-compose.prod.yml` for a production-ready version)
3. Add your domain (optional): `calendar-events.yourdomain.com`
4. Click **Deploy**

Your calendar will be available at:
```
https://calendar-events.yourdomain.com/merged_calendar.ics
```
_Note: If using the `docker-compose.prod.yml` production-ready variant, then your URL will instead be `https://calendar-events.yourdomain.com/calendar.ics`_

### Environment Variables

You can override configuration via environment variables:

```yaml
environment:
  - EVENTS_URL=https://example.com/events
  - UPDATE_INTERVAL=3600  # seconds between updates
  - MAX_WORKERS=5
```

### Scheduled Updates

The Docker container runs the aggregator in a loop:

```bash
# Updates every hour by default
while true; do 
  python aggregator.py 
  sleep 3600
done
```

Adjust the sleep interval in `docker-compose.yml`:
- `1800` = 30 minutes
- `3600` = 1 hour (default)
- `21600` = 6 hours

## Customization

### Change CSS Selectors

If the event page structure differs, update the selectors in `get_event_description()`:

```python
selectors = [
    '.eventlist-description',  # Primary selector
    '.sqs-block-html',         # Squarespace content block
    '.event-details',          # Alternative
    # Add your own selectors here
]
```

<!-- ### Filter Events by Keyword

Add filtering logic in `process_single_event()`:

```python
summary = str(event.get('summary', '')).lower()

# Only include specific event types
if 'festival' not in summary and 'concert' not in summary:
    continue
``` -->

<!-- ### Adjust Date Range

Modify `is_future_event()` to change the date filter:

```python
# Include only next 30 days
today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
thirty_days = today + timedelta(days=30)
return today <= event_datetime <= thirty_days
``` -->

### Adjust Parallel Workers

More workers = faster processing, but may trigger rate limiting:

```python
MAX_WORKERS = 3   # Conservative (slower, safer)
MAX_WORKERS = 5   # Balanced (default)
MAX_WORKERS = 10  # Aggressive (faster, may be rate-limited)
```

<!-- By default, a maximum number of 5 workers are configured, but no more than the number of events. -->

_Note: By default, the script uses up to 5 parallel workers, automatically reducing to match the number of events if fewer than 5. Setting `MAX_WORKERS` to a fixed number will force the script to always use that many workers, no matter the number of events._

## Troubleshooting

### No Events Found

**Problem**: Script finds no event URLs

**Solution**: Check the CSS selector for event links in `get_event_links()`:

```bash
# Run in debug mode to see HTML structure
python aggregator.py
# Check the console output for "Found X event links"
```

Update the selectors:
```python
selectors = [
    'a[href*="/events-calendar/"]',
    'a[href*="/events/"]',
    # Add selectors based on your site's HTML
]
```

### ICS Download Fails

**Problem**: Cannot download `.ics` files

**Solution**: Check the ICS URL pattern. Try accessing an event page manually and look for the download link:

```python
# Update URL patterns in download_ics()
ics_urls = [
    f"{event_url}?format=ics",
    f"{event_url}/?format=ics",
    f"{event_url}.ics",
    # Add patterns based on your site
]
```

### Duplicate Events

**Problem**: Events appear multiple times

**Solution**: Clear the cache database:

```bash
docker exec calendar-aggregator rm calendar_cache.db
# Or locally:
rm calendar_cache.db
```

### Description Not Extracted

**Problem**: Events have no descriptions

**Solution**: Inspect the event page HTML to find the correct selector:

1. Visit an event page in your browser
2. Right-click on the description → **Inspect**
3. Note the CSS class or ID
4. Update the selector in `get_event_description()`

### Rate Limiting

**Problem**: Too many requests too quickly

**Solution**: Reduce `MAX_WORKERS`:

```python
MAX_WORKERS = 3  # Slower but more respectful
```

<!-- Or add rate limiting (see code comments in the script). -->

## File Structure

```
ics-calendar-aggregator/
├── aggregator.py           # Main Python script
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Docker Compose configuration
├── nginx.conf             # Nginx config (optional)
├── README.md              # This file
├── merged_calendar.ics    # Generated calendar (created on first run)
└── calendar_cache.db      # SQLite cache (created on first run)
```

## Requirements

### Python Dependencies
- `requests` - HTTP requests
- `beautifulsoup4` - HTML parsing
- `icalendar` - ICS file parsing/generation
- `lxml` - XML parsing

### System Requirements
- Python 3.12+
- Docker & Docker Compose (for containerized deployment)
- 100MB disk space
- Minimal CPU/RAM (runs efficiently)

## Performance

**Example with 20 events:**
- Sequential: ~40 seconds
- Parallel (5 workers): ~8 seconds
- **5x speedup** with parallel processing

**Resource usage:**
- Memory: ~50MB
- CPU: Low (mostly I/O bound)
- Network: ~1-2MB per update cycle

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Ideas for Contributions
- Support for more event calendar platforms
- Additional calendar output formats (Google Calendar API, CalDAV)
- Web UI for configuration
- Event deduplication improvements
- More filtering options (categories, locations, etc.)

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built for aggregating events from [Noblesville Main Street](https://www.noblesvillemainstreet.org/events).

## Support

If you encounter issues:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review the console logs: `docker logs -f calendar-aggregator`
3. Open an issue on GitHub with:
   - Error message
   - Website URL you're scraping
   - Relevant log output

## Roadmap

- [ ] Web UI for configuration
- [ ] Support for recurring events
- [ ] Email notifications for new events
- [ ] Multiple calendar source support
- [ ] Event category/tag filtering
- [ ] CalDAV server integration
- [ ] Prometheus metrics endpoint

---

**Made with ❤️ for community event calendars**