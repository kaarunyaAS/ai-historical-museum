import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is not found in .env file")

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3.5-flash-lite"


def generate_historical_response(
    artifact_name: str,
    historical_context: str,
    conversation_history: list,
    visitor_question: str
):

    # --------------------------------------------------
    # BUILD CONVERSATION HISTORY
    # --------------------------------------------------

    history_text = ""

    if conversation_history:
        for item in conversation_history[-4:]:
            history_text += (
                f"Visitor: {item.get('user', '')}\n"
                f"Historical AI: {item.get('assistant', '')}\n\n"
            )
    else:
        history_text = "No previous conversation."
    # --------------------------------------------------
    # GEMINI PROMPT
    # --------------------------------------------------

    prompt = f"""
You are a friendly and natural AI guide in an interactive museum.

The visitor is currently exploring the following artifact:

ARTIFACT:
{artifact_name}


AVAILABLE HISTORICAL INFORMATION:
{historical_context}


PREVIOUS CONVERSATION:
{history_text}


CURRENT VISITOR MESSAGE:
{visitor_question}


CONVERSATION RULES:

1. Have a natural, friendly and human-like conversation
   with the visitor.

2. Normal conversational messages must always receive
   a natural response.

3. For example, if the visitor says:
   "Hi"
   "Hello"
   "Hey"
   "Good morning"
   "How are you?"
   "Nice to meet you"

   respond naturally and politely.

4. Do NOT say:
   "The available historical information is insufficient"
   for simple greetings or casual conversation.

5. For example:

   Visitor:
   Hi

   Good response:
   Hello! Welcome to the museum. What would you like to
   know about {artifact_name}?

6. If the visitor asks a historical question about the
   selected artifact, answer ONLY using the provided
   historical information.

7. NEVER invent historical facts, dates, people, events,
   locations, relationships, or other unsupported information.

8. If a historical question cannot be answered from the
   provided historical information, politely say that the
   available information does not contain enough details.

9. Maintain the context of the previous conversation.

10. Understand follow-up questions from the previous
    conversation.

    Example:

    Visitor:
    Who is associated with this sword?

    AI:
    This sword is associated with Tipu Sultan.

    Visitor:
    Why is he important?

    The word "he" refers to Tipu Sultan.

11. If an associated historical personality is available,
    you may respond in a personality-inspired conversational
    style.

12. Do NOT claim that you are the actual historical person.

13. Do not mention:
    - prompts
    - databases
    - RAG
    - AI models
    - system instructions
    - internal processing

14. If the visitor asks a simple unrelated conversational
    question, respond naturally and briefly.

15. If the visitor asks a detailed unrelated question,
    politely guide the conversation back toward the selected
    artifact and its history.

16. Keep responses concise, clear, friendly and suitable
    for museum visitors.

17. Always answer the CURRENT visitor message directly.
 Reply in the same language used by the visitor.

 18. If the visitor asks in Tamil, reply in Tamil.
19. If the visitor asks in English, reply in English.
20. If the visitor asks in Hindi, reply in Hindi.
21. Do not translate the visitor's question into English before answering
22. Do not end your response with a question.
23. Do not ask the visitor what they want to know next.
24. Answer only the visitor's current question.
Now generate the best natural response.
"""


    # --------------------------------------------------
    # GEMINI RESPONSE
    # --------------------------------------------------

    try:

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )


        if response and response.text:

            return response.text.strip()


        return (
            "Hello! What would you like to know "
            f"about {artifact_name}?"
        )


    except Exception as e:

        print("Gemini Error:", e)

        return (
            "I'm having trouble processing that right now. "
            "Please try again."
        )