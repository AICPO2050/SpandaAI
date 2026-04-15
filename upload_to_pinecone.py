import os
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

with open("ewb_architecture.txt", "r") as f:
    text = f.read()

chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
print(f"Found {len(chunks)} chunks to upload")

index_name = "pm-spanda-ai"
existing = pc.list_indexes().names()
if index_name not in existing:
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    print("Index created")

index = pc.Index(index_name)

for i, chunk in enumerate(chunks):
    vector = [0.1] * 1536
    index.upsert(vectors=[{
        "id": f"chunk-{i}",
        "values": vector,
        "metadata": {"text": chunk}
    }])
    print(f"Uploaded chunk {i+1}/{len(chunks)}")

print("Done! EWB knowledge base is in Pinecone.")