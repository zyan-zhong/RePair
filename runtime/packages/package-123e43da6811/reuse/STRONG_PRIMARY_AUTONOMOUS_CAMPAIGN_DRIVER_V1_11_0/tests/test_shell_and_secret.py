from pathlib import Path

def test_long_lived_supervisor_has_no_provider_secret_or_strict_shell():
    root=Path(__file__).resolve().parents[1]
    names=['RUN_DETACHED.sh','run_campaign_worker.sh','campaign_supervisor.py']
    for name in names:
        text=(root/name).read_text() if (root/name).exists() else ''
        assert 'OPENAI_API_KEY' not in text
        assert 'set -euo pipefail' not in text
