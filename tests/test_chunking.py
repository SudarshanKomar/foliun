from foliun.config import Settings
from foliun.services.chunking import ApproximateTokenCounter, split_text_into_chunks


def test_chunking_uses_512_tokens_and_102_overlap() -> None:
    settings = Settings(chunk_size_tokens=512, chunk_overlap_tokens=102)
    text = " ".join(f"word{i}" for i in range(900))
    chunks = split_text_into_chunks(text, [(1, 0, len(text))], ApproximateTokenCounter(), settings)
    assert chunks
    assert max(chunk.token_count for chunk in chunks) <= 512
    assert settings.chunk_overlap_tokens == 102
    assert chunks[1].content.split()[0] == "word410"


def test_empty_text_produces_no_chunks() -> None:
    settings = Settings()
    assert split_text_into_chunks("   ", [], ApproximateTokenCounter(), settings) == []
