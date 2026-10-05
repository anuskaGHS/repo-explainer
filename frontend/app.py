"""Streamlit web interface for the Local GitHub Repository Code Explainer."""

import html
import os
import re
import requests
import streamlit as st

DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"


def resolve_backend_url() -> tuple[str, bool]:
    """Resolve BACKEND_URL from st.secrets, environment variables, or default.

    Resolution order:
    1. st.secrets["BACKEND_URL"] if it exists
    2. BACKEND_URL environment variable
    3. Default: "http://127.0.0.1:8000"

    Returns:
        tuple[str, bool]: (resolved_url, is_explicitly_configured)
    """
    # a) st.secrets["BACKEND_URL"] (wrapped in try/except because st.secrets can raise when missing)
    try:
        if hasattr(st, "secrets") and "BACKEND_URL" in st.secrets:
            val = str(st.secrets["BACKEND_URL"]).strip()
            if val:
                return val.rstrip("/"), True
    except Exception:
        pass

    # b) BACKEND_URL environment variable
    env_val = os.environ.get("BACKEND_URL", "").strip()
    if env_val:
        return env_val.rstrip("/"), True

    # c) Default localhost
    return DEFAULT_BACKEND_URL, False


BACKEND_URL, IS_EXPLICIT_BACKEND_URL = resolve_backend_url()
REQUEST_TIMEOUT = 1200  # 20 minutes for large codebases and local inference

st.set_page_config(
    page_title="GitHub Code Explainer | Local AI Codebase Intelligence",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom Light Theme CSS
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #0F172A;
    }

    /* Overall App Canvas */
    .stApp {
        background-color: #F8FAFC;
    }

    /* Top Brand Header */
    .header-wrapper {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 1.25rem 1.75rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }
    .header-brand {
        display: flex;
        align-items: center;
        gap: 0.9rem;
    }
    .header-icon-box {
        width: 46px;
        height: 46px;
        border-radius: 12px;
        background: linear-gradient(135deg, #2563EB 0%, #4F46E5 100%);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.4rem;
        box-shadow: 0 4px 8px rgba(37, 99, 235, 0.2);
    }
    .header-title-box h1 {
        font-size: 1.5rem;
        font-weight: 800;
        color: #0F172A;
        margin: 0;
        line-height: 1.2;
    }
    .header-title-box p {
        font-size: 0.88rem;
        color: #64748B;
        margin: 0.15rem 0 0 0;
    }
    .header-badges {
        display: flex;
        gap: 0.6rem;
        align-items: center;
        flex-wrap: wrap;
    }
    .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.78rem;
        font-weight: 600;
        padding: 0.35rem 0.75rem;
        border-radius: 9999px;
        border: 1px solid #E2E8F0;
        background: #F8FAFC;
        color: #334155;
    }
    .badge-pill.status-ok {
        background: #ECFDF5;
        border-color: #A7F3D0;
        color: #047857;
    }

    /* URL Entry Container Box */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 16px !important;
        box-shadow: 0 2px 4px -1px rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.03) !important;
        padding: 0.25rem 0.25rem !important;
    }

    .url-box-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 1.05rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.25rem;
    }
    .url-box-desc {
        font-size: 0.85rem;
        color: #64748B;
        margin-bottom: 0.85rem;
        line-height: 1.4;
    }

    /* Quick Examples Label */
    .examples-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.35rem;
        margin-bottom: 0.2rem;
    }

    /* Section Cards Styling */
    .explanation-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 1.5rem 1.75rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        position: relative;
        overflow: hidden;
    }
    .card-overview {
        border-left: 5px solid #2563EB;
    }
    .card-features {
        border-left: 5px solid #059669;
    }
    .card-technologies {
        border-left: 5px solid #7C3AED;
    }
    .card-workflow {
        border-left: 5px solid #D97706;
    }

    .card-header-bar {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        margin-bottom: 1rem;
        padding-bottom: 0.6rem;
        border-bottom: 1px solid #F1F5F9;
    }
    .card-icon {
        width: 34px;
        height: 34px;
        border-radius: 9px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.15rem;
    }
    .icon-overview { background: #EFF6FF; color: #2563EB; }
    .icon-features { background: #ECFDF5; color: #059669; }
    .icon-technologies { background: #F5F3FF; color: #7C3AED; }
    .icon-workflow { background: #FFFBEB; color: #D97706; }

    .card-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1E293B;
        margin: 0;
    }

    /* Tech Badges */
    .tech-badges-container {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-bottom: 1rem;
    }
    .tech-tag {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: #F1F5F9;
        border: 1px solid #CBD5E1;
        color: #1E293B;
        border-radius: 9999px;
        padding: 0.3rem 0.85rem;
        font-weight: 600;
        font-size: 0.82rem;
    }

    /* Inline Code Styling */
    code, .inline-code {
        background: #F1F5F9 !important;
        color: #0F172A !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 4px !important;
        padding: 0.15rem 0.35rem !important;
        font-size: 0.88em !important;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace !important;
    }

    /* Workflow Step Cards */
    .step-item {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        font-size: 0.93rem;
        line-height: 1.5;
        color: #334155;
    }
    .step-number {
        background: #D97706;
        color: white;
        font-weight: 700;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        flex-shrink: 0;
        margin-top: 0.15rem;
    }

    /* Metadata Metrics Card */
    .repo-banner-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .repo-main-info {
        display: flex;
        align-items: center;
        gap: 0.8rem;
    }
    .repo-avatar {
        width: 44px;
        height: 44px;
        border-radius: 10px;
        background: #F1F5F9;
        border: 1px solid #CBD5E1;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
    }
    .repo-name-text {
        font-size: 1.35rem;
        font-weight: 800;
        color: #0F172A;
        margin: 0;
    }
    .repo-meta-sub {
        font-size: 0.83rem;
        color: #64748B;
        margin: 0.15rem 0 0 0;
    }

    /* Chat Placeholder Card */
    .chat-placeholder {
        background: #FFFFFF;
        border: 2px dashed #CBD5E1;
        border-radius: 16px;
        padding: 3.5rem 2rem;
        text-align: center;
        color: #64748B;
        margin-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def check_backend_status() -> bool:
    """Check if the FastAPI backend is currently running and reachable."""
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=1.5)
        return resp.status_code == 200
    except Exception:
        return False


def render_demo_info_card() -> None:
    """Render a calm, neutral info card when running in UI demo mode with a local backend."""
    st.markdown(
        """
        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-left: 5px solid #64748B; border-radius: 14px; padding: 1.25rem 1.5rem; margin: 1rem 0; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);">
            <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.5rem;">
                <span style="font-size: 1.2rem;">ℹ️</span>
                <h3 style="font-size: 1.05rem; font-weight: 700; color: #1E293B; margin: 0;">UI demo: backend runs locally</h3>
            </div>
            <p style="font-size: 0.92rem; color: #475569; margin: 0 0 0.75rem 0; line-height: 1.55;">
                This app needs the FastAPI backend and a local Ollama model (<code>llama3:8b</code>) running on your own machine, so the live page shows the interface only.
            </p>
            <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.75rem; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.85rem; color: #0F172A; line-height: 1.6;">
                <span style="color: #64748B;"># 1. Keep Ollama running in the background:</span><br>
                ollama serve<br><br>
                <span style="color: #64748B;"># 2. Start the FastAPI backend:</span><br>
                <strong>uvicorn backend.main:app</strong>
            </div>
            <div style="font-size: 0.88rem; color: #64748B;">
                📖 For step-by-step setup instructions, see the <a href="https://github.com/anuskaGHS/repo-explainer#quick-start-for-evaluators" target="_blank" style="color: #2563EB; font-weight: 600; text-decoration: underline;">Quick Start for Evaluators</a> section on GitHub.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def parse_explanation_sections(text: str) -> dict[str, str] | None:
    """Parse explanation markdown into four discrete sections."""
    headings = [
        "Project Overview",
        "What the project does",
        "Main Technologies",
        "How it works",
    ]
    positions = []
    for h in headings:
        pattern = re.compile(
            rf"(?:^|\n)[#*\-_ \t]*{re.escape(h)}[#*\-_ \t]*(?:\r?\n[-=]+)?(?:\r?\n|\Z)",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            positions.append((match.start(), match.end(), h))
        else:
            return None

    positions.sort(key=lambda x: x[0])
    if [p[2] for p in positions] != headings:
        return None

    sections = {}
    for i, (start, end, h) in enumerate(positions):
        next_start = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        content = text[end:next_start].strip()
        sections[h] = content

    return sections


def format_inline_code(text: str) -> str:
    """Escape untrusted LLM text with html.escape first, then convert `code` to <code> tags."""
    escaped = html.escape(text)
    # Convert `code` to <code> with a subtle background and border
    formatted = re.sub(
        r"`([^`\n]+)`",
        r'<code class="inline-code" style="background:#F1F5F9;color:#0F172A;border:1px solid #CBD5E1;border-radius:4px;padding:2px 6px;font-size:0.88em;font-family:monospace;">\1</code>',
        escaped,
    )
    # Convert **bold** markdown to <strong> tags
    formatted = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", formatted)
    return formatted


def render_content_to_html(content: str) -> str:
    """Convert raw section text to HTML with escaped text, <code> tags, and list/paragraph structure."""
    if not content:
        return ""

    lines = content.strip().splitlines()
    html_parts = []
    in_ul = False
    in_ol = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            if in_ol:
                html_parts.append("</ol>")
                in_ol = False
            continue

        # Check for bullet: '-', '*', or '•'
        bullet_match = re.match(r"^[-*•]\s+(.*)$", stripped)
        # Check for numbered list: '1. ', '2) ', etc.
        numbered_match = re.match(r"^(\d+)[\.\)]\s+(.*)$", stripped)

        if bullet_match:
            if in_ol:
                html_parts.append("</ol>")
                in_ol = False
            if not in_ul:
                html_parts.append('<ul style="margin: 0.3rem 0 0.5rem 0; padding-left: 1.4rem; color: #334155; line-height: 1.6;">')
                in_ul = True
            item_text = format_inline_code(bullet_match.group(1))
            html_parts.append(f'<li style="margin-bottom: 0.35rem;">{item_text}</li>')

        elif numbered_match:
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            if not in_ol:
                html_parts.append('<ol style="margin: 0.3rem 0 0.5rem 0; padding-left: 1.4rem; color: #334155; line-height: 1.6;">')
                in_ol = True
            item_text = format_inline_code(numbered_match.group(2))
            html_parts.append(f'<li style="margin-bottom: 0.35rem;">{item_text}</li>')

        else:
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            if in_ol:
                html_parts.append("</ol>")
                in_ol = False
            para_text = format_inline_code(stripped)
            html_parts.append(f'<p style="margin: 0 0 0.6rem 0; color: #334155; line-height: 1.6;">{para_text}</p>')

    if in_ul:
        html_parts.append("</ul>")
    if in_ol:
        html_parts.append("</ol>")

    return "\n".join(html_parts)


# Initialize session state keys
if "analysis_result" not in st.session_state:
    st.session_state["analysis_result"] = None
if "repo_url_input" not in st.session_state:
    st.session_state["repo_url_input"] = ""


# Check live backend connection for status pill
backend_is_up = check_backend_status()
if backend_is_up:
    status_pill = '<span class="badge-pill status-ok">🟢 Backend API Connected</span>'
elif not IS_EXPLICIT_BACKEND_URL:
    status_pill = '<span class="badge-pill" style="background:#FEF2F2; border-color:#FECACA; color:#B91C1C;">🔴 Backend Offline &middot; runs locally</span>'
else:
    status_pill = '<span class="badge-pill" style="background:#FEF2F2; border-color:#FECACA; color:#B91C1C;">🔴 Backend Offline</span>'

# 1. Enhanced Brand Header
st.markdown(
    f"""
    <div class="header-wrapper">
        <div class="header-brand">
            <div class="header-icon-box">🔍</div>
            <div class="header-title-box">
                <h1>GitHub Repository Code Explainer</h1>
                <p>Instant architectural breakdowns and structured workflows powered by local LLMs</p>
            </div>
        </div>
        <div class="header-badges">
            {status_pill}
            <span class="badge-pill">⚡ Engine: Ollama (Local)</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# 2. Enhanced URL Input Card Box
with st.container(border=True):
    st.markdown(
        """
        <div class="url-box-header">
            <span>📦</span> <span>Enter Public GitHub Repository</span>
        </div>
        <div class="url-box-desc">
            Provide the HTTPS clone URL of any public GitHub repository. The engine will clone the repo, 
            index the relevant code files, outline symbols, and generate a structured overview.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_url, col_btn = st.columns([5, 1.2], vertical_alignment="bottom")

    with col_url:
        input_url = st.text_input(
            label="Repository URL",
            value=st.session_state["repo_url_input"],
            placeholder="https://github.com/owner/repository",
            label_visibility="collapsed",
            help="Example: https://github.com/octocat/Hello-World",
        )

    with col_btn:
        start_analysis = st.button(
            "🚀 Analyze Repo",
            type="primary",
            use_container_width=True,
        )

    # Quick Example Buttons for effortless testing
    st.markdown('<div class="examples-label">Try Quick Examples:</div>', unsafe_allow_html=True)
    col_ex1, col_ex2, col_ex3, col_ex4 = st.columns(4)

    with col_ex1:
        if st.button("📌 octocat/Hello-World", use_container_width=True):
            st.session_state["repo_url_input"] = "https://github.com/octocat/Hello-World"
            st.rerun()

    with col_ex2:
        if st.button("📌 octocat/Spoon-Knife", use_container_width=True):
            st.session_state["repo_url_input"] = "https://github.com/octocat/Spoon-Knife"
            st.rerun()

    with col_ex3:
        if st.button("📌 anuskaGHS/Python_Project", use_container_width=True):
            st.session_state["repo_url_input"] = "https://github.com/anuskaGHS/Python_Project"
            st.rerun()

    with col_ex4:
        if st.button("📌 pallets/flask", use_container_width=True):
            st.session_state["repo_url_input"] = "https://github.com/pallets/flask"
            st.rerun()


# Show calm neutral info card when backend is unreachable on localhost default
if not backend_is_up and not IS_EXPLICIT_BACKEND_URL and not start_analysis:
    render_demo_info_card()

# Trigger Analysis Logic
if start_analysis:
    clean_url = input_url.strip()
    if not clean_url:
        st.warning("⚠️ Please enter a valid public GitHub repository URL before starting the analysis.")
    else:
        st.session_state["repo_url_input"] = clean_url

        with st.spinner("⏳ Cloning repository and analyzing codebase with local Ollama... This may take a few minutes for multi-file repositories."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/explain",
                    json={"repo_url": clean_url},
                    timeout=REQUEST_TIMEOUT,
                )

                if response.status_code == 200:
                    data = response.json()
                    st.session_state["analysis_result"] = data
                    st.toast("Repository analyzed successfully!", icon="✅")
                else:
                    try:
                        err_json = response.json()
                        detail = err_json.get("detail", response.text)
                    except Exception:
                        detail = response.text

                    if response.status_code == 400:
                        st.error(f"❌ **Invalid Request (400):** {detail}")
                    elif response.status_code == 503:
                        st.error(
                            f"🔌 **LLM Service Unavailable (503):** {detail}\n\n"
                            "Please ensure that your local Ollama server is running (`ollama serve`)."
                        )
                    elif response.status_code == 500:
                        st.error(f"💥 **Internal Server Error (500):** {detail}")
                    else:
                        st.error(f"⚠️ **Backend Error ({response.status_code}):** {detail}")

            except requests.exceptions.ConnectionError:
                if not IS_EXPLICIT_BACKEND_URL:
                    render_demo_info_card()
                else:
                    st.error(
                        "⚠️ **Cannot connect to the backend server.**\n\n"
                        f"The FastAPI server is not reachable at `{BACKEND_URL}`. "
                        "Start it in your PowerShell terminal using:\n\n"
                        "```powershell\nuvicorn backend.main:app --reload\n```"
                    )
            except requests.exceptions.Timeout:
                st.error(
                    f"⏱️ **The request timed out after {REQUEST_TIMEOUT} seconds.**\n\n"
                    "Processing large repositories can take time. Verify that your Ollama server is responding and re-try."
                )
            except requests.exceptions.RequestException as exc:
                st.error(f"⚠️ **Network Request Failed:** {exc}")


# 3. Enhanced Presentation Tabs
tab_explanation, tab_chat = st.tabs([
    "📊 Structured Repository Explanation",
    "💬 Interactive Chat (Coming Soon)",
])

result = st.session_state.get("analysis_result")

with tab_explanation:
    if result:
        repo_name = result.get("repo_name", "Repository")
        files_found = result.get("files_found", 0)
        explanation_raw = result.get("explanation", "").strip()

        # Repository Metadata Hero Banner
        st.markdown(
            f"""
            <div class="repo-banner-card">
                <div class="repo-main-info">
                    <div class="repo-avatar">📦</div>
                    <div>
                        <h2 class="repo-name-text">{repo_name}</h2>
                        <p class="repo-meta-sub">Repository Analysis Report &bull; {files_found} relevant source files analyzed</p>
                    </div>
                </div>
                <div style="display:flex; gap: 0.5rem; align-items:center;">
                    <span class="badge-pill" style="background:#EFF6FF; border-color:#BFDBFE; color:#1D4ED8;">
                        📂 {files_found} Files
                    </span>
                    <span class="badge-pill" style="background:#ECFDF5; border-color:#A7F3D0; color:#047857;">
                        ✨ Complete
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Parse the 4 sections
        sections = parse_explanation_sections(explanation_raw)

        if sections:
            # 1. Project Overview Card
            overview_text = sections.get("Project Overview", "").strip()
            overview_html = render_content_to_html(overview_text)
            st.markdown(
                f"""
                <div class="explanation-card card-overview">
                    <div class="card-header-bar">
                        <div class="card-icon icon-overview">📌</div>
                        <h3 class="card-title">Project Overview</h3>
                    </div>
                    {overview_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 2. What the Project Does Card
            features_text = sections.get("What the project does", "").strip()
            features_html = render_content_to_html(features_text)
            st.markdown(
                f"""
                <div class="explanation-card card-features">
                    <div class="card-header-bar">
                        <div class="card-icon icon-features">🎯</div>
                        <h3 class="card-title">What the Project Does</h3>
                    </div>
                    {features_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 3. Main Technologies Card (Chips ONLY, no duplicate bullet list)
            tech_text = sections.get("Main Technologies", "").strip()
            tech_items = [
                re.sub(r"^[-*•\d.]+\s*", "", line).strip()
                for line in tech_text.splitlines()
                if line.strip() and not line.strip().lower().startswith("main technologies")
            ]

            if tech_items:
                badges_spans = "".join(
                    f'<span class="tech-tag">⚙️ {html.escape(item.strip("`").strip())}</span>'
                    for item in tech_items
                    if item.strip()
                )
                tech_body_html = f'<div class="tech-badges-container" style="margin-bottom:0;">{badges_spans}</div>'
            else:
                tech_body_html = render_content_to_html(tech_text)

            st.markdown(
                f"""
                <div class="explanation-card card-technologies">
                    <div class="card-header-bar">
                        <div class="card-icon icon-technologies">🛠️</div>
                        <h3 class="card-title">Main Technologies</h3>
                    </div>
                    {tech_body_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 4. How It Works Card
            workflow_text = sections.get("How it works", "").strip()
            step_matches = re.findall(r"^\s*(\d+)\.\s*(.+)$", workflow_text, re.MULTILINE)

            if step_matches:
                workflow_html = "".join(
                    f'<div class="step-item"><div class="step-number">{num}</div><div>{format_inline_code(text)}</div></div>'
                    for num, text in step_matches
                )
            else:
                workflow_html = render_content_to_html(workflow_text)

            st.markdown(
                f"""
                <div class="explanation-card card-workflow">
                    <div class="card-header-bar">
                        <div class="card-icon icon-workflow">⚡</div>
                        <h3 class="card-title">How It Works</h3>
                    </div>
                    {workflow_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:
            # Fallback if section headings could not be segmented
            fallback_html = render_content_to_html(explanation_raw)
            st.markdown(
                f"""
                <div class="explanation-card card-overview">
                    <div class="card-header-bar">
                        <div class="card-icon icon-overview">📄</div>
                        <h3 class="card-title">Full Repository Explanation</h3>
                    </div>
                    {fallback_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

    else:
        st.markdown(
            """
            <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:16px; padding:3rem 2rem; text-align:center; color:#64748B; margin-top:0.5rem; box-shadow:0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 2.8rem; margin-bottom: 0.75rem;">💡</div>
                <h3 style="color:#1E293B; margin-bottom: 0.4rem; font-size:1.25rem;">No Repository Analyzed Yet</h3>
                <p style="max-width: 500px; margin: 0 auto; line-height: 1.6; font-size: 0.95rem;">
                    Enter a public GitHub repository link in the box above or click one of the quick examples to generate a comprehensive explanation.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


with tab_chat:
    st.markdown(
        """
        <div class="chat-placeholder">
            <div style="font-size: 2.75rem; margin-bottom: 0.75rem;">💬</div>
            <h3 style="color: #1E293B; margin-bottom: 0.5rem; font-size: 1.3rem;">Interactive Repository Q&A</h3>
            <p style="max-width: 540px; margin: 0 auto; line-height: 1.6; font-size: 0.95rem;">
                Chat directly with your local LLM about the cloned repository's source code, function signatures, 
                API schemas, and algorithms. This module is scheduled for the next release.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
