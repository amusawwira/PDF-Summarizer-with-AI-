from src.pdf_utils import chunk_text


def test_chunk_text_basic():
    text = "a" * 1000
    chunks = chunk_text(text, chunk_size=300, overlap=50)
    assert len(chunks) >= 3
    # Coverage: all chars reachable
    joined = "".join(chunks)
    assert len(joined) >= len(text)


def test_chunk_text_empty():
    assert chunk_text("") == []
