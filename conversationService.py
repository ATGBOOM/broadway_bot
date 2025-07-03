from openai import OpenAI

class ConversationService:
    def __init__(self):
        self.recs = []
        self.intent = "general"
        self.conversation_context = ""
        self.client = OpenAI()
        self.intents = [
            'Occasion',
            'Pairing',
            'Vacation'
        ]
    
    def processTurn(self, user_input, intent = "general"):
      

        self.conversation_context = self.addToConversation(user_input)
        self.intent = self.understandIntent(self.conversation_context, self.intent)
        return self.intent, self.conversation_context

    def endTurn(self, response, recs=None):
        if recs:
            self.recs = recs
        self.conversation_context = self.endConvo(response)
        return self.conversation_context
    
    def addToConversation(self, user_input):
        prompt = f"""
You are a smart assistant helping interpret user requests for fashion and product recommendations.

You are given:
- The previous **conversation context** between the assistant and user
- The latest **user query**
- A list of previously provided **recommendations**

Your task:
- Carefully analyze the user query in the context of the prior conversation and recommendations
- Determine the user's **true intent**
- You have to judge if the user input is related to the previous context, if it is unrelated create a new context based on the input
- Return a **clear, concise, and structured** natural-language summary of what the user wants, so that downstream services can respond accurately.

This summary should:
- Be written in complete sentences
- Capture any relevant details such as location, weather, product preferences, or reference to previous recommendations
- Be **actionable** and easy to pass into other services

---

CONVERSATION CONTEXT:
{self.conversation_context}

USER QUERY:
{user_input}

RECOMMENDATIONS PROVIDED:
{self.recs}

---

Return the user’s refined intent based on all of the above.
"""
        return self._call_ai(prompt)
        
    def endConvo(self, response):
        prompt = f"""
You are an intelligent conversation state manager for a personal fashion shopping assistant.  
Your task is to generate a **new, updated conversation context** based on the bot's most recent response, the recommendations made, and the previous conversation history.

This context will be used in the next interaction to maintain continuity of user preferences, goals, and the assistant's understanding.

---

**PREVIOUS CONTEXT:**  
{self.conversation_context}

**BOT RESPONSE:**  
{response}

**RECOMMENDATIONS GIVEN (if any):**  
{self.recs}


---

**YOUR TASK:**  
Summarize and update the context to include only relevant information for the next turn. This includes:
- Updated user goals or preferences
- Items or tags mentioned (e.g., floral shirt, beachwear)
- Inferred or explicitly stated parameters (e.g., gender, budget, occasion, colors, product types)
- Any follow-up intent (e.g., user liked something, asked for variations, changed direction)

**Format the new context as a structured paragraph. Keep it concise but informative.**

---

**OUTPUT FORMAT (strict):**
```text
[UpdatedContextHere]
"""
        return self._call_ai(prompt)

    def understandIntent(self, context, previous_intent):
        prompt = f"""
You are an intelligent assistant responsible for understanding user shopping requests.  
Your job is to **determine the updated intent of the user**, based on the latest message and the full conversation context.

---

**ALLOWED INTENTS:**  
Choose ONLY ONE of the following intents that best matches what the user now wants:
- "Occasion": When the user is shopping for an event (e.g., wedding, party, work, gym)
- "Pairing": When the user wants suggestions for items that go well with something they already have (e.g., "what shoes with black jeans")
- "Vacation": When the user is packing or shopping for a trip 
- "General": When the users intent does not match any of the others and we need to ask them followups to narrow down the intention 
---

**PREVIOUS INTENT:**  
{previous_intent}

**CONVERSATION CONTEXT:**  
{context}

---

**YOUR TASK:**  
Analyze the conversation holistically and decide whether the user’s intent has changed.  
Return ONLY the updated intent from the allowed list above.

---

**RESPONSE FORMAT (strict):**  

NewIntentName
"""

        return self._call_ai(prompt)


    def _call_ai(self, prompt):
        """Send prompt to AI model."""
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"AI API error: {e}")
            return ""
