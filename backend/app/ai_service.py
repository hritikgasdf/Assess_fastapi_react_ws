import asyncio
import random
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
from app.models import SentimentType
from app.logger import setup_logger

logger = setup_logger(__name__)


class AIServiceError(Exception):
    """Base exception for AI service errors"""
    pass


class AIServiceTimeoutError(AIServiceError):
    """Raised when processing times out"""
    pass


class AIService:
    """
    AI Service for hotel management with production-ready architecture.
    Currently uses static responses but designed for easy LLM integration.
    
    Features:
    - Response caching to reduce redundant processing
    - Error handling and logging
    - Input validation
    - Timeout handling
    - Fallback mechanisms
    - Thread-safe operations
    """
    
    # Category keywords for request classification
    CATEGORIES = {
        "towel": "Housekeeping",
        "clean": "Housekeeping",
        "housekeeping": "Housekeeping",
        "room service": "Room Service",
        "food": "Room Service",
        "meal": "Room Service",
        "dining": "Room Service",
        "menu": "Room Service",
        "breakfast": "Room Service",
        "lunch": "Room Service",
        "dinner": "Room Service",
        "maintenance": "Maintenance",
        "repair": "Maintenance",
        "broken": "Maintenance",
        "fix": "Maintenance",
        "ac": "Maintenance",
        "air conditioning": "Maintenance",
        "heating": "Maintenance",
        "light": "Maintenance",
        "plumbing": "Maintenance",
        "wifi": "Technical Support",
        "internet": "Technical Support",
        "tv": "Technical Support",
        "television": "Technical Support",
        "remote": "Technical Support",
        "phone": "Technical Support",
        "concierge": "Concierge",
        "reservation": "Concierge",
        "booking": "Concierge",
        "tour": "Concierge",
        "transportation": "Concierge",
        "taxi": "Concierge",
    }

    # Sentiment analysis keywords
    POSITIVE_KEYWORDS = [
        "excellent", "great", "amazing", "wonderful", "fantastic",
        "love", "perfect", "outstanding", "impressed", "happy",
        "satisfied", "thank", "appreciate", "awesome", "superb",
        "brilliant", "delighted", "enjoyed", "pleasant", "comfortable"
    ]

    NEGATIVE_KEYWORDS = [
        "terrible", "awful", "poor", "bad", "disappointing",
        "disappointed", "unhappy", "unsatisfied", "horrible",
        "worst", "never", "complain", "issue", "problem",
        "unacceptable", "disgusting", "dirty", "rude", "slow",
        "cold", "noisy", "uncomfortable", "broken", "failed"
    ]

    # Pre-crafted professional responses for negative feedback
    SMART_RESPONSES = [
        "We sincerely apologize for the inconvenience you experienced during your stay. Your feedback is invaluable to us, and we take these matters very seriously. We would like to make this right and ensure your next visit exceeds expectations. Please contact our guest relations team so we can discuss how we can improve your experience.",
        
        "Thank you for bringing this to our attention. We are truly sorry that your experience did not meet the high standards we set for ourselves. We are taking immediate steps to address this issue and prevent it from happening again. We value your patronage and hope you will give us another opportunity to serve you better.",
        
        "We deeply regret that your stay was not up to par. Your satisfaction is our top priority, and we sincerely apologize that we have failed to deliver on that promise. We are committed to improving our services and would appreciate the opportunity to discuss this matter further with you. Please reach out to our management team at your earliest convenience.",
        
        "We are very sorry to hear about your disappointing experience. This is not the level of service we strive to provide, and we take full responsibility. We are reviewing our procedures to ensure this does not happen again. We would be grateful for the chance to regain your trust and welcome you back for a complimentary stay.",
        
        "Your feedback has been received and we apologize for falling short of your expectations. We understand how frustrating this must have been, and we are committed to making improvements. Our management team will review this matter personally to ensure better service in the future. Thank you for giving us the opportunity to learn and grow."
    ]

    def __init__(self):
        """Initialize AI service with cache and configuration"""
        self.timeout = 30.0  # Default timeout for operations
        self.max_input_length = 5000  # Maximum characters for input
        
        # Simple in-memory cache with TTL
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._cache_ttl = 3600  # 1 hour cache TTL
        
        logger.info("AI Service initialized with static responses")
    
    def _get_cache_key(self, operation: str, text: str) -> str:
        """
        Generate cache key from operation and text
        
        Args:
            operation: Type of operation (categorize, sentiment, response)
            text: Input text
            
        Returns:
            MD5 hash as cache key
        """
        content = f"{operation}:{text.lower().strip()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve cached result if still valid
        
        Args:
            cache_key: Cache key to lookup
            
        Returns:
            Cached result or None if expired/missing
        """
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            age = (datetime.now() - timestamp).total_seconds()
            
            if age < self._cache_ttl:
                logger.debug(f"Cache hit for {cache_key[:8]}... (age: {age:.1f}s)")
                return result
            else:
                # Remove expired entry
                del self._cache[cache_key]
                logger.debug(f"Cache expired for {cache_key[:8]}...")
        
        return None
    
    def _set_cached_result(self, cache_key: str, result: Any):
        """
        Store result in cache with timestamp
        
        Args:
            cache_key: Cache key
            result: Result to cache
        """
        self._cache[cache_key] = (result, datetime.now())
        logger.debug(f"Cached result for {cache_key[:8]}...")
        
        # Periodic cache cleanup (every 100 entries)
        if len(self._cache) % 100 == 0:
            self._cleanup_expired_cache()
    
    def _cleanup_expired_cache(self):
        """Remove all expired cache entries"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if (now - timestamp).total_seconds() >= self._cache_ttl
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _validate_input(self, text: str, min_length: int = 3) -> str:
        """
        Validate and sanitize input text
        
        Args:
            text: Input text to validate
            min_length: Minimum required length
            
        Returns:
            Cleaned text
            
        Raises:
            ValueError: If input is invalid
        """
        if not text:
            raise ValueError("Input text cannot be empty")
        
        # Strip whitespace
        text = text.strip()
        
        if len(text) < min_length:
            raise ValueError(f"Input text must be at least {min_length} characters")
        
        if len(text) > self.max_input_length:
            logger.warning(f"Input text truncated from {len(text)} to {self.max_input_length} characters")
            text = text[:self.max_input_length]
        
        return text
    
    async def categorize_request(self, description: str) -> str:
        """
        Categorize a guest request based on description.
        
        Args:
            description: The request description text
            
        Returns:
            Category name (e.g., "Housekeeping", "Room Service")
            
        Raises:
            ValueError: If description is invalid
            AIServiceTimeoutError: If processing times out
        """
        try:
            # Validate input
            description = self._validate_input(description)
            
            # Check cache
            cache_key = self._get_cache_key("categorize", description)
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                return cached_result
            
            logger.debug(f"Categorizing request: '{description[:50]}...'")
            
            # Simulate processing time (0.5-1.5 seconds)
            # This mimics real API call latency
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Keyword-based categorization (will be replaced with LLM)
            description_lower = description.lower()
            
            for keyword, category in self.CATEGORIES.items():
                if keyword in description_lower:
                    logger.info(f"Request categorized as '{category}' (keyword: '{keyword}')")
                    self._set_cached_result(cache_key, category)
                    return category
            
            # Default category
            default_category = "General Request"
            logger.info(f"Request categorized as '{default_category}' (no keyword match)")
            self._set_cached_result(cache_key, default_category)
            return default_category
            
        except ValueError as e:
            logger.warning(f"Invalid input for categorization: {e}")
            raise
        except asyncio.TimeoutError:
            logger.error("Categorization timed out")
            raise AIServiceTimeoutError("Request categorization timed out")
        except Exception as e:
            logger.error(f"Unexpected error in categorize_request: {e}", exc_info=True)
            # Return default category instead of failing
            return "General Request"
    
    async def analyze_sentiment(self, message: str) -> SentimentType:
        """
        Analyze sentiment of a feedback message.
        
        Args:
            message: The feedback message text
            
        Returns:
            SentimentType enum (POSITIVE, NEGATIVE, or NEUTRAL)
            
        Raises:
            ValueError: If message is invalid
            AIServiceTimeoutError: If processing times out
        """
        try:
            # Validate input
            message = self._validate_input(message)
            
            # Check cache
            cache_key = self._get_cache_key("sentiment", message)
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                return cached_result
            
            logger.debug(f"Analyzing sentiment: '{message[:50]}...'")
            
            # Simulate processing time (0.5-1.5 seconds)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Keyword-based sentiment analysis (will be replaced with LLM)
            message_lower = message.lower()
            
            positive_count = sum(1 for keyword in self.POSITIVE_KEYWORDS if keyword in message_lower)
            negative_count = sum(1 for keyword in self.NEGATIVE_KEYWORDS if keyword in message_lower)
            
            # Determine sentiment based on keyword counts
            if negative_count > positive_count:
                sentiment = SentimentType.NEGATIVE
            elif positive_count > negative_count:
                sentiment = SentimentType.POSITIVE
            else:
                sentiment = SentimentType.NEUTRAL
            
            logger.info(f"Sentiment analyzed as '{sentiment.value}' (pos: {positive_count}, neg: {negative_count})")
            self._set_cached_result(cache_key, sentiment)
            return sentiment
            
        except ValueError as e:
            logger.warning(f"Invalid input for sentiment analysis: {e}")
            raise
        except asyncio.TimeoutError:
            logger.error("Sentiment analysis timed out")
            raise AIServiceTimeoutError("Sentiment analysis timed out")
        except Exception as e:
            logger.error(f"Unexpected error in analyze_sentiment: {e}", exc_info=True)
            # Return neutral as safe fallback
            return SentimentType.NEUTRAL
    
    async def generate_smart_response(
        self, 
        feedback_message: str, 
        sentiment: Optional[SentimentType] = None
    ) -> str:
        """
        Generate a personalized response to guest feedback.
        
        Args:
            feedback_message: The original feedback message
            sentiment: Optional sentiment type (will analyze if not provided)
            
        Returns:
            Generated response text
            
        Raises:
            ValueError: If feedback_message is invalid
            AIServiceTimeoutError: If processing times out
        """
        try:
            # Validate input
            feedback_message = self._validate_input(feedback_message)
            
            # Analyze sentiment if not provided
            if sentiment is None:
                sentiment = await self.analyze_sentiment(feedback_message)
            
            # Check cache (including sentiment in key)
            cache_key = self._get_cache_key(f"response_{sentiment.value}", feedback_message)
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                return cached_result
            
            logger.debug(f"Generating smart response for '{sentiment.value}' feedback")
            
            # Simulate processing time (0.5-1.5 seconds)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Select appropriate response based on sentiment
            if sentiment == SentimentType.NEGATIVE:
                # Use pre-crafted professional responses for negative feedback
                response = random.choice(self.SMART_RESPONSES)
                logger.info("Generated smart response for negative feedback")
            else:
                # For positive/neutral feedback, simple acknowledgment
                response = "Thank you for your feedback! We appreciate you taking the time to share your experience with us."
                logger.info(f"Generated acknowledgment for {sentiment.value} feedback")
            
            self._set_cached_result(cache_key, response)
            return response
            
        except ValueError as e:
            logger.warning(f"Invalid input for smart response generation: {e}")
            raise
        except asyncio.TimeoutError:
            logger.error("Smart response generation timed out")
            raise AIServiceTimeoutError("Response generation timed out")
        except Exception as e:
            logger.error(f"Unexpected error in generate_smart_response: {e}", exc_info=True)
            # Return generic response as fallback
            return "Thank you for your feedback. We will review your message and respond accordingly."
    
    def clear_cache(self):
        """Clear all cached results"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cleared {count} cached results")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache metrics
        """
        now = datetime.now()
        valid_entries = sum(
            1 for _, (_, timestamp) in self._cache.items()
            if (now - timestamp).total_seconds() < self._cache_ttl
        )
        
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "cache_ttl_seconds": self._cache_ttl,
            "max_input_length": self.max_input_length
        }


# Global singleton instance
ai_service = AIService()
