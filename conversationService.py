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
            'Vacation',
            'Stlying'
        ]
    
    def processTurn(self, user_input, gender, intent = "general"):
        self.conversation_context = self.addToConversation(user_input, gender)

        self.intent = self.understandIntent(self.conversation_context, self.intent, user_input)
        return self.intent, self.conversation_context

    def endTurn(self, response, gender, recs=None):
        if recs:
            self.recs = recs
        self.conversation_context = self.endConvo(response, gender)
        print("ending turn", self.conversation_context)
        return self.conversation_context
    
    def addToConversation(self, user_input, gender):
        print("conversation given to add bot", self.conversation_context)
        print("gender given to add convo bot", gender)
        prompt = f"""
You are a smart, context-aware assistant helping interpret user requests for fashion, beauty, and product recommendations.

You are given:
- The ongoing **conversation context** between the assistant and the user
- The latest **user query**
- The **user’s known gender** (if any)
- A list of **previous recommendations** already shown

---

Your primary aim is to create a context for the conversation between the user and the bot. To do this you can follow the following steps :-
1. Analyze the user's **latest message** as the primary focus.
2. Reference the **prior conversation context** and **past recommendations** only if they clarify or enrich the user’s intent.
3. Determine whether the latest message:
   - Continues or elaborates on the same topic (→ related)
   - Introduces a new topic or switches direction (→ unrelated)
4. Summarize the **user’s current intent** in **clear, structured natural language** for downstream microservices to act on.

---

### Your Output:
Return a **concise natural-language sentences ** that clearly states what the user is asking for **right now**, incorporating relevant supporting information only if it enhances clarity.

📝 **Your summary should**:
- Be complete, readable, and contextually aware
- Mention any **specific products, weather, location, occasions, pairing needs**, or references to prior items
- Be immediately **actionable** by microservices (e.g., vacation outfit planner, product matcher, pairing assistant)
- Include gender if provided for better reccomendations

🛑 Do NOT:
- Repeat the entire conversation or recommendations
- Speculate beyond what the user has reasonably implied

---

### Inputs

CONVERSATION CONTEXT:
{self.conversation_context}

USER QUERY:
{user_input}

USER'S KNOWN GENDER:
{gender}

RECOMMENDATIONS PROVIDED:
{self.recs}

---

### Final Output:
Return only the refined, context-aware **intent summary** below:
"""

        return self._call_ai(prompt)
        
    def endConvo(self, response, gender):
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

KNOWN GENDER:
{gender}

---

**YOUR TASK:**  
Summarize and update the context to include only relevant information for the next turn. This includes:
- Updated user goals or preferences
- The users gender
- Items or tags mentioned (e.g., floral shirt, beachwear)
- Inferred or explicitly stated parameters (e.g., gender, budget, occasion, colors, product types)
- Any follow-up intent (e.g., user liked something, asked for variations, changed direction)
- Any follow ups asked by the bot

**Format the new context as a structured paragraph. Keep it concise but informative.**

---

**OUTPUT FORMAT (strict):**

[UpdatedContextHere]
"""
        
        response = self._call_ai(prompt)
        self.conversation_context = response
        print("response from end bot", response)
        return response

    def understandIntent(self, context, previous_intent, user_input):
        print("conversation given to intent bot", self.conversation_context)
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
    * **Description:** The user is planning to go on a trip or packing for a trip.
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

**"Styling"**
* **Description:** The user is seeking validation, styling advice, or compatibility assessment for a specific clothing item. They want to know if something suits them personally based on their body type, skin tone, style preferences, or the occasion. This is focused on personal fit and styling analysis rather than finding new products.
* **Trigger Keywords:** "looks good on me," "suit me," "flattering," "does this work," "will this look good," "is this right for me," "does this fit my style," "appropriate for my body type," "complements my skin tone," "should I wear this," "does this make me look," "styling advice," "how do I look."
    
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
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"AI API error: {e}")
            return ""
