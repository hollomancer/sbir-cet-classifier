"""Tests for rate limiting and circuit breaker functionality."""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from sbir_cet_classifier.data.enrichment.rate_limiter import RateLimiter, CircuitBreaker, CircuitBreakerState


class TestRateLimiter:
    """Test cases for rate limiting functionality."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly."""
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.requests_per_minute == 60
        assert limiter.min_interval == 1.0  # 60 seconds / 60 requests
    
    def test_rate_limiter_allows_request_initially(self):
        """Test rate limiter allows first request immediately."""
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.can_make_request() is True
    
    def test_rate_limiter_enforces_minimum_interval(self):
        """Test rate limiter enforces minimum interval between requests."""
        limiter = RateLimiter(requests_per_minute=60)  # 1 request per second
        
        # First request should be allowed
        limiter.record_request()
        
        # Immediate second request should be blocked
        assert limiter.can_make_request() is False
    
    def test_rate_limiter_allows_request_after_interval(self):
        """Test rate limiter allows request after sufficient time has passed."""
        limiter = RateLimiter(requests_per_minute=3600)  # Very high rate for testing
        
        limiter.record_request()
        time.sleep(0.1)  # Small delay
        
        assert limiter.can_make_request() is True
    
    def test_rate_limiter_wait_time_calculation(self):
        """Test rate limiter calculates correct wait time."""
        limiter = RateLimiter(requests_per_minute=60)
        
        limiter.record_request()
        wait_time = limiter.get_wait_time()
        
        assert 0 < wait_time <= 1.0


class TestCircuitBreaker:
    """Test cases for circuit breaker functionality."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initializes in closed state."""
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failure_count == 0
    
    def test_circuit_breaker_allows_request_when_closed(self):
        """Test circuit breaker allows requests when closed."""
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        assert breaker.can_make_request() is True
    
    def test_circuit_breaker_records_success(self):
        """Test circuit breaker resets failure count on success."""
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        
        # Record some failures
        for _ in range(3):
            breaker.record_failure()
        
        assert breaker.failure_count == 3
        
        # Record success should reset count
        breaker.record_success()
        assert breaker.failure_count == 0
    
    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold reached."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # Record failures up to threshold
        for _ in range(3):
            breaker.record_failure()
        
        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.can_make_request() is False
    
    def test_circuit_breaker_transitions_to_half_open(self):
        """Test circuit breaker transitions to half-open after timeout."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)  # Short timeout for testing
        
        # Open the circuit
        for _ in range(3):
            breaker.record_failure()
        
        assert breaker.state == CircuitBreakerState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Should transition to half-open
        assert breaker.can_make_request() is True
        assert breaker.state == CircuitBreakerState.HALF_OPEN
    
    def test_circuit_breaker_closes_on_success_in_half_open(self):
        """Test circuit breaker closes on success when half-open."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        
        # Open the circuit
        for _ in range(3):
            breaker.record_failure()
        
        # Wait and transition to half-open
        time.sleep(0.2)
        breaker.can_make_request()  # Triggers transition to half-open
        
        # Success should close the circuit
        breaker.record_success()
        assert breaker.state == CircuitBreakerState.CLOSED
    
    def test_circuit_breaker_reopens_on_failure_in_half_open(self):
        """Test circuit breaker reopens on failure when half-open."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        
        # Open the circuit
        for _ in range(3):
            breaker.record_failure()
        
        # Wait and transition to half-open
        time.sleep(0.2)
        breaker.can_make_request()  # Triggers transition to half-open
        
        # Failure should reopen the circuit
        breaker.record_failure()
        assert breaker.state == CircuitBreakerState.OPEN


class TestIntegratedRateLimitingAndCircuitBreaker:
    """Test cases for integrated rate limiting and circuit breaker functionality."""
    
    def test_combined_functionality(self):
        """Test rate limiter and circuit breaker work together."""
        limiter = RateLimiter(requests_per_minute=60)
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # Both should allow initial request
        assert limiter.can_make_request() is True
        assert breaker.can_make_request() is True
        
        # Record request and failure
        limiter.record_request()
        breaker.record_failure()
        
        # Rate limiter should block immediate next request
        assert limiter.can_make_request() is False
        # Circuit breaker should still allow (not at threshold yet)
        assert breaker.can_make_request() is True
