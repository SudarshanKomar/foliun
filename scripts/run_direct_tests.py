import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.test_chunking import test_chunking_uses_512_tokens_and_102_overlap, test_empty_text_produces_no_chunks
from tests.test_context import test_context_orders_by_document_position_and_respects_budget, test_invalid_citation_detection
from tests.test_files import test_sanitize_filename_prevents_path_traversal, test_sha256_bytes_is_deterministic
from tests.test_llm import test_sse_format
from tests.test_retrieval import test_rrf_uses_k_60_and_deduplicates


def main() -> None:
    """Run lightweight tests without pytest."""

    tests = [
        test_chunking_uses_512_tokens_and_102_overlap,
        test_empty_text_produces_no_chunks,
        test_context_orders_by_document_position_and_respects_budget,
        test_invalid_citation_detection,
        test_sse_format,
        test_rrf_uses_k_60_and_deduplicates,
        test_sanitize_filename_prevents_path_traversal,
        test_sha256_bytes_is_deterministic,
    ]
    for test in tests:
        test()
    print("direct tests ok")


if __name__ == "__main__":
    main()
