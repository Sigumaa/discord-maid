from bot.names import is_reserved_name, normalize_preferred_name, resolve_call_name


def test_normalize_preferred_name() -> None:
    assert normalize_preferred_name("「しゆい」") == "しゆい"


def test_reserved_name() -> None:
    assert is_reserved_name("しゆい") is True
    assert is_reserved_name("しゆい様") is True
    assert is_reserved_name("ゆい") is False


def test_resolve_call_name() -> None:
    assert (
        resolve_call_name(
            user_id=1,
            special_user_id=2,
            display_name="しゆい",
            preferred_name=None,
        )
        == "ユーザー1"
    )
