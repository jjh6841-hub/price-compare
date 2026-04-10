import re
import streamlit as st
import pandas as pd
import psycopg2
import json
import base64
from pathlib import Path
import streamlit.components.v1 as components

CONFIG_FILE = Path(__file__).parent / "config.json"

# ── 버튼 정의 ─────────────────────────────────────────────────────────────────
BUTTON_GROUPS = [
    "수가_급여", "수가_비급여",
    "약가_급여", "약가_비급여",
    "재료대_급여", "재료대_비급여",
    "UBLAB",
]
ACTIONS = ["신설", "변경", "삭제"]

MUTED = {
    "신설": {"bd": "#86efac", "tx": "#15803d"},
    "변경": {"bd": "#93c5fd", "tx": "#1d4ed8"},
    "삭제": {"bd": "#fca5a5", "tx": "#b91c1c"},
}

HIGHLIGHT_KEYWORDS = {
    "비급여": "#8b5cf6",
    "신설":   "#10b981",
    "변경":   "#3b82f6",
    "삭제":   "#ef4444",
    "급여":   "#f59e0b",
}

# ── 테마별 인라인 색상 ─────────────────────────────────────────────────────────
THEME_COLORS = {
    "light": {
        "sheet_bg":     "#f8fafc",
        "sheet_border": "#e2e8f0",
        "group_label":  "#374151",
        "badge_bg":     "#fff",
        "btn_bg":       "#fff",
        "muted_text":   "#9ca3af",
        "result_count": "#6b7280",
        "placeholder":  "#9ca3af",
    },
    "dark": {
        "sheet_bg":     "#1e2030",
        "sheet_border": "#464a59",
        "group_label":  "#e5e7eb",
        "badge_bg":     "#262730",
        "btn_bg":       "#262730",
        "muted_text":   "#9ca3af",
        "result_count": "#a0aec0",
        "placeholder":  "#6b7280",
    },
}

DARK_CSS = """
<style>
/* ── DARK MODE ────────────────────────────────────────────────── */

/* 주 배경 */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background-color: #0e1117 !important;
}
.block-container {
    background-color: #0e1117 !important;
}

/* 사이드바 */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div:first-child {
    background-color: #1a1c24 !important;
}

/* 입력 필드 */
div[data-baseweb="input"],
div[data-baseweb="input"] > div {
    background-color: #262730 !important;
    border: 1px solid #7a7f96 !important;
}
input[type="text"], input[type="password"] {
    background-color: #262730 !important;
    color: #fafafa !important;
}
input::placeholder { color: #686880 !important; }

/* 메인 버튼 배경/테두리만 — color는 JS paint()가 관리 */
button[data-baseweb="button"],
button[data-testid^="stBaseButton"] {
    background:   #262730 !important;
    border-color: #565a6a !important;
}
/* 사이드바 secondary */
section[data-testid="stSidebar"] button[kind="secondary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
    background:   #363842 !important;
    color:        #fafafa !important;
    border-color: #565a6a !important;
}
/* 사이드바 primary (저장) */
section[data-testid="stSidebar"] button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    background:   #1565C0 !important;
    color:        #ffffff !important;
    border-color: #1565C0 !important;
}

/* 텍스트 */
.stMarkdown p, label { color: #e0e0e8 !important; }
h1, h2, h3           { color: #fafafa  !important; }
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label { color: #e0e0e8 !important; }

/* 구분선 */
hr { border-color: #464a59 !important; }
div[data-testid="column"]:first-of-type {
    border-right-color: #464a59 !important;
}

/* 알림 박스 */
div[data-testid="stAlert"] {
    background-color: #1e2030 !important;
    border-color:     #565a6a !important;
}
div[data-testid="stAlert"] p,
div[data-testid="stAlert"] span { color: #fafafa !important; }

/* 파일 업로더 */
[data-testid="stFileUploader"] section {
    background-color: #1e2030 !important;
    border-color:     #565a6a !important;
}
[data-testid="stFileUploader"] span { color: #9090a8 !important; }

/* border=True 컨테이너 */
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    background-color: #1a1c24 !important;
    border-color:     #565a6a !important;
}
</style>
"""


def highlight_sheet_name(name: str) -> str:
    keywords = sorted(HIGHLIGHT_KEYWORDS, key=len, reverse=True)
    pattern  = "(" + "|".join(re.escape(k) for k in keywords) + ")"
    def repl(m):
        kw = m.group(0)
        c  = HIGHLIGHT_KEYWORDS[kw]
        return (f'<span style="background:{c};color:#fff;padding:0 5px;'
                f'border-radius:3px;font-weight:700;font-size:0.8em;">{kw}</span>')
    return re.sub(pattern, repl, name)


# ── config.json 읽기/쓰기 ──────────────────────────────────────────────────────
def load_config():
    if not CONFIG_FILE.exists():
        return None
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        raw["password"] = base64.b64decode(raw.get("password_b64", "")).decode()
        return raw
    except Exception:
        return None

def save_config(host, port, dbname, user, password):
    existing = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    data = {
        "host":         host,
        "port":         int(port),
        "dbname":       dbname,
        "user":         user,
        "password_b64": base64.b64encode(password.encode()).decode(),
        "theme":        existing.get("theme", "light"),
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_theme(theme: str):
    existing = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing["theme"] = theme
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

def try_connect(cfg):
    conn = psycopg2.connect(
        host=cfg["host"], port=cfg["port"],
        dbname=cfg["dbname"], user=cfg["user"], password=cfg["password"],
    )
    conn.close()


# ══════════════════════════════════════════════════════════════════════════════
#  페이지 설정 + 전역 CSS
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="수가·약가·재료대 비교 조회",
    page_icon="🏥",
    layout="wide",
)

st.markdown("""
<style>
/* ── 사이드바: 너비 확보 + 스크롤 허용 ── */
section[data-testid="stSidebar"] {
    width: 260px    !important;
    min-width: 260px !important;
    overflow-y: auto !important;
}
section[data-testid="stSidebar"] > div:first-child {
    width: 260px !important;
    min-width: 260px !important;
    padding: 1.2rem 1rem !important;
    overflow-y: auto !important;
}

/* ── 메인 영역: 상단 패딩 확보 ── */
.block-container {
    padding: 1.4rem 1.2rem 0.5rem !important;
    max-width: 100% !important;
}

/* ── 메인 헤더 앱 타이틀 잘림 방지 ── */
header[data-testid="stHeader"] { display: none !important; }

/* ── 컬럼 간격 ── */
[data-testid="stColumns"] { gap: 0.4rem !important; }
[data-testid="column"]    { padding: 0  !important; }

/* ── 좌우 패널 구분선 ── */
div[data-testid="column"]:first-of-type {
    border-right: 1px solid #e5e7eb;
    padding-right: 1rem !important;
}
div[data-testid="column"]:last-of-type {
    padding-left: 1rem !important;
}

/* ── 버튼 (26px 고정) ── */
button[data-baseweb="button"],
button[data-testid^="stBaseButton"] {
    height:        26px   !important;
    min-height:    26px   !important;
    padding:       0 8px  !important;
    font-size:     0.68rem !important;
    font-weight:   600    !important;
    border-radius: 4px    !important;
    line-height:   26px   !important;
    background:    #fff   !important;
    transition:    opacity 0.12s;
}
button[data-baseweb="button"]:hover { opacity: 0.75; }

/* ── 버튼 행 균일 간격 ── */
.btn-row {
    display: flex;
    align-items: center;
    margin-bottom: 4px;
}

/* ── 요소 세로 여백 최소화 ── */
.element-container { margin-bottom: 3px !important; }
div[data-testid="stVerticalBlock"] > div { gap: 0 !important; }

/* ── 파일 업로더 컴팩트 ── */
[data-testid="stFileUploader"] { padding: 0 !important; }
[data-testid="stFileUploader"] section {
    padding: 0.35rem 0.5rem !important;
    min-height: 0 !important;
}
[data-testid="stFileUploader"] span { font-size: 0.72rem !important; }

/* ── 타이포그래피 ── */
h1 {
    font-size: 0.98rem !important;
    font-weight: 700   !important;
    margin: 0 0 0.3rem !important;
    line-height: 1.3   !important;
}
p, .stMarkdown p, label, small { font-size: 0.73rem !important; }
.stCaption { font-size: 0.65rem !important; }

/* ── 구분선 ── */
hr { margin: 0.3rem 0 !important; }

/* ── 알림/정보 박스 (메인) ── */
div[data-testid="stAlert"] {
    padding:   0.3rem 0.7rem !important;
    font-size: 0.7rem        !important;
}

/* ── 데이터프레임 ── */
[data-testid="stDataFrame"] { width: 100% !important; }

/* ── 사이드바 폰트 ── */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] small { font-size: 0.73rem !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2    { font-size: 0.85rem !important; }
section[data-testid="stSidebar"] input { font-size: 0.73rem !important; }

/* ── 사이드바 알림 박스: 아이콘-텍스트 수평 정렬 ── */
section[data-testid="stSidebar"] div[data-testid="stAlert"] {
    display: flex        !important;
    align-items: center  !important;
    gap: 0.4rem          !important;
    padding: 0.45rem 0.7rem !important;
    font-size: 0.78rem   !important;
    line-height: 1.3     !important;
}
section[data-testid="stSidebar"] div[data-testid="stAlert"] > * {
    flex-shrink: 0;
}

/* ── 사이드바 버튼: 전역 26px 오버라이드 ── */
section[data-testid="stSidebar"] button[data-baseweb="button"],
section[data-testid="stSidebar"] button[data-testid^="stBaseButton"] {
    height:      36px    !important;
    min-height:  36px    !important;
    line-height: 36px    !important;
    font-size:   0.78rem !important;
    font-weight: 600     !important;
    padding:     0 14px  !important;
    white-space: nowrap  !important;
    overflow:    visible !important;
}
/* secondary (일반) 버튼 */
section[data-testid="stSidebar"] button[kind="secondary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
    background: #f0f2f6 !important;
    color: #262730      !important;
    border-color: #d1d5db !important;
}
/* primary (저장) 버튼 */
section[data-testid="stSidebar"] button[kind="primary"],
section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    background: #1976D2 !important;
    color: #ffffff      !important;
    border-color: #1976D2 !important;
}

/* ── 테마 토글 버튼 ── */
button[data-testid="stBaseButton-secondary"].theme-toggle,
div[data-testid="column"]:last-of-type > div > div > div > button {
    height:        30px  !important;
    min-height:    30px  !important;
    line-height:   30px  !important;
    font-size:     1rem  !important;
    padding:       0 6px !important;
    border-radius: 50%   !important;
    float: right;
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  세션 초기화
# ══════════════════════════════════════════════════════════════════════════════
if "initialized" not in st.session_state:
    cfg = load_config()
    st.session_state.config        = cfg
    st.session_state.db_connected  = False
    st.session_state.result_key    = None
    st.session_state.df_result     = None
    st.session_state.theme         = (cfg.get("theme", "light") if cfg else "light")
    st.session_state.initialized   = True
    if cfg:
        try:
            try_connect(cfg)
            st.session_state.db_connected = True
        except Exception:
            pass

# ── 다크모드 CSS 주입 ──────────────────────────────────────────────────────────
if st.session_state.theme == "dark":
    st.markdown(DARK_CSS, unsafe_allow_html=True)

# ── 현재 테마 색상 ─────────────────────────────────────────────────────────────
T = THEME_COLORS[st.session_state.theme]


# ══════════════════════════════════════════════════════════════════════════════
#  사이드바 — DB 접속 설정만
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    if st.session_state.db_connected:
        st.success("✅ DB 연결됨")
    elif st.session_state.config:
        st.error("❌ 연결 실패")
    else:
        st.warning("⚠️ 접속 설정 필요")

    with st.container(border=True):
            st.markdown("**DB 접속 정보**")
            cfg = st.session_state.config or {}

            f_host   = st.text_input("Host",     value=cfg.get("host",   "192.168.246.64"))
            f_port   = st.text_input("Port", value=str(cfg.get("port", 5432)))
            f_dbname = st.text_input("Database", value=cfg.get("dbname", "ysr2000"))
            f_user   = st.text_input("Username", value=cfg.get("user",   "edba"))
            f_pw     = st.text_input(
                "Password", type="password",
                placeholder="변경 시만 입력" if cfg.get("password") else "비밀번호 입력",
            )
            effective_pw = f_pw or cfg.get("password", "")

            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("💾 저장", use_container_width=True, type="primary"):
                    if not effective_pw:
                        st.error("비밀번호를 입력하세요.")
                    else:
                        save_config(f_host, f_port, f_dbname, f_user, effective_pw)
                        new_cfg = {"host": f_host, "port": int(f_port),
                                   "dbname": f_dbname, "user": f_user, "password": effective_pw}
                        st.session_state.config = new_cfg
                        try:
                            try_connect(new_cfg)
                            st.session_state.db_connected = True

                        except Exception as e:
                            st.session_state.db_connected = False
                            st.error(f"저장됨, 연결 실패:\n{e}")
                        st.rerun()
            with bc2:
                if st.button("🔌 테스트", use_container_width=True):
                    if not effective_pw:
                        st.error("비밀번호를 입력하세요.")
                    else:
                        try:
                            try_connect({"host": f_host, "port": int(f_port),
                                         "dbname": f_dbname, "user": f_user,
                                         "password": effective_pw})
                            st.success("✅ 성공!")
                        except Exception as e:
                            st.error(f"❌ 실패:\n{e}")


# ══════════════════════════════════════════════════════════════════════════════
#  메인 — 타이틀 + 테마 토글
# ══════════════════════════════════════════════════════════════════════════════
title_col, toggle_col = st.columns([30, 1])
with title_col:
    st.markdown("<h1>🏥 수가·약가·재료대 비교 조회</h1>", unsafe_allow_html=True)
with toggle_col:
    toggle_icon = "☀️" if st.session_state.theme == "dark" else "🌙"
    if st.button(toggle_icon, key="theme_toggle", help="다크/라이트 모드 전환"):
        new_theme = "dark" if st.session_state.theme == "light" else "light"
        st.session_state.theme = new_theme
        save_theme(new_theme)
        st.rerun()

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  좌우 2컬럼 레이아웃
# ══════════════════════════════════════════════════════════════════════════════
left, right = st.columns([2, 3])

# ── 좌측: 엑셀 업로드 + 버튼 목록 ────────────────────────────────────────────
with left:
    # 엑셀 업로드
    st.markdown(
        f"<p style='font-size:0.68rem;font-weight:600;color:{T['muted_text']};"
        "letter-spacing:0.06em;text-transform:uppercase;margin:0 0 3px;'>"
        "Excel 업로드</p>", unsafe_allow_html=True)
    uploaded = st.file_uploader("", type=["xlsx", "xls"], label_visibility="collapsed")

    sheet_names = []
    if uploaded:
        try:
            xl = pd.ExcelFile(uploaded)
            sheet_names = xl.sheet_names
            items = "  |  ".join(
                f'<span style="font-size:0.7rem;">{highlight_sheet_name(n)}</span>'
                for n in sheet_names
            )
            st.markdown(
                f"<div style='background:{T['sheet_bg']};border:1px solid {T['sheet_border']};"
                f"border-radius:4px;padding:4px 8px;margin-bottom:4px;line-height:1.8;'>"
                f"{items}</div>",
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.error(f"파일 오류: {e}")

    st.divider()

    # 비교 버튼 목록
    st.markdown(
        f"<p style='font-size:0.68rem;font-weight:600;color:{T['muted_text']};"
        "letter-spacing:0.06em;text-transform:uppercase;margin:0 0 4px;'>"
        "비교 실행</p>", unsafe_allow_html=True)

    for group in BUTTON_GROUPS:
        g0, g1, g2, g3 = st.columns([3, 1, 1, 1])
        with g0:
            st.markdown(
                f"<div style='height:26px;line-height:26px;font-size:0.73rem;"
                f"font-weight:600;color:{T['group_label']};overflow:hidden;white-space:nowrap;"
                f"padding-right:4px;'>{group}</div>",
                unsafe_allow_html=True,
            )
        for col, action in zip([g1, g2, g3], ACTIONS):
            with col:
                if st.button(action, key=f"{group}_{action}", use_container_width=True):
                    st.session_state.result_key = f"{group}_{action}"
                    st.session_state.df_result  = None
                    st.rerun()

# ── 우측: 결과 ────────────────────────────────────────────────────────────────
with right:
    st.markdown(
        f"<p style='font-size:0.65rem;font-weight:600;color:{T['muted_text']};"
        "letter-spacing:0.07em;text-transform:uppercase;margin:0 0 4px;'>"
        "결과</p>",
        unsafe_allow_html=True,
    )

    rk = st.session_state.result_key
    df  = st.session_state.df_result

    if rk:
        action = rk.rsplit("_", 1)[1]
        m = MUTED[action]
        st.markdown(
            f"<span style='display:inline-block;padding:2px 12px;border-radius:4px;"
            f"border:1px solid {m['bd']};color:{m['tx']};background:{T['badge_bg']};"
            f"font-size:0.7rem;font-weight:600;margin-bottom:5px;'>"
            f"{rk}</span>",
            unsafe_allow_html=True,
        )

        if df is None:
            st.info("⏳ 준비 중입니다. 쿼리가 등록되면 결과가 표시됩니다.")
        elif len(df) == 0:
            st.warning("조회된 데이터가 없습니다.")
        else:
            st.markdown(
                f"<p style='font-size:0.7rem;color:{T['result_count']};margin:0 0 4px;'>"
                f"총 <b>{len(df):,}건</b></p>",
                unsafe_allow_html=True,
            )
            st.dataframe(df, use_container_width=True, height=420)
    else:
        st.markdown(
            f"<div style='color:{T['placeholder']};font-size:0.75rem;padding-top:0.4rem;'>"
            "버튼을 클릭하면 결과가 표시됩니다.</div>",
            unsafe_allow_html=True,
        )

# ── JS 버튼 색상 주입 ─────────────────────────────────────────────────────────
# setProperty(..., 'important') 로 CSS !important 를 이겨야 색상이 표시됨
is_dark = "true" if st.session_state.theme == "dark" else "false"
components.html(f"""
<script>
(function () {{
    var DARK = {is_dark};
    var C = {{
        '신설': {{bd:'#86efac', tx:'#15803d', dbg:'#1a3a1a'}},
        '변경': {{bd:'#93c5fd', tx:'#1d4ed8', dbg:'#1a1a3a'}},
        '삭제': {{bd:'#fca5a5', tx:'#b91c1c', dbg:'#3a1a1a'}}
    }};
    function paint() {{
        window.parent.document.querySelectorAll('button').forEach(function(b) {{
            var t = b.innerText.trim();
            if (C[t]) {{
                var bg = DARK ? C[t].dbg : '#fff';
                b.style.setProperty('background',    bg,       'important');
                b.style.setProperty('border-color',  C[t].bd,  'important');
                b.style.setProperty('color',         C[t].tx,  'important');
                b.style.fontWeight = '600';
            }}
        }});
    }}
    paint();
    new MutationObserver(paint).observe(
        window.parent.document.body, {{childList:true, subtree:true}}
    );
}})();
</script>
""", height=0, scrolling=False)
