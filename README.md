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
- 🏗️ **CI/CD Pipeline** - Automated builds with GitHub Actions
- 🌍 **Multi-Architecture** - Supports amd64 and arm64 platforms

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

### Environment Variables

You can override configuration via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `UPDATE_INTERVAL` | 3600 | Seconds between calendar updates |
| `USE_NGINX` | false | Set to 'true' when using nginx sidecar |
| `OUTPUT_DIR` | /app/output | Directory for generated files |
| `EVENTS_URL` | (set in code) | Source events page URL |

```yaml
environment:
  - EVENTS_URL=https://example.com/events
  - UPDATE_INTERVAL=3600  # seconds between updates
```

## How It Works

1. **Scrapes Event Listings** - Fetches the main events page and extracts event URLs
2. **Downloads ICS Files** - For each event, downloads the `.ics` file (tries `?format=ical` pattern)
3. **Scrapes Descriptions** - Fetches each event page and extracts description text
4. **Enriches Events** - Adds descriptions and URLs to calendar events<!-- 5. **Filters by Date** - Removes events before today -->
5. **Merges Calendar** - Combines all events into single `.ics` file
6. **Caches Results** - Stores event data to avoid redundant downloads
7. **Serves Calendar** - Makes the merged calendar available via HTTP

## Subscribing to the Calendar

### In Google Calendar
1. Click the **+** next to "Other calendars"
2. Select **From URL**
3. Enter: `http://your-server:8080/merged_calendar.ics` (or `/calendar.ics` if using nginx)
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

### Scheduled Updates

The Docker container runs the aggregator in a loop:

```bash
# Updates every hour by default
while true; do 
  python aggregator.py 
  sleep 3600
done
```

Adjust the sleep interval via `UPDATE_INTERVAL`:
- `1800` = 30 minutes
- `3600` = 1 hour (default)
- `21600` = 6 hours

## CI/CD Pipeline

This project uses GitHub Actions for automated building, testing, and publishing of Docker images.

### Available Image Tags

Images are automatically built and pushed to GitHub Container Registry (ghcr.io):

- `latest` - Latest main branch build
- `main` - Main branch builds
- `develop` - Develop branch builds  
- `v1.0.0` - Specific version tags
- `v1.0` - Minor version tags
- `v1` - Major version tags
- `main-abc1234` - Branch + commit SHA

### Creating a Release

To create a new release with semantic versioning:

```bash
# Tag your commit
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# GitHub Actions will automatically:
# 1. Run tests
# 2. Build multi-arch images (amd64 + arm64)
# 3. Push with version tags: v1.0.0, v1.0, v1, latest
```

### Multi-Architecture Support

The CI/CD pipeline builds images for multiple architectures:
- `linux/amd64` - x86_64 servers, most cloud providers
- `linux/arm64` - ARM64 servers (AWS Graviton, Apple Silicon, Raspberry Pi 4/5)

Pull and run on any supported platform:
```bash
docker pull ghcr.io/kaffolder7/ics-calendar-aggregator:latest
# Docker automatically selects the correct architecture
```

### CI/CD Workflow Triggers

The build pipeline is triggered on:
- **Push to main/develop** - Builds and pushes with branch name tag
- **Pull requests** - Builds but doesn't push (testing only)
- **Tags (v*)** - Creates semantic version tags
- **Manual trigger** - Via GitHub Actions UI

## Monitoring

### Check Service Health

```bash
# Check if calendar file exists
docker exec calendar-aggregator test -f /app/output/merged_calendar.ics && echo "OK"

# View logs
docker logs -f calendar-aggregator

# Check nginx health (if using nginx)
curl http://localhost:8080/health
```

### Healthchecks

Both `docker-compose.yml` configurations include healthchecks:
- Aggregator: Verifies calendar file exists
<!-- - Nginx: Checks server responds and file exists -->
- Nginx: Checks that calendar file exists

## Customization

### Change CSS Selectors

If the event page structure differs, update the selectors in `get_event_description()`:

```python
selectors = [
    '.eventitem-column-content',   # Primary selector
    '.eventlist-description',      # Alternative
    '.sqs-block-html',             # Squarespace content block
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

_Note: By default, the script uses up to 5 parallel workers, automatically reducing to match the number of events if fewer than 5. Setting `MAX_WORKERS` to a fixed number will force the script to always use that many workers, no matter the number of events._

### Modify ICS URL Patterns

Update the patterns tried in `download_ics()`:

```python
ics_urls = [
    f"{event_url}?format=ical",
    f"{event_url}?format=ics",
    f"{event_url.rstrip('/')}.ics",
    # Add patterns based on your site
]
```

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
    '.eventlist-event--upcoming a.eventlist-title-link[href*="/events/"]',
    'a[href*="/events-calendar/"]',
    # Add selectors based on your site's HTML
]
```

### ICS Download Fails

**Problem**: Cannot download `.ics` files

**Solution**: Check the ICS URL pattern. Try accessing an event page manually and look for the download link:

```python
# Update URL patterns in download_ics()
ics_urls = [
    f"{event_url}?format=ical",
    f"{event_url}?format=ics",
    f"{event_url}.ics",
    # Add patterns based on your site
]
```

### Duplicate Events

**Problem**: Events appear multiple times

**Solution**: Clear the cache database:

```bash
docker exec calendar-aggregator rm /app/output/calendar_cache.db
# Or locally:
rm output/calendar_cache.db
```

### Description Not Extracted

**Problem**: Events have no descriptions

**Solution**: Inspect the event page HTML to find the correct selector:

1. Visit an event page in your browser
2. Right-click on the description → **Inspect**
3. Note the CSS class or ID
4. Update the selector in `get_event_description()`

### Rate Limiting

**Problem**: Too many requests too quickly (HTTP 429 errors)

**Solution**: Reduce `MAX_WORKERS` or increase `min_delay`:

```python
MAX_WORKERS = 3  # Slower but more respectful
self.min_delay = 0.5  # 500ms between requests
```

### Container Won't Start

**Problem**: Docker container fails to start

**Solutions**:
- Verify volume permissions: `chmod 755 output/`
- Check port 8080 is not already in use: `netstat -tlnp | grep 8080`
- Review container logs: `docker logs calendar-aggregator`

### Calendar Not Updating

**Problem**: Calendar file doesn't refresh

**Solutions**:
- Check logs: `docker logs -f calendar-aggregator`
- Verify `UPDATE_INTERVAL` is set correctly
- Ensure source website is accessible from container
- Clear cache and restart: `docker-compose restart`

### Image Pull Fails

**Problem**: Cannot pull from GitHub Container Registry

**Solutions**:
- Ensure repository visibility is public, or authenticate:
  ```bash
  echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
  ```
- Verify image name is correct: `ghcr.io/kaffolder7/ics-calendar-aggregator`

## File Structure

```
ics-calendar-aggregator/
├── aggregator.py                         # Main Python script
├── requirements.txt                      # Python dependencies
├── Dockerfile                            # Docker image definition
├── docker-compose.yml                    # Dev/simple Docker Compose config
├── docker-compose.prod.yml               # Production Docker Compose config
├── docker-entrypoint.sh                  # Container entrypoint script
├── nginx.conf                            # Nginx config (for prod mode)
├── test_aggregator.py                    # Unit tests
├── .github/workflows/docker-build.yml    # CI/CD pipeline
├── README.md                             # This file
├── output/
│   ├── merged_calendar.ics              # Generated calendar (created on first run)
│   └── calendar_cache.db                # SQLite cache (created on first run)
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

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest test_aggregator.py -v

# Run with coverage
pytest test_aggregator.py --cov=aggregator
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run aggregator once
python aggregator.py

# Start development server
python -m http.server 8080 --directory output
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `pytest test_aggregator.py`
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Ideas for Contributions
- Support for more event calendar platforms
- Additional calendar output formats (Google Calendar API, CalDAV)
- Web UI for configuration
- Event deduplication improvements
- More filtering options (categories, locations, etc.)
- Enhanced error handling and retry logic
- Prometheus metrics endpoint

## License

MIT License - see [LICENSE](LICENSE) file for details

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
   - Docker/Python version

## Roadmap

- [x] Multi-threaded parallel processing
- [x] Rate limiting to prevent server overload
- [x] CI/CD pipeline with GitHub Actions
- [x] Multi-architecture Docker images
- [ ] Web UI for configuration
- [ ] Support for recurring events
- [ ] Email notifications for new events
- [ ] Multiple calendar source support
- [ ] Event category/tag filtering
- [ ] CalDAV server integration
- [ ] Prometheus metrics endpoint
- [ ] Helm chart for Kubernetes deployment

---

**Made with ❤️ for community event calendars**