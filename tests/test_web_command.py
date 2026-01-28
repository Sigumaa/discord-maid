from bot.discord_bot import _extract_tool_request


def test_extract_tool_request_web_only() -> None:
    web, x, code, remaining = _extract_tool_request("/web 検索して")
    assert web is True
    assert x is False
    assert code is False
    assert remaining == "検索して"


def test_extract_tool_request_x_only() -> None:
    web, x, code, remaining = _extract_tool_request("/x 検索して")
    assert web is False
    assert x is True
    assert code is False
    assert remaining == "検索して"


def test_extract_tool_request_both() -> None:
    web, x, code, remaining = _extract_tool_request("/web /x 検索して")
    assert web is True
    assert x is True
    assert code is False
    assert remaining == "検索して"


def test_extract_tool_request_code() -> None:
    web, x, code, remaining = _extract_tool_request("/code 2+2")
    assert web is False
    assert x is False
    assert code is True
    assert remaining == "2+2"


def test_extract_tool_request_none() -> None:
    web, x, code, remaining = _extract_tool_request("hello")
    assert web is False
    assert x is False
    assert code is False
    assert remaining == "hello"
