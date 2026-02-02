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
    "E":  {"name": "エルフ",     "color": "#10b981", "tag_bg": "rgba(16,185,129,0.10)", "tag_bd": "rgba(16,185,129,0.35)"},
    "R":  {"name": "ロイヤル",   "color": "#eab308", "tag_bg": "rgba(234,179,8,0.10)",  "tag_bd": "rgba(234,179,8,0.35)"},
    "D":  {"name": "ドラゴン",   "color": "#f97316", "tag_bg": "rgba(249,115,22,0.10)", "tag_bd": "rgba(249,115,22,0.35)"},
    "W":  {"name": "ウィッチ",   "color": "#a855f7", "tag_bg": "rgba(168,85,247,0.10)", "tag_bd": "rgba(168,85,247,0.35)"},
    "Ni": {"name": "ナイトメア", "color": "#ef4444", "tag_bg": "rgba(239,68,68,0.10)",  "tag_bd": "rgba(239,68,68,0.35)"},
    # Bishopの白は暗背景で沈むので、文字は少しグレー寄り + 枠は強め
    "B":  {"name": "ビショップ", "color": "#d1d5db", "tag_bg": "rgba(229,231,235,0.08)", "tag_bd": "rgba(229,231,235,0.28)"},
    "Nm": {"name": "ネメシス",   "color": "#06b6d4", "tag_bg": "rgba(6,182,212,0.10)",  "tag_bd": "rgba(6,182,212,0.35)"},
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
        "opp_class_filter": CLASS_ORDER,  # 対面集計用クラスフィルタ（相手クラス）
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
        if not isinstance(base["opp_class_filter"], list) or len(base["opp_class_filter"]) == 0:
            base["opp_class_filter"] = CLASS_ORDER
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
        "opp_class_filter": st.session_state.opp_class_filter,
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
    # クラス順に固定
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
    my_cls = get_deck_class(my)
    opp_cls = get_deck_class(opp)
    new_match = {
        "id": int(datetime.now().timestamp() * 1000),
        "my_deck": my,
        "my_deck_class": my_cls,
        "opponent_deck": opp,
        "opponent_deck_class": opp_cls,
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

def build_deck_summary_table(matches_all):
    """全体 + 各デッキ（マイデッキ別）の戦績表。マッチ数でソート。"""
    rows = []
    t, w, l, wr = compute_stats(matches_all)
    rows.append({"Deck": "(全体)", "Matches": t, "Wins": w, "Losses": l, "WinRate(%)": wr})

    mydecks = sorted(list({m["my_deck"] for m in matches_all}))
    for md in mydecks:
        ms = [m for m in matches_all if m["my_deck"] == md]
        t, w, l, wr = compute_stats(ms)
        rows.append({"Deck": md, "Matches": t, "Wins": w, "Losses": l, "WinRate(%)": wr})

    df = pd.DataFrame(rows)
    df = df.sort_values(by=["Matches", "WinRate(%)"], ascending=[False, False]).reset_index(drop=True)
    return df

def build_opponent_table(matches_filtered):
    """対面別集計（相手デッキ単位）"""
    opps = sorted(list({m["opponent_deck"] for m in matches_filtered}))
    rows = []
    for opp in opps:
        ms = [m for m in matches_filtered if m["opponent_deck"] == opp]
        t, w, l, wr = compute_stats(ms)
        rows.append({"Opponent": opp, "Matches": t, "Wins": w, "Losses": l, "WinRate(%)": wr})
    df = pd.DataFrame(rows)
    return df

def build_heatmap_df(matches_filtered):
    """my_deck × opponent_deck の勝率（%）と試合数"""
    if not matches_filtered:
        return None, None
    df = pd.DataFrame(matches_filtered)
    # count
    cnt = pd.pivot_table(df, index="my_deck", columns="opponent_deck", values="result", aggfunc="count", fill_value=0)
    # winrate
    win = pd.pivot_table(df[df["result"] == "win"], index="my_deck", columns="opponent_deck", values="result", aggfunc="count", fill_value=0)
    # align
    win = win.reindex(index=cnt.index, columns=cnt.columns, fill_value=0)
    with pd.option_context("mode.use_inf_as_na", True):
        wr = (win / cnt.replace(0, pd.NA) * 100).round(1)
    wr = wr.fillna(0.0)
    return wr, cnt

# =============================
# UI
# =============================
st.set_page_config(page_title="Shadowverse WB Tracker", layout="wide")

# シンプル＆小さめ＆見やすさ優先
st.markdown("""
<style>
.stApp { background:#0f0e1a; color:#e5e7eb; }
h1 { font-size: 22px !important; margin: 0.2rem 0 0.2rem 0 !important; }
h2 { font-size: 16px !important; margin-top: 0.4rem !important; }
h3 { font-size: 14px !important; margin-top: 0.4rem !important; }

.block-container { padding-top: 5rem; padding-bottom: 0.8rem; max-width: 1250px; }

.card {
  background: rgba(30, 27, 75, 0.38);
  border: 1px solid rgba(139, 92, 246, 0.14);
  border-radius: 10px;
  padding: 12px;
}

.small-muted { color: #9ca3af; font-size: 12px; }
.section-title { font-weight: 800; letter-spacing: 0.3px; }

/* ボタンを小さく、改行しにくく */
div.stButton > button {
  border-radius: 10px;
  border: 1px solid rgba(139, 92, 246, 0.28);
  background: rgba(139, 92, 246, 0.08);
  color: #e5e7eb;
  padding: 0.25rem 0.55rem;
  font-size: 12px;
  line-height: 1.1;
  white-space: nowrap;    /* 改行抑止 */
  overflow: hidden;
  text-overflow: ellipsis; /* 万一は省略表示 */
  font-family: "Inter", "Noto Sans JP", system-ui, sans-serif;
  width: 100% !important;     /* 列幅に必ず収める */
  display: block !important;
}

/* 勝敗ボタン */
.winbtn button {
  background: rgba(16,185,129,0.9) !important;
  border-color: rgba(16,185,129,0.95) !important;
  color: #071a12 !important;
  font-weight: 800 !important;
}
.lossbtn button {
  background: rgba(239,68,68,0.9) !important;
  border-color: rgba(239,68,68,0.95) !important;
  color: #1a0707 !important;
  font-weight: 800 !important;
}

/* 選択中の強調（Streamlitボタン自体はクラス付けられないので、ラベルに✅で対応） */

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
    st.session_state.opp_class_filter = data.get("opp_class_filter", CLASS_ORDER)
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

        # 折れ対策：1行のボタン数を減らして列を広くする（ここが効く）
        PER_ROW = 3  # 6だと狭すぎて折れる

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

        if st.session_state.my_deck:
            ci = CLASS_COLORS.get(get_deck_class(st.session_state.my_deck), CLASS_COLORS["E"])
            st.markdown(
                f"<div class='small-muted' style='margin-top:10px;'>選択中：</div>"
                f"<div style='font-weight:900; color:{ci['color']};'>{st.session_state.my_deck}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("まずはマイデッキを選択してください。")

        st.divider()

        st.markdown("<div class='section-title'>デッキ管理</div>", unsafe_allow_html=True)
        with st.expander("デッキ追加", expanded=False):
            new_name = st.text_input("デッキ名", value="", placeholder="例: 新型〇〇", key="new_deck_name")
            new_cls = st.selectbox("クラス", CLASS_ORDER, format_func=lambda k: CLASS_COLORS[k]["name"], key="new_deck_class")
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

    # ---- 右：対戦相手選択 & 勝敗入力 & 履歴（編集/削除）
    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>対戦入力</div>", unsafe_allow_html=True)

        if not st.session_state.my_deck:
            st.warning("左でマイデッキを選択してください。")
        else:
            grouped = grouped_decks()
            PER_ROW_OPP = 3  # 相手側も広め

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
                    f"<div class='small-muted' style='margin-top:10px;'>対戦相手：</div>"
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
        st.caption("最新10件表示。編集は展開して変更→保存。")

        show = st.session_state.matches[:10]
        if not show:
            st.caption("まだ履歴がありません。")
        else:
            # 編集用候補
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
                        new_my = st.selectbox("マイデッキ", deck_names, index=deck_names.index(m["my_deck"]) if m["my_deck"] in deck_names else 0, key=f"edit_my_{m['id']}")
                    with c2:
                        new_opp = st.selectbox("相手デッキ", deck_names, index=deck_names.index(m["opponent_deck"]) if m["opponent_deck"] in deck_names else 0, key=f"edit_opp_{m['id']}")
                    with c3:
                        new_res = st.selectbox("勝敗", ["win", "loss"], index=0 if m["result"] == "win" else 1, format_func=lambda x: "勝利" if x == "win" else "敗北", key=f"edit_res_{m['id']}")

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
# 集計タブ
# =============================
with tab_stats:
    matches_all = st.session_state.matches
    if not matches_all:
        st.info("まだ戦績がありません。入力タブで記録してください。")
        st.stop()

    # --- 集計対象（my_deckで絞り込み）: UIはボタン維持（selectboxは使わない）
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>集計対象（マイデッキ）</div>", unsafe_allow_html=True)
    st.caption("全体/デッキ別で表示を切り替えます。")

    # 「全体」ボタン
    cols = st.columns([1, 3], gap="small")
    with cols[0]:
        all_selected = (st.session_state.stats_mydeck_filter == "")
        if st.button("✅ 全体" if all_selected else "全体", key="stats_all"):
            st.session_state.stats_mydeck_filter = ""
            save_data()
            st.rerun()

    # デッキを「使用回数（マッチ数）順」で並べる（あなたの要望）
    mydecks = sorted(list({m["my_deck"] for m in matches_all}))
    # 試合数でソート
    counts = {md: sum(1 for m in matches_all if m["my_deck"] == md) for md in mydecks}
    mydecks_sorted = sorted(mydecks, key=lambda x: counts.get(x, 0), reverse=True)

    # ボタン群（折れ対策で1行4つ）
    PER_ROW_STATS = 4
    for i in range(0, len(mydecks_sorted), PER_ROW_STATS):
        row = st.columns(PER_ROW_STATS, gap="small")
        chunk = mydecks_sorted[i:i+PER_ROW_STATS]
        for j in range(PER_ROW_STATS):
            if j >= len(chunk):
                row[j].empty()
                continue
            md = chunk[j]
            selected = (st.session_state.stats_mydeck_filter == md)
            label = f"✅ {md} ({counts.get(md,0)})" if selected else f"{md} ({counts.get(md,0)})"
            with row[j]:
                if st.button(label, key=f"stats_md_{md}"):
                    st.session_state.stats_mydeck_filter = md
                    save_data()
                    st.rerun()

    # フィルタ適用
    if st.session_state.stats_mydeck_filter:
        matches_scope = [m for m in matches_all if m["my_deck"] == st.session_state.stats_mydeck_filter]
        scope_label = st.session_state.stats_mydeck_filter
    else:
        matches_scope = matches_all
        scope_label = "全体"

    total, wins, losses, win_rate = compute_stats(matches_scope)
    streak = compute_win_streak(matches_scope)

    st.divider()
    s1, s2, s3, s4 = st.columns(4, gap="small")
    s1.metric("対象", scope_label)
    s2.metric("勝敗", f"{wins}勝 {losses}敗")
    s3.metric("勝率", f"{win_rate}%")
    s4.metric("連勝", f"{streak}")
    st.markdown("</div>", unsafe_allow_html=True)

    # --- 1) 表：全体 + 各デッキ（マッチ数でソート）
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>全体＋各デッキ（表）</div>", unsafe_allow_html=True)
    st.caption("マッチ数降順（同数なら勝率降順）")
    df_sum = build_deck_summary_table(matches_all)
    st.dataframe(df_sum, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- 2) 対面別：クラスフィルタ + 表
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>対面別（相手デッキ）</div>", unsafe_allow_html=True)

    # クラス別フィルタ（相手クラス）
    with st.expander("相手クラスフィルタ", expanded=False):
        labels = {k: CLASS_COLORS[k]["name"] for k in CLASS_ORDER}
        default = st.session_state.opp_class_filter if st.session_state.opp_class_filter else CLASS_ORDER
        selected = st.multiselect(
            "対象に含める相手クラス",
            options=CLASS_ORDER,
            default=default,
            format_func=lambda k: labels[k],
        )
        if len(selected) == 0:
            st.warning("最低1つは選んでください（全除外になるため）")
        else:
            st.session_state.opp_class_filter = selected
            save_data()

    opp_filter = st.session_state.opp_class_filter if st.session_state.opp_class_filter else CLASS_ORDER
    # 対面集計は「集計対象（全体/マイデッキ）」に加えて「相手クラス」で絞る
    matches_opp_scope = [m for m in matches_scope if m.get("opponent_deck_class", "E") in opp_filter]

    sort_mode = st.selectbox("並び順", ["使用回数順", "勝率順"], index=0)
    min_games = st.slider("最小試合数", 1, 30, 1)

    df_opp = build_opponent_table(matches_opp_scope)
    if df_opp is None or df_opp.empty:
        st.caption("対面データがありません。")
    else:
        df_opp = df_opp[df_opp["Matches"] >= min_games]
        if sort_mode == "使用回数順":
            df_opp = df_opp.sort_values(["Matches", "WinRate(%)"], ascending=[False, False])
        else:
            df_opp = df_opp.sort_values(["WinRate(%)", "Matches"], ascending=[False, False])
        st.dataframe(df_opp.reset_index(drop=True), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Export
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

