#!/usr/bin/env python3
"""
ICS Calendar Aggregator
Scrapes event pages, downloads individual .ics files, and merges into single calendar
"""

import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import sqlite3
import os
from pathlib import Path
import hashlib

# Configuration
EVENTS_URL = "https://www.noblesvillemainstreet.org/events"
OUTPUT_ICS = "merged_calendar.ics"
DB_FILE = "calendar_cache.db"
# DB_FILE = "calendar_cache.sqlite"
CACHE_DURATION_HOURS = 6

class CalendarAggregator:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; CalendarAggregator/1.0)'
        })
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for tracking processed events"""
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                uid TEXT PRIMARY KEY,
                url TEXT,
                last_updated TIMESTAMP,
                ics_hash TEXT
            )
        ''')
        self.conn.commit()
    
    def get_event_links(self):
        """Scrape the events page to find all event URLs"""
        print(f"Fetching events page: {EVENTS_URL}")
        response = self.session.get(EVENTS_URL)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all event links - adjust selector based on actual HTML structure
        # Common Squarespace patterns:
        event_links = []
        
        # Try multiple selectors
        selectors = [
            # 'a[href*="/events-calendar/"]',
            # 'a[href*="/events/"]',
            # '.eventlist-event a',
            # '.event-item a',
            # 'article a[href*="event"]'
            # '.eventlist-event a.eventlist-title-link[href*="/events/"]',
            '.eventlist-event--upcoming a.eventlist-title-link[href*="/events/"]',
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            if links:
                for link in links:
                    href = link.get('href')
                    if href:
                        # Make absolute URL
                        if href.startswith('/'):
                            href = f"https://www.noblesvillemainstreet.org{href}"
                        if 'event' in href.lower() and href not in event_links:
                            event_links.append(href)
        
        print(f"Found {len(event_links)} event links")
        return event_links
    
    def download_ics(self, event_url):
        """Download .ics file for a specific event"""
        # Try common ICS URL patterns
        ics_urls = [
            # f"{event_url}?format=ics",
            # f"{event_url.rstrip('/')}.ics",
            # event_url.replace('/events/', '/events/').rstrip('/') + '?format=ics',
            f"{event_url}?format=ical",
            event_url.replace('/events/', '/events/').rstrip('/') + '?format=ical',
        ]
        
        for ics_url in ics_urls:
            try:
                print(f"  Trying: {ics_url}")
                response = self.session.get(ics_url, timeout=10)
                
                # Check if response is actually ICS content
                if response.status_code == 200 and 'BEGIN:VCALENDAR' in response.text:
                    print(f"  ✓ Downloaded ICS from {ics_url}")
                    return response.text
            except Exception as e:
                print(f"  ✗ Failed: {e}")
                continue
        
        return None
    
    def parse_ics(self, ics_content):
        """Parse ICS content and extract event"""
        try:
            cal = Calendar.from_ical(ics_content)
            events = []
            
            for component in cal.walk():
                if component.name == "VEVENT":
                    events.append(component)
            
            return events
        except Exception as e:
            print(f"  Error parsing ICS: {e}")
            return []
    
    def should_update_event(self, uid, ics_hash):
        """Check if event needs updating based on cache"""
        self.cursor.execute(
            'SELECT ics_hash, last_updated FROM events WHERE uid = ?',
            (uid,)
        )
        result = self.cursor.fetchone()
        
        if not result:
            return True  # New event
        
        stored_hash, last_updated = result
        
        # Check if content changed
        if stored_hash != ics_hash:
            return True
        
        # Check if cache expired
        last_updated_dt = datetime.fromisoformat(last_updated)
        if datetime.now() - last_updated_dt > timedelta(hours=CACHE_DURATION_HOURS):
            return True
        
        return False
    
    def merge_calendars(self):
        """Main function to aggregate all calendars"""
        # Create new calendar
        merged_cal = Calendar()
        merged_cal.add('prodid', '-//Calendar Aggregator//Noblesville Events//EN')
        merged_cal.add('version', '2.0')
        merged_cal.add('x-wr-calname', 'Noblesville Main Street Events')
        merged_cal.add('x-wr-caldesc', 'Aggregated events from Noblesville Main Street website')
        
        # Get all event URLs
        event_urls = self.get_event_links()
        
        events_added = 0
        events_skipped = 0
        
        for event_url in event_urls:
            print(f"\nProcessing: {event_url}")
            
            # Download ICS
            ics_content = self.download_ics(event_url)
            if not ics_content:
                print("  ✗ Could not download ICS")
                continue
            
            # Calculate hash for change detection
            ics_hash = hashlib.md5(ics_content.encode()).hexdigest()
            
            # Parse events
            events = self.parse_ics(ics_content)
            
            for event in events:
                uid = str(event.get('uid', ''))
                
                # Check if we should update this event
                if not self.should_update_event(uid, ics_hash):
                    print(f"  ↷ Skipped (cached): {event.get('summary', 'Untitled')}")
                    events_skipped += 1
                    
                    # Still add to merged calendar (load from cache or re-add)
                    merged_cal.add_component(event)
                    continue
                
                # Add event to merged calendar
                merged_cal.add_component(event)
                events_added += 1
                
                # Update database
                self.cursor.execute('''
                    INSERT OR REPLACE INTO events (uid, url, last_updated, ics_hash)
                    VALUES (?, ?, ?, ?)
                ''', (uid, event_url, datetime.now().isoformat(), ics_hash))
                
                print(f"  ✓ Added: {event.get('summary', 'Untitled')}")
        
        self.conn.commit()
        
        # Write merged calendar
        with open(OUTPUT_ICS, 'wb') as f:
            f.write(merged_cal.to_ical())
        
        print(f"\n{'='*50}")
        print(f"✓ Merged calendar saved to: {OUTPUT_ICS}")
        print(f"  Events added/updated: {events_added}")
        print(f"  Events skipped (cached): {events_skipped}")
        print(f"  Total events in calendar: {events_added + events_skipped}")
        
        return OUTPUT_ICS
    
    def __del__(self):
        """Cleanup database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()

def main():
    aggregator = CalendarAggregator()
    output_file = aggregator.merge_calendars()
    
    # Print subscription info
    print(f"\nTo subscribe to this calendar:")
    print(f"1. Serve '{output_file}' via HTTP")
    print(f"2. Add the HTTP URL to your calendar app")
    print(f"3. Set up this script to run periodically (cron/systemd timer)")

if __name__ == "__main__":
    main()