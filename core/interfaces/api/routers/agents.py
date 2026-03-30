"""FastAPI router for agent management endpoints."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from core.application import (
    ResearchAgent,
    AnalysisAgent,
    StrategyAgent,
    ReportAgent,
    CritiqueAgent,
    PlannerAgent,
)
from core.interfaces.api.models import (
    AgentExecuteRequest,
    AgentResultResponse,
    AgentStatusResponse,
)

router = APIRouter(prefix="/agents", tags=["agents"])

# Agent registry
AGENTS = {
    "research": ResearchAgent,
    "analysis": AnalysisAgent,
    "strategy": StrategyAgent,
    "report": ReportAgent,
    "critique": CritiqueAgent,
    "planner": PlannerAgent,
}


@router.post("/execute", response_model=AgentResultResponse)
async def execute_agent(request: AgentExecuteRequest) -> AgentResultResponse:
    """
    Execute an agent with a task.
    
    Args:
        request: Agent execution request
        
    Returns:
        Agent execution result
        
    Raises:
        HTTPException: If execution fails
    """
    try:
        agent_class = AGENTS.get(request.agent_type.lower())
        if not agent_class:
            raise ValueError(f"Unknown agent type: {request.agent_type}")
        
        agent = agent_class()
        execution_result = await agent.execute(request.task)
        
        return AgentResultResponse(
            success=True,
            agent_id=agent.agent_id,
            output=execution_result.output,
            execution_time_ms=execution_result.execution_time_ms,
            thoughts=execution_result.thoughts,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[AgentStatusResponse])
async def list_agents() -> list[AgentStatusResponse]:
    """
    List all available agents.
    
    Returns:
        List of agent statuses
    """
    try:
        agents_status = []
        for agent_type in AGENTS.keys():
            agent = AGENTS[agent_type]()
            agents_status.append(
                AgentStatusResponse(
                    agent_id=agent.agent_id,
                    status="READY",
                    success_rate=0.0,
                    total_executions=0,
                )
            )
        return agents_status
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_type}", response_model=AgentStatusResponse)
async def get_agent_status(agent_type: str) -> AgentStatusResponse:
    """
    Get status of a specific agent type.
    
    Args:
        agent_type: Agent type
        
    Returns:
        Agent status
    """
    try:
        agent_class = AGENTS.get(agent_type.lower())
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent = agent_class()
        return AgentStatusResponse(
            agent_id=agent.agent_id,
            status="READY",
            success_rate=0.0,
            total_executions=0,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.post("/{agent_type}/execute", response_model=AgentResultResponse)
async def execute_agent_by_type(
    agent_type: str,
    task: str = Query(..., description="Task for agent"),
) -> AgentResultResponse:
    """
    Execute a specific agent type with a task.
    
    Args:
        agent_type: Type of agent
        task: Task description
        
    Returns:
        Execution result
    """
    try:
        agent_class = AGENTS.get(agent_type.lower())
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        agent = agent_class()
        execution_result = await agent.execute(task)
        
        return AgentResultResponse(
            success=True,
            agent_id=agent.agent_id,
            output=execution_result.output,
            execution_time_ms=execution_result.execution_time_ms,
            thoughts=execution_result.thoughts,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{agent_id}/task")
async def submit_task_to_agent(
    agent_id: str,
    task: str = Query(..., description="Task description"),
):
    """
    Submit a task to a specific agent.
    
    Args:
        agent_id: Agent ID
        task: Task description
        
    Returns:
        Task submission result
    """
    try:
        # TODO: Implement agent task submission
        return {
            "success": True,
            "agent_id": agent_id,
            "task_id": "",
            "submitted": True,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/result/{task_id}")
async def get_agent_task_result(agent_id: str, task_id: str):
    """
    Get result of an agent task.
    
    Args:
        agent_id: Agent ID
        task_id: Task ID
        
    Returns:
        Task result
    """
    try:
        # TODO: Implement result retrieval
        return {
            "success": True,
            "agent_id": agent_id,
            "task_id": task_id,
            "result": {},
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Task not found")


@router.get("/{agent_type}/stats")
async def get_agent_stats(agent_type: str):
    """
    Get statistics for an agent type.
    
    Args:
        agent_type: Agent type
        
    Returns:
        Agent statistics
    """
    try:
        # TODO: Implement statistics retrieval
        return {
            "success": True,
            "agent_type": agent_type,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time_ms": 0.0,
            "success_rate": 0.0,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}/memory")
async def get_agent_memory(agent_id: str):
    """
    Get memory/context from an agent.
    
    Args:
        agent_id: Agent ID
        
    Returns:
        Agent memory
    """
    try:
        # TODO: Implement memory retrieval
        return {
            "success": True,
            "agent_id": agent_id,
            "memory": {},
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.delete("/{agent_id}/memory")
async def clear_agent_memory(agent_id: str):
    """
    Clear an agent's memory.
    
    Args:
        agent_id: Agent ID
        
    Returns:
        Clear confirmation
    """
    try:
        # TODO: Implement memory clearing
        return {
            "success": True,
            "agent_id": agent_id,
            "memory_cleared": True,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{agent_id}/configure")
async def configure_agent(agent_id: str, config: dict):
    """
    Configure agent parameters.
    
    Args:
        agent_id: Agent ID
        config: Configuration parameters
        
    Returns:
        Configuration confirmation
    """
    try:
        # TODO: Implement agent configuration
        return {
            "success": True,
            "agent_id": agent_id,
            "configured": True,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_type}/schema")
async def get_agent_schema(agent_type: str):
    """
    Get input/output schema for an agent type.
    
    Args:
        agent_type: Agent type
        
    Returns:
        Agent schema
    """
    try:
        # TODO: Implement schema retrieval
        return {
            "success": True,
            "agent_type": agent_type,
            "input_schema": {},
            "output_schema": {},
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Agent not found")
