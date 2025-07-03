import requests
import tempfile
import os
import contextlib

REPO = "droidrun/droidrun-portal"
ASSET_NAME = "droidrun-portal"
GITHUB_API_HOSTS = ["https://ungh.cc"]

def get_latest_release_assets(debug: bool = False):
    for host in GITHUB_API_HOSTS:
        url = f"{host}/repos/{REPO}/releases/latest"
        response = requests.get(url)
        if response.status_code == 200:
            if debug:
                print(f"Using GitHub release on {host}")
            break

    response.raise_for_status()
    latest_release = response.json()

    if "release" in latest_release:
        assets = latest_release["release"]["assets"]
    else:
        assets = latest_release.get("assets", [])

    return assets

@contextlib.contextmanager
def download_portal_apk(debug: bool = False):
    assets = get_latest_release_assets(debug)

    asset_url = None
    for asset in assets:
        if (
            "browser_download_url" in asset
            and "name" in asset
            and asset["name"].startswith(ASSET_NAME)
        ):
            asset_url = asset["browser_download_url"]
            break
        elif "downloadUrl" in asset and os.path.basename(
            asset["downloadUrl"]
        ).startswith(ASSET_NAME):
            asset_url = asset["downloadUrl"]
            break
        else:
            if debug:
                print(asset)

    if not asset_url:
        raise Exception(f"Asset named '{ASSET_NAME}' not found in the latest release.")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".apk")
    try:
        r = requests.get(asset_url, stream=True)
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                tmp.write(chunk)
        tmp.close()
        yield tmp.name
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)


if __name__ == "__main__":
    with download_portal_apk() as apk_path:
        print(apk_path)
