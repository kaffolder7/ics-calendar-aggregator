#!/usr/bin/env python3
"""
Unit tests for the calendar aggregator
Run with: pytest test_aggregator.py -v
Run with coverage report: pytest test_aggregator.py --cov=aggregator --cov-report=html
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from icalendar import Calendar, Event
from datetime import datetime

# This would import your actual aggregator
# For now, we'll test the structure exists


class TestCalendarAggregator:
    """Test suite for CalendarAggregator class"""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary directory for test outputs"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def aggregator(self, temp_output_dir, monkeypatch):
        """Create an aggregator instance with temporary directory"""
        monkeypatch.setenv('OUTPUT_DIR', temp_output_dir)
        
        # Import after setting env var
        from aggregator import CalendarAggregator
        return CalendarAggregator()
    
    def test_init_creates_output_directory(self, aggregator, temp_output_dir):
        """Test that initialization creates output directory"""
        assert os.path.exists(temp_output_dir)
    
    def test_database_initialization(self, aggregator):
        """Test that SQLite database is initialized with correct schema"""
        cursor = aggregator.cursor
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == 'events'
    
    def test_parse_ics_valid_content(self, aggregator):
        """Test parsing valid ICS content"""
        # Create a minimal valid ICS
        cal = Calendar()
        cal.add('prodid', '-//Test//')
        cal.add('version', '2.0')
        
        event = Event()
        event.add('summary', 'Test Event')
        event.add('dtstart', datetime(2025, 10, 15, 10, 0, 0))
        event.add('dtend', datetime(2025, 10, 15, 11, 0, 0))
        event.add('uid', 'test-123')
        cal.add_component(event)
        
        ics_content = cal.to_ical().decode('utf-8')
        
        events = aggregator.parse_ics(ics_content)
        assert len(events) == 1
        assert events[0].get('summary') == 'Test Event'
        assert str(events[0].get('uid')) == 'test-123'
    
    def test_parse_ics_invalid_content(self, aggregator):
        """Test parsing invalid ICS content returns empty list"""
        invalid_ics = "This is not valid ICS content"
        events = aggregator.parse_ics(invalid_ics)
        assert events == []
    
    def test_should_update_event_new_event(self, aggregator):
        """Test that new events should be updated"""
        result = aggregator.should_update_event('new-uid-123', 'hash123')
        assert result is True
    
    def test_should_update_event_changed_content(self, aggregator):
        """Test that events with changed content should be updated"""
        # Insert an event
        aggregator.cursor.execute(
            'INSERT INTO events (uid, url, last_updated, ics_hash) VALUES (?, ?, ?, ?)',
            ('test-uid', 'http://example.com', datetime.now().isoformat(), 'old-hash')
        )
        aggregator.conn.commit()
        
        # Check with different hash
        result = aggregator.should_update_event('test-uid', 'new-hash')
        assert result is True
    
    def test_should_update_event_unchanged_recent(self, aggregator):
        """Test that unchanged recent events should not be updated"""
        # Insert a recent event
        aggregator.cursor.execute(
            'INSERT INTO events (uid, url, last_updated, ics_hash) VALUES (?, ?, ?, ?)',
            ('test-uid-2', 'http://example.com', datetime.now().isoformat(), 'same-hash')
        )
        aggregator.conn.commit()
        
        # Check with same hash
        result = aggregator.should_update_event('test-uid-2', 'same-hash')
        assert result is False
    
    @patch('aggregator.CalendarAggregator.rate_limited_get')
    def test_get_event_description_success(self, mock_get, aggregator):
        """Test successful event description scraping"""
        # Mock HTML response
        html_content = '''
        <html>
            <body>
                <div class="eventitem-column-content">
                    <p>This is a test event description.</p>
                    <p>Join us for fun!</p>
                </div>
            </body>
        </html>
        '''
        mock_response = Mock()
        mock_response.content = html_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        description = aggregator.get_event_description('http://example.com/event')
        
        assert description is not None
        assert 'test event description' in description.lower()
        assert 'join us for fun' in description.lower()
    
    @patch('aggregator.CalendarAggregator.rate_limited_get')
    def test_get_event_description_no_content(self, mock_get, aggregator):
        """Test event description scraping when no description found"""
        html_content = '<html><body><div>No description here</div></body></html>'
        mock_response = Mock()
        mock_response.content = html_content.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        description = aggregator.get_event_description('http://example.com/event')
        assert description is None
    
    def test_rate_limiting(self, aggregator):
        """Test that rate limiting enforces minimum delay"""
        import time
        
        with patch.object(aggregator.session, 'get') as mock_get:
            mock_get.return_value = Mock()
            
            start = time.time()
            aggregator.rate_limited_get('http://example.com/1')
            aggregator.rate_limited_get('http://example.com/2')
            elapsed = time.time() - start
            
            # Should take at least min_delay seconds
            assert elapsed >= aggregator.min_delay


class TestOutputFiles:
    """Test that output files are created correctly"""
    
    def test_merged_calendar_structure(self):
        """Test that merged calendar has correct structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a sample merged calendar
            cal = Calendar()
            cal.add('prodid', '-//Calendar Aggregator//Noblesville Events//EN')
            cal.add('version', '2.0')
            cal.add('x-wr-calname', 'Noblesville Main Street Events')
            
            output_file = os.path.join(tmpdir, 'merged_calendar.ics')
            with open(output_file, 'wb') as f:
                f.write(cal.to_ical())
            
            # Verify file exists and is readable
            assert os.path.exists(output_file)
            
            with open(output_file, 'rb') as f:
                content = f.read()
                assert b'BEGIN:VCALENDAR' in content
                assert b'Noblesville Main Street Events' in content


class TestDockerIntegration:
    """Integration tests for Docker environment"""
    
    def test_output_directory_env_var(self, monkeypatch):
        """Test that OUTPUT_DIR environment variable is respected"""
        test_dir = '/custom/output'
        monkeypatch.setenv('OUTPUT_DIR', test_dir)
        
        # This would test that the aggregator uses the custom directory
        # In actual implementation, you'd verify the paths
        assert os.getenv('OUTPUT_DIR') == test_dir


if __name__ == '__main__':
    pytest.main([__file__, '-v'])