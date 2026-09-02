from filetrail.models import FileRecord, Origin
from filetrail.redact import fingerprint, looks_like_secret, redact_text, redact_url


def test_strips_credential_query_parameters_but_keeps_the_url_readable():
    result = redact_url("https://api.example.org/v1/export?range=90d&api_key=s3cr3tvalue123")

    assert "s3cr3tvalue123" not in result
    assert "https://api.example.org/v1/export" in result
    assert "range=90d" in result
    assert "REDACTED:query" in result


def test_url_without_a_query_is_untouched():
    url = "https://example.org/reports/annual.pdf"
    assert redact_url(url) == url


def test_harmless_query_parameters_survive():
    url = "https://example.org/search?q=acme&page=2"
    assert redact_url(url) == url


def test_redacts_space_separated_argument():
    result = redact_text("curl --password hunter2seventy https://example.org")
    assert "hunter2seventy" not in result
    assert "--password" in result


def test_redacts_equals_separated_argument():
    assert "abcdef123456" not in redact_text("tool --token=abcdef123456")


def test_redacts_bearer_header():
    result = redact_text('curl -H "Authorization: Bearer abcdef1234567890"')
    assert "abcdef1234567890" not in result
    assert "Authorization: Bearer" in result


def test_redacts_url_credentials():
    assert "sup3rs3cret" not in redact_text("git clone https://user:sup3rs3cret@host/repo.git")


def test_redacts_vendor_tokens_and_keys():
    for secret in (
        "AKIAIOSFODNN7EXAMPLE",
        "ghp_abcdefghijklmnopqrstuvwxyz0123",
        "sk-abcdefghijklmnopqrstuvwx",
    ):
        assert secret not in redact_text(f"tool {secret}")


def test_leaves_ordinary_commands_alone():
    command = "exiftool -json evidence/photo.jpg"
    assert redact_text(command) == command


def test_does_not_redact_documentation_placeholders():
    for value in ("${API_KEY}", "<token>", "changeme", "xxxxxxxx"):
        assert not looks_like_secret(value)


def test_does_not_redact_prose_words_in_credential_position():
    assert redact_text("tool --auth-mode environment") == "tool --auth-mode environment"


def test_fingerprint_is_stable_and_hides_the_value():
    secret = "hunter2seventy"
    handle = fingerprint(secret)

    assert handle == fingerprint(secret)
    assert len(handle) == 12
    assert secret not in handle
    assert not secret.startswith(handle)


def test_same_secret_twice_gets_the_same_fingerprint():
    output = redact_text("a --token=abcdef123456 and b --token=abcdef123456")
    marks = [part for part in output.split() if "REDACTED" in part]
    assert len(marks) == 2 and marks[0] == marks[1]


def test_origin_redacts_url_referrer_and_command():
    origin = Origin(
        source="browser-download",
        url="https://example.org/f?token=abcdef123456",
        referrer="https://example.org/p?api_key=zyxwvu987654",
        command="curl --password hunter2seventy",
    )

    safe = origin.redacted()

    assert "abcdef123456" not in safe.url
    assert "zyxwvu987654" not in safe.referrer
    assert "hunter2seventy" not in safe.command
    assert safe.source == origin.source


def test_origin_redacts_note_and_location_too():
    """A mail subject or a typed place name is free text like any other.

    Both fields reach the report word for word, so a token in a forwarded
    subject line or a URL pasted where a place name belongs would ride
    through `--redact` untouched.
    """
    origin = Origin(
        source="email-delivery",
        note="Fwd: your key sk-abcdefghijklmnopqrstuvwx",
        location="see https://vault.example.org/f?token=abcdef123456",
    )

    safe = origin.redacted()

    assert "sk-abcdefghijklmnopqrstuvwx" not in safe.note
    assert "abcdef123456" not in safe.location
    assert safe.note.startswith("Fwd: your key ")  # the subject itself survives


def test_file_record_redacts_every_origin():
    record = FileRecord(path="/case/a", size=1, mtime="2026-08-24T19:00:00Z")
    record.origins.append(Origin(source="shell-history", command="tool --token=abcdef123456"))

    safe = record.redacted()

    assert "abcdef123456" not in safe.origins[0].command
    assert "abcdef123456" in record.origins[0].command  # original untouched
