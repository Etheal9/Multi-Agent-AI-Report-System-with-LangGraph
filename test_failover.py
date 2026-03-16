import pytest
import os
from unittest.mock import patch, MagicMock
from groq_client import ask_groq

def test_groq_failover_to_gemini():
    """
    Test that if Groq fails (e.g. rate limit 429), the wrap catches the error
    and successfully redirects the generation to Gemini.
    """
    # Simulate a Groq API failure
    from groq import GroqError
    
    with patch("groq_client._get_client") as mock_groq_client:
        # Mock the Groq client to raise an exception when called
        mock_instance = MagicMock()
        mock_instance.chat.completions.create.side_effect = Exception("HTTP 429: Too Many Requests")
        mock_groq_client.return_value = mock_instance
        
        with patch("groq_client._call_gemini_fallback") as mock_gemini:
            # Mock the Gemini fallback to return a success message
            mock_gemini.return_value = "This is a Gemini Fallback Response."
            
            response = ask_groq("Tell me a joke")
            
            # Assert that the Gemini fallback was called because Groq failed
            mock_gemini.assert_called_once()
            assert response == "This is a Gemini Fallback Response."

def test_groq_success_no_fallback():
    """
    Test that if Groq succeeds, Gemini is NEVER called.
    """
    with patch("groq_client._get_client") as mock_groq_client:
        mock_instance = MagicMock()
        
        # Mock a successful Groq response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a successful Groq response."
        mock_instance.chat.completions.create.return_value = mock_response
        
        mock_groq_client.return_value = mock_instance
        
        with patch("groq_client._call_gemini_fallback") as mock_gemini:
            response = ask_groq("Tell me a joke")
            
            # Assert Gemini was NOT called
            mock_gemini.assert_not_called()
            assert response == "This is a successful Groq response."
