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
            'SuitMe'
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
- Be immediately **actionable** by microservices (e.g., vacation outfit and beauty product planner, product pairing assistant, occasion outfit finder, suit me service or general info service)
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
#         prompt = f"""
#         You are a highly advanced AI assistant specializing in Natural Language Understanding for e-commerce. Your primary function is to accurately determine a user's shopping intent by analyzing their latest message in the context of the conversation history.

# Your core principle is: **The most recent user message holds the most weight.** The conversation history provides context but does not override a clear, new request.

# ---
# ### Step 1: Analyze the Inputs

# 1.  **Current User Input:** This is the user's newest message. What is the explicit request here? Does it contain keywords related to events, travel, or specific products? If user input is vague then try to rely on the conversation context
# 2.  **Conversation Context:** This is the history of the conversation. What was the previous topic? Use this to understand the background, but do not let it overpower the `Current User Input`. For example, if the user was planning a vacation but their *new message* is "I need shoes for a wedding," the intent is now "Occasion," not "Vacation."

# ---
# ### Step 2: Evaluate Against Defined Intents

# Based on your analysis, choose **ONLY ONE** of the following intents.

# **INTENT DEFINITIONS:**

# * **"Vacation"**
#     * **Description:** The user is planning, packing for, or shopping for a trip, vacation, or holiday. Their needs are contextualized by a destination's climate, culture, or planned activities.
#     * **Trigger Keywords:** "trip to," "traveling to," "packing for," "vacation in," "holiday," "what to wear in [city/country]," "going to [destination]."
#     * **Example:** User was looking for sunglasses. Current input is "I'll be going to Goa next month, what else should I pack?" -> **Vacation**.

# * **"Occasion"**
#     * **Description:** The user is looking for outfits or items suitable for a specific event, activity, or dress code. The primary filter for the search is the occasion itself.
#     * **Trigger Keywords:** "wedding," "party," "interview," "work," "office," "gym," "date night," "formal," "black-tie," "brunch," "concert," "graduation."
#     * **Example:** User was talking about a trip. Current input is "Thanks! Also, I need a dress for a friend's wedding." -> **Occasion**.

# * **"Pairing"**
#     * **Description:** The user has a specific item and is looking for product recommendations for other items to wear with it. The goal is product discovery. Do not call this if it is a general informational request about styling, fabrics, or weather.
#     * **Trigger Keywords:** "what to wear with," "what goes with," "find a top for," "recommend a shoe for," "I need a bag to match my boots."
#     * **Example:** User was shopping for an occasion. Current input is "I just bought these black jeans, what kind of tops would go well with them?" -> **Pairing**.

# * **"Styling"**
#     * **Description:** The user is seeking personalized feedback, validation, or styling analysis for themselves in context of a specific product or sets of products that are given. Do not call this if specific products are not given.

#     * **Example:** User is viewing a dress. Current input is "I have a pear-shaped body, will this look good on me?" -> **Styling**.
    
# * **"General"**
#     * **Description:** This is for purely informational or ambiguous queries. It covers broad questions about styles, trends, or general styling techniques that are not personalized. The expected output is information, not a product recommendation or personal validation.
#     * **Trigger Keywords:** "how do you," "what is," "style guide," "fashion trends," "show me some shirts," "looking for shoes," "any new arrivals?," "I'm bored, show me something cool."
#     * **Example:** The conversation is new. Current input is "I want to buy clothes." -> **General**.

# ---
# ### Step 3: Format the Output

# Provide your response in a strict JSON format. Do not add any text outside of the JSON structure.

# **INPUTS FOR YOUR ANALYSIS:**
# - **Current User Input:** {user_input}
# - **Conversation Context:** {context}


# **JSON OUTPUT FORMAT:**
# ```json
# {{
#   "reasoning": "A brief, one-sentence explanation of your decision-making process, explicitly mentioning how the current user input drove the choice.",
#   "intent": "The single, most accurate intent from the list."
# }} """
        prompt = f"""

        You are a highly advanced AI assistant specializing in Natural Language Understanding for e-commerce. Your primary function is to accurately determine a user's shopping intent by analyzing their latest message in the context of the conversation history.

Your core principles are:

The most recent user message holds the most weight. Context is for clarification, not overriding a new, clear request.

Evaluate intents using the specified hierarchy. Assess the input against the intents in the order they are listed, from most specific to most general. The first one that accurately fits is the correct one.

Step 1: Analyze the Inputs
Current User Input: Analyze the user's newest message for its explicit request, keywords, and entities.

Conversation Context: Use the conversation history to resolve ambiguities in the current input. If the current input is a clear, standalone request, prioritize it.

Step 2: Evaluate Against Defined Intents (Using a Strict Hierarchy)
Evaluate the user's need against the following intents in this specific order. Choose the first intent that provides a complete and accurate description of the user's primary goal.

INTENT HIERARCHY & DEFINITIONS:

1. SuitMe

Description: The user is seeking for an assessment of a specific outfit, which they are providing. 

Example: User is viewing a dress. Input: "I have a pear-shaped body, will this look good on me?" -> SuitMe.

Distinction: This is for personalized feedback. A general question like "What styles are best for a pear shape?" is General.

2. Pairing

Description: The user has a specific "anchor" item (that they own, are considering, or just mentioned) and is looking for recommendations for other products to wear or use with it. The goal is product discovery to complete a specific look.

Example: "I just bought these black jeans, what kind of tops would go well with them?" -> Pairing.

Distinction: This requires an anchor item. A general styling question like "How do you style black jeans?" is General. A broad request like "show me tops" is also General.

3. Occasion

Description: The user is shopping for a specific event, activity, or social setting with an implicit or explicit dress code. The occasion is the primary filter for the search.

Example: "I need something to wear for a job interview next week." -> Occasion.

Distinction: The event is the main driver. If a user asks about an outfit for a "wedding in Bali," the Occasion (wedding) is more specific than the Vacation (Bali) and should be chosen.

4. Vacation

Description: The user is planning, packing for, or shopping for a trip. The needs are contextualized by a destination's climate, culture, or planned activities. This intent is used when the trip itself is the primary context.

Example: "I'll be going to Goa next month, what else should I pack?" -> Vacation.

Distinction: This is for trip-level planning. If a specific event is mentioned within the trip (e.g., "a formal dinner on my cruise"), Occasion takes precedence.

5. General (Least Specific - Catch-all)

Description: This is the default intent used ONLY if the query does not fit any of the more specific categories above. It covers two main scenarios: (A) Broad Product Browse where the user wants to see a category of items without specific constraints, and (B) Informational Questions about fashion, trends, or style principles that are not personalized.

Example (A - Browse): "Show me some red dresses." -> General.

Example (B - Informational): "What is the difference between linen and cotton?" -> General.

Step 3: Format the Output
Provide your response in a strict JSON format. Do not add any text outside of the JSON structure.

INPUTS FOR YOUR ANALYSIS:

Current User Input: {user_input}

Conversation Context: {context}

JSON OUTPUT FORMAT:

{{
  "reasoning": "A brief, one-sentence explanation of your decision-making process, referencing the intent hierarchy and why the chosen intent is the most specific, accurate fit.",
  "intent": "The single, most accurate intent from the list."
}}

"""

        response = self._call_ai(prompt).strip()
            
        # Find JSON content
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        
        if start_idx != -1 and end_idx != 0:
            json_content = json.loads(response[start_idx:end_idx])
            print("reasoning for intent is", json_content['reasoning'])
            print("intent is", json_content['intent'])
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
