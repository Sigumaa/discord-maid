from bot.discord_bot import _is_clear_request


def test_clear_request_ascii() -> None:
    assert _is_clear_request("/clear") is True
    assert _is_clear_request("#clear") is True
    assert _is_clear_request("clear") is False
    assert _is_clear_request("/reset") is False
    assert _is_clear_request("履歴クリア") is False
    assert _is_clear_request("hello") is False
