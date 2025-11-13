"""
Rate limiting middleware for API protection.
"""
import time
from typing import Dict, Tuple
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware to prevent API abuse.
    
    Implements sliding window rate limiting per IP address.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        """
        Initialize rate limiter.
        
        Args:
            app: FastAPI application
            requests_per_minute: Max requests per minute per IP
            requests_per_hour: Max requests per hour per IP
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # Storage: {ip: (minute_requests, hour_requests)}
        self.request_times: Dict[str, Tuple[deque, deque]] = defaultdict(
            lambda: (deque(), deque())
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address.
        
        Supports X-Forwarded-For header from proxies (Render uses this).
        """
        # Try X-Forwarded-For first (from proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Get first IP in chain
            return forwarded.split(",")[0].strip()
        
        # Try X-Real-IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct client
        return request.client.host if request.client else "unknown"
    
    def _clean_old_requests(
        self,
        requests_queue: deque,
        time_window: int
    ):
        """
        Remove requests older than time window.
        
        Args:
            requests_queue: Queue of request timestamps
            time_window: Time window in seconds
        """
        current_time = time.time()
        while requests_queue and requests_queue[0] < current_time - time_window:
            requests_queue.popleft()
    
    def _is_rate_limited(self, ip: str) -> Tuple[bool, str]:
        """
        Check if IP is rate limited.
        
        Args:
            ip: Client IP address
        
        Returns:
            Tuple of (is_limited, reason)
        """
        current_time = time.time()
        minute_requests, hour_requests = self.request_times[ip]
        
        # Clean old requests
        self._clean_old_requests(minute_requests, 60)  # 1 minute
        self._clean_old_requests(hour_requests, 3600)  # 1 hour
        
        # Check minute limit
        if len(minute_requests) >= self.requests_per_minute:
            return True, f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
        
        # Check hour limit
        if len(hour_requests) >= self.requests_per_hour:
            return True, f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
        
        # Add current request
        minute_requests.append(current_time)
        hour_requests.append(current_time)
        
        return False, ""
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        is_limited, reason = self._is_rate_limited(client_ip)
        
        if is_limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=reason,
                headers={"Retry-After": "60"}
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        minute_requests, hour_requests = self.request_times[client_ip]
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            self.requests_per_minute - len(minute_requests)
        )
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(
            self.requests_per_hour - len(hour_requests)
        )
        
        return response
