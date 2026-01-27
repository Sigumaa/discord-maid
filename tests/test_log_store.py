import asyncio

from bot.log_store import append_logs, read_user_log_tail


def test_log_store_roundtrip(tmp_path) -> None:
    entry = {
        "ts": "2026-01-27T00:00:00+00:00",
        "guild_id": 1,
        "channel_id": 2,
        "user_id": 3,
        "display_name": "user",
        "role": "user",
        "content": "hello",
        "message_id": 4,
    }

    asyncio.run(append_logs(str(tmp_path), entry))
    tail = asyncio.run(read_user_log_tail(str(tmp_path), 1, 3, 10))

    assert len(tail) == 1
    assert tail[0]["content"] == "hello"
