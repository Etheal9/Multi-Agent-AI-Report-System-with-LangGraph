import pytest
from unittest.mock import patch
from tools import expert_planner_skill, robust_search_skill, critique_skill, report_writer_skill

@patch("tools.ask_groq")
def test_expert_planner_skill(mock_ask_groq):
    mock_ask_groq.return_value = "This is a test plan."
    result = expert_planner_skill.invoke({"topic": "AI in 2025"})
    assert "This is a test plan." in result
    mock_ask_groq.assert_called_once()

@patch("tools.tavily")
@patch("tools.ask_groq")
def test_robust_search_skill(mock_ask_groq, mock_tavily_instance):
    # Mock LLM query generation
    mock_ask_groq.return_value = "query1\nquery2"
    
    # Mock Tavily search results
    mock_tavily_instance.search.return_value = {"results": [{"content": "Result 1", "url": "test.com"}]}
    
    result = robust_search_skill.invoke({"topic": "AI in 2025", "context": "Testing"})
    
    assert "Result 1" in result
    assert "test.com" in result
    mock_ask_groq.assert_called_once()
    assert mock_tavily_instance.search.call_count == 2

@patch("tools.ask_groq")
def test_critique_skill(mock_ask_groq):
    mock_ask_groq.return_value = "This draft needs more citations."
    result = critique_skill.invoke({"draft": "Here is a draft."})
    assert "This draft needs more citations." in result
    mock_ask_groq.assert_called_once()

@patch("tools.ask_groq")
def test_report_writer_skill(mock_ask_groq):
    mock_ask_groq.return_value = "Final robust report."
    result = report_writer_skill.invoke({"topic": "Topic", "plan": "Plan", "gathered_content": "Data"})
    assert "Final robust report." in result
    mock_ask_groq.assert_called_once()

