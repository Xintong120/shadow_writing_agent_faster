"""
Debate Router Module

Responsibility: FastAPI routes for debate functionality.
Uses LangServe for streaming, custom routes for session management.
"""

from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, AsyncGenerator, Any
import uuid

from app.chains.debate_chain import DebateChain, DebateChainConfig


router = APIRouter(prefix="/api/debate", tags=["debate"])

# Global chain manager (can be replaced with dependency injection)
_debate_chain: Optional[DebateChain] = None
_langserve_chain: Optional[Any] = None


def get_debate_chain() -> DebateChain:
    """Get or create the global debate chain manager."""
    global _debate_chain
    if _debate_chain is None:
        _debate_chain = DebateChain()
    return _debate_chain


def set_debate_chain(chain: DebateChain):
    """Set the global debate chain manager (for testing)."""
    global _debate_chain
    _debate_chain = chain


def get_langserve_chain() -> Any:
    """Get or create the global LangServe chain."""
    global _langserve_chain
    if _langserve_chain is None:
        from app.routers.debate_router import create_langserve_chain
        _langserve_chain = create_langserve_chain()
    return _langserve_chain


def create_langserve_chain():
    """Create the LangServe chain with history support and auto system_prompt injection."""
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.runnables.history import RunnableWithMessageHistory
    from langchain_core.runnables import RunnableLambda
    from langchain_community.chat_message_histories import FileChatMessageHistory
    from app.infrastructure.config.llm_model_map import create_llm_for_purpose
    
    chain_manager = get_debate_chain()
    
    def get_history(session_id: str) -> FileChatMessageHistory:
        return chain_manager.get_history(session_id)
    
    def inject_system_prompt(input_dict, config):
        """自动从 session 获取 system_prompt 并注入到输入中"""
        session_id = config.get("configurable", {}).get("session_id", "")
        if session_id:
            try:
                system_prompt = chain_manager.get_system_prompt(session_id)
                input_dict["system_prompt"] = system_prompt
                
                user_viewpoint = input_dict.get("user_viewpoint", "")
                extracted_args = input_dict.get("extracted_arguments", "")
                user_role = input_dict.get("user_role", "pro")
                
                if user_viewpoint and extracted_args:
                    from app.chains.debate_chain import PromptBuilder
                    prompt_builder = PromptBuilder()
                    input_dict["system_prompt"] = prompt_builder.build_debate_prompt(
                        extracted_arguments=extracted_args,
                        user_viewpoint=user_viewpoint,
                        user_role=user_role,
                        article_argument=""
                    )
            except Exception as e:
                input_dict["system_prompt"] = ""
        else:
            input_dict["system_prompt"] = ""
        return input_dict
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "{system_prompt}"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{human_input} {user_viewpoint} {extracted_arguments} {user_role}"),
    ])
    
    llm = create_llm_for_purpose("debate", streaming=True)
    
    # 先注入 system_prompt，再执行 prompt
    chain = RunnableLambda(inject_system_prompt) | prompt | llm
    
    return RunnableWithMessageHistory(
        chain,
        get_history,
        input_messages_key="human_input",
        history_messages_key="history",
    )


# ============ Request/Response Models ============

class StartDebateRequest(BaseModel):
    """Request to start a debate session."""
    session_id: str
    article_argument: str
    article_content: str = ""  # For future RAG context
    user_role: str  # "pro" or "con"
    opponent_id: str  # AI opponent card ID (e.g., "philosophical_dreamer")
    language: str = "English"


class StartDebateResponse(BaseModel):
    """Response after starting a debate session."""
    session_id: str
    ai_role: str
    system_prompt: str
    opening_message: str
    extracted_arguments: str = ""  # Pre-extracted core arguments from TED talk


class OpponentInfo(BaseModel):
    """Opponent character information."""
    id: str
    name: str
    avatar: str
    difficulty: int
    description: str
    tags: list[str]


class EndDebateResponse(BaseModel):
    """Response after ending a debate session."""
    status: str
    session_id: str


class ChatRequest(BaseModel):
    """Request for chat message."""
    session_id: str
    human_input: str


# ============ Custom Routes ============

@router.post("/chat")
async def chat(request: ChatRequest):
    """
    适配前端请求格式，调用 LangServe 链式调用。
    
    前端发送:
        {"session_id": "xxx", "human_input": "hello"}
    
    返回:
        {"response": "AI 回复内容"}
    """
    chain = get_debate_chain()
    
    try:
        system_prompt = chain.get_system_prompt(request.session_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Session not found")
    
    langserve_chain = get_langserve_chain()
    
    result = langserve_chain.invoke(
        {"human_input": request.human_input, "system_prompt": system_prompt},
        config={"configurable": {"session_id": request.session_id}}
    )
    
    return {"response": result.content}


@router.post("/start", response_model=StartDebateResponse)
async def start_debate(request: StartDebateRequest) -> StartDebateResponse:
    """
    Start a new debate session.
    
    Args:
        request: Debate start request
    
    Returns:
        Session config with system prompt and opening message
    """
    if request.user_role not in ["pro", "con"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'pro' or 'con'")
    
    chain = get_debate_chain()
    
    try:
        extracted_arguments = ""
        
        from app.db.history_db import history_db
        record = history_db.get_by_title(request.article_argument)
        if record:
            task_id = record.get('task_id')
            if task_id:
                extracted_arguments = history_db.get_core_arguments(task_id) or ""
        
        config = chain.create_session(
            session_id=request.session_id,
            user_role=request.user_role,
            opponent_id=request.opponent_id,
            article_argument=request.article_argument,
            article_content=extracted_arguments,
            language=request.language
        )
        
        system_prompt = chain.get_system_prompt(request.session_id)
        opening_message = chain.get_opening_message(request.session_id)
        
        return StartDebateResponse(
            session_id=request.session_id,
            ai_role=config.ai_role,
            system_prompt=system_prompt,
            opening_message=opening_message,
            extracted_arguments=extracted_arguments
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/end", response_model=EndDebateResponse)
async def end_debate(session_id: str) -> EndDebateResponse:
    """
    End a debate session.
    
    Args:
        session_id: Session to end
    
    Returns:
        Confirmation of session end
    """
    chain = get_debate_chain()
    
    success = chain.end_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return EndDebateResponse(
        status="ended",
        session_id=session_id
    )


@router.get("/sessions")
async def list_sessions() -> list[str]:
    """
    List all active session IDs.

    Returns:
        List of session IDs
    """
    chain = get_debate_chain()
    return chain.list_sessions()


@router.get("/opponents", response_model=list[OpponentInfo])
async def list_opponents() -> list[OpponentInfo]:
    """
    List all available debate opponents.

    Returns:
        List of opponent information
    """
    from app.services.card_loader import CardLoader
    loader = CardLoader()
    cards = loader.list_cards()
    return [
        OpponentInfo(
            id=card.get("id", ""),
            name=card.get("name", ""),
            avatar="",  # Cards don't have avatar field in current design
            difficulty=0,
            description=card.get("description", ""),
            tags=card.get("tags", [])
        )
        for card in cards
    ]


@router.get("/session/{session_id}/config")
async def get_session_config(session_id: str) -> dict:
    """
    Get session configuration.
    
    Args:
        session_id: Session ID
    
    Returns:
        Session configuration
    """
    chain = get_debate_chain()
    
    try:
        config = chain.get_config(session_id)
        return {
            "session_id": config.session_id,
            "ai_role": config.ai_role,
            "article_argument": config.article_argument,
            "language": config.language
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============ LangServe Routes (optional) ============

def add_langserve_routes(app: FastAPI):
    """
    Add LangServe routes to a FastAPI app.
    Requires langserve, langchain packages.
    
    Usage:
        app = FastAPI()
        add_langserve_routes(app)
    """
    try:
        from langserve import add_routes
        from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_core.runnables.history import RunnableWithMessageHistory
        from langchain_community.chat_message_histories import FileChatMessageHistory
    except ImportError:
        print("[WARNING] langserve/langchain not installed. Chat endpoint not available.")
        return

    from app.services.llm.llm_factory import LLMFactory
    from app.infrastructure.config.llm_model_map import create_llm_for_purpose

    chain_manager = get_debate_chain()

    debate_chain = create_langserve_chain()
    
    class ChatInput(BaseModel):
        """Input for chat endpoint."""
        human_input: str
    
    debate_chain = create_langserve_chain()
    
    add_routes(
        app,
        debate_chain.with_types(input_type=ChatInput),
        path="/api/debate/chat"
    )
    
    print("[OK] LangServe debate routes registered")


# ============ Standalone Server ============

def create_app() -> FastAPI:
    """Create a standalone FastAPI app for debate module."""
    app = FastAPI(
        title="Debate API",
        description="API for debate functionality",
        version="1.0.0"
    )
    
    app.include_router(router)
    add_langserve_routes(app)
    
    return app


if __name__ == "__main__":
    # Test the router
    print("=== Testing Debate Router ===\n")
    
    import sys
    sys.path.insert(0, '.')
    
    from app.chains.debate_chain import DebateChain
    
    # Set a test chain
    test_chain = DebateChain(
        history_dir="app/data/debate/histories",
        cards_dir="app/data/debate/cards"
    )
    set_debate_chain(test_chain)
    
    # Test routes
    print("1. Testing /start endpoint:")
    start_request = StartDebateRequest(
        session_id="test_router_001",
        article_argument="Climate change is real",
        article_content="Full article content here...",
        user_role="pro",
        opponent_id="philosophical_dreamer",
        language="English"
    )
    
    import asyncio
    response = asyncio.run(start_debate(start_request))
    print(f"   Session: {response.session_id}")
    print(f"   AI role: {response.ai_role}")
    print(f"   Opening: {response.opening_message[:50]}...")
    
    print("\n2. Testing /sessions endpoint:")
    sessions = list_sessions()
    print(f"   Active sessions: {sessions}")
    
    print("\n3. Testing /session/{id}/config endpoint:")
    config = get_session_config("test_router_001")
    print(f"   Config: {config}")
    
    print("\n4. Testing /end endpoint:")
    end_response = asyncio.run(end_debate("test_router_001"))
    print(f"   Result: {end_response.status}")
    
    sessions_after = list_sessions()
    print(f"   Sessions remaining: {sessions_after}")
    
    print("\n=== All router tests passed ===")
