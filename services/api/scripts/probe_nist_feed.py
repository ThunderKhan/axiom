"""Single fixed publisher feed transport probe; no content or credentials logged."""

from __future__ import annotations

from app.feed_source import parse_feed
from app.public_source import (
    SourceAccessBlocked,
    SourceAcquisitionFailed,
    fetch_reviewed_public_document,
)

# NIST explicitly advertises RSS syndication and allows redistribution of
# public information except material marked copyrighted. This is a transport
# check only: no excerpts are displayed or retained, no provider enabled.
URL = "https://www.nist.gov/news-events/cybersecurity/rss.xml"


def main() -> int:
    try:
        document = fetch_reviewed_public_document(URL, access_reviewed=True)
        items = parse_feed(document, query="", limit=10)
    except (SourceAccessBlocked, SourceAcquisitionFailed):
        print("BLOCKED: fixed NIST feed did not pass the real acquisition boundary.")
        return 1
    if not items:
        print("BLOCKED: no usable entries in the bounded retrieved feed.")
        return 1
    print(f"PASS: real NIST feed acquisition and parsing; {len(items)} usable entries.")
    print("Not evidence of purchase intent, permission for third-party excerpts or deployed access.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
