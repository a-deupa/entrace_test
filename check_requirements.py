import json
import re
import sys
import urllib.error
import urllib.request

PYPI = "https://pypi.org/pypi"

LINE_RE = re.compile(
    r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(?:===?\s*([^\s;,#]+))?"
)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "req-checker/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def parse(path):
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.split(" #")[0].strip()
            if not line or line.startswith(("#", "-")):
                continue
            m = LINE_RE.match(line)
            if m:
                yield m.group(1), m.group(2)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"

    checked = 0
    missing_packages = 0
    missing_versions = 0
    oldest = None  # (upload_time, "name==version")
    package_exists = {}  # cache: name -> bool

    for name, version in parse(path):
        checked += 1
        key = name.lower()

        if version:
            data = fetch(f"{PYPI}/{name}/{version}/json")
            if data is None:
                # Version missing: does the package exist at all?
                if key not in package_exists:
                    package_exists[key] = fetch(f"{PYPI}/{name}/json") is not None
                if package_exists[key]:
                    missing_versions+=1
                else:
                    missing_packages+=1
                continue

            package_exists[key] = True
            urls = data.get("urls") or []
            if urls and urls[0].get("upload_time"):
                uploaded = urls[0]["upload_time"]  # e.g. 2021-03-04T12:34:56
                if oldest is None or uploaded < oldest[0]:
                    oldest = (uploaded, f"{name}=={version}")
        else:
            if key not in package_exists:
                package_exists[key] = fetch(f"{PYPI}/{name}/json") is not None
            if not package_exists[key]:
                missing_packages += 1

    print(f"dependencies checked: {checked}")
    print(f"packages not on PyPI: {missing_packages}")
    print(f"versions not on PyPI: {missing_versions}")
    if oldest:
        print(f"Oldest pinned release: {oldest[1]} ({oldest[0][:4]})")
    else:
        print("Oldest pinned release: none")


if __name__ == "__main__":
    main()