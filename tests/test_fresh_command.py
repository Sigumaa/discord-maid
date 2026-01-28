from bot.discord_bot import _extract_fresh_request


def test_extract_fresh_request() -> None:
    assert _extract_fresh_request("/fresh こんにちは") == "こんにちは"
    assert _extract_fresh_request("fresh こんにちは") == "こんにちは"
    assert _extract_fresh_request("/fresh") == ""
    assert _extract_fresh_request("hello") is None
