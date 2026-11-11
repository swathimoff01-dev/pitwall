"""Step 1 smoke test: config loads, Postgres reachable, Gemini + Groq keys work."""

import sys

from pitwall.config import Settings, get_settings


def check_config(s: Settings) -> bool:
    missing = [
        name
        for name, val in [
            ("GOOGLE_API_KEY", s.google_api_key),
            ("GROQ_API_KEY", s.groq_api_key),
        ]
        if val is None
    ]
    if missing:
        print(f"❌ Config: missing {', '.join(missing)} in .env")
        return False
    print(f"✅ Config: loaded (db={s.postgres_db} @ {s.postgres_host}:{s.postgres_port})")
    return True


def check_postgres(s: Settings) -> bool:
    import psycopg

    try:
        with psycopg.connect(s.admin_conninfo(), connect_timeout=5) as conn:
            version = conn.execute("SELECT version()").fetchone()[0]
        print(f"✅ Postgres: {version.split(',')[0]}")
        return True
    except Exception as e:
        print(f"❌ Postgres: {e}")
        return False


def _print_flash_models(client) -> None:
    """If the configured model name is wrong, show which Flash models this key can use."""
    try:
        names = [m.name.removeprefix("models/") for m in client.models.list() if "flash" in m.name]
        if names:
            print("   Flash models available to your key:", ", ".join(sorted(names)))
    except Exception:
        pass


def check_gemini(s: Settings) -> bool:
    from google import genai

    client = None
    try:
        client = genai.Client(api_key=s.google_api_key.get_secret_value())
        resp = client.models.generate_content(
            model=s.gemini_model, contents="Reply with exactly: box box"
        )
        print(f"✅ Gemini ({s.gemini_model}): {(resp.text or '').strip()!r}")
        return True
    except Exception as e:
        print(f"❌ Gemini: {e}")
        if client is not None:
            _print_flash_models(client)
        return False


def check_groq(s: Settings) -> bool:
    from groq import Groq

    try:
        client = Groq(api_key=s.groq_api_key.get_secret_value())
        resp = client.chat.completions.create(
            model=s.groq_judge_model,
            max_tokens=300,
            messages=[{"role": "user", "content": "Reply with exactly: box box"}],
        )
        text = (resp.choices[0].message.content or "").strip()
        print(f"✅ Groq ({s.groq_judge_model}): {text!r}")
        return True
    except Exception as e:
        print(f"❌ Groq: {e}")
        return False


def main() -> int:
    s = get_settings()
    if not check_config(s):
        return 1
    results = [check_postgres(s), check_gemini(s), check_groq(s)]
    print("\nAll checks passed 🏁" if all(results) else "\nSome checks failed.")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
