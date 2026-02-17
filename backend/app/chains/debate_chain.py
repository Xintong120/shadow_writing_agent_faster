"""
Debate Chain Module (Using Project's LLM Service)

Responsibility: Build debate chain using project's existing LLM infrastructure.
Simple wrapper without LangChain Runnable protocol requirements.
"""

import os
from typing import Any, Optional, Iterator, AsyncIterator
from dataclasses import dataclass


@dataclass
class DebateCard:
    """Debate character card data structure."""
    id: str
    name: str
    description: str
    personality: str
    scenario: str
    response_rules: list[str]
    system_prompt_template: str
    opening_statements: list[str]
    tags: list[str]
    character_book_description: str = ""
    avatar: str = ""
    difficulty: int = 1


@dataclass
class DebateChainConfig:
    """Configuration for a debate chain session."""
    session_id: str
    ai_role: str
    article_argument: str
    language: str = "English"
    
    @property
    def role_display_name(self) -> str:
        return "Pro" if self.ai_role == "pro" else "Con"


class PromptBuilder:
    """Build system prompts from debate cards."""

    DEBATE_PROMPT_TEMPLATE = """You are a Debate AI expert, specializing in generating engaging debates based on TED Talk key arguments. First, you have a pre-extracted list of 3-5 core arguments from the TED Talk. Your task is to use these arguments to debate against or support a user's viewpoint on the topic.

Pre-extracted Core Arguments from the TED Talk:
{extracted_arguments}

User's Viewpoint: {user_viewpoint}

AI's Role: {ai_role} (The user chose {user_role} - you must {role_action})

Step-by-step Instructions:
0. Check if this is the initial interaction (User's Viewpoint is empty or "none"):
   - If yes: Generate an opening message to start the debate.
     - Introduce the TED Talk theme briefly (e.g., "In this TED Talk on [title], the speaker discusses [main theme].").
     - Invite the user: "What's your viewpoint on [theme]? I'll debate using the key arguments."
     - Keep it short and engaging.
   - If no: Proceed to step 1.
1. Analyze the user's viewpoint and check if it matches or closely aligns with any of the pre-extracted core arguments (exact match, paraphrase, or similar idea).
   - If it matches one or more arguments: Acknowledge the alignment (e.g., "Your viewpoint aligns with the speaker's point on [specific argument]"), then pivot to debate by:
     - Expanding on that argument with deeper insights or examples from the TED Talk.
     - Using the remaining non-matching arguments to provide counterpoints or balanced perspectives, to keep the debate going.
     - Avoid repetition; instead, build upon it to strengthen or challenge subtly.
   - If it does not match any: Proceed to debate by selecting 2-3 relevant core arguments to counter or support the user's viewpoint.
2. Generate a debate response in a structured format:
   - Start with a neutral introduction summarizing the TED Talk's theme.
   - Present your side of the debate (e.g., as the "opposing" or "supporting" debater).
   - Use evidence from the core arguments.
   - End with a question to invite the user to respond.
3. Keep the response engaging, polite, and evidence-based. Output only the debate content, no extra explanations.

Debate Response:"""

    def build(
        self,
        card: DebateCard,
        stance: str,
        article_argument: str,
        article_content: str = "",
        language: str = "English"
    ) -> str:
        """Build a system prompt from a card."""
        rules_list = "\n".join([f"{i+1}. {rule}" for i, rule in enumerate(card.response_rules)])

        prompt = card.system_prompt_template

        replacements = {
            "{{article_argument}}": article_argument,
            "{{name}}": card.name,
            "{{description}}": card.description,
            "{{personality_prompt}}": card.personality,
            "{{scenario}}": card.scenario,
            "{{rules_list}}": rules_list,
            "{{stance}}": stance,
            "{{language}}": language,
        }

        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)

        return prompt

    def build_debate_prompt(
        self,
        extracted_arguments: str,
        user_viewpoint: str,
        user_role: str,
        article_argument: str = ""
    ) -> str:
        """Build debate prompt with pre-extracted arguments."""
        ai_role = "OPPOSING" if user_role == "pro" else "SUPPORTING"
        role_action = "oppose the user's viewpoint" if user_role == "pro" else "support and defend the TED speaker's viewpoint"
        
        return self.DEBATE_PROMPT_TEMPLATE.format(
            extracted_arguments=extracted_arguments or "No core arguments available.",
            user_viewpoint=user_viewpoint or "none",
            ai_role=ai_role,
            user_role=user_role.upper(),
            role_action=role_action
        )

    def build_stance_instruction(self, stance: str) -> str:
        """Build stance instruction based on pro/con."""
        if stance == "pro":
            return "You are SUPPORTING the article's core argument."
        return "You are OPPOSING the article's core argument."

    def get_opening_statement(self, card: DebateCard) -> str:
        """Get a random opening statement from card."""
        import random
        if card.opening_statements:
            return random.choice(card.opening_statements)
        return "I'm ready to debate."


class DebateChainError(Exception):
    """Custom exception for debate chain errors."""
    pass


class ProjectLLMWrapper:
    """
    Wrap project's LLM provider for debate.
    
    Usage:
        llm = ProjectLLMWrapper()
        response = llm.invoke([HumanMessage(content="Hello")])
    """
    
    def __init__(self, provider: Optional[Any] = None):
        """
        Initialize wrapper.
        
        Args:
            provider: Project's LLM provider (MistralProvider, etc.)
                     If None, uses get_llm_service() to get default
        """
        self._provider = provider
    
    def _get_provider(self) -> Any:
        """Get the LLM provider."""
        if self._provider is not None:
            return self._provider
        
        from app.services.llm import get_llm_service
        llm_service = get_llm_service()
        
        if llm_service is None:
            raise DebateChainError(
                "No LLM service available. Configure API keys in .env"
            )
        
        provider = llm_service.create_shadow_writing_llm()
        
        if not provider.available:
            raise DebateChainError(
                f"LLM provider not available. Available: {llm_service.available_providers}"
            )
        
        return provider
    
    def invoke(self, messages: list[dict]) -> str:
        """
        Invoke LLM with messages.
        
        Args:
            messages: List of message dicts [{"role": "user", "content": "..."}]
        
        Returns:
            Response content as string
        """
        provider = self._get_provider()
        
        # Convert messages to single prompt
        prompt = self._messages_to_prompt(messages)
        
        # Output format - plain text
        output_format = {"type": "raw_text"}
        
        try:
            result = provider(prompt, output_format)
            content = result if isinstance(result, str) else result.get("raw", str(result))
            return content
        except Exception as e:
            raise DebateChainError(f"LLM invoke failed: {e}")
    
    def stream(self, messages: list[dict]) -> Iterator[str]:
        """Stream response (not supported, yields full response)."""
        response = self.invoke(messages)
        yield response
    
    def _messages_to_prompt(self, messages: list[dict]) -> str:
        """Convert message dicts to prompt string."""
        parts = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"{role.capitalize()}: {content}")
        
        return "\n\n".join(parts)


class DebateChain:
    """
    Manage debate chains using project's LLM infrastructure.
    
    Usage:
        # Default (uses project's LLM service)
        chain = DebateChain()
        
        # With custom provider
        llm_service = get_llm_service()
        provider = llm_service.create_shadow_writing_llm()
        chain = DebateChain(llm_provider=provider)
    """
    
    def __init__(
        self,
        card_loader: Optional[Any] = None,
        history_store: Optional[Any] = None,
        history_dir: Optional[str] = None,
        cards_dir: Optional[str] = None,
        llm_provider: Optional[Any] = None,
    ):
        """
        Initialize debate chain manager.
        
        Args:
            card_loader: Object with load_card() and list_cards() methods
            history_store: Object with get/add/clear history methods
            history_dir: Directory for history files
            cards_dir: Directory for card JSON files
            llm_provider: Project's LLM provider (optional)
        """
        self._card_loader = card_loader or self._create_default_card_loader(cards_dir)
        self._history_store = history_store or self._create_default_history_store(history_dir)
        self._llm_provider = llm_provider
        self._llm_wrapper = None
        
        self._prompt_builder = PromptBuilder()
        self._sessions: dict[str, DebateChainConfig] = {}
        self._chains: dict[str, dict] = {}
    
    def _create_llm_wrapper(self) -> ProjectLLMWrapper:
        """Create LLM wrapper."""
        return ProjectLLMWrapper(provider=self._llm_provider)
    
    def _create_default_card_loader(self, cards_dir: Optional[str]):
        """Create default file-based card loader."""
        from app.services.card_loader import CardLoader
        
        class DefaultCardLoader:
            def __init__(self, dir_path: str):
                self._loader = CardLoader(cards_dir=dir_path)
            
            def load_card(self, role: str) -> DebateCard:
                card = self._loader.load_card(role)
                return DebateCard(**card.to_dict())

            def list_cards(self) -> list[dict]:
                return self._loader.list_cards()
        
        dir_path = cards_dir or os.path.join("app", "data", "debate", "cards")
        return DefaultCardLoader(dir_path)
    
    def _create_default_history_store(self, history_dir: Optional[str]):
        """Create default file-based history store."""
        from langchain_community.chat_message_histories import FileChatMessageHistory
        
        class DefaultHistoryStore:
            def __init__(self, dir_path: str):
                self.dir = dir_path
                self._histories: dict[str, FileChatMessageHistory] = {}
                os.makedirs(dir_path, exist_ok=True)
            
            def get_history(self, session_id: str) -> FileChatMessageHistory:
                if session_id not in self._histories:
                    file_path = os.path.join(self.dir, f"{session_id}.json")
                    self._histories[session_id] = FileChatMessageHistory(str(file_path))
                return self._histories[session_id]
            
            def add_message(self, session_id: str, role: str, content: str):
                history = self.get_history(session_id)
                if role == "user":
                    history.add_user_message(content)
                else:
                    history.add_ai_message(content)
            
            def clear_history(self, session_id: str):
                if session_id in self._histories:
                    del self._histories[session_id]
        
        dir_path = history_dir or os.path.join("app", "data", "debate", "histories")
        return DefaultHistoryStore(dir_path)
    
    @property
    def llm(self) -> ProjectLLMWrapper:
        """Get the LLM wrapper."""
        if self._llm_wrapper is None:
            self._llm_wrapper = self._create_llm_wrapper()
        return self._llm_wrapper
    
    @property
    def card_loader(self) -> Any:
        """Get card loader."""
        return self._card_loader
    
    @property
    def history_store(self) -> Any:
        """Get history store."""
        return self._history_store
    
    def create_session(
        self,
        session_id: str,
        user_role: str,
        opponent_id: str,
        article_argument: str,
        article_content: str = "",
        language: str = "English"
    ) -> DebateChainConfig:
        """Create a new debate session.

        Args:
            session_id: Unique session identifier
            user_role: User's chosen role ("pro" or "con")
            opponent_id: AI opponent card ID (e.g., "philosophical_dreamer")
            article_argument: The article's core argument for debate context
            article_content: Pre-extracted core arguments from TED talk
            language: Response language (default: English)

        Returns:
            DebateChainConfig with session info
        """
        if session_id in self._sessions:
            raise DebateChainError(f"Session already exists: {session_id}")

        if user_role not in ["pro", "con"]:
            raise DebateChainError(f"Invalid user role: {user_role}")

        ai_role = "con" if user_role == "pro" else "pro"

        card = self._card_loader.load_card(opponent_id)

        stance_instruction = self._prompt_builder.build_stance_instruction(ai_role)
        
        if article_content:
            system_prompt = self._prompt_builder.build_debate_prompt(
                extracted_arguments=article_content,
                user_viewpoint="none",
                user_role=user_role,
                article_argument=article_argument
            )
        else:
            system_prompt = self._prompt_builder.build(
                card=card,
                stance=ai_role,
                article_argument=article_argument,
                language=language
            )

        config = DebateChainConfig(
            session_id=session_id,
            ai_role=ai_role,
            article_argument=article_argument,
            language=language
        )
        self._sessions[session_id] = config

        self._chains[session_id] = {
            "system_prompt": system_prompt,
            "config": config,
            "card": card,
            "stance_instruction": stance_instruction,
            "opponent_id": opponent_id,
            "extracted_arguments": article_content,
        }

        return config
    
    def get_chain_info(self, session_id: str) -> dict:
        """Get chain info for a session."""
        if session_id not in self._chains:
            raise DebateChainError(f"Session not found: {session_id}")
        return self._chains[session_id]
    
    def get_system_prompt(self, session_id: str) -> str:
        """Get the system prompt for a session."""
        return self.get_chain_info(session_id)["system_prompt"]
    
    def get_extracted_arguments(self, session_id: str) -> str:
        """Get the extracted arguments for a session."""
        return self.get_chain_info(session_id).get("extracted_arguments", "")
    
    def get_opening_message(self, session_id: str) -> str:
        """Get the opening message for a session."""
        chain_info = self.get_chain_info(session_id)
        extracted_args = chain_info.get("extracted_arguments", "")
        config = chain_info.get("config")
        ai_role = config.ai_role if config else "con"
        
        if extracted_args:
            prompt_builder = PromptBuilder()
            opening_prompt = prompt_builder.build_debate_prompt(
                extracted_arguments=extracted_args,
                user_viewpoint="none",
                user_role="pro" if ai_role == "con" else "con",
                article_argument=config.article_argument if config else ""
            )
            
            from app.infrastructure.config.llm_model_map import create_llm_for_purpose
            llm = create_llm_for_purpose("debate", streaming=False)
            response = llm.invoke(opening_prompt)
            if hasattr(response, 'content'):
                content = response.content
                return content if isinstance(content, str) else str(content)
            return str(response)
        
        card = chain_info["card"]
        statements = card.opening_statements
        return statements[0] if statements else "I'm ready to debate."
    
    def get_config(self, session_id: str) -> DebateChainConfig:
        """Get the config for a session."""
        return self.get_chain_info(session_id)["config"]
    
    def end_session(self, session_id: str) -> bool:
        """End a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            del self._chains[session_id]
            return True
        return False
    
    def list_sessions(self) -> list[str]:
        """List all active session IDs."""
        return list(self._sessions.keys())
    
    def get_history(self, session_id: str) -> Any:
        """Get chat history for a session."""
        return self._history_store.get_history(session_id)


def create_debate_session(
    session_id: str,
    user_role: str,
    opponent_id: str,
    article_argument: str,
    language: str = "English",
) -> DebateChainConfig:
    """
    Convenience function to create a debate session.
    Uses project's LLM service.

    Usage:
        create_debate_session("s1", "pro", "philosophical_dreamer", "topic")
    """
    manager = DebateChain()
    return manager.create_session(session_id, user_role, opponent_id, article_argument, language)


if __name__ == "__main__":
    print("=== Testing Debate Chain with Project's LLM Service ===\n")
    
    import sys
    sys.path.insert(0, '.')
    
    # Test 1: Default (uses project's LLM service)
    print("1. Default (project's LLM service):")
    chain = DebateChain(
        history_dir="app/data/debate/histories",
        cards_dir="app/data/debate/cards"
    )
    
    from app.services.llm import get_llm_service
    llm_service = get_llm_service()
    if llm_service:
        print(f"   LLM service available")
        print(f"   Providers: {llm_service.available_providers}")
    else:
        print("   LLM service not available (no API keys)")
    
    config = chain.create_session(
        session_id="test_001",
        user_role="pro",
        opponent_id="philosophical_dreamer",
        article_argument="Technology improves communication"
    )
    print(f"   Session: {config.session_id}")
    print(f"   AI role: {config.ai_role}")
    print(f"   System prompt: {chain.get_system_prompt(config.session_id)[:100]}...")
    
    # Test 2: With custom provider
    print("\n2. With custom provider:")
    if llm_service:
        provider = llm_service.create_shadow_writing_llm()
        chain2 = DebateChain(
            history_dir="app/data/debate/histories",
            cards_dir="app/data/debate/cards",
            llm_provider=provider
        )
        print(f"   Custom provider: {type(provider).__name__}")
    
    # Test 3: Test LLM invoke
    print("\n3. Testing LLM invoke:")
    llm = chain.llm
    messages = [{"role": "user", "content": "Why do you support this position?"}]
    try:
        response = llm.invoke(messages)
        print(f"   Response: {response[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Cleanup
    chain.end_session("test_001")
    
    print("\n=== Tests completed ===")
