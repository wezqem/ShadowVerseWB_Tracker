import json
import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st

# =============================
# 永続化（ユーザー別）
# =============================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


def sanitize_user_id(s: str) -> str:
    s = s.strip().lower()
    if not s:
        return ""
    s = re.sub(r"[^a-z0-9_\-]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:40]


def user_data_path(user_id: str) -> str:
    return os.path.join(DATA_DIR, f"tracker_{user_id}.json")


# =============================
# 初期データ
# =============================
CLASS_COLORS = {
    "E":  {"name": "エルフ",     "color": "#10b981"},
    "R":  {"name": "ロイヤル",   "color": "#eab308"},
    "D":  {"name": "ドラゴン",   "color": "#f97316"},
    "W":  {"name": "ウィッチ",   "color": "#a855f7"},
    "Ni": {"name": "ナイトメア", "color": "#ef4444"},
    "B":  {"name": "ビショップ", "color": "#d1d5db"},
    "Nm": {"name": "ネメシス",   "color": "#06b6d4"},
}
CLASS_ORDER = ["E", "R", "D", "W", "Ni", "B", "Nm"]

INITIAL_DECKS = [
    {"name": "リノE", "class": "E"},
    {"name": "テンポE", "class": "E"},
    {"name": "進化E", "class": "E"},
    {"name": "不殺E", "class": "E"},
    {"name": "財宝R", "class": "R"},
    {"name": "進化R", "class": "R"},
    {"name": "オルオーンR", "class": "R"},
    {"name": "ほーちゃんD", "class": "D"},
    {"name": "進化D", "class": "D"},
    {"name": "ランプD", "class": "D"},
    {"name": "海洋D", "class": "D"},
    {"name": "スペル秘術W", "class": "W"},
    {"name": "秘術W", "class": "W"},
    {"name": "スペルW", "class": "W"},
    {"name": "リンクルW", "class": "W"},
    {"name": "リアニメイトNi", "class": "Ni"},
    {"name": "モードNi", "class": "Ni"},
    {"name": "ミルティオNi", "class": "Ni"},
    {"name": "進化Ni", "class": "Ni"},
    {"name": "ミッドレンジNi", "class": "Ni"},
    {"name": "シャクドウNi", "class": "Ni"},
    {"name": "アグロNi", "class": "Ni"},
    {"name": "奇数B", "class": "B"},
    {"name": "クレストB", "class": "B"},
    {"name": "守護B", "class": "B"},
    {"name": "破壊Nm", "class": "Nm"},
    {"name": "人形Nm", "class": "Nm"},
    {"name": "アーティファクトNm", "class": "Nm"},
]


def default_state():
    return {
        "deck_types": INITIAL_DECKS,
        "my_deck": "",
        "current_opponent": "",
        "matches": [],  # newest first
        "stats_mydeck_filter": "",  # 集計対象（空=全体）
    }


def load_data(user_id: str) -> dict:
    path = user_data_path(user_id)
    if not os.path.exists(path):
        return default_state()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        base = default_state()
        for k in base.keys():
            if k in data:
                base[k] = data[k]
        if not isinstance(base["deck_types"], list):
            base["deck_types"] = INITIAL_DECKS
        if not isinstance(base["matches"], list):
            base["matches"] = []
        return base
    except Exception:
        return default_state()


def save_data():
    uid = st.session_state.user_id
    if not uid:
        return
    path = user_data_path(uid)
    data = {
        "deck_types": st.session_state.deck_types,
        "my_deck": st.session_state.my_deck,
        "current_opponent": st.session_state.current_opponent,
        "matches": st.session_state.matches,
        "stats_mydeck_filter": st.session_state.stats_mydeck_filter,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =============================
# 集計・ユーティリティ
# =============================
def get_deck_info(name: str):
    for d in st.session_state.deck_types:
        if d["name"] == name:
            return d
    return None


def get_deck_class(name: str) -> str:
    info = get_deck_info(name)
    return info["class"] if info and "class" in info else "E"


def grouped_decks():
    grouped = {k: [] for k in CLASS_ORDER}
    for d in st.session_state.deck_types:
        grouped.setdefault(d["class"], []).append(d)
    return {k: grouped.get(k, []) for k in CLASS_ORDER}


def compute_stats(matches):
    total = len(matches)
    wins = sum(1 for m in matches if m["result"] == "win")
    losses = total - wins
    win_rate = round((wins / total) * 100, 1) if total else 0.0
    return total, wins, losses, win_rate


def compute_win_streak(matches):
    streak = 0
    for m in matches:
        if m["result"] == "win":
            streak += 1
        else:
            break
    return streak


def add_match(result: str):
    if not st.session_state.my_deck or not st.session_state.current_opponent:
        return
    my = st.session_state.my_deck
    opp = st.session_state.current_opponent
    new_match = {
        "id": int(datetime.now().timestamp() * 1000),
        "my_deck": my,
        "my_deck_class": get_deck_class(my),
        "opponent_deck": opp,
        "opponent_deck_class": get_deck_class(opp),
        "result": result,  # win/loss
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    st.session_state.matches = [new_match] + st.session_state.matches
    st.session_state.current_opponent = ""
    save_data()


def update_match(match_id: int, new_my: str, new_opp: str, new_result: str):
    updated = []
    for m in st.session_state.matches:
        if m["id"] == match_id:
            m = dict(m)
            m["my_deck"] = new_my
            m["my_deck_class"] = get_deck_class(new_my)
            m["opponent_deck"] = new_opp
            m["opponent_deck_class"] = get_deck_class(new_opp)
            m["result"] = new_result
        updated.append(m)
    st.session_state.matches = updated
    save_data()


def delete_match(match_id: int):
    st.session_state.matches = [m for m in st.session_state.matches if m["id"] != match_id]
    save_data()


def add_deck(name: str, cls: str):
    name = name.strip()
    if not name:
        return "デッキ名が空です"
    if any(d["name"] == name for d in st.session_state.deck_types):
        return "同名デッキが既に存在します"
    if cls not in CLASS_COLORS:
        return "クラスが不正です"
    st.session_state.deck_types.append({"name": name, "class": cls})
    save_data()
    return None


def delete_deck(name: str):
    st.session_state.deck_types = [d for d in st.session_state.deck_types if d["name"] != name]
    if st.session_state.my_deck == name:
        st.session_state.my_deck = ""
    if st.session_state.current_opponent == name:
        st.session_state.current_opponent = ""
    save_data()


def build_mydeck_table(matches_all):
    rows = []
    mydecks = sorted(list({m["my_deck"] for m in matches_all}))
    for md in mydecks:
        ms = [m for m in matches_all if m["my_deck"] == md]
        t, w, l, wr = compute_stats(ms)
        rows.append({"Deck": md, "Matches": t, "Wins": w, "Losses": l, "WinRate(%)": wr})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values(["Matches", "WinRate(%)"], ascending=[False, False]).reset_index(drop=True)
    return df


def build_opponent_table(matches_filtered):
    opps = sorted(list({m["opponent_deck"] for m in matches_filtered}))
    rows = []
    for opp in opps:
        ms = [m for m in matches_filtered if m["opponent_deck"] == opp]
        t, w, l, wr = compute_stats(ms)
        rows.append({"Opponent": opp, "Matches": t, "Wins": w, "Losses": l, "WinRate(%)": wr})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values(["WinRate(%)", "Matches"], ascending=[False, False]).reset_index(drop=True)
    return df


# =============================
# UI
# =============================
st.set_page_config(page_title="Shadowverse WB Tracker", layout="wide")

st.markdown("""
<style>
/* ===== Base Dark Theme ===== */
:root{
  --bg0:#070810;
  --bg1:#0b0d18;
  --card: rgba(255,255,255,0.06);
  --border: rgba(255,255,255,0.10);
  --text:#ffffff;
  --muted: rgba(255,255,255,0.68);
  --muted2: rgba(255,255,255,0.52);
  --accent:#8b5cf6;
  --ok:#10b981;
  --ng:#ef4444;
  --pill-accent: #8b5cf6;
}

.stApp{
  background:
    radial-gradient(900px 420px at 20% 0%, rgba(139,92,246,0.18), transparent 60%),
    radial-gradient(900px 420px at 85% 8%, rgba(6,182,212,0.14), transparent 55%),
    linear-gradient(180deg, var(--bg0), var(--bg1));
  color: var(--text);
}

/* Cloudヘッダー重なり回避 */
.block-container{
  padding-top: 4.8rem;
  padding-bottom: 1.0rem;
  max-width: 1240px;
}

/* フォント */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&display=swap');
*{ font-family: "Inter","Noto Sans JP",system-ui,sans-serif !important; }

/* タイトル */
div[data-testid="stTitle"] h1{
  color: #fff !important;
  font-weight: 900 !important;
  letter-spacing: .3px;
  font-size: 24px !important;
}
div[data-testid="stCaption"]{
  color: var(--muted) !important;
}

/* Card */
.card{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 14px 14px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.28);
  backdrop-filter: blur(12px);
}
.section-title{
  font-weight: 900;
  color: #fff;
  letter-spacing: .2px;
}
.small-muted{
  color: var(--muted);
  font-size: 12px;
}

/* デフォルト：ボタンはピル */
div.stButton > button{
  border-radius: 999px !important;
  border: 1px solid rgba(255,255,255,0.14) !important;
  background: rgba(255,255,255,0.06) !important;
  color: #fff !important;
  padding: 0.32rem 0.78rem !important;
  font-size: 12px !important;
  font-weight: 800 !important;
  line-height: 1.1 !important;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: transform .08s ease, background .2s ease, border-color .2s ease, box-shadow .2s ease;
}
div.stButton > button:hover{
  background: rgba(255,255,255,0.10) !important;
  border-color: rgba(139,92,246,0.30) !important;
}
div.stButton > button:active{ transform: scale(0.98); }

/* 勝敗ボタン */
.winbtn button{
  background: rgba(16,185,129,0.95) !important;
  border-color: rgba(16,185,129,0.95) !important;
  color: #071d14 !important;
  font-weight: 900 !important;
}
.lossbtn button{
  background: rgba(239,68,68,0.95) !important;
  border-color: rgba(239,68,68,0.95) !important;
  color: #250707 !important;
  font-weight: 900 !important;
}

/* Dataframe */
div[data-testid="stDataFrame"]{
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 14px;
  overflow: hidden;
}

/* ===== Metric Cards (A) ===== */
.metrics-wrap{
  display:grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 8px;
}
@media (max-width: 1100px){
  .metrics-wrap{ grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.metric-card{
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.10);
  border-radius: 16px;
  padding: 14px 14px;
  box-shadow: 0 10px 28px rgba(0,0,0,0.30);
  backdrop-filter: blur(12px);
  position: relative;
  overflow: hidden;
}
.metric-card::before{
  content:"";
  position:absolute;
  inset:-1px;
  background: radial-gradient(600px 120px at 10% 0%, rgba(139,92,246,0.35), transparent 55%),
              radial-gradient(600px 120px at 90% 0%, rgba(6,182,212,0.22), transparent 55%);
  opacity: 0.55;
  pointer-events:none;
}
.metric-top{
  position:relative;
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:10px;
  margin-bottom:10px;
}
.metric-label{
  color: rgba(255,255,255,0.72);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: .2px;
}
.metric-badge{
  font-size: 11px;
  font-weight: 900;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.10);
  color: rgba(255,255,255,0.85);
}
.metric-value{
  position:relative;
  font-size: 26px;
  font-weight: 900;
  color: #fff;
  letter-spacing: 0.2px;
  line-height: 1.1;
}
.accent-line{
  position:absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, rgba(139,92,246,0.95), rgba(6,182,212,0.65));
  opacity: .95;
}

/* ===== Pill zone: compact + selected ring ===== */
/* ここが「横長化」を防ぐ（ピルだけautoに戻す） */
.pillzone div.stButton > button{
  width: auto !important;
  min-width: 0 !important;
  display: inline-flex !important;
}
.pillzone div.stButton{
  width: auto !important;
}
.pillzone{
  margin-top: 6px;
}

/* 選択中だけ：クラス色リング（primary） */
.pillzone div.stButton > button[kind="primary"]{
  border: 1px solid rgba(255,255,255,0.12) !important;
  box-shadow: 0 0 0 2px var(--pill-accent) inset, 0 8px 20px rgba(0,0,0,0.28) !important;
}

/* 削除：expander headerの色 */
div[data-testid="stExpander"] summary{
  color: rgba(255,255,255,0.86) !important;
}
            
/* ===== Ranking Cards ===== */
.rank-card{
  border-radius: 10px;
  padding: 16px 18px;
  margin-bottom: 14px;
  font-weight: 700;
  display:flex;
  align-items:center;
  justify-content:space-between;
  background: linear-gradient(90deg, rgba(255,255,255,0.95), rgba(255,255,255,0.78));
}
.rank-1{ border: 4px solid #E5C100; }
.rank-2{ border: 4px solid #B5B5B5; }
.rank-3{ border: 4px solid #C97A5A; }
.rank-left{ display:flex; align-items:center; gap:14px; }
.rank-no{ font-size: 20px; letter-spacing: 0.5px; }
.rank-deck{ font-size: 18px; }
.rank-rate{ font-size: 20px; }
.rank-sub{ font-size: 12px; opacity: 0.75; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

# ---- Sidebar: ユーザー
with st.sidebar:
    st.markdown("### ユーザー")
    uid_raw = st.text_input("ユーザー名", value=st.session_state.get("user_id_raw", ""))
    uid = sanitize_user_id(uid_raw)
    st.session_state.user_id_raw = uid_raw
    if not uid:
        st.warning("ユーザー名を入力してください。")
    else:
        st.success(f"ユーザー名: {uid}")

# ---- init by user
if "initialized_for_user" not in st.session_state:
    st.session_state.initialized_for_user = None

if uid and st.session_state.initialized_for_user != uid:
    data = load_data(uid)
    st.session_state.user_id = uid
    st.session_state.deck_types = data["deck_types"]
    st.session_state.my_deck = data["my_deck"]
    st.session_state.current_opponent = data["current_opponent"]
    st.session_state.matches = data["matches"]
    st.session_state.stats_mydeck_filter = data.get("stats_mydeck_filter", "")
    st.session_state.initialized_for_user = uid

st.title("Shadowverse WB Tracker")
st.caption("戦績管理（ユーザー別）")

if not uid:
    st.stop()

tab_input, tab_stats = st.tabs(["入力", "集計"])

# =============================
# 入力タブ
# =============================
with tab_input:
    left, right = st.columns([1.05, 1.35], gap="large")

    # ---- 左：マイデッキ選択 & 管理
    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>マイデッキ</div>", unsafe_allow_html=True)

        grouped = grouped_decks()
        PER_ROW = 3  # 折れにくい

        for ck in CLASS_ORDER:
            decks = grouped.get(ck, [])
            if not decks:
                continue
            info = CLASS_COLORS[ck]
            st.markdown(
                f"<div style='margin-top:10px; margin-bottom:6px; color:{info['color']}; font-weight:900;'>● {info['name']}</div>",
                unsafe_allow_html=True,
            )
            for i in range(0, len(decks), PER_ROW):
                row = st.columns(PER_ROW, gap="small")
                chunk = decks[i:i+PER_ROW]
                for j in range(PER_ROW):
                    if j >= len(chunk):
                        row[j].empty()
                        continue
                    name = chunk[j]["name"]
                    selected = (st.session_state.my_deck == name)
                    label = f"✅ {name}" if selected else name
                    with row[j]:
                        if st.button(label, key=f"my_{ck}_{name}"):
                            st.session_state.my_deck = name
                            st.session_state.current_opponent = ""
                            save_data()
                            st.rerun()

        if st.session_state.my_deck:
            ci = CLASS_COLORS.get(get_deck_class(st.session_state.my_deck), CLASS_COLORS["E"])
            st.markdown(
                f"<div class='small-muted' style='margin-top:10px;'>選択中</div>"
                f"<div style='font-weight:900; color:{ci['color']};'>{st.session_state.my_deck}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("まずはマイデッキを選択してください。")

        st.divider()

        st.markdown("<div class='section-title'>デッキ管理</div>", unsafe_allow_html=True)
        with st.expander("デッキ追加", expanded=False):
            new_name = st.text_input("デッキ名", value="", placeholder="例: 新型〇〇", key="new_deck_name")
            new_cls = st.selectbox(
                "クラス",
                CLASS_ORDER,
                format_func=lambda k: CLASS_COLORS[k]["name"],
                key="new_deck_class",
            )
            if st.button("追加", key="add_deck_btn"):
                err = add_deck(new_name, new_cls)
                if err:
                    st.error(err)
                else:
                    st.success("追加しました")
                    st.rerun()

        with st.expander("デッキ削除（戦績は残る）", expanded=False):
            all_names = [d["name"] for d in st.session_state.deck_types]
            if all_names:
                del_target = st.selectbox("削除するデッキ", all_names, key="del_target")
                if st.button("削除する", key="del_deck_btn"):
                    delete_deck(del_target)
                    st.success(f"削除: {del_target}")
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    # ---- 右：対戦相手選択 & 勝敗入力 & 履歴
    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>対戦入力</div>", unsafe_allow_html=True)

        if not st.session_state.my_deck:
            st.warning("左でマイデッキを選択してください。")
        else:
            grouped = grouped_decks()
            PER_ROW_OPP = 3

            for ck in CLASS_ORDER:
                decks = grouped.get(ck, [])
                if not decks:
                    continue
                info = CLASS_COLORS[ck]
                st.markdown(
                    f"<div style='margin-top:10px; margin-bottom:6px; color:{info['color']}; font-weight:900;'>● {info['name']}</div>",
                    unsafe_allow_html=True,
                )
                for i in range(0, len(decks), PER_ROW_OPP):
                    row = st.columns(PER_ROW_OPP, gap="small")
                    chunk = decks[i:i+PER_ROW_OPP]
                    for j in range(PER_ROW_OPP):
                        if j >= len(chunk):
                            row[j].empty()
                            continue
                        name = chunk[j]["name"]
                        selected = (st.session_state.current_opponent == name)
                        label = f"✅ {name}" if selected else name
                        with row[j]:
                            if st.button(label, key=f"opp_{ck}_{name}"):
                                st.session_state.current_opponent = name
                                save_data()

            if st.session_state.current_opponent:
                opp_ci = CLASS_COLORS.get(get_deck_class(st.session_state.current_opponent), CLASS_COLORS["E"])
                st.markdown(
                    f"<div class='small-muted' style='margin-top:10px;'>対戦相手</div>"
                    f"<div style='font-weight:900; color:{opp_ci['color']};'>{st.session_state.current_opponent}</div>",
                    unsafe_allow_html=True,
                )

                b1, b2 = st.columns(2, gap="small")
                with b1:
                    st.markdown("<div class='winbtn'>", unsafe_allow_html=True)
                    if st.button("勝利", use_container_width=True, key="win_btn"):
                        add_match("win")
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
                with b2:
                    st.markdown("<div class='lossbtn'>", unsafe_allow_html=True)
                    if st.button("敗北", use_container_width=True, key="loss_btn"):
                        add_match("loss")
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("対戦相手を選んでください。")

        st.divider()
        st.markdown("<div class='section-title'>履歴（編集/削除）</div>", unsafe_allow_html=True)
        st.caption("最新10件。展開→変更→保存 / 削除。")

        show = st.session_state.matches[:10]
        if not show:
            st.caption("まだ履歴がありません。")
        else:
            deck_names = [d["name"] for d in st.session_state.deck_types]

            for m in show:
                res_text = "勝" if m["result"] == "win" else "敗"
                res_color = "#10b981" if m["result"] == "win" else "#ef4444"
                ts = m["timestamp"].replace("T", " ")

                header = f"{ts} | {m['my_deck']} vs {m['opponent_deck']} → {res_text}"
                with st.expander(header, expanded=False):
                    st.markdown(f"<div style='color:{res_color}; font-weight:900; margin-bottom:6px;'>結果: {res_text}</div>", unsafe_allow_html=True)

                    c1, c2, c3 = st.columns([1.2, 1.2, 0.8], gap="small")
                    with c1:
                        new_my = st.selectbox(
                            "マイデッキ",
                            deck_names,
                            index=deck_names.index(m["my_deck"]) if m["my_deck"] in deck_names else 0,
                            key=f"edit_my_{m['id']}",
                        )
                    with c2:
                        new_opp = st.selectbox(
                            "相手デッキ",
                            deck_names,
                            index=deck_names.index(m["opponent_deck"]) if m["opponent_deck"] in deck_names else 0,
                            key=f"edit_opp_{m['id']}",
                        )
                    with c3:
                        new_res = st.selectbox(
                            "勝敗",
                            ["win", "loss"],
                            index=0 if m["result"] == "win" else 1,
                            format_func=lambda x: "勝利" if x == "win" else "敗北",
                            key=f"edit_res_{m['id']}",
                        )

                    b1, b2 = st.columns([1, 1], gap="small")
                    if b1.button("変更を保存", key=f"save_{m['id']}"):
                        update_match(m["id"], new_my, new_opp, new_res)
                        st.success("更新しました")
                        st.rerun()
                    if b2.button("この履歴を削除", key=f"del_{m['id']}"):
                        delete_match(m["id"])
                        st.success("削除しました")
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# =============================
# 集計タブ（表＋メトリクス）
# =============================
with tab_stats:
    matches_all = st.session_state.matches
    if not matches_all:
        st.info("まだ戦績がありません。入力タブで記録してください。")
        st.stop()

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    # st.markdown("<div class='section-title'>集計対象</div>", unsafe_allow_html=True)

    # ---- 集計対象（入力タブと同じ：クラスごと）
    # ※ 戦績に一度でも登場したマイデッキのみを表示
    mydecks_in_stats = sorted(list({m["my_deck"] for m in matches_all}))
    mydecks_in_stats_set = set(mydecks_in_stats)

    decks_by_class = {k: [] for k in CLASS_ORDER}
    for d in st.session_state.deck_types:
        if d["name"] in mydecks_in_stats_set:
            decks_by_class.get(d["class"], []).append(d["name"])

    # ---- 全体
    # all_selected = (st.session_state.stats_mydeck_filter == "")
    # if st.button("✅ 全体" if all_selected else "全体", key="stats_scope_all", use_container_width=True,
    #              type="primary" if all_selected else "secondary"):
    #     st.session_state.stats_mydeck_filter = ""
    #     save_data()
    #     st.rerun()

    PER_ROW_STATS = 3
    for ck in CLASS_ORDER:
        names = decks_by_class.get(ck, [])
        if not names:
            continue
        info = CLASS_COLORS[ck]
        st.markdown(
            f"<div style='margin-top:10px; margin-bottom:6px; color:{info['color']}; font-weight:900;'>● {info['name']}</div>",
            unsafe_allow_html=True,
        )
        for i in range(0, len(names), PER_ROW_STATS):
            cols = st.columns(PER_ROW_STATS, gap="small")
            chunk = names[i:i+PER_ROW_STATS]
            for j in range(PER_ROW_STATS):
                if j >= len(chunk):
                    cols[j].empty()
                    continue
                name = chunk[j]
                selected = (st.session_state.stats_mydeck_filter == name)
                label = f"✅ {name}" if selected else name
                with cols[j]:
                    if st.button(label, key=f"stats_{ck}_{name}", use_container_width=True,
                                 type="primary" if selected else "secondary"):
                        st.session_state.stats_mydeck_filter = name
                        save_data()
                        st.rerun()
# ---- スコープ
    if st.session_state.stats_mydeck_filter:
        scope_label = st.session_state.stats_mydeck_filter
        matches_scope = [m for m in matches_all if m["my_deck"] == scope_label]
        scope_cls = get_deck_class(scope_label)
        scope_color = CLASS_COLORS.get(scope_cls, CLASS_COLORS["E"])["color"]
    else:
        scope_label = "全体"
        matches_scope = matches_all
        scope_color = "#8b5cf6"

    total, wins, losses, win_rate = compute_stats(matches_scope)
    streak = compute_win_streak(matches_scope)

    # メトリクス：左ラインはスコープ色に寄せる
    st.markdown(f"<style>.metric-card .accent-line{{ background:{scope_color} !important; }}</style>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="metrics-wrap">
      <div class="metric-card">
        <div class="accent-line"></div>
        <div class="metric-top">
          <div class="metric-label">対象</div>
          <div class="metric-badge">SCOPE</div>
        </div>
        <div class="metric-value">{scope_label}</div>
      </div>

      <div class="metric-card">
        <div class="accent-line"></div>
        <div class="metric-top">
          <div class="metric-label">勝敗</div>
          <div class="metric-badge">W-L</div>
        </div>
        <div class="metric-value">{wins}勝 {losses}敗</div>
      </div>

      <div class="metric-card">
        <div class="accent-line"></div>
        <div class="metric-top">
          <div class="metric-label">勝率</div>
          <div class="metric-badge">WR</div>
        </div>
        <div class="metric-value">{win_rate:.1f}%</div>
      </div>

      <div class="metric-card">
        <div class="accent-line"></div>
        <div class="metric-top">
          <div class="metric-label">連勝</div>
          <div class="metric-badge">STREAK</div>
        </div>
        <div class="metric-value">{streak}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ---- 対面表（選択したマイデッキのみ） + 得意デッキTop3（左右レイアウト）
    left_col, right_col = st.columns([2.2, 1.3], gap="large")

    # ---- 左：相手デッキ相性（選択したマイデッキのみ）
    with left_col:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        if st.session_state.stats_mydeck_filter:
            st.markdown(f"<div class='section-title'>相手デッキ相性：{scope_label}</div>", unsafe_allow_html=True)
            df_opp = build_opponent_table(matches_scope)
            if df_opp.empty:
                st.caption("対面データがありません。")
            else:
                st.dataframe(df_opp, use_container_width=True, hide_index=True)
        else:
            st.markdown("<div class='section-title'>相手デッキ相性</div>", unsafe_allow_html=True)
            st.caption("上の「集計対象」でマイデッキを選ぶと、対面表を表示します。")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---- 右：得意デッキ Top3（勝率ベース）- 添付イメージ風
    with right_col:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>得意デッキ Top3（勝率）</div>", unsafe_allow_html=True)

        df_md = build_mydeck_table(matches_all)
        if df_md.empty:
            st.caption("データがありません。")
        else:
            # 少数試合でのブレを避けたいので、まずは「3戦以上」を優先してランキング
            df_rank_base = df_md.copy()
            df_rank_3 = df_rank_base[df_rank_base["Matches"] >= 3]
            df_rank = df_rank_3 if not df_rank_3.empty else df_rank_base
            df_rank = df_rank.sort_values(["WinRate(%)", "Matches"], ascending=[False, False]).reset_index(drop=True).head(3)

            # カード描画（NO.1〜3 + デッキ名 + 勝率）
            for i, (_, r) in enumerate(df_rank.iterrows(), start=1):
                # build_mydeck_table() は列名が "Deck" / "WinRate(%)" / "Matches"
                deck = r.get("Deck", "")
                wr = r.get("WinRate(%)", 0.0)
                n = int(r.get("Matches", 0))
                st.markdown(
                    f"""
                    <div class="rank-card rank-{i}">
                      <div class="rank-left">
                        <div class="rank-no">NO.{i}</div>
                        <div>
                          <div class="rank-deck">{deck}</div>
                          <div class="rank-sub">n={n}</div>
                        </div>
                      </div>
                      <div class="rank-rate">{wr:.1f}%</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            

        st.markdown("</div>", unsafe_allow_html=True)

    # ---- Export

    st.download_button(
        "データを書き出し(JSON)",
        data=json.dumps(
            {
                "user_id": st.session_state.user_id,
                "deck_types": st.session_state.deck_types,
                "matches": st.session_state.matches,
            },
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
        file_name=f"shadowverse_tracker_{st.session_state.user_id}.json",
        mime="application/json",
    )

