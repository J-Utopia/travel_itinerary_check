from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType
from typing import Any

import streamlit as st

from app.auth import header_configuration_status
from app.config import settings


GPTS_URL = "https://chatgpt.com/g/g-6a70449513408191a61cf43948a1ecf2-iljeongpyogeomsu-3-0"
SCRIPT_PATH = Path(__file__).with_name("일정표데이터추출.py")


def load_extractor() -> ModuleType:
    spec = importlib.util.spec_from_file_location("itinerary_extractor", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("일정표 데이터 추출 모듈을 불러올 수 없습니다.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_group_id(value: str) -> str:
    return re.sub(r"\D", "", value.strip())


def validate_group_id(value: str) -> str | None:
    group_id = normalize_group_id(value)
    if not group_id:
        return "단체번호를 입력해주세요."
    if len(group_id) < 6 or len(group_id) > 12:
        return "단체번호는 숫자 6~12자리로 입력해주세요."
    return None


@st.cache_data(ttl=1800, show_spinner=False)
def build_json_download(group_id: str) -> tuple[str, bytes, dict[str, Any]]:
    extractor = load_extractor()
    data = extractor.build_extraction(group_id)
    errors = extractor.validate_extraction(data)
    if errors:
        raise RuntimeError("추출 결과 검증 실패: " + ", ".join(errors[:5]))
    json_text = json.dumps(data, ensure_ascii=False, indent=2)
    return f"일정표_{group_id}.json", json_text.encode("utf-8"), data


def render_style() -> None:
    st.markdown(
        """
        <style>
        :root {
          --text-primary: #191f28;
          --text-secondary: #6b7684;
          --line: #e5e8eb;
          --blue: #3182f6;
          --blue-dark: #1b64da;
          --surface: #ffffff;
          --bg: #f7f8fa;
        }
        .stApp {
          background:
            radial-gradient(circle at 12% 4%, rgba(49, 130, 246, 0.10), transparent 26rem),
            linear-gradient(180deg, #ffffff 0%, var(--bg) 48%, #ffffff 100%);
          color: var(--text-primary);
        }
        .block-container {
          max-width: 860px;
          padding-top: 56px;
          padding-bottom: 56px;
        }
        .hero-title {
          margin: 0 0 10px;
          color: var(--text-primary);
          font-size: 38px;
          font-weight: 800;
          line-height: 1.18;
          letter-spacing: 0;
        }
        .hero-copy {
          margin: 0 0 28px;
          color: var(--text-secondary);
          font-size: 17px;
          line-height: 1.65;
        }
        .result-box {
          margin-top: 22px;
          padding: 20px;
          border: 1px solid #d8e8ff;
          border-radius: 8px;
          background: #f5f9ff;
        }
        .result-title {
          margin: 0 0 6px;
          color: var(--text-primary);
          font-size: 20px;
          font-weight: 750;
        }
        .result-copy {
          margin: 0;
          color: var(--text-secondary);
          font-size: 15px;
          line-height: 1.6;
        }
        .gpts-link {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-height: 46px;
          padding: 0 18px;
          border-radius: 8px;
          background: var(--text-primary);
          color: #fff !important;
          font-weight: 700;
          text-decoration: none !important;
        }
        .guide {
          margin-top: 18px;
          color: var(--text-secondary);
          font-size: 14px;
          line-height: 1.7;
          text-align: center;
        }
        .gpts-action {
          margin-top: 10px;
          text-align: center;
        }
        div[data-testid="stTextInput"] label p {
          color: var(--text-primary);
          font-size: 18px;
          font-weight: 750;
          line-height: 1.35;
        }
        div[data-testid="stTextInput"] div[data-baseweb="input"] {
          min-height: 54px;
          display: flex;
          align-items: center;
        }
        div[data-testid="stTextInput"] input {
          height: 54px;
          min-height: 54px;
          border-radius: 8px;
          font-size: 18px;
          line-height: 24px;
          padding: 15px 14px;
          display: flex;
          align-items: center;
        }
        div[data-testid="stButton"] button,
        div[data-testid="stDownloadButton"] button {
          min-height: 52px;
          border-radius: 8px;
          font-weight: 750;
        }
        div[data-testid="stButton"] button {
          background: var(--blue);
          border-color: var(--blue);
          color: #fff;
        }
        div[data-testid="stButton"] button:hover {
          background: var(--blue-dark);
          border-color: var(--blue-dark);
          color: #fff;
        }
        @media (max-width: 640px) {
          .block-container { padding: 32px 18px; }
          .hero-title { font-size: 30px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app() -> None:
    st.set_page_config(page_title="일정표 데이터 추출", page_icon="📄", layout="centered")
    render_style()
    headers_ready, header_status = header_configuration_status(settings)

    st.markdown('<h1 class="hero-title">일정표 데이터 추출</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-copy">단체번호를 입력하면 일정표 검수용 JSON 파일을 생성합니다. 생성 후 검수 진행 해주세요</p>',
        unsafe_allow_html=True,
    )

    if not headers_ready:
        st.warning("서버 인증 헤더가 설정되지 않아 추출을 실행할 수 없습니다.")
        st.caption(header_status)

    group_input = st.text_input(
        "단체번호",
        placeholder="예: 105514210",
        label_visibility="visible",
    )

    _, button_col, _ = st.columns([1, 2, 1])
    with button_col:
        extract_clicked = st.button("추출시작", use_container_width=True, disabled=not headers_ready)

    if extract_clicked:
        error_message = validate_group_id(group_input)
        if error_message:
            st.error(error_message)
        else:
            group_id = normalize_group_id(group_input)
            with st.spinner("일정표 데이터를 추출하고 있습니다."):
                try:
                    filename, payload, data = build_json_download(group_id)
                except Exception as exc:
                    st.error(
                        "일정표 추출에 실패했습니다. 서버 인증 헤더 또는 모두투어 API 상태를 확인해야 합니다."
                    )
                    st.caption(str(exc))
                else:
                    st.session_state["download"] = {
                        "filename": filename,
                        "payload": payload,
                        "group_id": group_id,
                        "title": data.get("title") or "",
                    }

    download = st.session_state.get("download")
    if download:
        st.markdown(
            """
            <div class="result-box">
              <p class="result-title">추출완료</p>
              <p class="result-copy">다운로드받으시겠습니까?</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _, download_col, _ = st.columns([1, 2, 1])
        with download_col:
            st.download_button(
                "JSON 다운로드",
                data=download["payload"],
                file_name=download["filename"],
                mime="application/json",
                use_container_width=True,
            )
        st.markdown(
            f"""
            <div class="guide">
              다운받은 파일을 아래 GPT 링크에 접속해서 일정표 검수를 진행해보세요.<br>
              GPT접속 → 다운받은 파일 첨부 → 일정표 검수가 진행됩니다.
            </div>
            <div class="gpts-action">
              <a class="gpts-link" href="{GPTS_URL}" target="_blank" rel="noopener noreferrer">GPT 접속</a>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    render_app()
