#!/usr/bin/env python3
"""
Azure DevOps ONLY - upload a rendered swimlane image (PNG by default) to the wiki's
hidden /.attachments folder via the Wiki Attachments REST API, then print the
root-relative reference for embedding.

Owned by the docs-wiki `wiki-plantuml` skill. Standard library only (urllib); runs on
Windows, macOS and Linux. Called by publish_update.py ONLY after --approve.

Encapsulates the Azure attachment gotchas:
  - PAT read from the AZDO_PAT env var (scope vso.wiki_write) - NEVER echoed or logged.
  - Body encoding is a parameter (--body-encoding, WIKI-P3-11). The default is base64,
    the form that rendered on the Azure DevOps Services instance this was verified on
    (a raw body showed a "broken image link" there). Microsoft's REST reference shows a
    raw octet-stream body; if an image uploaded with base64 shows broken on your
    instance, re-upload with --body-encoding raw. Content-Type is
    application/octet-stream either way.
  - PNG is the correct attachment format (official list: PNG/GIF/JPEG/ICO; SVG not listed).
  - VERIFY-ON-FAIL: the PUT commonly returns HTTP 500 even though the attachment WAS
    written. The 7.1 API is Create-only (no GET-by-name), so verify by RE-PUTting the
    same name (idempotent: a new ETag version, not an error); fail only if that fails too.
  - "Wiki not found" / TF401174 => the wiki is not provisioned yet (a human creates it
    once), NOT a permission error.

    AZDO_PAT=<pat>  python upload_attachment.py --org https://dev.azure.com/contoso \\
        --project Web --wiki-id Web.wiki --file swimlane-orders-fulfilment.png \\
        --name swimlane-orders-fulfilment.png
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN_ENV = "AZDO_PAT"
TIMEOUT = 60


class UploadError(Exception):
    pass


AZURE_HOSTS = ("dev.azure.com", "visualstudio.com", "azure.com")  # + subdomains


def org_url(org: str) -> str:
    """Accept a full org URL or a bare org name (-> https://dev.azure.com/<org>)."""
    org = org.strip().rstrip("/")
    if "://" not in org:
        org = "https://dev.azure.com/" + urllib.parse.quote(org, safe="")
    return org


def check_org(org: str) -> tuple[str, str | None]:
    """Validate where the PAT will be sent (WIKI-P3-21). Returns (url, warning).
    Raises ValueError for a non-https URL or one without a host: the Basic-auth header
    would otherwise travel in clear text, or to an unreadable destination. A host that
    is not Azure DevOps Services (an on-premises Azure DevOps Server, or a URL supplied
    by a cloned repo's adapter file) is allowed with a warning naming the host."""
    raw = (org or "").strip()
    url = urllib.parse.urlsplit(raw).geturl() if "://" in raw else org_url(raw)
    parts = urllib.parse.urlsplit(url)
    if parts.scheme.lower() != "https":
        raise ValueError(f"REFUSED: --org must be an https URL (got scheme "
                         f"'{parts.scheme}'); the PAT would be sent unencrypted.")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        raise ValueError("REFUSED: --org has no host.")
    if any(host == h or host.endswith("." + h) for h in AZURE_HOSTS):
        return org_url(raw), None
    return org_url(raw), (f"--org host '{host}' is not Azure DevOps Services "
                          f"(dev.azure.com / *.visualstudio.com). The AZDO_PAT is sent to "
                          f"it; continue only if this is your Azure DevOps Server.")


def build_request(org: str, project: str, wiki_id: str, name: str, data: bytes,
                  pat: str, api_version: str = "7.1",
                  body_encoding: str = "base64") -> urllib.request.Request:
    q = lambda s: urllib.parse.quote(s, safe="")  # noqa: E731
    url = (f"{org_url(org)}/{q(project)}/_apis/wiki/wikis/{q(wiki_id)}/attachments"
           f"?name={q(name)}&api-version={q(api_version)}")
    auth = base64.b64encode(f":{pat}".encode("utf-8")).decode("ascii")
    return urllib.request.Request(
        url, data=base64.b64encode(data) if body_encoding == "base64" else data,
        method="PUT",
        headers={"Authorization": f"Basic {auth}",
                 "Content-Type": "application/octet-stream"})


def _put(req: urllib.request.Request) -> None:
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310 (https org URL)
        resp.read()


def _body(exc: urllib.error.HTTPError) -> str:
    try:
        return exc.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""


def upload(req: urllib.request.Request, wiki_id: str) -> None:
    """PUT with verify-on-500. Raises UploadError on a real failure."""
    try:
        _put(req)
        print("OK: uploaded.")
        return
    except urllib.error.HTTPError as exc:
        text = f"{exc.reason} {_body(exc)}"
        if "Wiki not found" in text or "TF401174" in text:
            raise UploadError(
                f"Wiki '{wiki_id}' not found - the project wiki is not provisioned yet (a "
                "human creates it once via Project Settings -> Wiki). This is NOT a "
                "permission error.") from None
        if exc.code != 500:
            raise UploadError(f"Attachment upload failed (HTTP {exc.code}): {exc.reason}") \
                from None
    except urllib.error.URLError as exc:
        raise UploadError(f"Attachment upload failed (network): {exc.reason}") from None

    print("warning: PUT returned HTTP 500 - re-PUTting (idempotent) to confirm the "
          "attachment landed...", file=sys.stderr)
    try:
        _put(req)
    except urllib.error.HTTPError as exc:
        raise UploadError("HTTP 500 on the first PUT and the idempotent re-PUT also failed "
                          f"(HTTP {exc.code}) - real failure.") from None
    except urllib.error.URLError as exc:
        raise UploadError("HTTP 500 on the first PUT and the re-PUT failed (network): "
                          f"{exc.reason}") from None
    print("OK: re-PUT succeeded - the attachment is present (the first 500 was spurious).")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Upload an image to an Azure DevOps wiki's "
                                             "/.attachments (PAT from $AZDO_PAT).")
    ap.add_argument("--org", required=True, help="org URL or bare org name")
    ap.add_argument("--project", required=True)
    ap.add_argument("--wiki-id", required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--name", required=True, help="attachment name (URL-encoded for you)")
    ap.add_argument("--api-version", default="7.1")
    ap.add_argument("--body-encoding", choices=["base64", "raw"], default="base64",
                    help="request body form (default base64; use raw if base64 renders as "
                         "a broken image on your instance)")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = Path(args.file)
    if not path.is_file():
        print(f"error: file not found: {args.file}", file=sys.stderr)
        return 1
    try:
        _, warning = check_org(args.org)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if warning:
        print(f"warning: {warning}", file=sys.stderr)
    pat = os.environ.get(TOKEN_ENV, "")
    if not pat:
        print(f"error: {TOKEN_ENV} not set in the environment (scope vso.wiki_write). It is "
              "read from env and never echoed.", file=sys.stderr)
        return 1
    req = build_request(args.org, args.project, args.wiki_id, args.name, path.read_bytes(),
                        pat, args.api_version, args.body_encoding)
    print(f"Uploading {args.name} to wiki {args.wiki_id} (.attachments) ...")
    try:
        upload(req, args.wiki_id)
    except UploadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    ref = f"/.attachments/{args.name}"
    print(f"Embed reference: ![alt]({ref})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
