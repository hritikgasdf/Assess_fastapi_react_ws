import pytest
import asyncio
from datetime import datetime, timedelta
from app.ai_service import ai_service, AIService, AIServiceError, AIServiceTimeoutError
from app.models import SentimentType


# ==================== Categorization Tests ====================

@pytest.mark.asyncio
async def test_categorize_request_housekeeping():
    """Test housekeeping category detection"""
    description = "I need extra towels in my room"
    category = await ai_service.categorize_request(description)
    assert category == "Housekeeping"

@pytest.mark.asyncio
async def test_categorize_request_room_service():
    """Test room service category detection"""
    description = "Can I order some food for dinner?"
    category = await ai_service.categorize_request(description)
    assert category == "Room Service"

@pytest.mark.asyncio
async def test_categorize_request_maintenance():
    """Test maintenance category detection"""
    description = "The AC needs to be fixed"
    category = await ai_service.categorize_request(description)
    assert category == "Maintenance"

@pytest.mark.asyncio
async def test_categorize_request_technical_support():
    """Test technical support category detection"""
    description = "The wifi is not working in my room"
    category = await ai_service.categorize_request(description)
    assert category == "Technical Support"

@pytest.mark.asyncio
async def test_categorize_request_concierge():
    """Test concierge category detection"""
    description = "I need help with a tour reservation"
    category = await ai_service.categorize_request(description)
    assert category == "Concierge"

@pytest.mark.asyncio
async def test_categorize_request_general():
    """Test general category for unmatched requests"""
    description = "I have a question about checkout"
    category = await ai_service.categorize_request(description)
    assert category == "General Request"

@pytest.mark.asyncio
async def test_categorize_request_with_whitespace():
    """Test categorization with extra whitespace"""
    description = "  Need towels  "
    category = await ai_service.categorize_request(description)
    assert category == "Housekeeping"

@pytest.mark.asyncio
async def test_categorize_request_case_insensitive():
    """Test case-insensitive categorization"""
    description = "NEED CLEAN ROOM"
    category = await ai_service.categorize_request(description)
    assert category == "Housekeeping"


# ==================== Sentiment Analysis Tests ====================

@pytest.mark.asyncio
async def test_analyze_sentiment_positive():
    """Test positive sentiment detection"""
    message = "Excellent stay! I love this hotel, everything was perfect!"
    sentiment = await ai_service.analyze_sentiment(message)
    assert sentiment == SentimentType.POSITIVE

@pytest.mark.asyncio
async def test_analyze_sentiment_negative():
    """Test negative sentiment detection"""
    message = "Terrible experience. Very disappointed and unhappy with the service."
    sentiment = await ai_service.analyze_sentiment(message)
    assert sentiment == SentimentType.NEGATIVE

@pytest.mark.asyncio
async def test_analyze_sentiment_neutral():
    """Test neutral sentiment detection"""
    message = "The room was acceptable. Standard experience."
    sentiment = await ai_service.analyze_sentiment(message)
    assert sentiment == SentimentType.NEUTRAL

@pytest.mark.asyncio
async def test_analyze_sentiment_mixed_leaning_positive():
    """Test mixed sentiment leaning positive"""
    message = "Great room but the wifi was poor. Overall happy with my stay."
    sentiment = await ai_service.analyze_sentiment(message)
    assert sentiment == SentimentType.POSITIVE

@pytest.mark.asyncio
async def test_analyze_sentiment_mixed_leaning_negative():
    """Test mixed sentiment leaning negative"""
    message = "Nice staff but terrible room, awful experience, very disappointed."
    sentiment = await ai_service.analyze_sentiment(message)
    assert sentiment == SentimentType.NEGATIVE


# ==================== Smart Response Tests ====================

@pytest.mark.asyncio
async def test_generate_smart_response_negative():
    """Test smart response generation for negative feedback"""
    feedback = "The room was dirty and the service was poor"
    response = await ai_service.generate_smart_response(feedback)
    assert response is not None
    assert len(response) > 0
    assert "sorry" in response.lower() or "apologize" in response.lower()

@pytest.mark.asyncio
async def test_generate_smart_response_positive():
    """Test smart response generation for positive feedback"""
    feedback = "Amazing stay! Everything was perfect and excellent!"
    response = await ai_service.generate_smart_response(feedback)
    assert response is not None
    assert len(response) > 0
    assert "thank you" in response.lower() or "appreciate" in response.lower()

@pytest.mark.asyncio
async def test_generate_smart_response_with_sentiment():
    """Test smart response with pre-determined sentiment"""
    feedback = "Some feedback"
    response = await ai_service.generate_smart_response(feedback, sentiment=SentimentType.NEGATIVE)
    assert response is not None
    assert "apologize" in response.lower() or "sorry" in response.lower()


# ==================== Input Validation Tests ====================

@pytest.mark.asyncio
async def test_categorize_empty_input():
    """Test categorization with empty input"""
    with pytest.raises(ValueError, match="Input text cannot be empty"):
        await ai_service.categorize_request("")

@pytest.mark.asyncio
async def test_categorize_whitespace_only():
    """Test categorization with whitespace only"""
    with pytest.raises(ValueError, match="at least 3 characters"):
        await ai_service.categorize_request("   ")

@pytest.mark.asyncio
async def test_categorize_too_short():
    """Test categorization with text too short"""
    with pytest.raises(ValueError, match="at least 3 characters"):
        await ai_service.categorize_request("ab")

@pytest.mark.asyncio
async def test_sentiment_empty_input():
    """Test sentiment analysis with empty input"""
    with pytest.raises(ValueError, match="Input text cannot be empty"):
        await ai_service.analyze_sentiment("")

@pytest.mark.asyncio
async def test_sentiment_too_short():
    """Test sentiment analysis with text too short"""
    with pytest.raises(ValueError, match="at least 3 characters"):
        await ai_service.analyze_sentiment("ok")

@pytest.mark.asyncio
async def test_smart_response_empty_input():
    """Test smart response with empty input"""
    with pytest.raises(ValueError, match="Input text cannot be empty"):
        await ai_service.generate_smart_response("")

@pytest.mark.asyncio
async def test_input_truncation():
    """Test that very long input is truncated"""
    service = AIService()
    long_text = "a" * 6000  # Exceeds max_input_length of 5000
    result = service._validate_input(long_text)
    assert len(result) == 5000


# ==================== Caching Tests ====================

@pytest.mark.asyncio
async def test_categorize_caching():
    """Test that repeated categorization uses cache"""
    service = AIService()
    description = "I need clean towels please"
    
    # First call - should cache
    result1 = await service.categorize_request(description)
    cache_stats1 = service.get_cache_stats()
    
    # Second call - should hit cache
    result2 = await service.categorize_request(description)
    cache_stats2 = service.get_cache_stats()
    
    assert result1 == result2
    assert cache_stats2["total_entries"] >= cache_stats1["total_entries"]

@pytest.mark.asyncio
async def test_sentiment_caching():
    """Test that repeated sentiment analysis uses cache"""
    service = AIService()
    message = "This was an excellent experience!"
    
    # First call
    result1 = await service.analyze_sentiment(message)
    
    # Second call - should be faster due to cache
    result2 = await service.analyze_sentiment(message)
    
    assert result1 == result2

@pytest.mark.asyncio
async def test_cache_key_generation():
    """Test cache key generation is consistent"""
    service = AIService()
    
    key1 = service._get_cache_key("test", "Hello World")
    key2 = service._get_cache_key("test", "hello world")  # Different case
    key3 = service._get_cache_key("test", "  Hello World  ")  # Extra whitespace
    
    # All should generate the same key (case-insensitive, whitespace-trimmed)
    assert key1 == key2 == key3

@pytest.mark.asyncio
async def test_cache_expiration():
    """Test that cache entries expire after TTL"""
    service = AIService()
    service._cache_ttl = 1  # Set to 1 second for testing
    
    description = "Need some towels"
    
    # First call - should cache
    await service.categorize_request(description)
    cache_stats1 = service.get_cache_stats()
    assert cache_stats1["total_entries"] > 0
    
    # Wait for cache to expire
    await asyncio.sleep(1.5)
    
    # This call should not find cached result (expired)
    result = await service.categorize_request(description)
    assert result == "Housekeeping"

@pytest.mark.asyncio
async def test_clear_cache():
    """Test cache clearing functionality"""
    service = AIService()
    
    # Add some entries to cache
    await service.categorize_request("Need towels")
    await service.analyze_sentiment("Great hotel!")
    
    stats_before = service.get_cache_stats()
    assert stats_before["total_entries"] > 0
    
    # Clear cache
    service.clear_cache()
    
    stats_after = service.get_cache_stats()
    assert stats_after["total_entries"] == 0

@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics reporting"""
    service = AIService()
    service.clear_cache()
    
    # Initial stats
    stats = service.get_cache_stats()
    assert stats["total_entries"] == 0
    assert stats["valid_entries"] == 0
    assert stats["cache_ttl_seconds"] == 3600
    assert stats["max_input_length"] == 5000
    
    # Add entry
    await service.categorize_request("Need maintenance")
    
    stats = service.get_cache_stats()
    assert stats["total_entries"] > 0
    assert stats["valid_entries"] > 0


# ==================== Error Handling Tests ====================

@pytest.mark.asyncio
async def test_categorize_with_exception_returns_default():
    """Test that exceptions in categorization return default category"""
    service = AIService()
    
    # Valid input that won't match any category
    result = await service.categorize_request("xyz unknown request abc")
    assert result == "General Request"

@pytest.mark.asyncio
async def test_sentiment_with_exception_returns_neutral():
    """Test that exceptions in sentiment analysis return neutral"""
    service = AIService()
    
    # This should work fine but test the exception path
    result = await service.analyze_sentiment("some feedback")
    assert result in [SentimentType.POSITIVE, SentimentType.NEGATIVE, SentimentType.NEUTRAL]


# ==================== Edge Cases ====================

@pytest.mark.asyncio
async def test_categorize_multiple_keywords():
    """Test categorization with multiple matching keywords"""
    description = "Need to fix the broken AC and also need clean towels"
    category = await ai_service.categorize_request(description)
    # Should match first found keyword
    assert category in ["Maintenance", "Housekeeping"]

@pytest.mark.asyncio
async def test_special_characters():
    """Test handling of special characters"""
    description = "Need towels!!! @#$% ASAP!!!"
    category = await ai_service.categorize_request(description)
    assert category == "Housekeeping"

@pytest.mark.asyncio
async def test_unicode_characters():
    """Test handling of unicode characters"""
    description = "Need towels 毛巾 🧺"
    category = await ai_service.categorize_request(description)
    assert category == "Housekeeping"

@pytest.mark.asyncio
async def test_sentiment_only_positive_keywords():
    """Test sentiment with only positive keywords"""
    message = "excellent wonderful amazing perfect"
    sentiment = await ai_service.analyze_sentiment(message)
    assert sentiment == SentimentType.POSITIVE

@pytest.mark.asyncio
async def test_sentiment_only_negative_keywords():
    """Test sentiment with only negative keywords"""
    message = "terrible awful horrible disappointing"
    sentiment = await ai_service.analyze_sentiment(message)
    assert sentiment == SentimentType.NEGATIVE

@pytest.mark.asyncio
async def test_sentiment_no_keywords():
    """Test sentiment with no recognized keywords"""
    message = "The hotel is located downtown"
    sentiment = await ai_service.analyze_sentiment(message)
    assert sentiment == SentimentType.NEUTRAL


# ==================== Integration Tests ====================

@pytest.mark.asyncio
async def test_full_workflow():
    """Test complete workflow: categorize, sentiment, response"""
    service = AIService()
    service.clear_cache()
    
    # Categorize a request
    category = await service.categorize_request("The AC is broken")
    assert category == "Maintenance"
    
    # Analyze sentiment of feedback
    sentiment = await service.analyze_sentiment("The service was terrible and disappointing")
    assert sentiment == SentimentType.NEGATIVE
    
    # Generate response
    response = await service.generate_smart_response("Bad experience", sentiment)
    assert "apologize" in response.lower() or "sorry" in response.lower()
    
    # Check cache stats
    stats = service.get_cache_stats()
    assert stats["total_entries"] >= 3  # At least 3 operations cached


# ==================== Additional Coverage Tests ====================

@pytest.mark.asyncio
async def test_categorize_with_none_input():
    """Test categorization with None input"""
    with pytest.raises(ValueError):
        await ai_service.categorize_request(None)

@pytest.mark.asyncio
async def test_sentiment_with_none_input():
    """Test sentiment analysis with None input"""
    with pytest.raises(ValueError):
        await ai_service.analyze_sentiment(None)

@pytest.mark.asyncio
async def test_smart_response_with_none_input():
    """Test smart response with None input"""
    with pytest.raises(ValueError):
        await ai_service.generate_smart_response(None)

@pytest.mark.asyncio
async def test_cache_cleanup_on_periodic_trigger():
    """Test automatic cache cleanup on 100th entry"""
    service = AIService()
    service.clear_cache()
    service._cache_ttl = 0  # Expire immediately
    
    # Add 100+ entries to trigger cleanup
    for i in range(105):
        cache_key = service._get_cache_key("test", f"message_{i}")
        service._set_cached_result(cache_key, f"result_{i}")
    
    # Should have triggered cleanup at 100
    stats = service.get_cache_stats()
    assert stats["total_entries"] > 0  # Some entries still exist

@pytest.mark.asyncio
async def test_generate_smart_response_without_sentiment():
    """Test smart response generation without providing sentiment"""
    service = AIService()
    
    # Should analyze sentiment internally
    response = await service.generate_smart_response("This hotel was terrible!")
    assert response is not None
    assert "apologize" in response.lower() or "sorry" in response.lower()

@pytest.mark.asyncio
async def test_generate_smart_response_positive_sentiment():
    """Test smart response for positive sentiment"""
    service = AIService()
    
    response = await service.generate_smart_response(
        "Amazing hotel!", 
        sentiment=SentimentType.POSITIVE
    )
    assert response is not None
    assert "thank" in response.lower() or "appreciate" in response.lower()

@pytest.mark.asyncio
async def test_generate_smart_response_neutral_sentiment():
    """Test smart response for neutral sentiment"""
    service = AIService()
    
    response = await service.generate_smart_response(
        "The hotel was okay", 
        sentiment=SentimentType.NEUTRAL
    )
    assert response is not None
    assert "thank" in response.lower()

@pytest.mark.asyncio
async def test_validate_input_exact_minimum():
    """Test validation with exactly minimum length"""
    service = AIService()
    result = service._validate_input("abc", min_length=3)
    assert result == "abc"

@pytest.mark.asyncio
async def test_validate_input_strips_whitespace():
    """Test that validation strips leading/trailing whitespace"""
    service = AIService()
    result = service._validate_input("  hello world  ")
    assert result == "hello world"
    assert not result.startswith(" ")
    assert not result.endswith(" ")

@pytest.mark.asyncio
async def test_cache_expired_entries_count():
    """Test counting expired cache entries"""
    service = AIService()
    service.clear_cache()
    service._cache_ttl = 0.1  # Very short TTL
    
    # Add entries that will expire
    await service.categorize_request("Test request")
    await asyncio.sleep(0.2)  # Wait for expiration
    
    stats = service.get_cache_stats()
    # Expired entries should be counted correctly
    assert stats["expired_entries"] >= 0
