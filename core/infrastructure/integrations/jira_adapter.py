"""Jira integration adapter."""

import asyncio
import base64
import json
import logging
from typing import Any, Dict, Optional

import aiohttp

from core.infrastructure.integrations.base_adapter import (
    BaseIntegrationAdapter,
    IntegrationType,
    IntegrationStatus,
    IntegrationConfig,
)

logger = logging.getLogger(__name__)


class JiraAdapter(BaseIntegrationAdapter):
    """Jira Cloud integration adapter."""

    def __init__(self, config: IntegrationConfig):
        """Initialize Jira adapter."""
        super().__init__(config)
        self.instance_url: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.projects: Dict[str, str] = {}  # Project key -> ID mapping
        self.issue_types: Dict[str, str] = {}  # Issue type -> ID mapping

    async def connect(self) -> bool:
        """Connect to Jira instance."""
        try:
            self.session = aiohttp.ClientSession()

            if not await self.authenticate():
                logger.error("Failed to authenticate with Jira")
                self.status = IntegrationStatus.ERROR
                return False

            # Fetch projects and issue types
            await self._sync_metadata()

            self.status = IntegrationStatus.ACTIVE
            self.increment_success()
            logger.info(f"Connected to Jira: {self.instance_url}")
            return True
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.status = IntegrationStatus.ERROR
            self.increment_error()
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Jira."""
        try:
            if self.session:
                await self.session.close()

            self.status = IntegrationStatus.DISCONNECTED
            logger.info("Disconnected from Jira")
            return True
        except Exception as e:
            logger.error(f"Disconnection error: {e}")
            return False

    async def authenticate(self) -> bool:
        """Authenticate with Jira Cloud API."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            self.instance_url = self.config.get_secret("jira_instance_url")
            email = self.config.get_secret("jira_email")
            api_token = self.config.get_secret("jira_api_token")

            if not all([self.instance_url, email, api_token]):
                logger.error("Missing Jira credentials")
                return False

            # Create authorization header
            auth_string = f"{email}:{api_token}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()

            headers = {"Authorization": f"Basic {encoded_auth}"}

            # Test authentication
            async with self.session.get(
                f"{self.instance_url}/rest/api/3/myself",
                headers=headers,
                timeout=10,
            ) as resp:
                if resp.status == 200:
                    return True
                else:
                    logger.error(f"Authentication failed: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    async def send_data(self, data: Dict[str, Any]) -> bool:
        """Create or update Jira issue."""
        try:
            operation = data.get("operation", "create")

            if operation == "create":
                return await self._create_issue(data)
            elif operation == "update":
                return await self._update_issue(data)
            else:
                logger.warning(f"Unknown operation: {operation}")
                return False
        except Exception as e:
            logger.error(f"Send error: {e}")
            self.increment_error()
            return False

    async def receive_data(self) -> Optional[Dict[str, Any]]:
        """Receive data from Jira (via webhooks)."""
        # Webhooks handled separately
        logger.debug("Receive not applicable for Jira adapter (webhook-driven)")
        return None

    async def sync(self) -> bool:
        """Sync Jira metadata."""
        try:
            await self._sync_metadata()
            self.set_last_sync()
            self.increment_success()
            logger.info("Jira metadata synced")
            return True
        except Exception as e:
            logger.error(f"Sync error: {e}")
            self.increment_error()
            return False

    async def _sync_metadata(self) -> None:
        """Sync projects and issue types from Jira."""
        try:
            email = self.config.get_secret("jira_email")
            api_token = self.config.get_secret("jira_api_token")
            auth_string = f"{email}:{api_token}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers = {"Authorization": f"Basic {encoded_auth}"}

            # Get projects
            async with self.session.get(
                f"{self.instance_url}/rest/api/3/project",
                headers=headers,
                timeout=10,
            ) as resp:
                if resp.status == 200:
                    projects = await resp.json()
                    for proj in projects:
                        self.projects[proj["key"]] = proj["id"]

            # Get issue types
            async with self.session.get(
                f"{self.instance_url}/rest/api/3/issuetype",
                headers=headers,
                timeout=10,
            ) as resp:
                if resp.status == 200:
                    issue_types = await resp.json()
                    for itype in issue_types:
                        self.issue_types[itype["name"]] = itype["id"]
        except Exception as e:
            logger.error(f"Metadata sync error: {e}")

    async def _create_issue(self, data: Dict[str, Any]) -> bool:
        """Create a new Jira issue."""
        try:
            project_key = data.get("project_key")
            issue_type = data.get("issue_type", "Bug")
            summary = data.get("summary", "")
            description = data.get("description", "")
            priority = data.get("priority", "Medium")

            if not project_key or not summary:
                logger.warning("Missing required fields: project_key or summary")
                return False

            project_id = self.projects.get(project_key)
            issue_type_id = self.issue_types.get(issue_type)

            if not project_id or not issue_type_id:
                logger.warning(f"Project or issue type not found")
                return False

            email = self.config.get_secret("jira_email")
            api_token = self.config.get_secret("jira_api_token")
            auth_string = f"{email}:{api_token}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers = {
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json",
            }

            payload = {
                "fields": {
                    "project": {"id": project_id},
                    "issuetype": {"id": issue_type_id},
                    "summary": summary,
                    "description": {
                        "version": 3,
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": description,
                                    }
                                ],
                            }
                        ],
                    },
                    "priority": {"name": priority},
                }
            }

            # Add custom fields if provided
            for key, value in data.get("custom_fields", {}).items():
                payload["fields"][key] = value

            async with self.session.post(
                f"{self.instance_url}/rest/api/3/issue",
                json=payload,
                headers=headers,
                timeout=10,
            ) as resp:
                result = await resp.json()

                if resp.status in [201, 200]:
                    self.increment_success()
                    issue_key = result.get("key")
                    logger.debug(f"Issue created: {issue_key}")
                    return True
                else:
                    self.increment_error()
                    logger.error(f"Create failed: {result.get('errorMessages')}")
                    return False
        except Exception as e:
            logger.error(f"Create error: {e}")
            self.increment_error()
            return False

    async def _update_issue(self, data: Dict[str, Any]) -> bool:
        """Update an existing Jira issue."""
        try:
            issue_key = data.get("issue_key")
            if not issue_key:
                logger.warning("Missing issue_key")
                return False

            email = self.config.get_secret("jira_email")
            api_token = self.config.get_secret("jira_api_token")
            auth_string = f"{email}:{api_token}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers = {
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json",
            }

            fields = {}
            if "summary" in data:
                fields["summary"] = data["summary"]
            if "description" in data:
                fields["description"] = {
                    "version": 3,
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": data["description"]}],
                        }
                    ],
                }
            if "status" in data:
                fields["status"] = {"name": data["status"]}

            payload = {"fields": fields}

            async with self.session.put(
                f"{self.instance_url}/rest/api/3/issue/{issue_key}",
                json=payload,
                headers=headers,
                timeout=10,
            ) as resp:
                if resp.status in [204, 200]:
                    self.increment_success()
                    logger.debug(f"Issue updated: {issue_key}")
                    return True
                else:
                    self.increment_error()
                    logger.error(f"Update failed: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Update error: {e}")
            self.increment_error()
            return False

    async def health_check(self) -> bool:
        """Check Jira health."""
        try:
            return await self.test_connection()
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False

    async def test_connection(self) -> bool:
        """Test connection to Jira."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            return await self.authenticate()
        except Exception as e:
            logger.error(f"Connection test error: {e}")
            return False

    def __del__(self):
        """Cleanup."""
        if self.session:
            try:
                asyncio.run(self.session.close())
            except Exception:
                pass
