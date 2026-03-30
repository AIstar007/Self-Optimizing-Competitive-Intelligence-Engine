"""WebSocket routes for real-time communication."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from core.interfaces.websocket.connection import (
    connection_manager,
    event_broadcaster,
    WebSocketHandler,
    websocket_receiver,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/workflow/{workflow_id}/{client_id}")
async def websocket_workflow_updates(websocket: WebSocket, workflow_id: str, client_id: str):
    """
    WebSocket endpoint for workflow status updates.

    Args:
        websocket: WebSocket connection
        workflow_id: Workflow ID
        client_id: Client identifier
    """
    await connection_manager.connect(websocket, f"workflow:{workflow_id}:{client_id}")
    handler = WebSocketHandler(connection_manager)

    async def handle_subscription(message: dict, cid: str):
        """Handle subscription message."""
        logger.info(f"Client {cid} subscribed to workflow {workflow_id}")

    handler.register_handler("subscribe", handle_subscription)

    try:
        await websocket_receiver(websocket, f"workflow:{workflow_id}:{client_id}", handler)
    except Exception as e:
        logger.error(f"Error in workflow WebSocket: {e}")


@router.websocket("/task/{task_id}/{client_id}")
async def websocket_task_updates(websocket: WebSocket, task_id: str, client_id: str):
    """
    WebSocket endpoint for task status updates.

    Args:
        websocket: WebSocket connection
        task_id: Task ID
        client_id: Client identifier
    """
    await connection_manager.connect(websocket, f"task:{task_id}:{client_id}")
    handler = WebSocketHandler(connection_manager)

    async def handle_subscription(message: dict, cid: str):
        """Handle subscription message."""
        logger.info(f"Client {cid} subscribed to task {task_id}")

    handler.register_handler("subscribe", handle_subscription)

    try:
        await websocket_receiver(websocket, f"task:{task_id}:{client_id}", handler)
    except Exception as e:
        logger.error(f"Error in task WebSocket: {e}")


@router.websocket("/agent/{agent_id}/{client_id}")
async def websocket_agent_updates(websocket: WebSocket, agent_id: str, client_id: str):
    """
    WebSocket endpoint for agent status updates.

    Args:
        websocket: WebSocket connection
        agent_id: Agent ID
        client_id: Client identifier
    """
    await connection_manager.connect(websocket, f"agent:{agent_id}:{client_id}")
    handler = WebSocketHandler(connection_manager)

    async def handle_subscription(message: dict, cid: str):
        """Handle subscription message."""
        logger.info(f"Client {cid} subscribed to agent {agent_id}")

    handler.register_handler("subscribe", handle_subscription)

    try:
        await websocket_receiver(websocket, f"agent:{agent_id}:{client_id}", handler)
    except Exception as e:
        logger.error(f"Error in agent WebSocket: {e}")


@router.websocket("/signals/{company_id}/{client_id}")
async def websocket_signal_updates(websocket: WebSocket, company_id: str, client_id: str):
    """
    WebSocket endpoint for signal updates.

    Args:
        websocket: WebSocket connection
        company_id: Company ID
        client_id: Client identifier
    """
    await connection_manager.connect(websocket, f"signals:{company_id}:{client_id}")
    handler = WebSocketHandler(connection_manager)

    async def handle_subscription(message: dict, cid: str):
        """Handle subscription message."""
        logger.info(f"Client {cid} subscribed to signals for company {company_id}")

    handler.register_handler("subscribe", handle_subscription)

    try:
        await websocket_receiver(websocket, f"signals:{company_id}:{client_id}", handler)
    except Exception as e:
        logger.error(f"Error in signals WebSocket: {e}")


@router.websocket("/reports/{company_id}/{client_id}")
async def websocket_report_updates(websocket: WebSocket, company_id: str, client_id: str):
    """
    WebSocket endpoint for report updates.

    Args:
        websocket: WebSocket connection
        company_id: Company ID
        client_id: Client identifier
    """
    await connection_manager.connect(websocket, f"reports:{company_id}:{client_id}")
    handler = WebSocketHandler(connection_manager)

    async def handle_subscription(message: dict, cid: str):
        """Handle subscription message."""
        logger.info(f"Client {cid} subscribed to reports for company {company_id}")

    handler.register_handler("subscribe", handle_subscription)

    try:
        await websocket_receiver(websocket, f"reports:{company_id}:{client_id}", handler)
    except Exception as e:
        logger.error(f"Error in reports WebSocket: {e}")


@router.websocket("/updates/{client_id}")
async def websocket_system_updates(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for general system updates.

    Args:
        websocket: WebSocket connection
        client_id: Client identifier
    """
    await connection_manager.connect(websocket, f"system:{client_id}")
    handler = WebSocketHandler(connection_manager)

    async def handle_ping(message: dict, cid: str):
        """Handle ping message."""
        pong = {"type": "pong", "timestamp": ""}
        await connection_manager.send_to_client(cid, pong)

    handler.register_handler("ping", handle_ping)

    try:
        await websocket_receiver(websocket, f"system:{client_id}", handler)
    except Exception as e:
        logger.error(f"Error in system WebSocket: {e}")


@router.get("/status")
async def get_websocket_status():
    """
    Get WebSocket connection status.

    Returns:
        Status information
    """
    return {
        "connected_clients": connection_manager.get_client_count(),
        "active_channels": len(connection_manager.active_connections),
        "clients": connection_manager.get_connected_clients(),
    }
