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

# ── Linear ───────────────────────────────────────────────────────────────────
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

# ── AI generation ─────────────────────────────────────────────────────────────
def generate_section(section, concept, users, problem, system, priority, context):
    prompts = {
        "summary": f"""You are PM Spanda AI for East West Bank.
EWB Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | System: {system} | Priority: {priority}
Write a 3 paragraph executive summary covering problem statement, proposed solution and business impact. Reference EWB systems specifically.""",

        "features": f"""You are PM Spanda AI for East West Bank.
EWB Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | System: {system} | Priority: {priority}
List Core Features and Enhanced Features with descriptions. Reference MuleSoft, FIS, ACH Engine, FX Engine where relevant.""",

        "jira": f"""You are PM Spanda AI for East West Bank.
EWB Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | System: {system} | Priority: {priority}
Generate minimum 4 Jira user stories. For each story include Story ID, As a / I want / So that, Acceptance Criteria (minimum 4 points), Technical Requirements referencing EWB systems, Story Points.""",

        "architecture": f"""You are PM Spanda AI for East West Bank.
EWB Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | System: {system} | Priority: {priority}
First generate a Mermaid flowchart diagram (flowchart TD) showing the architecture layers:
- Frontend (BusinessExpress UI or Retail UI)
- MuleSoft Process API layer
- Backend systems (FIS Core, ACH Engine, FX Engine as relevant)
- Okta Authentication
- Compliance layer (OFAC, KYC)
Use subgraphs for each layer. Wrap in ```mermaid code block.
Then write 2 paragraphs explaining the architecture and provide a complexity rating (Low/Medium/High) with justification.""",

        "ux": f"""You are PM Spanda AI for East West Bank.
Feature: {concept} | Users: {users} | System: {system}
Design exactly 5 screens for the UX flow. For each screen use this exact format:
SCREEN [number]: [Screen Name]
PURPOSE: [one sentence what this screen does]
ELEMENTS: [comma separated list of UI elements eg Button, Input field, Dropdown, Label]
ACTION: [what happens when user proceeds]
ERROR: [error state message]""",

        "risks": f"""You are PM Spanda AI for East West Bank.
EWB Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | System: {system} | Priority: {priority}
Identify Technical Risks, Business Risks and Compliance Risks with Impact, Probability and Mitigation strategy for each. Include Team Routing recommendation and Sprint estimate.""",

        "npc_eval": f"""You are a senior banking product committee evaluator at East West Bank.
Feature: {concept} | System: {system} | Priority: {priority} | Problem: {problem}
Evaluate if NPC (New Product Committee) approval is required.
NPC IS required when: completely new product/service, significant regulatory impact, investment >$1M, new external vendor relationship, new customer segment.
NPC is NOT required when: enhancement to existing feature, internal process improvement, investment <$500K, no new vendors, existing customer base.
Respond in exactly this format:
DECISION: [REQUIRED or NOT REQUIRED]
REASON: [2-3 sentences]
RISK_LEVEL: [High, Medium, or Low]""",

        "npc": f"""You are PM Spanda AI for East West Bank.
EWB Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | System: {system} | Priority: {priority}
Generate a complete NPC approval document including: Executive Summary, Strategic Alignment, Revenue Opportunity, Resource Requirements, Risk Assessment, Recommendation, Dependencies, and Approval Checklist.""",

        "bi": f"""You are a business intelligence analyst at East West Bank.
Feature: {concept} | System: {system} | Users: {users} | Problem: {problem}
Generate a Business Intelligence summary with realistic EWB-scale numbers:
**Current State Metrics** - existing customer counts, transaction volumes, current revenue
**Market Opportunity** - addressable market, revenue opportunity, customer acquisition potential
**Competitor Benchmarks** - how JPMorgan, BofA, HSBC handle this (specific metrics)
**Expected Impact** - projected revenue uplift, cost savings, customer growth
**Key KPIs** - 5 metrics to track post-launch with targets
Use specific realistic numbers throughout.""",

        "market_insights": f"""You are a banking market research expert.
Feature concept: {concept}
Provide exactly 4 bullet points of market insights for this banking feature.
Each bullet: one concise sentence. Focus on competitor practices, industry benchmarks, customer expectations, regulatory trends. Be specific with numbers where possible.""",
    }

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompts[section]}]
    )
    return response.content[0].text


# ── UX Mockup renderer ────────────────────────────────────────────────────────
def render_ux_mockups(concept, system, ux_text, bank_type="BE"):
    if bank_type == "Retail":
        primary = "#00529B"
        secondary = "#F5A623"
        bg = "#F0F4F8"
        header_bg = "#00529B"
        logo_text = "East West Bank"
        nav_items = ["Dashboard", "Transfers", "Pay Bills", "Cards", "Profile"]
    else:
        primary = "#003087"
        secondary = "#C4922A"
        bg = "#F5F6FA"
        header_bg = "#003087"
        logo_text = "BusinessExpress"
        nav_items = ["Dashboard", "Payments", "ACH", "Cards", "Reports", "Admin"]

    # Parse screens
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

    # Fallback screens
    if not screens:
        screens = [
            {"name": "Login / Authentication", "purpose": "Secure user login with MFA", "elements": "Username field, Password field, MFA Code field, Login button, Forgot password link", "action": "Redirect to dashboard", "error": "Invalid credentials — please try again"},
            {"name": "Main Dashboard", "purpose": "Overview of accounts and feature entry point", "elements": "Account balance cards, Quick action buttons, Notification banner, Feature shortcut button", "action": "Navigate to feature", "error": "Session expired — please log in again"},
            {"name": f"{concept} — Entry Form", "purpose": f"User enters required details for {concept}", "elements": "Input fields, Dropdown selectors, File upload, Validation messages, Continue button, Cancel link", "action": "Submit for validation", "error": "Required field missing or invalid format"},
            {"name": "Review & Confirm", "purpose": "User reviews all entered details before submission", "elements": "Summary card, Edit links, Terms checkbox, Confirm button, Cancel button", "action": "Submit to backend via MuleSoft", "error": "Submission failed — please retry"},
            {"name": "Confirmation & Next Steps", "purpose": "Success state with reference and next steps", "elements": "Success checkmark, Reference number, Download PDF button, Email confirmation toggle, Return to Dashboard button", "action": "Complete — ticket created", "error": "Download failed — try again"},
        ]

    icons = ["🔐", "🏠", "📝", "✅", "🎉"]
    cards_html = ""

    for i, scr in enumerate(screens[:5]):
        icon = icons[i] if i < len(icons) else "📱"
        elems = [e.strip() for e in scr.get("elements", "").split(",") if e.strip()][:6]
        elem_html = "".join([f'<div style="background:white;border:1px solid #dde3ef;border-radius:6px;padding:7px 12px;margin-bottom:5px;font-size:12px;color:#333;display:flex;align-items:center;gap:8px;"><span style="color:{primary};">▸</span>{el}</div>' for el in elems])

        cards_html += f"""
<div style="background:white;border-radius:12px;box-shadow:0 2px 14px rgba(0,0,52,0.09);overflow:hidden;margin-bottom:22px;">
  <!-- Browser chrome bar -->
  <div style="background:#2d2d2d;padding:6px 12px;display:flex;align-items:center;gap:6px;">
    <div style="width:10px;height:10px;border-radius:50%;background:#ff5f57;"></div>
    <div style="width:10px;height:10px;border-radius:50%;background:#febc2e;"></div>
    <div style="width:10px;height:10px;border-radius:50%;background:#28c840;"></div>
    <div style="flex:1;background:#444;border-radius:4px;padding:2px 10px;font-size:11px;color:#aaa;margin:0 8px;">eastwestbank.com/businessexpress</div>
  </div>
  <!-- Bank nav bar -->
  <div style="background:{header_bg};padding:10px 20px;display:flex;align-items:center;justify-content:space-between;">
    <span style="color:{secondary};font-weight:700;font-size:14px;letter-spacing:0.3px;">{logo_text}</span>
    <div style="display:flex;gap:12px;">{''.join([f"<span style='color:rgba(255,255,255,0.75);font-size:11px;'>{n}</span>" for n in nav_items[:5]])}</div>
    <div style="width:28px;height:28px;border-radius:50%;background:{secondary};display:flex;align-items:center;justify-content:center;font-size:12px;color:white;font-weight:700;">VM</div>
  </div>
  <!-- Screen content -->
  <div style="padding:20px 24px;background:{bg};">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:14px;">
      <span style="font-size:26px;">{icon}</span>
      <div style="flex:1;">
        <div style="font-size:10px;color:{primary};font-weight:700;text-transform:uppercase;letter-spacing:0.8px;margin-bottom:2px;">Step {i+1} of {min(len(screens),5)}</div>
        <div style="font-size:16px;font-weight:700;color:#0d1b40;">{scr['name']}</div>
      </div>
      <div style="background:{secondary};color:white;font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px;">{bank_type}</div>
    </div>
    <div style="font-size:12px;color:#555;margin-bottom:14px;padding:9px 14px;background:white;border-radius:8px;border-left:3px solid {primary};">{scr.get('purpose','')}</div>
    <div style="font-size:10px;font-weight:700;color:{primary};text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">UI Elements</div>
    {elem_html}
    <div style="display:flex;gap:10px;margin-top:14px;">
      <div style="flex:1;padding:9px;background:{primary};color:white;border-radius:7px;font-size:12px;font-weight:600;text-align:center;cursor:pointer;">{scr.get('action','Continue').split('—')[0].strip()} →</div>
      <div style="padding:9px 16px;background:white;color:{primary};border:1.5px solid {primary};border-radius:7px;font-size:12px;text-align:center;">Cancel</div>
    </div>
    <div style="margin-top:10px;padding:7px 12px;background:#fff8e1;border:1px solid #ffe082;border-radius:6px;font-size:11px;color:#7b5800;">
      ⚠ Error state: {scr.get('error','Validation error — please check your input')}
    </div>
  </div>
</div>"""

    full_html = f"""<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:680px;margin:0 auto;padding:4px;">
  <div style="background:linear-gradient(135deg,{primary},{primary}dd);padding:18px 22px;border-radius:12px;margin-bottom:22px;display:flex;align-items:center;justify-content:space-between;">
    <div>
      <div style="color:{secondary};font-weight:700;font-size:17px;margin-bottom:3px;">{logo_text} — UX Flow</div>
      <div style="color:rgba(255,255,255,0.8);font-size:12px;">{concept}</div>
    </div>
    <div style="background:{secondary};color:white;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:700;">{min(len(screens),5)} Screens</div>
  </div>
  {cards_html}
</div>"""
    return full_html


# ── Architecture renderer ─────────────────────────────────────────────────────
def render_architecture_diagram(arch_text):
    mermaid_code = ""
    explanation = arch_text

    if "```mermaid" in arch_text:
        parts = arch_text.split("```mermaid")
        if len(parts) > 1:
            mermaid_code = parts[1].split("```")[0].strip()
            explanation = arch_text.replace(f"```mermaid\n{mermaid_code}\n```", "").strip()
    elif "```" in arch_text:
        parts = arch_text.split("```")
        if len(parts) > 1:
            mermaid_code = parts[1].strip()
            explanation = "".join(parts[2:]).strip() if len(parts) > 2 else ""

    if mermaid_code:
        html = f"""
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<script>
  mermaid.initialize({{
    startOnLoad: true,
    theme: 'base',
    themeVariables: {{
      primaryColor: '#003087',
      primaryTextColor: '#ffffff',
      primaryBorderColor: '#C4922A',
      lineColor: '#C4922A',
      secondaryColor: '#f0f4f8',
      tertiaryColor: '#e8edf3',
      fontFamily: 'Segoe UI, sans-serif'
    }}
  }});
</script>
<div style="background:#f5f6fa;padding:24px;border-radius:12px;border:1px solid #dde3ef;">
  <div class="mermaid">{mermaid_code}</div>
</div>"""
        return html, explanation
    return None, arch_text


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="PM Spanda AI", page_icon="🧠", layout="wide")

# ── Session state ─────────────────────────────────────────────────────────────
defaults = {
    "summary": "", "features": "", "jira_output": "", "jira_edited": "",
    "architecture": "", "ux": "", "risks": "", "research": "",
    "npc": "", "npc_eval": "", "bi": "", "generated": False,
    "ticket_pushed": False, "ticket_url": "", "bank_type": "BusinessExpress (BE)",
    "market_insights": "", "concept_store": "", "system_store": "",
    "users_store": "", "problem_store": "", "priority_store": "High"
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("📋 Feature Input")

    bank_type = st.selectbox("Banking Channel", ["BusinessExpress (BE)", "Retail"])
    concept = st.text_input("Feature Concept", value="ACH Onboarding for Business Customers")
    users = st.text_input("Who are the users?", value="Business banking customers and Relationship Managers")
    problem = st.text_area("What problem does it solve?",
        value="Manual ACH onboarding takes 5-7 days, causes customer drop-off and requires RM intervention for every request.",
        height=100)
    system = st.selectbox("Which EWB system?", ["ACH Engine", "FX Engine", "Core Banking", "Onboarding", "RM Dashboard"])
    priority = st.selectbox("Priority", ["High", "Medium", "Low"])

    st.markdown("---")

    # Market insights
    if concept and len(concept) > 8:
        with st.expander("💡 Market Insights", expanded=False):
            if st.button("🔍 Fetch Insights", use_container_width=True):
                with st.spinner("Researching market..."):
                    st.session_state["market_insights"] = generate_section(
                        "market_insights", concept, users, problem, system, priority, "")
            if st.session_state["market_insights"]:
                st.markdown(st.session_state["market_insights"])

    st.markdown("---")
    generate = st.button("🚀 Generate with PM Spanda AI", use_container_width=True, type="primary")
    st.markdown("---")
    st.caption("PM Spanda AI — Ancient wisdom. Modern product intelligence.")

# ── Main ──────────────────────────────────────────────────────────────────────
st.title("🧠 PM Spanda AI")
st.subheader("Product Management Intelligence for East West Bank")
st.markdown("---")

# ── Generate ──────────────────────────────────────────────────────────────────
if generate and concept:
    vector = [0.1] * 1536
    results = index.query(vector=vector, top_k=5, include_metadata=True)
    context = "\n\n".join([m["metadata"]["text"] for m in results["matches"]])

    # Store inputs in session for use in tabs after rerun
    st.session_state["concept_store"] = concept
    st.session_state["system_store"] = system
    st.session_state["users_store"] = users
    st.session_state["problem_store"] = problem
    st.session_state["priority_store"] = priority
    st.session_state["bank_type"] = bank_type
    st.session_state["ticket_pushed"] = False

    with st.spinner("PM Spanda AI is thinking — generating all sections..."):
        st.session_state["summary"]      = generate_section("summary",      concept, users, problem, system, priority, context)
        st.session_state["features"]     = generate_section("features",     concept, users, problem, system, priority, context)
        st.session_state["jira_output"]  = generate_section("jira",         concept, users, problem, system, priority, context)
        st.session_state["jira_edited"]  = st.session_state["jira_output"]
        st.session_state["architecture"] = generate_section("architecture", concept, users, problem, system, priority, context)
        st.session_state["ux"]           = generate_section("ux",           concept, users, problem, system, priority, context)
        st.session_state["risks"]        = generate_section("risks",        concept, users, problem, system, priority, context)
        st.session_state["research"]     = generate_section("research",     concept, users, problem, system, priority, context)
        st.session_state["npc_eval"]     = generate_section("npc_eval",     concept, users, problem, system, priority, context)
        st.session_state["bi"]           = generate_section("bi",           concept, users, problem, system, priority, context)
        st.session_state["npc"]          = ""
        st.session_state["generated"]    = True

    st.success("✅ All sections generated! Click any tab to explore.")

elif generate and not concept:
    st.warning("Please fill in the Feature Concept field.")

# ── Tabs ──────────────────────────────────────────────────────────────────────
if st.session_state["generated"]:
    c = st.session_state["concept_store"]
    s = st.session_state["system_store"]
    u = st.session_state["users_store"]
    pr = st.session_state["problem_store"]
    pri = st.session_state["priority_store"]
    bt = st.session_state["bank_type"]
    bank_mode = "Retail" if "Retail" in bt else "BE"

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
        st.info("Edit the stories below if needed. When satisfied click **Approve & Push to Linear**.")
        edited = st.text_area("Edit Jira Stories:", value=st.session_state["jira_edited"], height=420, key="jira_edit_box")
        st.session_state["jira_edited"] = edited

        col_a, col_b = st.columns([3, 1])
        with col_a:
            if not st.session_state["ticket_pushed"]:
                if st.button("✅ Approve & Push to Linear", type="primary", use_container_width=True):
                    with st.spinner("Pushing to Linear..."):
                        try:
                            ticket = create_linear_ticket(
                                f"{s} — {c}",
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
            if st.button("🔄 Reset to Original", use_container_width=True):
                st.session_state["jira_edited"] = st.session_state["jira_output"]
                st.rerun()

    with tab4:
        st.markdown("### 🏗️ System Architecture Diagram")
        arch_text = st.session_state["architecture"]
        diagram_html, explanation = render_architecture_diagram(arch_text)

        if diagram_html:
            components.html(diagram_html, height=520, scrolling=True)
            if explanation:
                st.markdown(explanation)
        else:
            st.markdown(arch_text)

        st.markdown("---")
        st.markdown("#### 📧 Notify Solution Architect")
        col1, col2 = st.columns([3, 1])
        with col1:
            sa_email = st.text_input("SA Email Address", placeholder="sa@eastwestbank.com")
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📤 Send", use_container_width=True) and sa_email:
                body = f"Hi,%0A%0AArchitecture review required for:%0AFeature: {c}%0ASystem: {s}%0APriority: {pri}%0A%0APlease review and comment in Linear.%0A%0AThank you"
                mailto = f"mailto:{sa_email}?subject=Architecture Review — {c}&body={body}"
                st.markdown(f"[📧 Open Email Draft]({mailto})")
                st.success(f"Email draft ready for {sa_email}")

    with tab5:
        st.markdown("### 🖥️ UX Flow — Visual Screen Mockups")
        col_l, col_r = st.columns([4, 1])
        with col_r:
            view_mode = st.radio("View", ["Visual", "Text"], horizontal=False)

        if view_mode == "Visual":
            ux_html = render_ux_mockups(c, s, st.session_state["ux"], bank_mode)
            components.html(ux_html, height=900, scrolling=True)
        else:
            st.markdown(st.session_state["ux"])

    with tab6:
        st.markdown(st.session_state["risks"])

    with tab7:
        st.markdown("### 📊 Business Intelligence Panel")
        st.info("💡 Estimates based on EWB-scale data. Connect Power BI for live metrics.")
        st.markdown(st.session_state["bi"])

    with tab8:
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
                with st.spinner("Generating NPC document..."):
                    vector = [0.1] * 1536
                    results = index.query(vector=vector, top_k=5, include_metadata=True)
                    context = "\n\n".join([m["metadata"]["text"] for m in results["matches"]])
                    st.session_state["npc"] = generate_section("npc", c, u, pr, s, pri, context)

        if st.session_state["npc"]:
            st.markdown(st.session_state["npc"])

else:
    st.info("👈 Fill in the feature details on the left and click Generate to start.")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("EWB Systems Connected", "5")
    with col2:
        st.metric("Output Sections", "9")
    with col3:
        st.metric("Auto Ticket Creation", "Linear ✅")
