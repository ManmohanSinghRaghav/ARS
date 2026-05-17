#!/usr/bin/env python3
"""
Test suite for paper JSON extraction and parsing.
Tests the robust parser with various LLM output formats.
"""

import json
import sys
sys.path.insert(0, '/Users/suryanshagarwal/ARS/backend')

from app.pipeline.utils import extract_paper_json, extract_json_from_text


def test_case_1_perfect_json():
    """Test: Perfect JSON structure"""
    print("\n" + "="*60)
    print("TEST 1: Perfect JSON Structure")
    print("="*60)
    
    perfect_json = {
        "metadata": {
            "title": "Bio-Inspired Adaptive Control",
            "author": "Research Team",
            "date": "2026-05-02",
            "institution": "GLA Lab"
        },
        "sections": [
            {
                "id": "abs",
                "type": "abstract",
                "title": "Abstract",
                "content": "This paper proposes a novel framework..."
            },
            {
                "id": "intro",
                "type": "content",
                "title": "1. Introduction",
                "content": "The development of cyborg systems..."
            }
        ]
    }
    
    result = extract_paper_json(json.dumps(perfect_json))
    assert result is not None, "Failed to parse perfect JSON"
    assert len(result['sections']) == 2, "Wrong section count"
    print(f"✅ PASSED: Extracted {len(result['sections'])} sections correctly")
    return True


def test_case_2_markdown_wrapped():
    """Test: JSON wrapped in markdown code fence"""
    print("\n" + "="*60)
    print("TEST 2: Markdown-Wrapped JSON")
    print("="*60)
    
    markdown_json = '''
    Here's the compiled paper JSON:
    
    ```json
    {
        "metadata": {
            "title": "Advanced Research",
            "author": "AI Assistant",
            "date": "2026-05-02",
            "institution": "Research Lab"
        },
        "sections": [
            {
                "id": "abs",
                "type": "abstract",
                "title": "Abstract",
                "content": "Comprehensive study of modern AI..."
            },
            {
                "id": "intro",
                "type": "content",
                "title": "1. Introduction",
                "content": "Introduction to the topic..."
            }
        ]
    }
    ```
    '''
    
    result = extract_paper_json(markdown_json)
    assert result is not None, "Failed to parse markdown-wrapped JSON"
    assert result['metadata']['title'] == "Advanced Research"
    print(f"✅ PASSED: Extracted markdown-wrapped JSON with {len(result['sections'])} sections")
    return True


def test_case_3_with_explanation():
    """Test: JSON with surrounding explanation text"""
    print("\n" + "="*60)
    print("TEST 3: JSON with Surrounding Text")
    print("="*60)
    
    with_explanation = '''
    I have compiled the complete research paper. Here's the final JSON structure:
    
    {
        "metadata": {
            "title": "Neuromorphic Computing",
            "author": "ARS System",
            "date": "2026-05-02",
            "institution": "AI Research Center"
        },
        "sections": [
            {
                "id": "abs",
                "type": "abstract",
                "title": "Abstract",
                "content": "This research explores neuromorphic approaches..."
            },
            {
                "id": "rw",
                "type": "content",
                "title": "2. Related Work",
                "content": "Recent advances in the field include..."
            }
        ]
    }
    
    This completes the paper generation pipeline. The JSON has been validated.
    '''
    
    result = extract_paper_json(with_explanation)
    assert result is not None, "Failed to extract JSON from text with explanation"
    assert result['metadata']['institution'] == "AI Research Center"
    print(f"✅ PASSED: Extracted JSON from text with surrounding explanation")
    return True


def test_case_4_long_content():
    """Test: Large content sections (like methodology)"""
    print("\n" + "="*60)
    print("TEST 4: Long Content Sections")
    print("="*60)
    
    long_content = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 50
    
    long_json = {
        "metadata": {
            "title": "Comprehensive Study",
            "author": "Researcher",
            "date": "2026-05-02",
            "institution": "Lab"
        },
        "sections": [
            {
                "id": "intro",
                "type": "content",
                "title": "1. Introduction",
                "content": "Short intro content"
            },
            {
                "id": "meth",
                "type": "content",
                "title": "3. Methodology",
                "content": long_content
            },
            {
                "id": "res",
                "type": "content",
                "title": "4. Results",
                "content": long_content
            }
        ]
    }
    
    result = extract_paper_json(json.dumps(long_json))
    assert result is not None, "Failed to parse JSON with long content"
    assert len(result['sections'][1]['content']) > 2500, "Content was truncated"
    print(f"✅ PASSED: Successfully parsed {len(long_content)} char methodology section")
    return True


def test_case_5_trailing_comma():
    """Test: JSON with trailing commas (common LLM error)"""
    print("\n" + "="*60)
    print("TEST 5: JSON with Trailing Commas")
    print("="*60)
    
    trailing_comma_json = '''
    {
        "metadata": {
            "title": "Paper Title",
            "author": "Author",
            "date": "2026-05-02",
            "institution": "Institution",
        },
        "sections": [
            {
                "id": "abs",
                "type": "abstract",
                "title": "Abstract",
                "content": "Abstract content",
            },
        ],
    }
    '''
    
    result = extract_paper_json(trailing_comma_json)
    assert result is not None, "Failed to parse JSON with trailing commas"
    assert len(result['sections']) == 1
    print(f"✅ PASSED: Successfully handled trailing commas")
    return True


def test_case_6_quote_variations():
    """Test: JSON with single quotes (LLM artifact)"""
    print("\n" + "="*60)
    print("TEST 6: Quote Variations")
    print("="*60)
    
    single_quote_json = """{
        'metadata': {
            'title': 'Paper Title',
            'author': 'Author',
            'date': '2026-05-02',
            'institution': 'Institution'
        },
        'sections': [
            {
                'id': 'abs',
                'type': 'abstract',
                'title': 'Abstract',
                'content': 'Abstract content here'
            }
        ]
    }"""
    
    result = extract_paper_json(single_quote_json)
    assert result is not None, "Failed to parse JSON with single quotes"
    assert result['metadata']['title'] == "Paper Title"
    print(f"✅ PASSED: Successfully converted single quotes to double quotes")
    return True


def test_case_7_escaped_quotes():
    """Test: JSON with escaped quotes in content"""
    print("\n" + "="*60)
    print("TEST 7: Escaped Quotes in Content")
    print("="*60)
    
    escaped_json = {
        "metadata": {
            "title": "Paper with \"Quotes\"",
            "author": "Author",
            "date": "2026-05-02",
            "institution": "Lab"
        },
        "sections": [
            {
                "id": "abs",
                "type": "abstract",
                "title": "Abstract",
                "content": "Content with \"quoted words\" and 'apostrophes'"
            }
        ]
    }
    
    result = extract_paper_json(json.dumps(escaped_json))
    assert result is not None, "Failed to parse JSON with escaped quotes"
    assert '"' in result['metadata']['title']
    print(f"✅ PASSED: Successfully handled escaped quotes")
    return True


def test_case_8_multiple_sections():
    """Test: All 6 typical paper sections"""
    print("\n" + "="*60)
    print("TEST 8: Multiple Sections (Complete Paper)")
    print("="*60)
    
    complete_paper = {
        "metadata": {
            "title": "Complete Research Paper",
            "author": "Research Team",
            "date": "2026-05-02",
            "institution": "University"
        },
        "sections": [
            {
                "id": "abs",
                "type": "abstract",
                "title": "Abstract",
                "content": "Abstract paragraph"
            },
            {
                "id": "intro",
                "type": "content",
                "title": "1. Introduction",
                "content": "Introduction paragraph"
            },
            {
                "id": "rw",
                "type": "content",
                "title": "2. Related Work",
                "content": "Related work paragraph"
            },
            {
                "id": "meth",
                "type": "content",
                "title": "3. Methodology",
                "content": "Methodology paragraph"
            },
            {
                "id": "res",
                "type": "content",
                "title": "4. Results",
                "content": "Results paragraph"
            },
            {
                "id": "concl",
                "type": "content",
                "title": "5. Conclusion",
                "content": "Conclusion paragraph"
            }
        ]
    }
    
    result = extract_paper_json(json.dumps(complete_paper))
    assert result is not None, "Failed to parse complete paper"
    assert len(result['sections']) == 6, f"Wrong section count: {len(result['sections'])}"
    print(f"✅ PASSED: Successfully parsed complete paper with {len(result['sections'])} sections")
    return True


def run_all_tests():
    """Run all test cases"""
    print("\n" + "█"*60)
    print("█ PAPER JSON PARSER TEST SUITE (Professional Grade)")
    print("█"*60)
    
    tests = [
        test_case_1_perfect_json,
        test_case_2_markdown_wrapped,
        test_case_3_with_explanation,
        test_case_4_long_content,
        test_case_5_trailing_comma,
        test_case_6_quote_variations,
        test_case_7_escaped_quotes,
        test_case_8_multiple_sections,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            failed += 1
            print(f"❌ FAILED: {e}")
        except Exception as e:
            failed += 1
            print(f"❌ ERROR: {e}")
    
    # Summary
    print("\n" + "="*60)
    print(f"TEST RESULTS: {passed} PASSED, {failed} FAILED")
    print("="*60)
    
    if failed == 0:
        print("✅ ALL TESTS PASSED - Parser is production-ready!")
        return 0
    else:
        print(f"⚠️  {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
