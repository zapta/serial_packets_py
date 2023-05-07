from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

class IntervalTracker:
    """Tracks time interval between outgoing packets."""
    def __init__(self, time_limit: float):
        self.__time_limit = time_limit
        self.__last_packet_time=0
        
    def track_packet(self) -> bool:
      """Test if more than time_limit passed since last call. 
      """
      prev_time = self.__last_packet_time
      time_now = time.time()
      self.__last_packet_time = time_now
      return (time_now - prev_time) > self.__time_limit
      
        