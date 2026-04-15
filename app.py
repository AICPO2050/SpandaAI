import os
import requests
import streamlit as st
from dotenv import load_dotenv
from pinecone import Pinecone
from anthropic import Anthropic

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
index = pc.Index("pm-spanda-ai")

LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
LINEAR_API_URL = "https://api.linear.app/graphql"
headers = {
    "Authorization": LINEAR_API_KEY,
    "Content-Type": "application/json"
}

def get_team_id():
    query = {"query": "{ teams { nodes { id name } } }"}
    response = requests.post(LINEAR_API_URL, json=query, headers=headers)
    return response.json()["data"]["teams"]["nodes"][0]["id"]

def create_linear_ticket(title, description):
    team_id = get_team_id()
    mutation = {
        "query": """
        mutation IssueCreate($title: String!, $description: String!, $teamId: String!) {
            issueCreate(input: {
                title: $title,
                description: $description,
                teamId: $teamId
            }) {
                success
                issue { id title url }
            }
        }
        """,
        "variables": {
            "title": title,
            "description": description,
            "teamId": team_id
        }
    }
    response = requests.post(LINEAR_API_URL, json=mutation, headers=headers)
    return response.json()["data"]["issueCreate"]["issue"]

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
Generate minimum 4 Jira user stories. For each story include Story ID, As a I want So that, Acceptance Criteria minimum 4 points, Technical Requirements referencing EWB systems, Story Points.""",

        "architecture": f"""You are PM Spanda AI for East West Bank.
EWB Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | System: {system} | Priority: {priority}
Describe the technical architecture including frontend layer, MuleSoft middleware, backend systems, Okta authentication, data flow and complexity rating.""",

        "ux": f"""You are PM Spanda AI for East West Bank.
EWB Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | System: {system} | Priority: {priority}
Design the UX flow screen by screen. For each screen describe what the user sees, actions they can take, what happens next and error states.""",

        "risks": f"""You are PM Spanda AI for East West Bank.
EWB Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | System: {system} | Priority: {priority}
Identify Technical Risks, Business Risks and Compliance Risks with Impact, Probability and Mitigation. Include Team Routing and Sprint recommendation.""",

        "research": f"""You are PM Spanda AI for East West Bank.
EWB Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | System: {system} | Priority: {priority}
Provide market research including market size, competitor analysis JPMorgan BofA HSBC, EWB unique positioning, benchmarks and success metrics.""",

        "npc": f"""You are PM Spanda AI for East West Bank.
EWB Context: {context}
Feature: {concept} | Users: {users} | Problem: {problem} | System: {system} | Priority: {priority}
Generate NPC approval document with executive summary, strategic alignment, revenue opportunity, resource requirements, recommendation, dependencies and approval checklist."""
    }

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompts[section]}]
    )
    return response.content[0].text

st.set_page_config(page_title="PM Spanda AI", page_icon="🧠", layout="wide")

with st.sidebar:
    st.header("📋 Feature Input")
    concept = st.text_input("Feature Concept", placeholder="e.g. ACH onboarding for business customers")
    users = st.text_input("Who are the users?", placeholder="e.g. Business banking customers")
    problem = st.text_area("What problem does it solve?", placeholder="Describe the pain point", height=100)
    system = st.selectbox("Which EWB system?", ["ACH Engine", "FX Engine", "Core Banking", "Onboarding", "RM Dashboard"])
    priority = st.selectbox("Priority", ["High", "Medium", "Low"])
    generate = st.button("🚀 Generate with PM Spanda AI", use_container_width=True)
    st.markdown("---")
    st.caption("PM Spanda AI — Ancient wisdom. Modern product intelligence.")

st.title("🧠 PM Spanda AI")
st.subheader("Product Management Intelligence for East West Bank")
st.markdown("---")

if generate and concept:
    vector = [0.1] * 1536
    results = index.query(vector=vector, top_k=5, include_metadata=True)
    context = "\n\n".join([m["metadata"]["text"] for m in results["matches"]])

    # Generate all sections first
    with st.spinner("PM Spanda AI is thinking..."):
        summary = generate_section("summary", concept, users, problem, system, priority, context)
        features = generate_section("features", concept, users, problem, system, priority, context)
        jira_output = generate_section("jira", concept, users, problem, system, priority, context)
        architecture = generate_section("architecture", concept, users, problem, system, priority, context)
        ux = generate_section("ux", concept, users, problem, system, priority, context)
        risks = generate_section("risks", concept, users, problem, system, priority, context)
        research = generate_section("research", concept, users, problem, system, priority, context)
        npc = generate_section("npc", concept, users, problem, system, priority, context)

    # Create Linear ticket immediately after generation
    try:
        ticket = create_linear_ticket(
            f"{system} - {concept}",
            f"Users: {users}\nProblem: {problem}\nPriority: {priority}\n\n{jira_output}"
        )
        st.success(f"✅ Ticket created in Linear: {ticket['title']}")
        st.markdown(f"[View in Linear]({ticket['url']})")
    except Exception as e:
        st.warning(f"Output generated but ticket creation failed: {e}")

    # Show all tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📋 Summary", "⚡ Features", "🎯 Jira Stories",
        "🏗️ Architecture", "🖥️ UX Flow", "⚠️ Risks & Routing",
        "🔍 Research", "📄 NPC Approval"
    ])

    with tab1:
        st.markdown(summary)
    with tab2:
        st.markdown(features)
    with tab3:
        st.markdown(jira_output)
    with tab4:
        st.markdown(architecture)
    with tab5:
        st.markdown(ux)
    with tab6:
        st.markdown(risks)
    with tab7:
        st.markdown(research)
    with tab8:
        st.markdown(npc)

elif generate and not concept:
    st.warning("Please fill in the Feature Concept field.")
else:
    st.info("👈 Fill in the feature details on the left and click Generate to start.")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("EWB Systems Connected", "5")
    with col2:
        st.metric("Output Sections", "8")
    with col3:
        st.metric("Auto Ticket Creation", "Linear ✅")