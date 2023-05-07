# Unit tests of IntervalTracker

import unittest
import sys
import time

# Assuming VSCode project opened at repo directory
sys.path.insert(0, "./src")

from serial_packets._interval_tracker import IntervalTracker


class TestIntervalTracker(unittest.TestCase):

    def test_interval_tracker(self):
        t= IntervalTracker(0.5)
        self.assertTrue(t.track_packet())
        self.assertFalse(t.track_packet())
        self.assertFalse(t.track_packet())
        time.sleep(0.6)
        self.assertTrue(t.track_packet())
        self.assertFalse(t.track_packet())
        self.assertFalse(t.track_packet())


    

if __name__ == '__main__':
    unittest.main()
