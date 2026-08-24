import logging
import random
import time

logger = logging.getLogger(__name__)

class ExponentialBackoff:
    def __init__(self, initial_delay: float = 2.0, max_delay: float = 60.0, factor: float = 2.0, jitter: float = 0.2):
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.factor = factor
        self.jitter = jitter
        self.attempts = 0
        self.current_delay = initial_delay

    def reset(self):
        self.attempts = 0
        self.current_delay = self.initial_delay

    def wait(self):
        delay = self.current_delay
        jitter_val = delay * self.jitter
        actual_delay = delay + random.uniform(-jitter_val, jitter_val)
        
        logger.debug(f"[BACKOFF] Attempt {self.attempts + 1}: Waiting {actual_delay:.2f}s before reconnecting.")
        time.sleep(max(0, actual_delay))
        
        self.attempts += 1
        self.current_delay = min(self.current_delay * self.factor, self.max_delay)
