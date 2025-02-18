"""Tests for the Supadata client."""

import pytest
import requests
from requests import Response

from supadata import (
    Supadata,
    Transcript,
    TranslatedTranscript,
    TranscriptChunk,
    Scrape,
    Map,
    Error,
    CrawlJob,
    CrawlPage,
)

from supadata.errors import SupadataError


@pytest.fixture
def api_key() -> str:
    """Return a dummy API key for testing."""
    return "test_api_key"


@pytest.fixture
def base_url() -> str:
    """Return a dummy base URL for testing."""
    return "https://api.test.com/v1"


@pytest.fixture
def client(api_key: str, base_url: str) -> Supadata:
    """Return a configured Supadata client."""
    return Supadata(api_key=api_key, base_url=base_url)


def test_client_initialization(api_key: str, base_url: str) -> None:
    """Test client initialization."""
    client = Supadata(api_key=api_key, base_url=base_url)
    assert client.base_url == base_url
    assert client.session.headers["x-api-key"] == api_key
    assert client.session.headers["Accept"] == "application/json"


def test_get_transcript_chunks(client: Supadata, requests_mock) -> None:
    """Test getting YouTube transcript with chunks."""
    video_id = "test123"
    mock_response = {
        "content": [
            {
                "text": "Hello",
                "offset": 0,
                "duration": 1000,
                "lang": "en"
            }
        ],
        "lang": "en",
        "availableLangs": ["en", "es"]
    }
    requests_mock.get(
        f"{client.base_url}/youtube/transcript",
        json=mock_response
    )

    transcript = client.youtube.transcript(video_id=video_id)
    assert isinstance(transcript, Transcript)
    assert isinstance(transcript.content[0], TranscriptChunk)
    assert transcript.content[0].text == "Hello"
    assert transcript.lang == "en"
    assert transcript.available_langs == ["en", "es"]


def test_get_transcript_text(client: Supadata, requests_mock) -> None:
    """Test getting YouTube transcript as plain text."""
    video_id = "test123"
    mock_response = {
        "content": "Hello, this is a test transcript",
        "lang": "en",
        "availableLangs": ["en", "es"]
    }
    requests_mock.get(
        f"{client.base_url}/youtube/transcript",
        json=mock_response
    )

    transcript = client.youtube.transcript(video_id=video_id, text=True)
    assert isinstance(transcript, Transcript)
    assert isinstance(transcript.content, str)
    assert transcript.content == "Hello, this is a test transcript"


def test_translate_transcript(client: Supadata, requests_mock) -> None:
    """Test translating YouTube transcript."""
    video_id = "test123"
    mock_response = {
        "content": "Hola, esto es una prueba",
        "lang": "es"
    }
    requests_mock.get(
        f"{client.base_url}/youtube/transcript/translate",
        json=mock_response
    )

    transcript = client.youtube.translate(
        video_id=video_id,
        lang="es",
        text=True
    )
    assert isinstance(transcript, TranslatedTranscript)
    assert transcript.content == "Hola, esto es una prueba"
    assert transcript.lang == "es"


def test_scrape(client: Supadata, requests_mock) -> None:
    """Test web scraping."""
    url = "https://test.com"
    mock_response = {
        "url": url,
        "content": "# Test\nThis is a test page",
        "name": "Test Page",
        "description": "A test page",
        "ogUrl": "https://test.com/og.png",
        "countCharacters": 100,
        "urls": ["https://test.com/about"]
    }
    requests_mock.get(
        f"{client.base_url}/web/scrape",
        json=mock_response
    )

    content = client.web.scrape(url=url)
    assert isinstance(content, Scrape)
    assert content.url == url
    assert content.name == "Test Page"
    assert content.og_url == "https://test.com/og.png"
    assert content.count_characters == 100


def test_map(client: Supadata, requests_mock) -> None:
    """Test site mapping."""
    url = "https://test.com"
    mock_response = {
        "urls": [
            "https://test.com",
            "https://test.com/about"
        ]
    }
    requests_mock.get(
        f"{client.base_url}/web/map",
        json=mock_response
    )

    site_map = client.web.map(url=url)
    assert isinstance(site_map, Map)
    assert len(site_map.urls) == 2


def test_error_handling(client: Supadata, requests_mock) -> None:
    """Test error handling for JSON API errors."""
    video_id = "invalid"
    error_response = {
        "code": "video-not-found",
        "title": "Video Not Found",
        "description": "The specified video was not found",
        "documentationUrl": "https://docs.test.com/errors#video-not-found"
    }
    requests_mock.get(
        f"{client.base_url}/youtube/transcript",
        status_code=400,  # Changed from 404 to 400 since 404 is handled as gateway error
        json=error_response,
        headers={'content-type': 'application/json'}
    )

    with pytest.raises(SupadataError) as exc_info:
        client.youtube.transcript(video_id=video_id)

    error = exc_info.value
    assert error.code == error_response["code"]
    assert error.title == error_response["title"]
    assert error.description == error_response["description"]
    assert error.documentation_url == error_response["documentationUrl"]


def test_start_crawl(client: Supadata, requests_mock) -> None:
    """Test starting a crawl job."""
    url = "https://test.com"
    mock_response = {
        "jobId": "test-job-123"
    }
    requests_mock.post(
        f"{client.base_url}/web/crawl",
        json=mock_response
    )

    job = client.web.crawl(url=url, limit=100)
    assert isinstance(job, CrawlJob)
    assert job.job_id == "test-job-123"


def test_get_crawl_results(client: Supadata, requests_mock) -> None:
    """Test getting crawl results with pagination."""
    job_id = "test-job-123"
    
    # First page response
    mock_response1 = {
        "status": "completed",
        "pages": [
            {
                "url": "https://test.com",
                "content": "# Page 1",
                "name": "Test Page 1",
                "description": "First test page"
            }
        ],
        "next": "page2"
    }
    
    # Second page response
    mock_response2 = {
        "status": "completed",
        "pages": [
            {
                "url": "https://test.com/2",
                "content": "# Page 2",
                "name": "Test Page 2",
                "description": "Second test page"
            }
        ],
        "next": None
    }

    requests_mock.get(
        f"{client.base_url}/web/crawl/{job_id}",
        [
            {'json': mock_response1},
            {'json': mock_response2}
        ]
    )

    pages = client.web.get_crawl_results(job_id=job_id)
    assert len(pages) == 2
    assert isinstance(pages[0], CrawlPage)
    assert pages[0].name == "Test Page 1"
    assert pages[1].name == "Test Page 2"


def test_get_crawl_results_failed(client: Supadata, requests_mock) -> None:
    """Test getting crawl results for a failed job."""
    job_id = "test-job-123"
    mock_response = {
        "status": "failed",
        "pages": None,
        "next": None
    }
    requests_mock.get(
        f"{client.base_url}/web/crawl/{job_id}",
        json=mock_response
    )

    with pytest.raises(Exception, match="Crawl job failed"):
        client.web.get_crawl_results(job_id=job_id)


def test_gateway_error_403(client: Supadata, requests_mock) -> None:
    '''Test handling of 403 gateway error.'''
    requests_mock.get(
        f'{client.base_url}/youtube/transcript',
        status_code=403,
        text='Invalid API key provided'
    )

    with pytest.raises(SupadataError) as exc_info:
        client.youtube.transcript(video_id='test123')
    
    error = exc_info.value
    assert error.code == 'invalid-request'
    assert error.title == 'Invalid or missing API key'
    assert error.description == 'Invalid API key provided'


def test_gateway_error_404(client: Supadata, requests_mock) -> None:
    '''Test handling of 404 gateway error.'''
    requests_mock.get(
        f'{client.base_url}/invalid/endpoint',
        status_code=404,
        text='Endpoint not found'
    )

    with pytest.raises(SupadataError) as exc_info:
        client._request('GET', '/invalid/endpoint')
    
    error = exc_info.value
    assert error.code == 'invalid-request'
    assert error.title == 'Endpoint does not exist'
    assert error.description == 'Endpoint not found'


def test_gateway_error_429(client: Supadata, requests_mock) -> None:
    '''Test handling of 429 gateway error.'''
    requests_mock.get(
        f'{client.base_url}/youtube/transcript',
        status_code=429,
        text='Rate limit exceeded'
    )

    with pytest.raises(SupadataError) as exc_info:
        client.youtube.transcript(video_id='test123')
    
    error = exc_info.value
    assert error.code == 'limit-exceeded'
    assert error.title == 'Limit exceeded'
    assert error.description == 'Rate limit exceeded' 