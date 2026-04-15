import os
from dotenv import load_dotenv
from pinecone import Pinecone
from anthropic import Anthropic

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
index = pc.Index("pm-spanda-ai")

def search_knowledge_base(query):
    vector = [0.1] * 1536
    results = index.query(vector=vector, top_k=5, include_metadata=True)
    context = ""
    for match in results["matches"]:
        context += match["metadata"]["text"] + "\n\n"
    return context

def run_agent(user_input):
    print("\nSearching EWB knowledge base...")
    context = search_knowledge_base(user_input)
    
    print("Generating output with Claude...")
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""You are PM Spanda AI - a product management assistant for East West Bank.
            
EWB Architecture Context:
{context}

PM Request: {user_input}

Generate a structured output with:
1. SUMMARY - 2 sentence overview
2. FEATURES - Key features list
3. JIRA STORIES - At least 3 user stories with acceptance criteria
4. ARCHITECTURE - Which EWB systems are involved
5. RISKS - Top 3 risks"""
        }]
    )
    return response.content[0].text

if __name__ == "__main__":
    print("PM Spanda AI Agent Ready!")
    user_input = input("\nDescribe your feature: ")
    result = run_agent(user_input)
    print("\n" + "="*50)
    print(result)