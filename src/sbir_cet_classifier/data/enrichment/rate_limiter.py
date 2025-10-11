"""Rate limiting and circuit breaker implementations for SAM.gov API."""

import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RateLimiter:
    """Rate limiter to control API request frequency."""
    
    def __init__(self, requests_per_minute: int):
        """Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute  # Seconds between requests
        self.last_request_time: Optional[float] = None
    
    def can_make_request(self) -> bool:
        """Check if a request can be made now.
        
        Returns:
            True if request is allowed, False if rate limited
        """
        if self.last_request_time is None:
            return True
        
        time_since_last = time.time() - self.last_request_time
        return time_since_last >= self.min_interval
    
    def record_request(self) -> None:
        """Record that a request was made."""
        self.last_request_time = time.time()
    
    def get_wait_time(self) -> float:
        """Get time to wait before next request is allowed.
        
        Returns:
            Seconds to wait, or 0 if request can be made immediately
        """
        if self.can_make_request():
            return 0.0
        
        time_since_last = time.time() - self.last_request_time
        return self.min_interval - time_since_last


class CircuitBreaker:
    """Circuit breaker to handle API failures gracefully."""
    
    def __init__(self, failure_threshold: int, recovery_timeout: int):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        self.last_failure_time: Optional[datetime] = None
    
    def can_make_request(self) -> bool:
        """Check if a request can be made based on circuit state.
        
        Returns:
            True if request is allowed, False if circuit is open
        """
        if self.state == CircuitBreakerState.CLOSED:
            return True
        
        if self.state == CircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if (self.last_failure_time and 
                datetime.now() - self.last_failure_time >= timedelta(seconds=self.recovery_timeout)):
                self.state = CircuitBreakerState.HALF_OPEN
                return True
            return False
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    def record_success(self) -> None:
        """Record a successful request."""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
        self.last_failure_time = None
    
    def record_failure(self) -> None:
        """Record a failed request."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Failure in half-open state reopens the circuit
            self.state = CircuitBreakerState.OPEN
