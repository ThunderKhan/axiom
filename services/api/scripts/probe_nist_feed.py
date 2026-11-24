"""Single fixed publisher feed transport probe; no content or credentials logged."""

from __future__ import annotations

from xml.etree import ElementTree as ET

from app.feed_source import _citation, _plain, parse_feed
from app.public_source import (
    SourceAccessBlocked,
    SourceAcquisitionFailed,
    fetch_reviewed_public_document,
)

# NIST explicitly advertises RSS syndication and allows redistribution of
# public information except material marked copyrighted. This is a transport
# check only: no excerpts are displayed or retained, no provider enabled.
URL = "https://www.nist.gov/news-events/news/rss.xml"


def main() -> int:
    try:
        document = fetch_reviewed_public_document(URL, access_reviewed=True)
        items = parse_feed(document, query="", limit=10)
    except (SourceAccessBlocked, SourceAcquisitionFailed):
        print("BLOCKED: fixed NIST feed did not pass the real acquisition boundary.")
        return 1
    if not items:
        # parse_feed already validated the bounded document and denied DTDs.
        root = ET.fromstring(document.body.decode(document.charset))  # noqa: S314
        atom = "{http://www.w3.org/2005/Atom}"
        if root.tag == atom + "feed":
            print(f"BLOCKED: {len(root.findall(atom + 'entry'))} Atom entries; no usable items.")
            return 1
        entries = root.findall("channel/item")[:128]
        safe_links = sum(_citation(entry.findtext("link", "")) is not None for entry in entries)
        titles = sum(bool(_plain(entry.find("title"), 180)) for entry in entries)
        excerpts = sum(bool(_plain(entry.find("description"), 500)) for entry in entries)
        print(
            f"BLOCKED: {len(entries)} RSS entries; {safe_links} safe links; "
            f"{titles} titles; {excerpts} usable excerpts."
        )
        return 1
    print(f"PASS: real NIST feed acquisition and parsing; {len(items)} usable entries.")
    print(
        "Not evidence of purchase intent, permission for third-party excerpts or deployed access."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
