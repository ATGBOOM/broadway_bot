import json
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
        self.intent = self.understandIntent(self.conversation_context, self.intent, user_input)
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

    def understandIntent(self, context, previous_intent, user_input):
        prompt = f"""
        You are a highly advanced AI assistant specializing in Natural Language Understanding for e-commerce. Your primary function is to accurately determine a user's shopping intent by analyzing their latest message in the context of the conversation history.

Your core principle is: **The most recent user message holds the most weight.** The conversation history provides context but does not override a clear, new request.

---
### Step 1: Analyze the Inputs

1.  **Current User Input:** This is the user's newest message. What is the explicit request here? Does it contain keywords related to events, travel, or specific products?
2.  **Conversation Context:** This is the history of the conversation. What was the previous topic? Use this to understand the background, but do not let it overpower the `Current User Input`. For example, if the user was planning a vacation but their *new message* is "I need shoes for a wedding," the intent is now "Occasion," not "Vacation."

---
### Step 2: Evaluate Against Defined Intents

Based on your analysis, choose **ONLY ONE** of the following intents.

**INTENT DEFINITIONS:**

* **"Vacation"**
    * **Description:** The user is planning, packing for, or currently on a trip, and their request is for outfits on the trabel. - this should only be called once, otherwise call occasion
    * **Trigger Keywords:** "trip," "traveling to," "packing for," "vacation," "holiday," "going to [destination]," "what to wear in [city/country]."
    * **Example:** User was looking for sunglasses. Current input is "I'll be going to Goa next month, what else should I pack?" -> **Vacation**.

* **"Occasion"**
    * **Description:** The user needs an outfit or items for a specific event, activity, or function. This is event-driven.
    * **Trigger Keywords:** "wedding," "party," "interview," "work," "office," "gym," "date night," "formal event," "concert," "festival."
    * **Example:** User was talking about a trip. Current input is "Thanks! Also, I need a dress for a friend's wedding." -> **Occasion**.

* **"Pairing"**
    * **Description:** The user has a specific item or product category in mind and wants to find complementary items that match or complete the look. The request is anchored to an existing product.
    * **Trigger Keywords:** "what goes with," "how to style," "shoes for this dress," "what top for these jeans," "need a bag to match my boots."
    * **Example:** User was shopping for an occasion. Current input is "I just bought these black jeans, what kind of tops would go well with them?" -> **Pairing**.

* **"General"**
    * **Description:** The user's request is broad, ambiguous, or doesn't fit any of the other categories. This intent signals that follow-up questions are needed to clarify their goal.
    * **Trigger Keywords:** "show me some shirts," "looking for shoes," "any new arrivals?," "I'm bored, show me something cool."
    * **Example:** The conversation is new. Current input is "I want to buy clothes." -> **General**.

---
### Step 3: Format the Output

Provide your response in a strict JSON format. Do not add any text outside of the JSON structure.

**INPUTS FOR YOUR ANALYSIS:**
- **Previous Intent:** `{previous_intent}`
- **Conversation Context:** `{context}`
- **Current User Input:** `{user_input}`  <-- *You will need to add this variable to your code*

**JSON OUTPUT FORMAT:**
```json
{{
  "reasoning": "A brief, one-sentence explanation of your decision-making process, explicitly mentioning how the current user input drove the choice.",
  "intent": "The single, most accurate intent from the list."
}}

"""

        response = self._call_ai(prompt).strip()
            
        # Find JSON content
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        
        if start_idx != -1 and end_idx != 0:
            json_content = json.loads(response[start_idx:end_idx])
            print(json_content['reasoning'])
            return json_content['intent']
        return 'General'


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
