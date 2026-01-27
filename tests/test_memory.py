from bot.memory import InMemoryBackend


def test_memory_roundtrip() -> None:
    memory = InMemoryBackend(max_history=2)
    key = (None, 1)
    memory.append(key, {"role": "user", "content": "a"})
    memory.append(key, {"role": "assistant", "content": "b"})
    memory.append(key, {"role": "user", "content": "c"})

    assert memory.get(key) == [
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
    ]

    memory.clear(key)
    assert memory.get(key) == []
