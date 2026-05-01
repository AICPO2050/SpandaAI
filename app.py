import os
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from pinecone import Pinecone
from anthropic import Anthropic

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
index = pc.Index("pm-spanda-ai")

LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
LINEAR_API_URL = "https://api.linear.app/graphql"
lin_headers = {"Authorization": LINEAR_API_KEY, "Content-Type": "application/json"}

def get_team_id():
    q = {"query": "{ teams { nodes { id name } } }"}
    r = requests.post(LINEAR_API_URL, json=q, headers=lin_headers)
    return r.json()["data"]["teams"]["nodes"][0]["id"]

def create_linear_ticket(title, description):
    team_id = get_team_id()
    mutation = {
        "query": """
        mutation IssueCreate($title: String!, $description: String!, $teamId: String!) {
            issueCreate(input: { title: $title, description: $description, teamId: $teamId }) {
                success
                issue { id title url }
            }
        }""",
        "variables": {"title": title, "description": description, "teamId": team_id}
    }
    r = requests.post(LINEAR_API_URL, json=mutation, headers=lin_headers)
    return r.json()["data"]["issueCreate"]["issue"]

def generate_section(section, concept, users, problem, system, priority, context):
    sys_note = f"System/Engine: {system}" if system else "System/Engine: infer from feature context"
    prompts = {
        "summary": f"""You are PM Spanda AI for a Regional Commercial Bank.
Bank Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | {sys_note} | Priority: {priority}
Write a 3 paragraph executive summary covering problem statement, proposed solution and business impact.""",

        "features": f"""You are PM Spanda AI for a Regional Commercial Bank.
Bank Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | {sys_note} | Priority: {priority}
List Core Features and Enhanced Features with descriptions. Reference MuleSoft, FIS, ACH Engine, FX Engine where relevant.""",

        "jira": f"""You are PM Spanda AI for a Regional Commercial Bank.
Bank Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | {sys_note} | Priority: {priority}
Generate exactly 4 Jira user stories. For EACH use this EXACT format:

## [STORY-ID] Story Title

**User Story**
As a [user type], I want [action] so that [benefit].

**Acceptance Criteria**
- [ ] Criteria 1
- [ ] Criteria 2
- [ ] Criteria 3
- [ ] Criteria 4

**Technical Requirements**
- Core banking system requirement
- API/integration requirement
- Security/compliance requirement

**Story Points:** [number]
**Team:** [team name]

---""",

        "architecture": f"""You are PM Spanda AI for a Regional Commercial Bank.
Feature: {concept} | Users: {users} | {sys_note} | Priority: {priority}
Describe the technical architecture including:
- Frontend layer (portal/mobile)
- MuleSoft API layer
- Backend systems ({system if system else 'relevant core banking systems'})
- Authentication (Okta)
- Compliance (OFAC, KYC)
Provide complexity rating (Low/Medium/High) with justification.""",

        "ux": f"""You are PM Spanda AI for a Regional Commercial Bank.
Feature: {concept} | Users: {users} | {sys_note}
Design exactly 5 screens for the UX flow. For each screen use this exact format:
SCREEN [number]: [Screen Name]
PURPOSE: [one sentence what this screen does]
ELEMENTS: [comma separated list of UI elements]
ACTION: [what happens when user proceeds]
ERROR: [error state message]""",

        "risks": f"""You are PM Spanda AI for a Regional Commercial Bank.
Bank Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | {sys_note} | Priority: {priority}
Identify Technical Risks, Business Risks and Compliance Risks with Impact, Probability and Mitigation. Include Team Routing and Sprint estimate.""",

        "npc_eval": f"""You are a senior banking product committee evaluator.
Feature: {concept} | {sys_note} | Priority: {priority} | Problem: {problem}
Evaluate if NPC approval is required.
NPC IS required: new product, regulatory impact, over $1M, new vendor, new segment.
NPC NOT required: enhancement, internal improvement, under $500K, no new vendors.
Respond ONLY in this format:
DECISION: [REQUIRED or NOT REQUIRED]
REASON: [2-3 sentences]
RISK_LEVEL: [High, Medium, or Low]""",

        "npc": f"""You are PM Spanda AI for a Regional Commercial Bank.
Feature: {concept} | Users: {users} | Problem: {problem} | {sys_note} | Priority: {priority}
Generate complete NPC document: Executive Summary, Strategic Alignment, Revenue Opportunity, Resource Requirements, Risk Assessment, Recommendation, Dependencies, Approval Checklist.""",

        "bi": f"""You are a business intelligence analyst at a Regional Commercial Bank.
Feature: {concept} | {sys_note} | Users: {users} | Problem: {problem}
Generate BI summary with realistic numbers:
**Current State Metrics** | **Market Opportunity** | **Competitor Benchmarks** (JPMorgan, BofA, HSBC) | **Expected Impact** | **Key KPIs** (5 with targets)""",

        "competitor_insights": f"""You are a banking product strategy expert.
Feature concept: {concept}
List 5 bullet points. For each:
- Name a specific bank (JPMorgan, BofA, Wells Fargo, HSBC, Citi, Chase)
- What feature they offer related to this
- Measurable advantage or outcome

Then suggest 3 additional related features the PM should consider building.
Use real numbers and specific bank names.""",

        "research": f"""You are a banking product research analyst at a Regional Commercial Bank.
Feature: {concept} | Users: {users} | Problem: {problem} | {sys_note}
Provide: Industry Trends, Competitor Analysis (JPMorgan/BofA/Wells Fargo), Customer Insights, Regulatory Landscape, Recommended Approach.""",
    }

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompts[section]}]
    )
    return response.content[0].text


def render_ux_mockups(concept, system, ux_text, bank_type="BE"):
    if bank_type == "Retail":
        primary, secondary, bg = "#00529B", "#F5A623", "#F0F4F8"
        logo_text = "Retail Banking"
        nav_items = ["Dashboard", "Transfers", "Pay Bills", "Cards", "Profile"]
    else:
        primary, secondary, bg = "#003087", "#C4922A", "#F5F6FA"
        logo_text = "Business Banking"
        nav_items = ["Dashboard", "Payments", "ACH", "Cards", "Reports", "Admin"]

    screens = []
    lines = ux_text.split('\n')
    current = None
    for line in lines:
        l = line.strip()
        if l.upper().startswith('SCREEN') and ':' in l:
            if current:
                screens.append(current)
            name = l.split(':', 1)[1].strip()
            current = {"name": name, "purpose": "", "elements": "", "action": "", "error": ""}
        elif current:
            if l.upper().startswith('PURPOSE:'):
                current["purpose"] = l.split(':', 1)[1].strip()
            elif l.upper().startswith('ELEMENTS:'):
                current["elements"] = l.split(':', 1)[1].strip()
            elif l.upper().startswith('ACTION:'):
                current["action"] = l.split(':', 1)[1].strip()
            elif l.upper().startswith('ERROR:'):
                current["error"] = l.split(':', 1)[1].strip()
    if current:
        screens.append(current)

    if not screens:
        screens = [
            {"name": "Login / Authentication", "purpose": "Secure user login with MFA", "elements": "Username field, Password field, MFA Code, Login button", "action": "Redirect to dashboard", "error": "Invalid credentials"},
            {"name": "Main Dashboard", "purpose": "Overview of accounts and feature entry", "elements": "Balance cards, Quick actions, Notifications, Feature shortcut", "action": "Navigate to feature", "error": "Session expired"},
            {"name": f"{concept} — Entry Form", "purpose": f"User enters details for {concept}", "elements": "Input fields, Dropdowns, File upload, Continue button", "action": "Submit for validation", "error": "Required field missing"},
            {"name": "Review & Confirm", "purpose": "User reviews all details before submission", "elements": "Summary card, Edit links, Terms checkbox, Confirm button", "action": "Submit to backend", "error": "Submission failed"},
            {"name": "Confirmation", "purpose": "Success state with reference number", "elements": "Success icon, Reference number, Download PDF, Return to Dashboard", "action": "Complete", "error": "Download failed"},
        ]

    icons = ["🔐", "🏠", "📝", "✅", "🎉"]
    cards_html = ""

    for i, scr in enumerate(screens[:5]):
        icon = icons[i] if i < len(icons) else "📱"
        elems = [e.strip() for e in scr.get("elements", "").split(",") if e.strip()][:6]
        elem_html = "".join([f'<div style="background:white;border:1px solid #dde3ef;border-radius:6px;padding:7px 12px;margin-bottom:5px;font-size:12px;color:#333;display:flex;align-items:center;gap:8px;"><span style="color:{primary};">▸</span>{el}</div>' for el in elems])

        cards_html += f"""
<div style="background:white;border-radius:12px;box-shadow:0 2px 14px rgba(0,0,52,0.09);overflow:hidden;margin-bottom:22px;">
  <div style="background:#2d2d2d;padding:6px 12px;display:flex;align-items:center;gap:6px;">
    <div style="width:10px;height:10px;border-radius:50%;background:#ff5f57;"></div>
    <div style="width:10px;height:10px;border-radius:50%;background:#febc2e;"></div>
    <div style="width:10px;height:10px;border-radius:50%;background:#28c840;"></div>
    <div style="flex:1;background:#444;border-radius:4px;padding:2px 10px;font-size:11px;color:#aaa;margin:0 8px;">yourbank.com/portal</div>
  </div>
  <div style="background:{primary};padding:10px 20px;display:flex;align-items:center;justify-content:space-between;">
    <span style="color:{secondary};font-weight:700;font-size:14px;">{logo_text}</span>
    <div style="display:flex;gap:12px;">{"".join([f"<span style='color:rgba(255,255,255,0.75);font-size:11px;'>{n}</span>" for n in nav_items[:5]])}</div>
    <div style="width:28px;height:28px;border-radius:50%;background:{secondary};display:flex;align-items:center;justify-content:center;font-size:12px;color:white;font-weight:700;">PM</div>
  </div>
  <div style="padding:20px 24px;background:{bg};">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
      <span style="font-size:26px;">{icon}</span>
      <div style="flex:1;">
        <div style="font-size:10px;color:{primary};font-weight:700;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:2px;">Screen {i+1} of {min(len(screens),5)}</div>
        <div style="font-size:16px;font-weight:700;color:#0d1b40;">{scr['name']}</div>
      </div>
      <div style="background:{secondary};color:white;font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px;">{bank_type}</div>
    </div>
    <div style="font-size:12px;color:#555;margin-bottom:14px;padding:9px 14px;background:white;border-radius:8px;border-left:3px solid {primary};">{scr.get('purpose','')}</div>
    <div style="font-size:10px;font-weight:700;color:{primary};text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">UI Elements</div>
    {elem_html}
    <div style="display:flex;gap:10px;margin-top:14px;">
      <div style="flex:1;padding:9px;background:{primary};color:white;border-radius:7px;font-size:12px;font-weight:600;text-align:center;">{scr.get('action','Continue').split('—')[0].strip()} →</div>
      <div style="padding:9px 16px;background:white;color:{primary};border:1.5px solid {primary};border-radius:7px;font-size:12px;text-align:center;">Cancel</div>
    </div>
    <div style="margin-top:10px;padding:7px 12px;background:#fff8e1;border:1px solid #ffe082;border-radius:6px;font-size:11px;color:#7b5800;">
      ⚠ Error: {scr.get('error','Validation error — please check your input')}
    </div>
  </div>
</div>"""

    # Spanda AI screen
    cards_html += f"""
<div style="background:white;border-radius:12px;box-shadow:0 2px 14px rgba(0,0,52,0.09);overflow:hidden;margin-bottom:22px;">
  <div style="background:#2d2d2d;padding:6px 12px;display:flex;align-items:center;gap:6px;">
    <div style="width:10px;height:10px;border-radius:50%;background:#ff5f57;"></div>
    <div style="width:10px;height:10px;border-radius:50%;background:#febc2e;"></div>
    <div style="width:10px;height:10px;border-radius:50%;background:#28c840;"></div>
    <div style="flex:1;background:#444;border-radius:4px;padding:2px 10px;font-size:11px;color:#aaa;margin:0 8px;">yourbank.com/portal</div>
  </div>
  <div style="background:{primary};padding:10px 20px;display:flex;align-items:center;justify-content:space-between;">
    <span style="color:{secondary};font-weight:700;font-size:14px;">{logo_text}</span>
    <div style="display:flex;gap:12px;">{"".join([f"<span style='color:rgba(255,255,255,0.75);font-size:11px;'>{n}</span>" for n in nav_items[:4]])}</div>
    <div style="width:28px;height:28px;border-radius:50%;background:{secondary};display:flex;align-items:center;justify-content:center;font-size:12px;color:white;font-weight:700;">PM</div>
  </div>
  <div style="display:flex;background:{bg};min-height:220px;">
    <div style="flex:1;padding:20px 24px;">
      <div style="font-size:11px;color:{primary};font-weight:700;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">✦ Screen 6 — Spanda AI Embedded</div>
      <div style="font-size:14px;font-weight:700;color:#0d1b40;margin-bottom:10px;">AI Assistant Live in Portal</div>
      <div style="font-size:12px;color:#555;margin-bottom:12px;padding:8px 12px;background:white;border-radius:8px;border-left:3px solid {primary};">Spanda AI embedded — customers get real-time guidance without leaving the page.</div>
      <div style="display:flex;flex-wrap:wrap;gap:6px;">
        <div style="background:#EEF4FF;border:1px solid #C7D9FF;border-radius:20px;padding:4px 10px;font-size:11px;color:{primary};">What is my balance?</div>
        <div style="background:#EEF4FF;border:1px solid #C7D9FF;border-radius:20px;padding:4px 10px;font-size:11px;color:{primary};">Recent transfers</div>
        <div style="background:#EEF4FF;border:1px solid #C7D9FF;border-radius:20px;padding:4px 10px;font-size:11px;color:{primary};">Schedule a wire</div>
      </div>
    </div>
    <div style="width:200px;background:white;border-left:1px solid #e5e7eb;display:flex;flex-direction:column;">
      <div style="background:{primary};padding:8px 12px;display:flex;align-items:center;gap:6px;">
        <span style="color:{secondary};">✦</span>
        <div style="color:white;font-size:12px;font-weight:700;">Spanda AI</div>
      </div>
      <div style="flex:1;padding:10px;display:flex;flex-direction:column;gap:6px;">
        <div style="background:#f0f4ff;border-radius:0 8px 8px 8px;padding:7px 9px;font-size:11px;color:#333;">Hi! How can I help with {concept}?</div>
        <div style="background:{primary};border-radius:8px 8px 0 8px;padding:7px 9px;font-size:11px;color:white;align-self:flex-end;">How long does this take?</div>
        <div style="background:#f0f4ff;border-radius:0 8px 8px 8px;padding:7px 9px;font-size:11px;color:#333;">Typically 2-3 minutes. ✅</div>
      </div>
      <div style="padding:6px;border-top:1px solid #e5e7eb;display:flex;gap:5px;">
        <div style="flex:1;background:#f8faff;border:1px solid #e5e7eb;border-radius:20px;padding:5px 8px;font-size:11px;color:#aaa;">Ask anything...</div>
        <div style="background:{primary};border-radius:50%;width:26px;height:26px;display:flex;align-items:center;justify-content:center;font-size:11px;color:white;">➤</div>
      </div>
    </div>
  </div>
</div>"""

    return f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:700px;margin:0 auto;padding:4px;">
  <div style="background:linear-gradient(135deg,{primary},{primary}dd);padding:18px 22px;border-radius:12px;margin-bottom:22px;display:flex;align-items:center;justify-content:space-between;">
    <div>
      <div style="color:{secondary};font-weight:700;font-size:17px;margin-bottom:3px;">{logo_text} — UX Flow</div>
      <div style="color:rgba(255,255,255,0.8);font-size:12px;">{concept}</div>
    </div>
    <div style="background:{secondary};color:white;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:700;">6 Screens</div>
  </div>
  {cards_html}
</div>"""


def render_architecture_diagram(arch_text, concept="", system=""):
    layers = [
        {"label": "Frontend Layer", "color": "#1A56DB", "icon": "🖥️",
         "nodes": ["Online Banking Portal", "Mobile App", "Business Express UI"]},
        {"label": "API Gateway", "color": "#0E9F6E", "icon": "🔀",
         "nodes": ["API Gateway", "Load Balancer", "Rate Limiting"]},
        {"label": "MuleSoft Process API", "color": "#C4922A", "icon": "⚙️",
         "nodes": ["Process API", "Orchestration", "Data Transformation"]},
        {"label": "Backend Systems", "color": "#6366F1", "icon": "🏦",
         "nodes": ["Core Banking (FIS)", system if system else "ACH / FX Engine", "Data Store"]},
        {"label": "Auth & Compliance", "color": "#E3A008", "icon": "🔐",
         "nodes": ["Okta Authentication", "OFAC Screening", "KYC Validation"]},
    ]
    rows = ""
    for i, layer in enumerate(layers):
        nodes_html = "".join([
            f'<div style="background:white;border:1px solid {layer["color"]}44;border-radius:8px;padding:7px 12px;font-size:12px;color:#333;font-weight:500;">{n}</div>'
            for n in layer["nodes"]
        ])
        arrow = '<div style="text-align:center;font-size:18px;color:#94a3b8;margin:2px 0;">↓</div>' if i < len(layers)-1 else ""
        rows += f'''<div style="background:{layer["color"]}11;border:1.5px solid {layer["color"]}44;border-radius:10px;padding:12px 16px;margin-bottom:4px;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
    <span style="font-size:18px;">{layer["icon"]}</span>
    <span style="font-size:12px;font-weight:700;color:{layer["color"]};text-transform:uppercase;letter-spacing:0.5px;">{layer["label"]}</span>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;">{nodes_html}</div>
</div>{arrow}'''

    explanation = arch_text
    for marker in ["```mermaid", "```"]:
        if marker in arch_text:
            parts = arch_text.split(marker)
            if len(parts) > 2:
                explanation = parts[0] + "".join(parts[2:])
            break

    html = f'''<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:700px;">
  <div style="background:linear-gradient(135deg,#003087,#1A56DB);padding:16px 20px;border-radius:10px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;">
    <div style="color:white;font-weight:700;font-size:15px;">🏗️ System Architecture — {concept}</div>
    <div style="background:#C4922A;color:white;padding:3px 12px;border-radius:20px;font-size:11px;font-weight:700;">5 Layers</div>
  </div>
  {rows}
</div>'''
    return html, explanation


st.set_page_config(page_title="PM Spanda AI", page_icon="🧠", layout="wide")

defaults = {
    "summary": "", "features": "", "jira_output": "", "jira_edited": "",
    "architecture": "", "ux": "", "risks": "", "research": "",
    "npc": "", "npc_eval": "", "bi": "", "generated": False,
    "ticket_pushed": False, "ticket_url": "", "bank_type": "Business (BE)",
    "competitor_insights": "", "concept_store": "", "system_store": "",
    "users_store": "", "problem_store": "", "priority_store": "High"
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

with st.sidebar:
    st.header("📋 Feature Input")
    bank_type = st.selectbox("Banking Channel", ["Business (BE)", "Retail", "Both"])
    concept = st.text_input("Feature Concept *", placeholder="e.g. ACH onboarding, FX payments, card controls...")
    users = st.text_input("Who are the users?", placeholder="e.g. Business customers, RMs, Retail customers...")
    problem = st.text_area("What problem does it solve?", placeholder="Describe the pain point...", height=90)
    system = st.text_input("System / Engine (optional)",
        placeholder="e.g. ACH Engine, FX Engine — or leave blank, AI will infer",
        help="Optional. Leave blank and AI will identify the right system.")
    priority = st.selectbox("Priority", ["High", "Medium", "Low"])
    st.markdown("---")
    if concept and len(concept) > 5:
        with st.expander("💡 Competitor Features & Additional Ideas", expanded=False):
            if st.button("🔍 Get Insights", use_container_width=True):
                with st.spinner("Researching..."):
                    st.session_state["competitor_insights"] = generate_section(
                        "competitor_insights", concept, users, problem, system, priority, "")
            if st.session_state["competitor_insights"]:
                st.markdown(st.session_state["competitor_insights"])
    st.markdown("---")
    generate = st.button("🚀 Generate with PM Spanda AI", use_container_width=True, type="primary", disabled=not concept)
    if not concept:
        st.caption("⚠ Feature Concept is required.")
    st.markdown("---")
    st.caption("PM Spanda AI — Ancient wisdom. Modern product intelligence.")

st.title("🧠 PM Spanda AI")
st.subheader("Product Management Intelligence for Regional Commercial Banks")
st.markdown("---")

if generate and concept:
    vector = [0.1] * 1536
    results = index.query(vector=vector, top_k=5, include_metadata=True)
    context = "\n\n".join([m["metadata"]["text"] for m in results["matches"]])
    st.session_state.update({
        "concept_store": concept, "system_store": system, "users_store": users,
        "problem_store": problem, "priority_store": priority, "bank_type": bank_type,
        "ticket_pushed": False
    })
    for k in ["summary","features","jira_output","jira_edited","architecture","ux","risks","research","npc_eval","bi","npc"]:
        st.session_state[k] = ""

    prog = st.progress(0, text="Generating Summary...")
    st.session_state["summary"] = generate_section("summary", concept, users, problem, system, priority, context)
    prog.progress(25, text="Generating Features...")
    st.session_state["features"] = generate_section("features", concept, users, problem, system, priority, context)
    prog.progress(50, text="Generating Jira Stories...")
    st.session_state["jira_output"] = generate_section("jira", concept, users, problem, system, priority, context)
    st.session_state["jira_edited"] = st.session_state["jira_output"]
    prog.progress(75, text="Evaluating NPC...")
    st.session_state["npc_eval"] = generate_section("npc_eval", concept, users, problem, system, priority, context)
    prog.progress(100, text="Done!")
    st.session_state["generated"] = True
    prog.empty()
    st.success("✅ Core sections ready! Click any tab. Other sections load on demand.")

if st.session_state["generated"]:
    c   = st.session_state["concept_store"]
    s   = st.session_state["system_store"]
    u   = st.session_state["users_store"]
    pr  = st.session_state["problem_store"]
    pri = st.session_state["priority_store"]
    bt  = st.session_state["bank_type"]
    bank_mode = "Retail" if bt == "Retail" else "BE"

    def lazy_gen(key, section, label):
        if not st.session_state[key]:
            vector = [0.1] * 1536
            results = index.query(vector=vector, top_k=5, include_metadata=True)
            ctx = "\n\n".join([m["metadata"]["text"] for m in results["matches"]])
            with st.spinner(f"Generating {label}..."):
                st.session_state[key] = generate_section(section, c, u, pr, s, pri, ctx)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📋 Summary", "⚡ Features", "🎯 Jira Stories",
        "🏗️ Architecture", "🖥️ UX Flow", "⚠️ Risks",
        "📊 Business Intel", "🔍 Research", "📄 NPC Approval"
    ])

    with tab1:
        st.markdown(st.session_state["summary"])

    with tab2:
        st.markdown(st.session_state["features"])

    with tab3:
        st.markdown("### 🎯 Jira Stories — Review & Edit Before Pushing")
        st.info("Edit stories directly. Preview formatting below. Then Approve & Push.")
        edited = st.text_area("Edit Jira Stories:", value=st.session_state["jira_edited"], height=500, key="jira_edit_box")
        st.session_state["jira_edited"] = edited
        with st.expander("👁 Preview formatted stories", expanded=False):
            st.markdown(st.session_state["jira_edited"])
        col_a, col_b = st.columns([3, 1])
        with col_a:
            if not st.session_state["ticket_pushed"]:
                if st.button("✅ Approve & Push to Linear", type="primary", use_container_width=True):
                    with st.spinner("Pushing to Linear..."):
                        try:
                            ticket = create_linear_ticket(
                                f"{s or c} — {c}",
                                f"Users: {u}\nProblem: {pr}\nPriority: {pri}\n\n{st.session_state['jira_edited']}"
                            )
                            st.session_state["ticket_pushed"] = True
                            st.session_state["ticket_url"] = ticket["url"]
                            st.success(f"✅ Pushed: {ticket['title']}")
                            st.markdown(f"[View in Linear ↗]({ticket['url']})")
                        except Exception as e:
                            st.error(f"Push failed: {e}")
            else:
                st.success("✅ Already pushed to Linear!")
                if st.session_state["ticket_url"]:
                    st.markdown(f"[View in Linear ↗]({st.session_state['ticket_url']})")
        with col_b:
            if st.button("🔄 Reset", use_container_width=True):
                st.session_state["jira_edited"] = st.session_state["jira_output"]
                st.rerun()

    with tab4:
        lazy_gen("architecture", "architecture", "Architecture")
        st.markdown("### 🏗️ System Architecture Diagram")
        diagram_html, explanation = render_architecture_diagram(st.session_state["architecture"], c, s)
        components.html(diagram_html, height=500, scrolling=True)
        if explanation and explanation.strip():
            st.markdown("---")
            st.markdown(explanation)
        st.markdown("---")
        st.markdown("#### 📧 Notify Solution Architect")
        col1, col2 = st.columns([3, 1])
        with col1:
            sa_email = st.text_input("SA Email Address", placeholder="sa@yourbank.com")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            send_btn = st.button("📤 Generate", use_container_width=True)
        if send_btn and sa_email:
            st.success(f"✅ Copy and send to {sa_email}")
            st.code(f"""To: {sa_email}
Subject: Architecture Review Required — {c}

Hi,

Architecture review is required for the following feature:

Feature: {c}
System: {s or "TBD"}
Priority: {pri}

Please review and provide feedback in Linear.
Jira stories have been pushed and are awaiting SA sign-off.

Thank you""", language="text")

    with tab5:
        lazy_gen("ux", "ux", "UX Flow")
        st.markdown("### 🖥️ UX Flow")
        col_l, col_r = st.columns([1, 1])
        with col_l:
            st.markdown("#### 📄 Detailed Text Flow")
            st.markdown(st.session_state["ux"])
        with col_r:
            st.markdown("#### 🎨 Visual Mockups")
            components.html(render_ux_mockups(c, s, st.session_state["ux"], bank_mode), height=1800, scrolling=True)

    with tab6:
        lazy_gen("risks", "risks", "Risks")
        st.markdown(st.session_state["risks"])

    with tab7:
        lazy_gen("bi", "bi", "Business Intelligence")
        st.markdown("### 📊 Business Intelligence Panel")
        st.info("💡 Estimates based on regional commercial bank scale.")
        st.markdown(st.session_state["bi"])

    with tab8:
        lazy_gen("research", "research", "Research")
        st.markdown(st.session_state["research"])

    with tab9:
        st.markdown("### 📄 NPC Approval")
        npc_eval = st.session_state.get("npc_eval", "")
        if "NOT REQUIRED" in npc_eval:
            st.success("✅ NPC Approval is **NOT REQUIRED** for this feature.")
        else:
            st.warning("⚠️ NPC Approval is **REQUIRED** for this feature.")
        st.markdown(npc_eval)
        st.markdown("---")
        if st.button("📄 Generate Full NPC Document", use_container_width=True):
            if not st.session_state["npc"]:
                vector = [0.1] * 1536
                results = index.query(vector=vector, top_k=5, include_metadata=True)
                ctx = "\n\n".join([m["metadata"]["text"] for m in results["matches"]])
                with st.spinner("Generating NPC document..."):
                    st.session_state["npc"] = generate_section("npc", c, u, pr, s, pri, ctx)
        if st.session_state["npc"]:
            st.markdown(st.session_state["npc"])

else:
    st.info("👈 Enter a Feature Concept on the left and click Generate to start.")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Systems Supported", "Any")
    with col2:
        st.metric("Output Sections", "9")
    with col3:
        st.metric("Auto Ticket Creation", "Linear ✅")
