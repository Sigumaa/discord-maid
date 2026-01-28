from bot.discord_bot import _chunk_text


def test_chunk_text_preserves_footer() -> None:
    body = "a" * 1890
    text = f"{body}\n-# tools: none"
    chunks = _chunk_text(text, limit=1900)
    assert chunks[-1].endswith("-# tools: none")
    assert len("".join(chunks).replace("\n", "")) >= len(body)


def test_chunk_text_footer_falls_to_new_chunk() -> None:
    body = "a" * 1901
    text = f"{body}\n-# tools: none"
    chunks = _chunk_text(text, limit=1900)
    assert chunks[-1].endswith("-# tools: none")
    assert all(len(chunk) <= 1900 for chunk in chunks)
    assert len(chunks) >= 2


def test_chunk_text_no_footer() -> None:
    body = "a" * 2000
    chunks = _chunk_text(body, limit=1900)
    assert len(chunks) == 2
