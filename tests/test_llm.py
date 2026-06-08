from foliun.services.llm import format_sse


def test_sse_format() -> None:
    event = format_sse("token", {"content": "hello"})
    assert event.startswith("event: token\n")
    assert '"content": "hello"' in event
    assert event.endswith("\n\n")
