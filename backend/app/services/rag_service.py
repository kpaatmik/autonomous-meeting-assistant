from services.persistence import get_persistence
from services.llm_client import generate

persistence = get_persistence()

async def ask_meeting(meeting_id: str, question: str):

    results = persistence.search(meeting_id, question, top_k=5)

    if not results:
        return "No relevant discussion found."

    context = "\n".join([r[0][5] for r in results])

    prompt = f"""
    Answer ONLY based on the meeting transcript.

    Context:
    {context}

    Question:
    {question}
    """

    answer = await generate(prompt)

    return answer