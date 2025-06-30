import json
from typing import Dict, List, Optional, Any
from openai import OpenAI
from reccomendationBot import RecommendationService
import os


class OccasionService:
    PARAMETER_PRIORITY = ["gender", "occasion", "mood", "time", "budget", "location", "body_type"]
    def __init__(self, api_key: str):
        """
        Initialize the OccasionService with OpenAI client.
        
        Args:
            api_key (str): OpenAI API key
        """

        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found. Please set environment variable or pass api_key parameter.")
        
       
        self.client = OpenAI(api_key=self.api_key)
        
        self.core_parameters = [
            "occasion", "time", "location", "body_type", "budget", "gender"
        ]
        
        self.inferred_parameters = [
            "weather", "formality", "mood", "color", "fabric", "trend", "age"
        ]

        #self.reccomendation_bot = RecommendationService()
    
    def extract_parameters(self, user_input: str, conversation_history: str = "") -> Dict[str, Any]:
        """
        Extract parameters from user input using AI.
        
        Args:
            user_input (str): The user's current input
            conversation_history (str): Previous conversation context
            
        Returns:
            Dict[str, Any]: Dictionary containing core and inferred parameters
        """
        prompt = self._create_extraction_prompt(user_input, conversation_history)
        
        try:
            response = self._call_ai(prompt)
            parameters = self._parse_ai_response(response)
            return parameters
        except Exception as e:
            print(f"Error in parameter extraction: {e}")
            return self._get_empty_parameters()
    
    def _create_extraction_prompt(self, user_input: str, conversation_history: str) -> str:
        """
        Create the prompt for AI parameter extraction.
        
        Args:
            user_input (str): User's input
            conversation_history (str): Previous conversation
            
        Returns:
            str: Formatted prompt for AI
        """
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
- age: ["teen", "young_adult", "adult", "middle_aged", "senior"]

**INFERRED PARAMETERS (Infer based on context and occasion):**
- weather: ["hot", "cold", "rainy", "humid", "mild", "sunny", etc.] - if they give some country or region get its weather
- formality: ["casual", "smart_casual", "business_casual", "formal", "black_tie"]
- mood: ["confident", "romantic", "playful", "professional", "elegant", "edgy", "comfortable"]
- color: ["bright", "neutral", "dark", "pastels", "jewel_tones", "earth_tones", "red", "blue", etc.]
- brand: ["luxury", "premium", "mid_range", "affordable", "sustainable", "trendy"]
- fabric: ["cotton", "silk", "denim", "wool", "linen", "synthetic", "breathable", "formal"]
- trend: ["classic", "trendy", "vintage", "minimalist", "bohemian", "streetwear", "traditional"]

**RULES:**
1. Each parameter should be a LIST of relevant tags, or null if not applicable
2. Include multiple relevant values for each parameter (e.g., occasion could be ["wedding", "formal_event"])
3. For colors, include both general (["neutral", "dark"]) and specific (["navy", "black"]) if mentioned
4. Be conservative - only include values you're confident about
5. For inferred parameters, use logical connections (e.g., wedding → ["formal", "elegant"])
6. Consider cultural context (Indian fashion context)
7. Maximum 3-4 values per parameter to keep it focused

**OUTPUT FORMAT:**
Return ONLY a valid JSON object. Use null for missing parameters, and arrays for present ones.

Example structure:
{{
  "core_parameters": {{
    "occasion": ["value1", "value2"] or null,
    "time": ["value1"] or null,
    "location": ["value1", "value2"] or null,
    "body_type": null,
    "budget": ["value1"] or null,
    "gender": null,
    "age": null
  }},
  "inferred_parameters": {{
    "weather": null,
    "formality": ["value1", "value2"] or null,
    "mood": ["value1"] or null,
    "color": ["value1", "value2"] or null,
    "brand": ["value1"] or null,
    "fabric": ["value1", "value2"] or null,
    "trend": ["value1"] or null
  }}
}}

**EXAMPLE 1:**
Input: "I need something elegant and comfortable for my sister's wedding tomorrow evening"
{{
  "core_parameters": {{
    "occasion": ["wedding"],
    "time": ["evening"],
    "location": null,
    "body_type": null,
    "budget": null,
    "gender": null,
    "age": null
  }},
  "inferred_parameters": {{
    "weather": null,
    "formality": ["formal", "semi_formal"],
    "mood": ["elegant", "comfortable"],
    "color": ["jewel_tones", "rich_colors"],
    "brand": ["premium", "mid_range"],
    "fabric": ["silk", "chiffon", "comfortable"],
    "trend": ["classic", "traditional"]
  }}
}}

**EXAMPLE 2:**
Input: "Casual but smart office look for Monday morning meeting, budget around 3000, want to look professional"
{{
  "core_parameters": {{
    "occasion": ["work", "meeting"],
    "time": ["morning"],
    "location": ["office", "indoor"],
    "body_type": null,
    "budget": ["1000-3000"],
    "gender": null,
    "age": null
  }},
  "inferred_parameters": {{
    "weather": null,
    "formality": ["business_casual", "smart_casual"],
    "mood": ["professional", "confident"],
    "color": ["neutral", "navy", "black"],
    "brand": ["mid_range", "affordable"],
    "fabric": ["cotton", "formal", "breathable"],
    "trend": ["classic", "minimalist"]
  }}
}}

**EXAMPLE 3:**
Input: "Need a fun colorful dress for brunch with friends this weekend"
{{
  "core_parameters": {{
    "occasion": ["brunch", "casual"],
    "time": ["morning", "afternoon"],
    "location": ["restaurant", "indoor"],
    "body_type": null,
    "budget": null,
    "gender": ["female"],
    "age": null
  }},
  "inferred_parameters": {{
    "weather": null,
    "formality": ["casual", "smart_casual"],
    "mood": ["fun", "playful", "comfortable"],
    "color": ["bright", "colorful", "vibrant"],
    "brand": ["mid_range", "trendy"],
    "fabric": ["cotton", "light", "breathable"],
    "trend": ["trendy", "bohemian"]
  }}
}}

Now analyze the user input and return the JSON:"""
        return prompt
    
    def _call_ai(self, prompt: str) -> str:
        """
        Send prompt to AI and get response.
        
        Args:
            prompt (str): The prompt to send
            
        Returns:
            str: AI response
        """
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1  # Lower temperature for more consistent JSON output
        )
        return completion.choices[0].message.content
    
    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """
        Parse the AI response JSON into a dictionary.
        
        Args:
            ai_response (str): Raw AI response
            
        Returns:
            Dict[str, Any]: Parsed parameters
        """
        try:
            # Clean the response - remove any text before/after JSON
            response = ai_response.strip()
            
            # Find JSON content between braces
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx != 0:
                json_content = response[start_idx:end_idx]
                parameters = json.loads(json_content)
                
                # Validate structure
                if "core_parameters" in parameters and "inferred_parameters" in parameters:
                    return parameters
                else:
                    print("Invalid JSON structure in AI response")
                    return self._get_empty_parameters()
            else:
                print("No JSON found in AI response")
                return self._get_empty_parameters()
                
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"AI Response: {ai_response}")
            return self._get_empty_parameters()
        except Exception as e:
            print(f"Unexpected error parsing AI response: {e}")
            return self._get_empty_parameters()
    
    def _get_empty_parameters(self) -> Dict[str, Any]:
        """
        Return empty parameter structure as fallback.
        
        Returns:
            Dict[str, Any]: Empty parameters with null values
        """
        return {
            "core_parameters": {param: None for param in self.core_parameters},
            "inferred_parameters": {param: None for param in self.inferred_parameters}
        }
    
    def get_missing_core_parameters(self, parameters: Dict[str, Any]) -> List[str]:
        """
        Get list of missing core parameters that need follow-up questions.
        
        Args:
            parameters (Dict[str, Any]): Extracted parameters
            
        Returns:
            List[str]: List of missing core parameter names
        """
        missing = []
        core_params = parameters.get("core_parameters", {})
        
        for param in self.core_parameters:
            param_value = core_params.get(param)
            # Check if parameter is null or empty list
            if param_value is None or (isinstance(param_value, list) and len(param_value) == 0):
                missing.append(param)
        
        return missing
    

    
    def get_confidence_score(self, parameters: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on how many parameters were extracted.
        
        Args:
            parameters (Dict[str, Any]): Extracted parameters
            
        Returns:
            float: Confidence score between 0 and 1
        """
        core_params = parameters.get("core_parameters", {})
        inferred_params = parameters.get("inferred_parameters", {})
        
        # Count non-null and non-empty parameters
        filled_core = 0
        for param_value in core_params.values():
            if param_value is not None and (not isinstance(param_value, list) or len(param_value) > 0):
                filled_core += 1
        
        filled_inferred = 0
        for param_value in inferred_params.values():
            if param_value is not None and (not isinstance(param_value, list) or len(param_value) > 0):
                filled_inferred += 1
        
        # Weight core parameters more heavily
        weighted_score = (filled_core * 2 + filled_inferred) / (len(self.core_parameters) * 2 + len(self.inferred_parameters))
        
        return min(weighted_score, 1.0)
    
    def get_all_tags_flat(self, parameters: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Get all extracted tags in a flattened format for easy use with recommendation service.
        
        Args:
            parameters (Dict[str, Any]): Extracted parameters
            
        Returns:
            Dict[str, List[str]]: Flattened tags by category (core/inferred)
        """
        all_tags = {
            "core_tags": [],
            "inferred_tags": []
        }
        
        # Flatten core parameters
        core_params = parameters.get("core_parameters", {})
        for param_name, param_value in core_params.items():
            if param_value is not None:
                if isinstance(param_value, list):
                    all_tags["core_tags"].extend(param_value)
                else:
                    all_tags["core_tags"].append(param_value)
        
        # Flatten inferred parameters
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
        """
        Generates a trendy, Gen Z-focused style tip.
        """
        core_params = extracted_parameters.get("core_parameters", {})
        occasion = self._get_param_value(core_params.get("occasion"))
        
        # --- NEW PROMPT FOCUSED ON GEN Z TRENDS ---
        prompt = f"""
        You are a super-stylish friend who is on top of all the latest Gen Z fashion trends, aesthetics, and terminology 
        (like Y2K revival, streetwear, gorpcore, baggy silhouettes, cargos, baby tees, etc.).
        
        An India friend has made the following request: "{user_query}"
        Your previous conversation: "{conversation}
        The known occasion is: {occasion}
        The recs given to your friend: {recs}

        YOUR TASK:
        Give them a cool, insightful tip in a friendly, conversational tone. Your advice should follow this structure:
        1. Suggest a current, Gen Z reccomendation that fits the occasion and the recs given to your friend
        2. Educate on why they should make this choice - this should be max 2 phrases
        
        GUIDELINES:
        - Use current fashion terms correctly 
        - Keep the tone like a helpful, in-the-know friend.
        - Keep the responses tailored for indian context
        - Avoid sounding like a corporate brand trying to be "hip."

        EXAMPLE 1 (if occasion is 'brunch'): 
        recs given : Wide linen pants

        Output : "Okay, brunch! You could totally own the vibe with some wide-leg linen pants and a baby tee, or even a Y2K-inspired denim midi skirt for a major look."

        EXAMPLE 2 (if occasion is 'concert'):
        recs given : None

        Output: "A concert, let's go! Everyone defaults to skinny jeans and a band tee. How about a streetwear look instead, like some baggy cargo pants with a graphic tee and a utility vest? Super functional and on-trend."

        Now, generate the insightful statement for your friend's request.
        """
        try:
            return self._call_ai(prompt).strip()
        except Exception as e:
            print(f"Error generating Gen Z insightful statement: {e}")
            return ""

    def _get_prioritized_missing_params(self, missing_parameters: List[str], max_questions: int) -> List[str]:
        """Sorts the missing parameters based on a predefined priority list."""
        prioritized_list = [p for p in self.PARAMETER_PRIORITY if p in missing_parameters]
        remaining_params = [p for p in missing_parameters if p not in self.PARAMETER_PRIORITY]
        return (prioritized_list + remaining_params)[:max_questions]

    def generate_followup_questions(self, 
                         
                                    missing_parameters: List[str], 
                                  
                                    max_questions: int = 2) -> str:
        """
        Generates a Gen Z style tip followed by casual, direct follow-up questions.
        """
        if not missing_parameters:
            return "Bet. I've got all the info I need to find some fire options for you. 🔥"

        

        params_to_ask = self._get_prioritized_missing_params(missing_parameters, max_questions)


        # --- UPDATED CASUAL TONE FOR QUESTIONS ---
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
            return f"Help me out, what's the deal with the {params_to_ask[0]}?"

    def _get_param_value(self, param_value):
        """Helper to extract string value from parameter (handles lists and strings)"""
        if param_value is None:
            return None
        if isinstance(param_value, list) and len(param_value) > 0:
            return ", ".join(param_value)
        if isinstance(param_value, str):
            return param_value
        return str(param_value)

