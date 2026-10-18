#!/usr/bin/env python3
"""Reject common publication hazards in an exact, tracked Git tree.

Run ``python tools/check_public_snapshot.py --tree HEAD`` after committing the
candidate. This never reads environment files from disk, runs application code,
queries production, or prints matching values. It also never scans untracked
files: the tree passed here must be the tree that is subsequently published.

This is a bounded, dependency-free guard, not a secrecy or privacy certificate.
An independent review must compare private identifiers/history, inspect media
rights and sensitive business content, and review GitHub logs/artifacts/settings.
Generic patterns cannot identify every private repository URL or novel secret.
Do not add private hostnames, addresses, credentials or commit IDs as deny rules.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import ipaddress
import json
from pathlib import PurePosixPath
import re
import subprocess
import sys
import unittest


MAX_BLOB_BYTES = 8 * 1024 * 1024
MAX_TREE_BYTES = 64 * 1024 * 1024
MAX_TREE_FILES = 10_000
MAX_FINDINGS = 200
GIT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True, order=True)
class Finding:
    category: str
    path: str
    line: int = 1


FORBIDDEN_SEGMENTS = {
    ".git", ".ssh", ".venv", "venv", "node_modules", "__pycache__",
    ".private_backup", ".local_runtime", "backup", "backups", "uploads",
}
FORBIDDEN_SUFFIXES = {
    ".sqlite", ".sqlite3", ".db", ".sql", ".dump", ".bak", ".backup",
    ".pem", ".key", ".p12", ".pfx", ".jks", ".keystore", ".log", ".har",
    ".pcap", ".zip", ".7z", ".tar", ".gz", ".tgz", ".rar", ".xz", ".bz2",
    ".pyc", ".pyo",
}
SECRET_NAME = re.compile(
    r"(?i)(?:password|passwd|secret(?:_key)?|api_key|access_key|access_token|"
    r"auth_token|database_url|private_key)"
)
DEMO_VALUE = re.compile(
    r"(?i)^(?:development[-_ ]only|local[-_ ]only|demo(?:[-_ ]|$)|"
    r"dummy(?:[-_ ]|$)|example(?:[-_ ]|$)|test(?:[-_ ]|$)|"
    r"ci(?:[-_ ]|$)|placeholder|your[-_ ]|replace[-_ ]|change[-_ ]?me|"
    r"not[-_ ](?:a[-_ ])?real|invalid[-_ ]for[-_ ]production|\$\{|<)"
)
FIXTURE_PATH = re.compile(
    r"(?:^|/)(?:tests?|fixtures?)(?:/|\.[^/]+$)|"
    r"(?:^|/)(?:test_[^/]+|[^/]+_test)\.py$|\.test\.[^/]+$", re.I
)
TEXT_RULES = (
    ("private-key-material", re.compile(
        r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY(?: BLOCK)?-----")),
    ("provider-token", re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|"
        r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{15,}|"
        r"SG\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,})\b")),
    ("cloud-access-key", re.compile(
        r"\b(?:(?:AKIA|ASIA)[A-Z0-9]{16}|AIza[A-Za-z0-9_-]{30,})\b")),
    ("password-hash", re.compile(
        r"(?:\bpbkdf2_sha256\$\d+\$[^\s\"']+|\$2[aby]\$\d+\$[./A-Za-z0-9]{30,})")),
    ("jwt-like-token", re.compile(
        r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("credentialed-connection-url", re.compile(
        r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp|https?)://"
        r"[^\s/\"':]+:[^\s/\"'@]+@", re.I)),
    ("sql-data-records", re.compile(
        r"^\s*(?:COPY\s+\S+\s*\([^\n]+\)\s+FROM\s+stdin|"
        r"INSERT\s+INTO\s+[\w\".]+\s*(?:\(|VALUES))", re.I | re.M)),
    ("private-operator-path", re.compile(
        r"(?:/(?:root|home)/[^\s/\"']+/|"
        r"[A-Z]:[\\/](?:Users|Documents and Settings)[\\/][^\s\\/\"']+[\\/]|"
        r"[~][\\/]\.ssh[\\/]|\.(?:private_backup|local_runtime)[\\/])", re.I)),
    ("private-repository-reference", re.compile(
        r"(?:https?://|git@)github\.com[:/][\w.-]+/[\w.-]*"
        r"(?:private|production|prod)(?:[._/-]|\b)", re.I)),
)
IPV4_LITERAL = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
BRACKETED_IPV6 = re.compile(r"\[([0-9a-fA-F]*:[0-9a-fA-F:]+)\]")
EXAMPLE_NETWORKS = tuple(ipaddress.ip_network(network) for network in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8",
    "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "2001:db8::/32",
    "fc00::/7", "fe80::/10",
))
CREDENTIAL_KEY = (
    r"[A-Za-z_][A-Za-z0-9_]*(?:PASSWORD|PASSWD|SECRET|SECRET_KEY|API_KEY|"
    r"ACCESS_KEY|ACCESS_TOKEN|AUTH_TOKEN|DATABASE_URL|PRIVATE_KEY)[A-Za-z0-9_]*|"
    r"password|passwd|secret|secret_key|api_key|access_key|access_token|auth_token"
)
CREDENTIAL_ASSIGNMENT = re.compile(
    rf"(?<![\w\"'\\])(?:[\"'](?:{CREDENTIAL_KEY})[\"']|(?:{CREDENTIAL_KEY}))"
    r"\s*[:=]\s*[\"'](?P<value>[^\"'\r\n]{16,})[\"']", re.I
)


def path_findings(path: str) -> list[Finding]:
    parts = PurePosixPath(path.lower()).parts
    name = parts[-1] if parts else ""
    findings = []
    if name.startswith(".env") and name != ".env.example":
        findings.append(Finding("runtime-environment-file", path))
    if (set(parts) & FORBIDDEN_SEGMENTS or
            (parts and parts[0] in {"assets", "media", "staticfiles", "collected_static"})):
        findings.append(Finding("private-or-runtime-directory", path))
    if PurePosixPath(name).suffix in FORBIDDEN_SUFFIXES or name in {
        "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "authorized_keys", "known_hosts",
    }:
        findings.append(Finding("data-key-log-or-archive-artifact", path))
    if (any(part in {"deploy", "deployment", "deployments", "nginx"} for part in parts) or
            re.search(r"(?:^|[._-])(?:prod|production)(?:[._-]|$)", name) or
            re.match(r"deploy(?:[._-]|$)", name) or
            name.startswith("nginx.") or
            ("settings" in parts and name in {"prod.py", "production.py"})):
        findings.append(Finding("production-deployment-configuration", path))
    return findings


def is_example_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return True  # CSS/SVG decimal sequences are not addresses.
    return (address.is_loopback or address.is_unspecified or
            any(address.version == network.version and address in network
                for network in EXAMPLE_NETWORKS))


def credential_is_fixture(path: str, value: str) -> bool:
    return bool(FIXTURE_PATH.search(path) or DEMO_VALUE.search(value))


def scan_blob(path: str, data: bytes) -> list[Finding]:
    findings = path_findings(path)
    if len(data) > MAX_BLOB_BYTES:
        return findings + [Finding("blob-size-limit", path)]
    text = data.decode("utf-8", errors="replace")
    container_user = re.search(r"^USER\s+([a-z_][a-z0-9_-]*)\s*$", text, re.M)
    container_home = "/" + f"home/{container_user.group(1)}/" if container_user else ""
    for category, pattern in TEXT_RULES:
        for match in pattern.finditer(text):
            if category == "private-operator-path":
                # Generic ignore declarations disclose no operator filesystem.
                if path in {".gitignore", ".dockerignore"} and match.group().startswith("."):
                    continue
                # A container account's declared home is not a host operator's.
                if (PurePosixPath(path).name == "Dockerfile" and container_user and
                        match.group().startswith(container_home) and
                        f"--home {container_home.rstrip('/')}" in text):
                    continue
            findings.append(Finding(category, path, text.count("\n", 0, match.start()) + 1))
            if len(findings) >= MAX_FINDINGS:
                return findings
    for pattern in (IPV4_LITERAL, BRACKETED_IPV6):
        for match in pattern.finditer(text):
            value = match.group(1) if pattern is BRACKETED_IPV6 else match.group()
            if not is_example_address(value):
                findings.append(Finding("external-address-review", path,
                                        text.count("\n", 0, match.start()) + 1))
    for match in CREDENTIAL_ASSIGNMENT.finditer(text):
        if not credential_is_fixture(path, match.group("value")):
            findings.append(Finding("hardcoded-credential-review", path,
                                    text.count("\n", 0, match.start()) + 1))
    if PurePosixPath(path).name == ".env.example":
        for line_number, line in enumerate(text.splitlines(), 1):
            key, separator, value = line.partition("=")
            if (separator and SECRET_NAME.search(key) and len(value.strip()) >= 16 and
                    not credential_is_fixture(path, value.strip().strip("\"'"))):
                findings.append(Finding("hardcoded-credential-review", path, line_number))
    if path.endswith(".py") and len(data) <= 1024 * 1024:
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError, RecursionError):
            findings.append(Finding("python-source-unparsed", path))
            return sorted(set(findings))
        for node in ast.walk(tree):
            value = None
            if isinstance(node, ast.Assign):
                names = [item.id for target in node.targets for item in ast.walk(target)
                         if isinstance(item, ast.Name)]
                if any(SECRET_NAME.search(name) for name in names):
                    value = node.value
            elif isinstance(node, ast.keyword) and node.arg and SECRET_NAME.search(node.arg):
                value = node.value
            if isinstance(value, ast.Call) and len(value.args) > 1:
                # Also inspect a long secret supplied as an environment fallback.
                value = value.args[1]
            if (isinstance(value, ast.Constant) and isinstance(value.value, str) and
                    len(value.value) >= 16 and not credential_is_fixture(path, value.value)):
                findings.append(Finding("hardcoded-credential-review", path, value.lineno))
    return sorted(set(findings))[:MAX_FINDINGS]


class GuardError(Exception):
    """A safe failure category, never a raw Git diagnostic."""


def git(*args: str, stdin: bytes | None = None) -> bytes:
    try:
        result = subprocess.run(["git", "--no-pager", *args], input=stdin,
                                capture_output=True, timeout=GIT_TIMEOUT_SECONDS,
                                check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise GuardError("git-unavailable-or-timeout") from error
    if result.returncode:
        raise GuardError("git-tree-read-failed")
    return result.stdout


def scan_tree(treeish: str) -> tuple[list[Finding], int, int]:
    resolved = git("rev-parse", "--verify", "--end-of-options", f"{treeish}^{{tree}}").strip()
    if not re.fullmatch(rb"[0-9a-f]{40,64}", resolved):
        raise GuardError("git-tree-identity-invalid")
    rows = git("ls-tree", "-rlz", "--full-tree", resolved.decode()).split(b"\0")
    blobs: dict[str, tuple[int, list[str]]] = {}
    findings = []
    file_count = 0
    total_bytes = 0
    for row in rows:
        if not row:
            continue
        metadata, path_bytes = row.split(b"\t", 1)
        mode, kind, oid, size = metadata.decode("ascii").split()
        path = path_bytes.decode("utf-8", errors="replace")
        file_count += 1
        if kind != "blob" or mode == "120000":
            findings.append(Finding("unsupported-submodule-or-symlink", path))
            continue
        blob_size = int(size)
        if blob_size > MAX_BLOB_BYTES:
            findings.append(Finding("blob-size-limit", path))
            continue
        if oid not in blobs:
            blobs[oid] = (blob_size, [])
            total_bytes += blob_size
        blobs[oid][1].append(path)
    if file_count > MAX_TREE_FILES or total_bytes > MAX_TREE_BYTES:
        raise GuardError("tree-size-limit")
    payload = git("cat-file", "--batch", stdin="".join(f"{oid}\n" for oid in blobs).encode())
    offset = 0
    for oid, (expected_size, paths) in blobs.items():
        end = payload.find(b"\n", offset)
        if end < 0:
            raise GuardError("git-blob-response-invalid")
        header = payload[offset:end].decode("ascii").split()
        if header != [oid, "blob", str(expected_size)]:
            raise GuardError("git-blob-response-invalid")
        offset = end + 1
        data = payload[offset:offset + expected_size]
        offset += expected_size + 1
        for path in paths:
            findings.extend(scan_blob(path, data))
            if len(findings) >= MAX_FINDINGS:
                findings.append(Finding("finding-limit-more-review-required", "<tree>"))
                return sorted(set(findings))[:MAX_FINDINGS + 1], file_count, total_bytes
    return sorted(set(findings)), file_count, total_bytes


class PublicationGuardTests(unittest.TestCase):
    def categories(self, path: str, content: str = "") -> set[str]:
        return {finding.category for finding in scan_blob(path, content.encode())}

    def test_demo_and_fixture_values_allowed(self):
        self.assertFalse(self.categories(".env.example", "SECRET_KEY=development-only-key\n"))
        self.assertFalse(self.categories("settings/base.py", 'SECRET_KEY = "development-only-example-key"'))
        self.assertFalse(self.categories("tests/test_login.py", 'password = "Fictional-fixture-credential"'))
        self.assertFalse(self.categories("site.py", 'secret_key = os.environ.get("SECRET_KEY")'))

    def test_runtime_artifacts_denied(self):
        for path in (".env", ".env.dev", "db.sqlite3", "backup/data.tar.gz", "media/patient.jpg",
                     "uploads/a.jpg", "." + "local_runtime/run.py", "id_ed25519", "access.log"):
            with self.subTest(path=path):
                self.assertTrue(self.categories(path))

    def test_production_configuration_denied(self):
        for path in ("docker-compose.prod.yml", "settings/production.py", "nginx/site.conf", "deploy.sh"):
            with self.subTest(path=path):
                self.assertIn("production-deployment-configuration", self.categories(path))

    def test_public_source_assets_allowed(self):
        for path in ("Dockerfile", "docker-compose.yml", "website/migrations/0001_initial.py",
                     "website/static/img/logo.png", "website/static/fonts/icons.woff"):
            with self.subTest(path=path):
                self.assertFalse(self.categories(path))

    def test_secret_signatures_not_waived_by_fixture_paths(self):
        examples = (
            ("private-key-material", "-----BEGIN " + "PRIVATE KEY-----"),
            ("provider-token", "ghp_" + "x" * 36),
            ("cloud-access-key", "AKIA" + "A" * 16),
            ("password-hash", "pbkdf2_" + "sha256$12345$salt$hash"),
            ("jwt-like-token", "eyJ" + "x" * 12 + "." + "x" * 12 + "." + "x" * 12),
            ("credentialed-connection-url", "postgresql" + "://demo:credential@localhost/db"),
        )
        for category, content in examples:
            with self.subTest(category=category):
                self.assertIn(category, self.categories("tests/fixture.txt", content))

    def test_hardcoded_credential_denied_even_in_env_example(self):
        content = 'PASSWORD = "' + "Q7s!" * 6 + '"'
        self.assertIn("hardcoded-credential-review", self.categories("settings/base.py", content))
        self.assertIn("hardcoded-credential-review", self.categories(".env.example", content))
        self.assertIn("hardcoded-credential-review", self.categories(".env.example", "SECRET_KEY=" + "Q7s!" * 6))

    def test_ignore_declarations_and_container_homes_are_not_host_paths(self):
        self.assertFalse(self.categories(".gitignore", "." + "local_runtime/\n"))
        home = "/" + "home/app"
        docker = f"RUN adduser --home {home} app\nUSER app\nWORKDIR {home}/site\n"
        self.assertFalse(self.categories("Dockerfile", docker))
        self.assertIn("private-operator-path", self.categories("notes.txt", docker))

    def test_vendor_query_parameter_concatenation_is_not_a_literal_secret(self):
        script = 'params.push("access_token=' + '"+token); params.push("access_token=' + '"+x+"query_suffix_here")'
        self.assertFalse(self.categories("vendor.js", script))

    def test_environment_fallback_is_reviewed(self):
        content = 'SECRET_KEY = os.environ.get("SECRET_KEY", "' + "Q7s!" * 6 + '")'
        self.assertIn("hardcoded-credential-review", self.categories("settings.py", content))

    def test_sql_data_not_schema_is_denied(self):
        self.assertIn("sql-data-records", self.categories("notes.txt", "INSERT " + "INTO patient VALUES (1);"))
        self.assertFalse(self.categories("schema.txt", "CREATE TABLE appointment (id integer);"))

    def test_only_documentation_private_loopback_addresses_allowed(self):
        for address in ("127.0.0.1", "0.0.0.0", "10.1.2.3", "172.16.1.2", "192.168.2.3",
                        "192.0.2.1", "198.51.100.2", "203.0.113.9", "[::1]", "[2001:db8::1]"):
            with self.subTest(address=address):
                self.assertFalse(self.categories("demo.txt", address))
        self.assertIn("external-address-review", self.categories("demo.txt", ".".join(("8",) * 4)))
        self.assertIn("external-address-review", self.categories("demo.txt", "[" + "2606:4700::1111" + "]"))
        self.assertFalse(self.categories("drawing.svg", "999.123.777.123"))

    def test_private_paths_and_explicit_private_repository_denied(self):
        content = "/" + "home/operator/project/"
        self.assertIn("private-operator-path", self.categories("notes.txt", content))
        url = "https://github.com/" + "example/project-private"
        self.assertIn("private-repository-reference", self.categories("notes.txt", url))

    def test_outputs_are_locations_not_matching_values(self):
        token = "ghp_" + "x" * 36
        findings = scan_blob("notes.txt", ("ordinary\n" + token).encode())
        self.assertEqual(findings, [Finding("provider-token", "notes.txt", 2)])
        self.assertNotIn(token, repr(findings))

    def test_oversized_blobs_fail_closed(self):
        self.assertIn("blob-size-limit", self.categories("large.txt", "x" * (MAX_BLOB_BYTES + 1)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", default="HEAD", help="Exact committed Git tree to inspect (default: HEAD).")
    parser.add_argument("--unit-tests", action="store_true", help="Run isolated, synthetic guard tests only.")
    args = parser.parse_args()
    if args.unit_tests:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(PublicationGuardTests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    try:
        findings, files, size = scan_tree(args.tree)
    except (GuardError, ValueError, UnicodeError) as error:
        category = str(error) if isinstance(error, GuardError) else "git-tree-parse-failed"
        print(json.dumps({"class": category, "path": "<tree>", "line": 1}))
        return 1
    for finding in findings:
        print(json.dumps({"class": finding.category, "path": finding.path, "line": finding.line}))
    print(json.dumps({"result": "FAIL" if findings else "PASS", "files": files,
                      "bytes": size, "findings": len(findings)}))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
