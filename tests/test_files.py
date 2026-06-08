from foliun.services.files import sanitize_filename, sha256_bytes


def test_sanitize_filename_prevents_path_traversal() -> None:
    assert sanitize_filename("../../secret.txt") == "secret.txt"


def test_sha256_bytes_is_deterministic() -> None:
    assert sha256_bytes(b"abc") == sha256_bytes(b"abc")
    assert len(sha256_bytes(b"abc")) == 64
