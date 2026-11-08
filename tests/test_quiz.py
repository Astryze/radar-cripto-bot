import pytest

from src.quiz_analyzer import analyze_public_quiz, analyze_question


def test_quiz_support_and_citations():
    result = analyze_question("What does a blockchain store?", ["Distributed ledger records", "Weather clouds"], [
        {"url": "https://example.org/material", "official": True,
         "text": "A blockchain stores distributed ledger records across a network."}])
    assert result["probable_answer"] == "Distributed ledger records"
    assert result["evidence"][0]["source"] == "https://example.org/material"
    assert not result["automatic_submission"]


def test_quiz_abstains_without_evidence():
    assert analyze_question("What is blockchain?", ["A", "B"], [])["probable_answer"] is None


def test_quiz_requires_authorization():
    with pytest.raises(ValueError):
        analyze_public_quiz({"questions": []}, [], None)


def test_untrusted_material_does_not_prove_answer():
    result = analyze_question("What is blockchain?", ["Ledger", "Cloud"], [
        {"url": "https://evil.test", "official": False, "text": "Blockchain is definitely a cloud."}])
    assert result["probable_answer"] is None


def test_read_public_question_page(source):
    from unittest.mock import Mock
    client = Mock()
    body = b'<fieldset><legend>What does blockchain store?</legend><label>Ledger records</label><label>Clouds</label></fieldset>'
    client.get.return_value = body, "https://example.org/quiz", "text/html"
    result = analyze_public_quiz({"authorized_public_material": True, "materials": [],
                                 "question_pages": [{"url": "https://example.org/quiz"}]}, [source], client)
    assert result[0]["question"] == "What does blockchain store?"
    assert result[0]["question_source"] == "https://example.org/quiz"
    assert result[0]["automatic_submission"] is False
