import uuid

from mizan.platform.ids import short_id, uuid7


def test_uuid7_version_and_variant() -> None:
    value = uuid7()
    assert value.version == 7
    assert value.variant == uuid.RFC_4122


def test_uuid7_is_monotonic_within_process() -> None:
    values = [uuid7() for _ in range(5000)]
    assert values == sorted(values)
    assert len(set(values)) == len(values)


def test_short_id_is_eight_uppercase_hex_chars() -> None:
    assert len(short_id(uuid7())) == 8
    assert short_id(uuid7()).isupper() or short_id(uuid7()).isdigit()
