# fashion_graph.py - Fixed version
from typing import Dict, List, Optional, Literal, TypedDict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


class FashionState(TypedDict):
    """State that flows through the LangGraph workflow"""
    user_input: str
    client_id: str
    conversation_history: str
    service_mode: Optional[str]
    gender: Optional[str]
    current_parameters: Optional[Dict]
    recommendations: List[Dict]
    response_message: Optional[str]
    websocket_messages: List[Dict]
    follow_up_needed: bool
    follow_up_message: Optional[List[Dict]]  # FIXED: Should be List[Dict] for multiple questions
    confidence_score: Optional[float]
    error_message: Optional[str]
    is_gender_loop: bool  
    user_info: Optional[Dict]  # FIXED: Added default initialization


class FashionWorkflow:
    """LangGraph workflow for fashion bot conversations"""
    
    def __init__(self, services_dict):
        """Initialize with your existing services"""
        self.occasion_service = services_dict['occasion']
        self.recommendation_service = services_dict['recommendation']
        self.pairing_service = services_dict['pairing']
        self.vacation_service = services_dict['vacation']
        self.conversation_service = services_dict['conversation']
        self.general_service = services_dict['general']
        self.gender_service = services_dict['gender']
        self.styling_service = services_dict['styling']
        
        # FIXED: Removed duplicate style_preferences key
        self.questions = {
            "gender": {
                "key": "gender",
                "label": "What's your gender?",
                "type": "select",
                "options": ["Male", "Female", "Non-binary", "Prefer not to say"]
            },
            "body_type": {
                "key": "body_type",
                "label": "What's your body type?",
                "type": "select",
                "options": [
                    "Pear (wider hips, narrower shoulders)",
                    "Apple (broader shoulders, narrower hips)",
                    "Hourglass (balanced shoulders and hips, defined waist)",
                    "Rectangle (straight up and down, minimal curves)",
                    "Inverted Triangle (broad shoulders, narrow hips)",
                    "Oval (fuller midsection)",
                    "Athletic (muscular, well-defined)",
                    "Plus Size",
                    "Petite",
                    "Tall",
                    "Not sure"
                ]
            },
            "skin_tone": {
                "key": "skin_tone",
                "label": "What's your skin tone?",
                "type": "select",
                "options": [
                    "Fair (light with pink undertones)",
                    "Light (light with neutral undertones)",
                    "Medium-Light (light to medium with warm undertones)",
                    "Medium (medium with neutral undertones)",
                    "Medium-Dark (medium to dark with warm undertones)",
                    "Dark (deep with rich undertones)",
                    "Deep (very deep with cool or warm undertones)",
                    "Warm undertones (yellow/golden base)",
                    "Cool undertones (pink/blue base)",
                    "Neutral undertones (mix of warm and cool)",
                    "Not sure"
                ]
            },
            "height": {
                "key": "height",
                "label": "What's your height range?",
                "type": "select",
                "options": [
                    "Under 5'0\" (152 cm)",
                    "5'0\" - 5'2\" (152-157 cm)",
                    "5'3\" - 5'5\" (160-165 cm)",
                    "5'6\" - 5'8\" (168-173 cm)",
                    "5'9\" - 5'11\" (175-180 cm)",
                    "6'0\" and above (183 cm+)",
                    "Prefer not to say"
                ]
            },
            "style_preferences": {
                "key": "style_preferences",
                "label": "What's your preferred style?",
                "type": "select",
                "options": [
                    "Classic & Timeless",
                    "Casual & Comfortable",
                    "Business & Professional",
                    "Trendy & Fashion-Forward",
                    "Bohemian & Free-Spirited",
                    "Minimalist & Clean",
                    "Edgy & Bold",
                    "Romantic & Feminine",
                    "Sporty & Athletic",
                    "Vintage & Retro",
                    "Eclectic & Mix-and-Match",
                    "Glamorous & Elegant"
                ]
            },
            "size_preferences": {
                "key": "size_preferences",
                "label": "What's your usual clothing size?",
                "type": "select",
                "options": [
                    "XS (Extra Small)",
                    "S (Small)",
                    "M (Medium)",
                    "L (Large)",
                    "XL (Extra Large)",
                    "XXL (2X Large)",
                    "XXXL (3X Large)",
                    "Varies by brand",
                    "Prefer not to say"
                ]
            }
        }
        
        # Build and compile the workflow
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile(checkpointer=MemorySaver())
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        workflow = StateGraph(FashionState)
        
        # Add nodes
        workflow.add_node("process_conversation", self._process_conversation)
        workflow.add_node("extract_gender", self._extract_gender)
        workflow.add_node("route_to_service", self._route_to_service)
        workflow.add_node("handle_occasion", self._handle_occasion)
        workflow.add_node("handle_pairing", self._handle_pairing)
        workflow.add_node("handle_vacation", self._handle_vacation)
        workflow.add_node("handle_general", self._handle_general)
        workflow.add_node("handle_styling", self._handle_styling)
        workflow.add_node("generate_followup", self._generate_followup)
        workflow.add_node("prepare_response", self._prepare_response)
        workflow.add_node("process_bot_response", self._process_bot_response)
        
        # Define the flow
        workflow.set_entry_point("process_conversation")
        workflow.add_edge("process_conversation", "extract_gender")
        
        workflow.add_conditional_edges(
            "extract_gender",
            self._check_gender_available,
            {
                "gender_found": "route_to_service",
                "gender_missing": "generate_followup"
            }
        )
        
        workflow.add_conditional_edges(
            "route_to_service",
            self._decide_service_route,
            {
                "occasion": "handle_occasion",
                "pairing": "handle_pairing", 
                "vacation": "handle_vacation",
                "general": "handle_general",
                "styling": "handle_styling"
            }
        )
        
        # Check if follow-up is needed after each service
        workflow.add_conditional_edges(
            "handle_occasion",
            self._check_followup_needed,
            {
                "followup": "generate_followup",
                "complete": "prepare_response"
            }
        )
        
        workflow.add_conditional_edges(
            "handle_pairing",
            self._check_followup_needed,
            {
                "followup": "generate_followup",
                "complete": "prepare_response"
            }
        )
        
        workflow.add_conditional_edges(
            "handle_vacation",
            self._check_followup_needed,
            {
                "followup": "generate_followup",
                "complete": "prepare_response"
            }
        )

        workflow.add_conditional_edges(
            "handle_styling",
            self._check_followup_style_needed,
            {
                "followup": "generate_followup",
                "complete": "prepare_response"
            }
        )
        
        workflow.add_edge("handle_general", "prepare_response")
        workflow.add_edge("generate_followup", "prepare_response")
        workflow.add_edge("prepare_response", "process_bot_response")
        workflow.add_edge("process_bot_response", END)
        
        return workflow
    
    def _process_conversation(self, state: FashionState) -> FashionState:
        """Process conversation using your existing conversation service"""
        try:
            intent, context = self.conversation_service.processTurn(state["user_input"], state['user_info']['gender'])
            state["service_mode"] = intent.lower()
            state["conversation_history"] = context
            return state
        except Exception as e:
            state["error_message"] = f"Error processing conversation: {str(e)}"
            return state
    
    def _extract_gender(self, state: FashionState) -> FashionState:
        """Extract gender using your existing logic"""
        try:
            gender = self._infer_gender(state["user_input"], state["conversation_history"], state['user_info']['gender'])
            state['user_info']['gender'] = gender
            return state
        except Exception as e:
            state["error_message"] = f"Error extracting gender: {str(e)}"
            return state
    
    def _route_to_service(self, state: FashionState) -> FashionState:
        """Prepare for service routing"""
        return state
    
    def _handle_occasion(self, state: FashionState) -> FashionState:
        """Handle occasion mode using your existing logic"""
        try:
            parameters = self.occasion_service.extract_parameters(
                state["user_input"], 
                state.get("current_parameters"), 
                state["conversation_history"]
            )
            state["current_parameters"] = parameters
            
            confidence_score = self.occasion_service.get_confidence_score(parameters)
            state["confidence_score"] = confidence_score
            
            if not (state['user_info'] and state['user_info']['gender']):
                state["follow_up_needed"] = True
                state["follow_up_message"] = [self.questions["gender"]]  # FIXED: Make it a list
            else:
                dialogue, recommendations = self._generate_occasion_recommendations(state)
                state["recommendations"] = recommendations
                state["response_message"] = dialogue
                state["follow_up_needed"] = False
                
            return state
            
        except Exception as e:
            state["error_message"] = f"Error in occasion handling: {str(e)}"
            return state
    
    def _handle_pairing(self, state: FashionState) -> FashionState:
        """Handle pairing mode using your existing logic"""
        try:
            complements = self.pairing_service.getComplementProducts(
                state["user_input"], 
                state["conversation_history"]
            )
            state["recommendations"] = complements
            
            item_to_pair = state["user_input"].lower().strip()
            if complements:
                response_message = f"Perfect! For {item_to_pair}, here are some great pieces that would complement it beautifully. These combinations will create cohesive, stylish looks!"
            else:
                response_message = f"I couldn't find specific pairings for '{item_to_pair}'. Could you try describing the item differently? For example: 'blue jeans', 'white shirt', 'black boots', etc."
            
            state["response_message"] = response_message
            state["follow_up_needed"] = False
                
            return state
            
        except Exception as e:
            state["error_message"] = f"Error in pairing handling: {str(e)}"
            return state
    
    def _handle_vacation(self, state: FashionState) -> FashionState:
        """Handle vacation mode using your existing logic"""
        try:
            dialogue, products = self.vacation_service.get_vacation_recommendation(
                state["user_input"], 
                state["conversation_history"]
            )
            state["recommendations"] = products
            state["response_message"] = dialogue
            state["follow_up_needed"] = False
                
            return state
            
        except Exception as e:
            state["error_message"] = f"Error in vacation handling: {str(e)}"
            return state
    
    def _handle_general(self, state: FashionState) -> FashionState:
        """Handle general mode using your existing logic"""
        try:
            general_message, prods = self.general_service.respond(
                state["conversation_history"], 
                state["user_input"]
            )
            state["recommendations"] = prods or []
            state["response_message"] = general_message
            state["follow_up_needed"] = False
            return state
            
        except Exception as e:
            state["error_message"] = f"Error in general handling: {str(e)}"
            return state
        
    def _handle_styling(self, state: FashionState) -> FashionState:
        """Handle styling mode using your existing logic"""
        try:
            # FIXED: Initialize user_info if not present
            if not state.get("user_info"):
                state["user_info"] = {}
            
            result = self.styling_service.analyze_looks_good_on_me(
                user_input=state['user_input'],
                conversation_context=state['conversation_history'],
                user_info=state["user_info"],
                product_details={},
                recs=state.get('recommendations', [])
            )
            summary = result['user_response']['summary']
            tips = result['styling_tips_for_recommendations']

            formatted_text = f"{summary}\n\nStyling Tips:\n" + "\n".join([f"{i+1}. {tip.capitalize()}" for i, tip in enumerate(tips)])

            state["recommendations"] = []
            state["response_message"] = formatted_text
            state["follow_up_needed"] = False
            return state
            
        except Exception as e:
            state["error_message"] = f"Error in styling handling: {str(e)}"
            return state
    
    def _generate_followup(self, state: FashionState) -> FashionState:
        """Generate follow-up question"""

        
        user_info = state['user_info']
        
        if state['service_mode'] == 'styling':
            
            required_fields = ['body_type', 'skin_tone', 'height', 'style_preferences', 'size_preferences']
          
            missing_fields = [field for field in required_fields if not user_info.get(field)]
            followup_questions = []
            for field in missing_fields:  # Limit to 3 questions
                if field in self.questions:
                    followup_questions.append(self.questions[field])
       
            if followup_questions:
                state['follow_up_needed'] = True
                state['follow_up_message'] = followup_questions
        
        
        gender = state.get('user_info', {}).get('gender')
        if not gender or gender.lower() not in ['male', 'female', 'unisex', 'not_needed']:
            print("gender not found")
            state["follow_up_needed"] = True
            state["follow_up_message"] = [self.questions['gender']]
            state["is_gender_loop"] = True
        return state
    
    def _prepare_response(self, state: FashionState) -> FashionState:
        """Prepare WebSocket response messages"""
        messages = []

        messages.append({
            "type": "intent",
            "message": state["conversation_history"],
            "message_type": "recommendation_intro"
        })
        
        if state.get("error_message"):
            print("error called")
            messages.append({
                "type": "error",
                "message": state["error_message"]
            })
        elif state.get("follow_up_needed"):
            print("the followup message being sent", state['follow_up_message'])
            messages.append({
                "type": "followup",
                "title": "Help me personalize your recommendations",  # FIXED: Fixed typo
                "questions": state['follow_up_message'],  # This is now a list
                "message_type": "followup_question"
            })
        elif state.get("is_gender_loop", False):
            messages.append({
                "type": "bot_message",
                "message": state.get("response_message", "Could you please tell me your gender?"),
                "message_type": "gender_question"
            })
        else:
            response_message = state.get("response_message", "Here are some recommendations for you!")
            messages.append({
                "type": "bot_message",
                "message": response_message,
                "message_type": "recommendation_intro"
            })
            
            if state.get("recommendations"):
                messages.append({
                    "type": "recommendations",
                    "recommendations": [
                        {
                            "id": i + 1,
                            "product_id": rec['product_id'],
                            "title": rec['title'],
                            "brand_name": rec['brand_name'],
                            "price": rec.get('price', 'N/A'),
                        }
                        for i, rec in enumerate(state["recommendations"][:7], 0)
                    ]
                })
        
        state["websocket_messages"] = messages
        return state

    def _check_gender_available(self, state: FashionState) -> str:
        """Check if gender is available in the state"""
        gender = state['user_info']['gender']
        if gender and gender.lower() in ['male', 'female', 'unisex', 'not_needed']:
            print(f"Gender found: {gender}")
            return "gender_found"
        else:
            print("Gender missing")
            return "gender_missing"
    
    def _decide_service_route(self, state: FashionState) -> str:
        """Decide which service to route to"""
        return state.get("service_mode", "general")
    
    def _check_followup_needed(self, state: FashionState) -> str:
        """Check if follow-up is needed"""
        return 'complete'
    
    def _check_followup_style_needed(self, state: FashionState) -> str:
        """Check if styling followup is needed"""
        # FIXED: Initialize user_info if not present
        user_info = state.get('user_info', {})
        
        # Check if any required styling info is missing
        required_fields = ['body_type', 'skin_tone', 'height', 'style_preferences', 'size_preferences']
        print("check followup for styles")
        missing_fields = [field for field in required_fields if not user_info.get(field)]
        
        if len(required_fields) - len(missing_fields) < 2:
            print("there are missing fields")
            return 'followup'
        
        return 'complete'
    
    def _infer_gender(self, user_input: str, conversation_history: str, gender) -> Optional[str]:
        """Use your existing gender inference logic"""
        return self.gender_service.getGender(conversation_history, user_input, gender)
    
    def _generate_occasion_recommendations(self, state: FashionState) -> tuple:
        """Generate occasion recommendations using your existing logic"""
        try:
            parameters = state["current_parameters"]
            parameters_flat = self.occasion_service.get_all_tags_flat(parameters)
            all_tags = parameters_flat["core_tags"] + parameters_flat["inferred_tags"]
            if not state['user_info']:
                state['user_info'] = {}
            gender = state['user_info']['gender']
            categories = parameters['product_categories']
            
            recommendations = self.recommendation_service.get_recommendations(
                user_query=state["user_input"], 
                tags=all_tags, 
                gender=[gender] if gender else None,
                sub_categories=categories,
                conversation_history=state["conversation_history"]
            )

            dialogue = self.occasion_service.generate_insightful_statement(
                state["user_input"], 
                state["conversation_history"], 
                recommendations, 
                parameters
            )
            
            return dialogue, recommendations
            
        except Exception as e:
            print(f"Error generating occasion recommendations: {e}")
            return "Sorry, I couldn't generate recommendations at the moment.", []

    def _process_bot_response(self, state: FashionState) -> FashionState:
        """Process bot response and update conversation history"""
        try:
            context = self.conversation_service.endTurn(
                state.get('response_message', ''), 
                state['user_info']['gender'], 
                state.get('recommendations', [])
            )
            state['conversation_history'] = context
            return state
        except Exception as e:
            print(f"Error processing bot response: {e}")
            return state


class ChatSession:
    def __init__(self, services_dict):
        self.conversation_history = ""
        self.service_mode = None
        self.current_parameters = None
        self.current_recommendations = None
        self.gender = None
        
        # Initialize LangGraph workflow
        self.fashion_workflow = FashionWorkflow(services_dict)
    
    async def process_with_langgraph(self, user_input: str, client_id: str, followup_data: Dict = None) -> List[Dict]:
        """Process user input using LangGraph workflow"""
        
        # FIXED: Initialize user_info properly
        user_info = {'gender' : None}
        if followup_data:
            user_info.update(followup_data)
        print("followup data received", followup_data)
        # Create initial state
        initial_state = FashionState(
            user_input=user_input,
            client_id=client_id,
            conversation_history=self.conversation_history,
            service_mode=self.service_mode,
            gender=self.gender,
            current_parameters=self.current_parameters,
            recommendations=[],
            response_message=None,
            websocket_messages=[],
            follow_up_needed=False,
            follow_up_message=None,
            confidence_score=None,
            error_message=None,
            is_gender_loop=False,
            user_info=user_info  # FIXED: Properly initialize user_info
        )
        
        try:
            # Run the workflow
            final_state = await self.fashion_workflow.app.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": client_id}}
            )
            
            # Update session state
            self.conversation_history = final_state.get("conversation_history", "")
            self.service_mode = final_state.get("service_mode")
            self.gender = final_state.get("gender")
            self.current_parameters = final_state.get("current_parameters")
            self.current_recommendations = final_state.get("recommendations", [])
            
            # Return messages to send via WebSocket
            return final_state.get("websocket_messages", [])
            
        except Exception as e:
            print(f"Error in LangGraph workflow: {e}")
            return [{
                "type": "error",
                "message": f"Sorry, I encountered an error: {str(e)}"
            }]