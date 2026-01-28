from types import SimpleNamespace

from bot.discord_bot import _collect_image_urls


def test_collect_image_urls() -> None:
    attachments = [
        SimpleNamespace(
            content_type="image/png",
            filename="a.png",
            size=1024,
            url="https://example.com/a.png",
        ),
        SimpleNamespace(
            content_type="image/jpeg",
            filename="b.jpg",
            size=1024,
            url="https://example.com/b.jpg",
        ),
        SimpleNamespace(
            content_type="image/jpeg",
            filename="c.jpg",
            size=1024,
            url="https://example.com/c.jpg",
        ),
    ]
    assert _collect_image_urls(attachments) == [
        "https://example.com/a.png",
        "https://example.com/b.jpg",
    ]
