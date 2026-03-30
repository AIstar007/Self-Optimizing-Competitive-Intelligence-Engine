"""Slack integration adapter."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import aiohttp

from core.infrastructure.integrations.base_adapter import (
    BaseIntegrationAdapter,
    IntegrationType,
    IntegrationStatus,
    IntegrationConfig,
    IntegrationEvent,
)

logger = logging.getLogger(__name__)


class SlackAdapter(BaseIntegrationAdapter):
    """Slack workspace integration adapter."""

    def __init__(self, config: IntegrationConfig):
        """Initialize Slack adapter."""
        super().__init__(config)
        self.api_url = "https://slack.com/api"
        self.session: Optional[aiohttp.ClientSession] = None
        self.bot_user_id: Optional[str] = None
        self.workspace_name: Optional[str] = None
        self.channels: Dict[str, str] = {}  # Channel name -> ID mapping

    async def connect(self) -> bool:
        """Connect to Slack workspace."""
        try:
            self.session = aiohttp.ClientSession()

            # Verify authentication
            if not await self.authenticate():
                logger.error("Failed to authenticate with Slack")
                self.status = IntegrationStatus.ERROR
                return False

            # Get workspace info
            await self._get_workspace_info()

            self.status = IntegrationStatus.ACTIVE
            self.increment_success()
            logger.info(f"Connected to Slack workspace: {self.workspace_name}")
            return True
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.status = IntegrationStatus.ERROR
            self.increment_error()
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Slack."""
        try:
            if self.session:
                await self.session.close()

            self.status = IntegrationStatus.DISCONNECTED
            logger.info("Disconnected from Slack")
            return True
        except Exception as e:
            logger.error(f"Disconnection error: {e}")
            return False

    async def authenticate(self) -> bool:
        """Authenticate with Slack API."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            token = self.config.get_secret("slack_token")
            if not token:
                logger.error("Slack token not configured")
                return False

            headers = {"Authorization": f"Bearer {token}"}

            async with self.session.post(
                f"{self.api_url}/auth.test", headers=headers, timeout=10
            ) as resp:
                result = await resp.json()

                if not result.get("ok"):
                    logger.error(f"Auth failed: {result.get('error')}")
                    return False

                self.bot_user_id = result.get("user_id")
                return True
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    async def send_data(self, data: Dict[str, Any]) -> bool:
        """Send alert/notification to Slack."""
        try:
            channel = data.get("channel", data.get("target_channel"))
            message = data.get("message", "")
            thread_ts = data.get("thread_ts")

            if not channel or not message:
                logger.warning("Missing required fields: channel or message")
                return False

            # Convert channel name to ID if needed
            channel_id = await self._get_channel_id(channel)
            if not channel_id:
                logger.warning(f"Channel not found: {channel}")
                return False

            payload = {
                "channel": channel_id,
                "text": message,
                "blocks": data.get("blocks", []),
            }

            if thread_ts:
                payload["thread_ts"] = thread_ts

            token = self.config.get_secret("slack_token")
            headers = {"Authorization": f"Bearer {token}"}

            async with self.session.post(
                f"{self.api_url}/chat.postMessage",
                json=payload,
                headers=headers,
                timeout=10,
            ) as resp:
                result = await resp.json()

                if result.get("ok"):
                    self.increment_success()
                    logger.debug(f"Message sent to {channel}")
                    return True
                else:
                    self.increment_error()
                    logger.error(f"Send failed: {result.get('error')}")
                    return False
        except Exception as e:
            logger.error(f"Send error: {e}")
            self.increment_error()
            return False

    async def receive_data(self) -> Optional[Dict[str, Any]]:
        """Receive events from Slack (via event subscriptions)."""
        # Events are typically received via webhook
        # This would be implemented in the webhook handler
        logger.debug("Receive not applicable for Slack adapter (event-driven)")
        return None

    async def sync(self) -> bool:
        """Sync channels and user list from Slack."""
        try:
            token = self.config.get_secret("slack_token")
            headers = {"Authorization": f"Bearer {token}"}

            # Get channels list
            async with self.session.get(
                f"{self.api_url}/conversations.list",
                params={"types": "public_channel,private_channel"},
                headers=headers,
                timeout=10,
            ) as resp:
                result = await resp.json()

                if result.get("ok"):
                    for channel in result.get("channels", []):
                        self.channels[channel["name"]] = channel["id"]

            self.set_last_sync()
            self.increment_success()
            logger.info(f"Synced {len(self.channels)} channels from Slack")
            return True
        except Exception as e:
            logger.error(f"Sync error: {e}")
            self.increment_error()
            return False

    async def _get_workspace_info(self) -> None:
        """Get workspace information."""
        try:
            token = self.config.get_secret("slack_token")
            headers = {"Authorization": f"Bearer {token}"}

            async with self.session.get(
                f"{self.api_url}/team.info", headers=headers, timeout=10
            ) as resp:
                result = await resp.json()

                if result.get("ok"):
                    self.workspace_name = result.get("team", {}).get("name")
        except Exception as e:
            logger.error(f"Error getting workspace info: {e}")

    async def _get_channel_id(self, channel_identifier: str) -> Optional[str]:
        """Get channel ID from name or ID."""
        if channel_identifier.startswith("C"):
            # Already a channel ID
            return channel_identifier

        # Look up in cached channels
        if channel_identifier in self.channels:
            return self.channels[channel_identifier]

        # Fetch from API
        try:
            token = self.config.get_secret("slack_token")
            headers = {"Authorization": f"Bearer {token}"}

            async with self.session.get(
                f"{self.api_url}/conversations.info",
                params={"channel": channel_identifier},
                headers=headers,
                timeout=10,
            ) as resp:
                result = await resp.json()

                if result.get("ok"):
                    channel_id = result.get("channel", {}).get("id")
                    if channel_id:
                        self.channels[channel_identifier] = channel_id
                        return channel_id
        except Exception as e:
            logger.error(f"Error getting channel ID: {e}")

        return None

    async def health_check(self) -> bool:
        """Check Slack API health."""
        try:
            return await self.test_connection()
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False

    async def test_connection(self) -> bool:
        """Test connection to Slack."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            return await self.authenticate()
        except Exception as e:
            logger.error(f"Connection test error: {e}")
            return False

    def format_alert_for_slack(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format alert data for Slack message."""
        severity = alert_data.get("severity", "INFO")
        color_map = {
            "CRITICAL": "#FF0000",
            "HIGH": "#FF6600",
            "MEDIUM": "#FFCC00",
            "LOW": "#00CC00",
            "INFO": "#0099CC",
        }

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": alert_data.get("title", "Alert"),
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": alert_data.get("description", ""),
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Timestamp:*\n{datetime.utcnow().isoformat()}",
                    },
                ],
            },
        ]

        if alert_data.get("metrics"):
            metrics_text = "\n".join(
                [f"• {k}: {v}" for k, v in alert_data.get("metrics", {}).items()]
            )
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Metrics:*\n{metrics_text}",
                    },
                }
            )

        if alert_data.get("action_url"):
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Details"},
                            "url": alert_data.get("action_url"),
                        },
                    ],
                }
            )

        return {
            "channel": alert_data.get("channel", "#alerts"),
            "blocks": blocks,
            "text": alert_data.get("title", "Alert"),
        }

    def __del__(self):
        """Cleanup."""
        if self.session:
            try:
                asyncio.run(self.session.close())
            except Exception:
                pass
