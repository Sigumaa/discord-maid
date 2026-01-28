from bot.discord_bot import _extract_search_request


def test_extract_search_request_web_only() -> None:
    web, x, remaining = _extract_search_request("/web 検索して")
    assert web is True
    assert x is False
    assert remaining == "検索して"


def test_extract_search_request_x_only() -> None:
    web, x, remaining = _extract_search_request("/x 検索して")
    assert web is False
    assert x is True
    assert remaining == "検索して"


def test_extract_search_request_both() -> None:
    web, x, remaining = _extract_search_request("/web /x 検索して")
    assert web is True
    assert x is True
    assert remaining == "検索して"


def test_extract_search_request_none() -> None:
    web, x, remaining = _extract_search_request("hello")
    assert web is False
    assert x is False
    assert remaining == "hello"
