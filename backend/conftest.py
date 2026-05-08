"""pytest bootstrap: load env vars from repo-root .env so importing modules that
construct API clients at import time (negotiation, auction) doesn't blow up
when the test process doesn't have OPENAI_API_KEY exported."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Last-resort stub so import-time client construction in negotiation.py /
# auction.py never fails the suite even if .env is absent.
os.environ.setdefault("OPENAI_API_KEY", "sk-test-placeholder")
