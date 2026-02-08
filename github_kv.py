# github_kv.py
import base64
import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

import streamlit as st

API_BASE = "https://api.github.com"


def _cfg() -> Tuple[str, str, str, str, str]:
    token = st.secrets["GITHUB_TOKEN"]
    owner = st.secrets["GITHUB_OWNER"]
    repo = st.secrets["GITHUB_REPO"]
    branch = st.secrets.get("GITHUB_BRANCH", "main")
    data_dir = st.secrets.get("GITHUB_DATA_DIR", "data").strip("/")
    return token, owner, repo, branch, data_dir


def _contents_url(owner: str, repo: str, path: str) -> str:
    return f"{API_BASE}/repos/{owner}/{repo}/contents/{path}"


def _req(method: str, url: str, token: str, payload: Optional[dict] = None) -> dict:
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "streamlit-app",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body) if body else {}


def _safe_http_code(e: Exception) -> Optional[int]:
    if isinstance(e, urllib.error.HTTPError):
        return e.code
    return None


def read_json(path: str) -> Optional[Dict[str, Any]]:
    token, owner, repo, branch, _ = _cfg()
    url = _contents_url(owner, repo, path) + f"?ref={branch}"
    try:
        res = _req("GET", url, token)
    except Exception:
        return None

    content_b64 = res.get("content")
    if not content_b64:
        return None
    raw = base64.b64decode(content_b64).decode("utf-8")
    return json.loads(raw)


def write_json(path: str, data: Dict[str, Any], message: str) -> bool:
    """
    成功: True
    失敗: False（画面にHTTPコードを表示してアプリは落とさない）
    """
    token, owner, repo, branch, _ = _cfg()
    url = _contents_url(owner, repo, path)

    raw = json.dumps(data, ensure_ascii=False, indent=2)
    content = base64.b64encode(raw.encode("utf-8")).decode("utf-8")

    last_code = None

    for _ in range(3):
        try:
            # sha取得（存在しない場合は新規作成）
            current = None
            try:
                current = _req("GET", url + f"?ref={branch}", token)
            except Exception as e:
                # 404なら新規作成扱いでOK、他はコード記録
                code = _safe_http_code(e)
                if code and code != 404:
                    last_code = code
                current = None

            payload = {
                "message": message,
                "content": content,
                "branch": branch,
            }
            sha = (current or {}).get("sha")
            if sha:
                payload["sha"] = sha

            _req("PUT", url, token, payload)
            return True

        except Exception as e:
            code = _safe_http_code(e)
            if code:
                last_code = code
            time.sleep(0.5)

    # 失敗したがアプリは落とさない
    if last_code:
        st.error(f"GitHub保存に失敗しました（HTTP {last_code}）")
    else:
        st.error("GitHub保存に失敗しました（HTTPコード不明）")
    return False
