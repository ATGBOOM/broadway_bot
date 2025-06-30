import json
from typing import Dict, List, Optional, Any
from openai import OpenAI
import os

class OccasionService:
    PARAMETER_PRIORITY = ["gender", "occasion", "mood", "time", "budget", "location", "body_type"]
    
    def __init__(self):
        """Initialize the OccasionService with OpenAI client."""
        # OpenAI() automatically uses OPENAI_API_KEY environment variable
        self.client = OpenAI()
        
        self.core_parameters = [
            "occasion", "time", "location", "body_type", "budget", "gender"
        ]
        
        self.inferred_parameters = [
            "weather", "formality", "mood", "color", "fabric", "trend", "age"
        ]

    # Rest of your methods remain the same...
    def extract_parameters(self, user_input: str, conversation_history: str = "") -> Dict[str, Any]:
        """Extract parameters from user input using AI."""
        prompt = self._create_extraction_prompt(user_input, conversation_history)
        
        try:
            response = self._call_ai(prompt)
            parameters = self._parse_ai_response(response)
            
            # If parsing failed, use simple keyword detection as fallback
            if not parameters or not parameters.get('core_parameters'):
                print("❌ AI parsing failed, using keyword fallback")
                return self._keyword_fallback(user_input)
                
            return parameters
        except Exception as e:
            print(f"Error in parameter extraction: {e}")
            return self._keyword_fallback(user_input)
    
    def _keyword_fallback(self, user_input: str) -> Dict[str, Any]:
        """Simple keyword-based parameter extraction as fallback"""
        user_lower = user_input.lower()
        
        # Simple keyword detection
        occasion = None
        if any(word in user_lower for word in ['wedding', 'marriage', 'shaadi']):
            occasion = ['wedding']
        elif any(word in user_lower for word in ['work', 'office', 'meeting']):
            occasion = ['work']
        elif any(word in user_lower for word in ['party', 'celebration']):
            occasion = ['party']
        elif any(word in user_lower for word in ['date', 'dinner']):
            occasion = ['date']
        
        gender = None
        if any(word in user_lower for word in ['women', 'female', 'girl', 'dress', 'lady']):
            gender = ['female']
        elif any(word in user_lower for word in ['men', 'male', 'guy', 'man']):
            gender = ['male']
        
        time = None
        if any(word in user_lower for word in ['evening', 'night', 'tonight']):
            time = ['evening']
        elif any(word in user_lower for word in ['morning', 'am']):
            time = ['morning']
        elif any(word in user_lower for word in ['afternoon', 'lunch']):
            time = ['afternoon']
        
        return {
            "core_parameters": {
                "occasion": occasion,
                "time": time,
                "location": None,
                "body_type": None,
                "budget": None,
                "gender": gender
            },
            "inferred_parameters": {
                "weather": None,
                "formality": ['formal'] if occasion == ['wedding'] else None,
                "mood": ['elegant'] if occasion == ['wedding'] else None,
                "color": None,
                "fabric": None,
                "trend": None,
                "age": None
            }
        }
    
    def _create_extraction_prompt(self, user_input: str, conversation_history: str) -> str:
        """Create the prompt for AI parameter extraction."""
        prompt = f"""You are an expert fashion stylist and personal shopper. Analyze the user's request and extract relevant parameters for outfit recommendations.

**USER INPUT:** {user_input}
**CONVERSATION HISTORY:** {conversation_history}

Extract the following parameters and return them in JSON format. Each parameter should be a LIST of relevant values or null if not applicable.

**CORE PARAMETERS (Extract if and only if explicitly mentioned and clearly implied):**
- occasion: ["wedding", "work", "party", "date", "travel", "festival", etc.]
- time: ["morning", "afternoon", "evening", "night", "specific_time"]
- location: ["indoor", "outdoor", "office", "restaurant", "home", "beach", "mall", "India", "Kenya" etc.]
- body_type: ["petite", "tall", "curvy", "athletic", "slim", "plus-size", etc.]
- budget: ["under_1000", "1000-3000", "3000-5000", "5000-10000", "above_10000", "luxury"]
- gender: ["male", "female", "unisex"]

**INFERRED PARAMETERS (Infer based on context and occasion):**
- weather: ["hot", "cold", "rainy", "humid", "mild", "sunny", etc.]
- formality: ["casual", "smart_casual", "business_casual", "formal", "black_tie"]
- mood: ["confident", "romantic", "playful", "professional", "elegant", "edgy", "comfortable"]
- color: ["bright", "neutral", "dark", "pastels", "jewel_tones", "earth_tones", "red", "blue", etc.]
- fabric: ["cotton", "silk", "denim", "wool", "linen", "synthetic", "breathable", "formal"]
- trend: ["classic", "trendy", "vintage", "minimalist", "bohemian", "streetwear", "traditional"]
- age: ["teen", "young_adult", "adult", "middle_aged", "senior"]

**CRITICAL: Return ONLY valid JSON. No extra text before or after the JSON.**

**REQUIRED FORMAT:**
{{
  "core_parameters": {{
    "occasion": null,
    "time": null,
    "location": null,
    "body_type": null,
    "budget": null,
    "gender": null
  }},
  "inferred_parameters": {{
    "weather": null,
    "formality": null,
    "mood": null,
    "color": null,
    "fabric": null,
    "trend": null,
    "age": null
  }}
}}

Replace null with arrays of relevant values or keep as null if not applicable.

Example for "I need a dress for a wedding tonight":
{{
  "core_parameters": {{
    "occasion": ["wedding"],
    "time": ["evening"],
    "location": null,
    "body_type": null,
    "budget": null,
    "gender": ["female"]
  }},
  "inferred_parameters": {{
    "weather": null,
    "formality": ["formal"],
    "mood": ["elegant"],
    "color": ["jewel_tones"],
    "fabric": ["silk"],
    "trend": ["classic"],
    "age": null
  }}
}}

Now analyze the user input and return ONLY the JSON:"""
        return prompt
    
    def _call_ai(self, prompt: str) -> str:
        """Send prompt to AI and get response."""
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        return completion.choices[0].message.content
    
    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse the AI response JSON into a dictionary."""
        try:
            # Clean the response - remove any text before/after JSON
            response = ai_response.strip()
            
            # Debug: Print the raw response
            print(f"Raw AI Response: {response[:500]}...")
            
            # Try to find JSON content between braces
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_content = response[start_idx:end_idx]
                print(f"Extracted JSON: {json_content[:200]}...")
                
                try:
                    parameters = json.loads(json_content)
                    
                    # Validate structure
                    if "core_parameters" in parameters and "inferred_parameters" in parameters:
                        print("✅ Valid JSON structure found")
                        return parameters
                    else:
                        print("❌ Invalid JSON structure - missing required keys")
                        print(f"Available keys: {list(parameters.keys())}")
                        return self._get_empty_parameters()
                        
                except json.JSONDecodeError as json_error:
                    print(f"❌ JSON decode error: {json_error}")
                    # Try to fix common JSON issues
                    return self._try_fix_json(json_content)
            else:
                print("❌ No JSON braces found in response")
                return self._get_empty_parameters()
                
        except Exception as e:
            print(f"❌ Unexpected error parsing AI response: {e}")
            return self._get_empty_parameters()
    
    def _try_fix_json(self, json_content: str) -> Dict[str, Any]:
        """Try to fix common JSON issues"""
        try:
            # Common fixes
            fixed_content = json_content
            
            # Fix trailing commas
            import re
            fixed_content = re.sub(r',(\s*[}\]])', r'\1', fixed_content)
            
            # Fix single quotes to double quotes
            fixed_content = fixed_content.replace("'", '"')
            
            # Try parsing again
            parameters = json.loads(fixed_content)
            
            if "core_parameters" in parameters and "inferred_parameters" in parameters:
                print("✅ Fixed JSON successfully")
                return parameters
            else:
                print("❌ Fixed JSON still has wrong structure")
                return self._get_empty_parameters()
                
        except Exception as e:
            print(f"❌ Could not fix JSON: {e}")
            return self._get_empty_parameters()
    
    def _get_empty_parameters(self) -> Dict[str, Any]:
        """Return empty parameter structure as fallback."""
        return {
            "core_parameters": {param: None for param in self.core_parameters},
            "inferred_parameters": {param: None for param in self.inferred_parameters}
        }
    
    def get_missing_core_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """Get list of missing core parameters that need follow-up questions."""
        missing = []
        core_params = parameters.get("core_parameters", {})
        
        for param in self.core_parameters:
            param_value = core_params.get(param)
            if param_value is None or (isinstance(param_value, list) and len(param_value) == 0):
                missing.append(param)
        
        return missing
    
    def get_confidence_score(self, parameters: Dict[str, Any]) -> float:
        """Calculate confidence score based on how many parameters were extracted."""
        core_params = parameters.get("core_parameters", {})
        inferred_params = parameters.get("inferred_parameters", {})
        
        filled_core = 0
        for param_value in core_params.values():
            if param_value is not None and (not isinstance(param_value, list) or len(param_value) > 0):
                filled_core += 1
        
        filled_inferred = 0
        for param_value in inferred_params.values():
            if param_value is not None and (not isinstance(param_value, list) or len(param_value) > 0):
                filled_inferred += 1
        
        weighted_score = (filled_core * 2 + filled_inferred) / (len(self.core_parameters) * 2 + len(self.inferred_parameters))
        return min(weighted_score, 1.0)
    
    def get_all_tags_flat(self, parameters: Dict[str, Any]) -> Dict[str, List[str]]:
        """Get all extracted tags in a flattened format for easy use with recommendation service."""
        all_tags = {
            "core_tags": [],
            "inferred_tags": []
        }
        
        core_params = parameters.get("core_parameters", {})
        for param_name, param_value in core_params.items():
            if param_value is not None:
                if isinstance(param_value, list):
                    all_tags["core_tags"].extend(param_value)
                else:
                    all_tags["core_tags"].append(param_value)
        
        inferred_params = parameters.get("inferred_parameters", {})
        for param_name, param_value in inferred_params.items():
            if param_value is not None:
                if isinstance(param_value, list):
                    all_tags["inferred_tags"].extend(param_value)
                else:
                    all_tags["inferred_tags"].append(param_value)
        
        return all_tags
    
    def _get_param_value(self, param: Any) -> str:
        """Safely gets a string representation of a parameter."""
        return str(param) if param else 'Not specified'

    def generate_insightful_statement(self, user_query: str, conversation, recs, extracted_parameters: Dict[str, Any]) -> str:
        """Generates a trendy, Gen Z-focused style tip."""
        core_params = extracted_parameters.get("core_parameters", {})
        occasion = self._get_param_value(core_params.get("occasion"))
        
        prompt = f"""
        You are a super-stylish friend who is on top of all the latest Gen Z fashion trends, aesthetics, and terminology 
        (like Y2K revival, streetwear, gorpcore, baggy silhouettes, cargos, baby tees, etc.).
        
        An India friend has made the following request: "{user_query}"
        Your previous conversation: "{conversation}"
        The known occasion is: {occasion}
        The recs given to your friend: {recs}

        YOUR TASK:
        Give them a cool, insightful tip in a friendly, conversational tone. Your advice should follow this structure:
        1. Suggest a current, Gen Z recommendation that fits the occasion and the recs given to your friend
        2. Educate on why they should make this choice - this should be max 2 phrases
        
        GUIDELINES:
        - Use current fashion terms correctly 
        - Keep the tone like a helpful, in-the-know friend.
        - Keep the responses tailored for indian context
        - Avoid sounding like a corporate brand trying to be "hip."

        Now, generate the insightful statement for your friend's request.
        """
        try:
            return self._call_ai(prompt).strip()
        except Exception as e:
            print(f"Error generating Gen Z insightful statement: {e}")
            return f"Great! I found some perfect options for your {occasion}!"

    def _get_prioritized_missing_params(self, missing_parameters: List[str], max_questions: int) -> List[str]:
        """Sorts the missing parameters based on a predefined priority list."""
        prioritized_list = [p for p in self.PARAMETER_PRIORITY if p in missing_parameters]
        remaining_params = [p for p in missing_parameters if p not in self.PARAMETER_PRIORITY]
        return (prioritized_list + remaining_params)[:max_questions]

    def generate_followup_questions(self, missing_parameters: List[str], max_questions: int = 2) -> str:
        """Generates a Gen Z style tip followed by casual, direct follow-up questions."""
        if not missing_parameters:
            return "Bet. I've got all the info I need to find some fire options for you. 🔥"

        params_to_ask = self._get_prioritized_missing_params(missing_parameters, max_questions)

        prompt = f"""
        You are a friendly, super-stylish Gen Z Indian friend. You just gave some initial advice and now you need more info.
        
        YOUR TASK:
        Formulate a casual, natural question to get the following details: {', '.join(params_to_ask)}.
        Keep it brief and bundle the questions together.
        
        Example (if missing ['occasion', 'budget']):
        "So to get the vibe right, what's the actual event? And what's the budget we're playing with?"

        Example (if missing ['time', 'gender']):
        "Okay, so is this a daytime or nighttime thing? And are we looking for men's or women's styles?"

        Now, generate the follow-up questions.
        """
        try:
            follow_up_questions = self._call_ai(prompt).strip()
            return f"{follow_up_questions}"
        except Exception as e:
            print(f"Error generating follow-up questions: {e}")
            return f"Help me out, what's the deal with the {params_to_ask[0] if params_to_ask else 'occasion'}?"