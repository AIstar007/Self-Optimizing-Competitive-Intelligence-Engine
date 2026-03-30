"""ServiceNow integration adapter."""

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


class ServiceNowAdapter(BaseIntegrationAdapter):
    """ServiceNow instance integration adapter."""

    def __init__(self, config: IntegrationConfig):
        """Initialize ServiceNow adapter."""
        super().__init__(config)
        self.instance_url: Optional[str] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.tables: Dict[str, Dict[str, Any]] = {}  # Table metadata cache

    async def connect(self) -> bool:
        """Connect to ServiceNow instance."""
        try:
            self.session = aiohttp.ClientSession()

            if not await self.authenticate():
                logger.error("Failed to authenticate with ServiceNow")
                self.status = IntegrationStatus.ERROR
                return False

            # Sync available tables
            await self._sync_tables()

            self.status = IntegrationStatus.ACTIVE
            self.increment_success()
            logger.info(f"Connected to ServiceNow: {self.instance_url}")
            return True
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.status = IntegrationStatus.ERROR
            self.increment_error()
            return False

    async def disconnect(self) -> bool:
        """Disconnect from ServiceNow."""
        try:
            if self.session:
                await self.session.close()

            self.status = IntegrationStatus.DISCONNECTED
            logger.info("Disconnected from ServiceNow")
            return True
        except Exception as e:
            logger.error(f"Disconnection error: {e}")
            return False

    async def authenticate(self) -> bool:
        """Authenticate with ServiceNow API."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()

            self.instance_url = self.config.get_secret("servicenow_instance_url")
            username = self.config.get_secret("servicenow_username")
            password = self.config.get_secret("servicenow_password")

            if not all([self.instance_url, username, password]):
                logger.error("Missing ServiceNow credentials")
                return False

            # Normalize instance URL
            if not self.instance_url.startswith("http"):
                self.instance_url = f"https://{self.instance_url}"
            if not self.instance_url.endswith(".com"):
                self.instance_url = f"{self.instance_url}.service-now.com"

            # Create authorization header
            auth_string = f"{username}:{password}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()

            headers = {"Authorization": f"Basic {encoded_auth}"}

            # Test authentication
            async with self.session.get(
                f"{self.instance_url}/api/now/table/sys_user",
                headers=headers,
                timeout=10,
                params={"sysparm_limit": 1},
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
        """Create or update ServiceNow record."""
        try:
            operation = data.get("operation", "create")
            table = data.get("table", "incident")

            if operation == "create":
                return await self._create_record(table, data)
            elif operation == "update":
                return await self._update_record(table, data)
            else:
                logger.warning(f"Unknown operation: {operation}")
                return False
        except Exception as e:
            logger.error(f"Send error: {e}")
            self.increment_error()
            return False

    async def receive_data(self) -> Optional[Dict[str, Any]]:
        """Receive data from ServiceNow (via webhooks)."""
        # Webhooks handled separately
        logger.debug("Receive not applicable for ServiceNow adapter (webhook-driven)")
        return None

    async def sync(self) -> bool:
        """Sync ServiceNow metadata."""
        try:
            await self._sync_tables()
            self.set_last_sync()
            self.increment_success()
            logger.info("ServiceNow metadata synced")
            return True
        except Exception as e:
            logger.error(f"Sync error: {e}")
            self.increment_error()
            return False

    async def _sync_tables(self) -> None:
        """Sync available tables from ServiceNow."""
        try:
            username = self.config.get_secret("servicenow_username")
            password = self.config.get_secret("servicenow_password")
            auth_string = f"{username}:{password}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers = {"Authorization": f"Basic {encoded_auth}"}

            # Common tables to track
            common_tables = ["incident", "change_request", "problem", "cmdb_ci"]

            for table in common_tables:
                async with self.session.get(
                    f"{self.instance_url}/api/now/table/{table}",
                    headers=headers,
                    timeout=10,
                    params={"sysparm_limit": 0},
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        self.tables[table] = {
                            "count": len(result.get("result", [])),
                            "available": True,
                        }
                    else:
                        self.tables[table] = {"available": False}
        except Exception as e:
            logger.error(f"Table sync error: {e}")

    async def _create_record(self, table: str, data: Dict[str, Any]) -> bool:
        """Create a new ServiceNow record."""
        try:
            username = self.config.get_secret("servicenow_username")
            password = self.config.get_secret("servicenow_password")
            auth_string = f"{username}:{password}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers = {
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json",
            }

            # Build payload from data (excluding metadata)
            payload = {k: v for k, v in data.items() if k not in ["operation", "table"]}

            async with self.session.post(
                f"{self.instance_url}/api/now/table/{table}",
                json=payload,
                headers=headers,
                timeout=10,
            ) as resp:
                result = await resp.json()

                if resp.status in [201, 200]:
                    sys_id = result.get("result", {}).get("sys_id")
                    self.increment_success()
                    logger.debug(f"Record created in {table}: {sys_id}")
                    return True
                else:
                    self.increment_error()
                    logger.error(f"Create failed: {result.get('error')}")
                    return False
        except Exception as e:
            logger.error(f"Create error: {e}")
            self.increment_error()
            return False

    async def _update_record(self, table: str, data: Dict[str, Any]) -> bool:
        """Update a ServiceNow record."""
        try:
            sys_id = data.get("sys_id")
            if not sys_id:
                logger.warning("Missing sys_id for update")
                return False

            username = self.config.get_secret("servicenow_username")
            password = self.config.get_secret("servicenow_password")
            auth_string = f"{username}:{password}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers = {
                "Authorization": f"Basic {encoded_auth}",
                "Content-Type": "application/json",
            }

            # Build payload (excluding metadata)
            payload = {k: v for k, v in data.items() if k not in ["sys_id", "operation", "table"]}

            async with self.session.patch(
                f"{self.instance_url}/api/now/table/{table}/{sys_id}",
                json=payload,
                headers=headers,
                timeout=10,
            ) as resp:
                if resp.status in [200, 204]:
                    self.increment_success()
                    logger.debug(f"Record updated in {table}: {sys_id}")
                    return True
                else:
                    self.increment_error()
                    logger.error(f"Update failed: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"Update error: {e}")
            self.increment_error()
            return False

    async def query_records(
        self, table: str, query: Dict[str, Any], limit: int = 10
    ) -> Optional[Dict[str, Any]]:
        """Query ServiceNow records."""
        try:
            username = self.config.get_secret("servicenow_username")
            password = self.config.get_secret("servicenow_password")
            auth_string = f"{username}:{password}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()
            headers = {"Authorization": f"Basic {encoded_auth}"}

            # Build query parameter
            query_params = "&".join([f"{k}={v}" for k, v in query.items()])

            async with self.session.get(
                f"{self.instance_url}/api/now/table/{table}",
                headers=headers,
                params={"sysparm_query": query_params, "sysparm_limit": limit},
                timeout=10,
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"Query failed: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Query error: {e}")
            return None

    async def health_check(self) -> bool:
        """Check ServiceNow health."""
        try:
            return await self.test_connection()
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False

    async def test_connection(self) -> bool:
        """Test connection to ServiceNow."""
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
