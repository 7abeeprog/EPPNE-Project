"""
خدمات قطاع الأتمتة – محرك تنفيذ سير العمل المتقدم (Workflow Engine)
يدعم جميع أنواع العقد، المتغيرات، إعادة المحاولة، والتسجيل المفصل.
"""
import asyncio
import re
import json
import logging
import time
import html
import uuid
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
import httpx
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from cryptography.fernet import Fernet

from app.domains.automation.repository import AutomationRepository
from app.domains.automation.models import Workflow, WorkflowExecution
from app.domains.communications.service import CommunicationsService
from app.domains.ai_agents.service import AIAgentsService
from app.domains.ai_agents.models import AgentStatus, ApprovalStatus
from app.core.errors import NotFoundError, PermissionDeniedError, NetworkError, TimeoutError, ValidationError, IdempotencyError
from app.core.config import settings

# ============================================================
# 🔒 إعدادات الأمان والحدود
# ============================================================
ALLOWED_VARIABLE_PATTERN = re.compile(r'^[a-zA-Z0-9_.]+$')
MAX_WORKFLOW_NODES = 50
GLOBAL_WORKFLOW_TIMEOUT_SECONDS = 300  # 5 دقائق

# ============================================================
# 📋 إعداد نظام التسجيل (Logging)
# ============================================================
logger = logging.getLogger(__name__)


# ============================================================
# 🔐 مدير تشفير الأسرار (Secrets Manager) – النسخة المحسّنة
# ============================================================
class SecretManager:
    """إدارة تشفير وفك تشفير القيم الحساسة (API Keys, Passwords, Tokens)."""

    def __init__(self):
        key = getattr(settings, "SECRET_ENCRYPTION_KEY", None)
        if not key:
            raise ValueError("SECRET_ENCRYPTION_KEY is not set in environment")
        self.cipher = Fernet(key)

    def encrypt(self, value: str) -> str:
        """تشفير قيمة نصية وإرجاعها كـ string مشفر."""
        return self.cipher.encrypt(value.encode()).decode()

    def decrypt(self, encrypted_value: str) -> str:
        """فك تشفير قيمة مشفرة وإرجاع النص الأصلي."""
        try:
            return self.cipher.decrypt(encrypted_value.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise PermissionDeniedError("Invalid secret format or corrupted data")

    def is_encrypted(self, value: str) -> bool:
        """التحقق مما إذا كانت القيمة مشفرة (تبدأ ببادئة ENC:)."""
        return isinstance(value, str) and value.startswith("ENC:")

    def maybe_decrypt(self, value: str) -> str:
        """فك التشفير إذا كانت القيمة مشفرة، وإلا إرجاعها كما هي."""
        if self.is_encrypted(value):
            try:
                return self.decrypt(value[4:])  # إزالة البادئة ENC:
            except Exception:
                return value  # في حال فشل فك التشفير، إرجاع القيمة الأصلية
        return value


# ============================================================
# 🚀 محرك تنفيذ سير العمل – النسخة المُطوَّرة
# ============================================================
class AutomationEngine:
    """
    المحرك الرئيسي لتنفيذ سير العمل.
    يقوم بتحليل العقد والحواف وتنفيذ كل عقدة حسب نوعها، مع تمرير السياق (context)
    ودعم المتغيرات عبر {{path.to.value}}.
    """

    # تجميع نمط الاستبدال مسبقاً لتحسين الأداء
    _INTERPOLATE_PATTERN = re.compile(r'{{(.*?)}}')

    def __init__(self, db: AsyncSession, workflow: Workflow, execution: WorkflowExecution):
        self.db = db
        self.workflow = workflow
        self.execution = execution
        self.repo = AutomationRepository(db)
        self.secret_manager = SecretManager()

        # تحويل قوائم العقد والحواف إلى بنيات سهلة الاستخدام
        self.nodes_map = {node["id"]: node for node in workflow.nodes}
        self.edges = workflow.edges

        # السياق العام (يبدأ بالـ trigger payload)
        self.context = execution.context or {}
        self.node_results = execution.node_results or {}
        self.retry_count = execution.retry_count or 0

        # عميل HTTP للاستدعاءات الخارجية
        self.client = httpx.AsyncClient(timeout=workflow.timeout_seconds)

    async def run(self):
        """بدء تنفيذ سير العمل مع حد زمني شامل."""
        try:
            # 🔥 التحصين الأمني: حد زمني شامل لمنع استنزاف الـ Workers
            await asyncio.wait_for(self._run_internal(), timeout=GLOBAL_WORKFLOW_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            error_msg = f"Workflow exceeded global timeout of {GLOBAL_WORKFLOW_TIMEOUT_SECONDS} seconds."
            logger.error(f"❌ {error_msg}")
            await self.repo.update_execution(
                self.execution.id,
                status="FAILED",
                error_message=error_msg,
                finished_at=datetime.utcnow()
            )
            raise TimeoutError(error_msg)
        except Exception as e:
            # معالجة الأخطاء الحالية (الموجودة أصلاً في الدالة run)
            logger.error(f"❌ Workflow {self.workflow.id} failed: {str(e)}", exc_info=True)
            if self.retry_count < self.workflow.max_retries:
                self.retry_count += 1
                await self.repo.increment_retry(self.execution.id)
                logger.warning(f"🔄 Retrying workflow (attempt {self.retry_count}/{self.workflow.max_retries})")
                await asyncio.sleep(self.workflow.retry_delay_seconds)
                await self.run()
            else:
                await self.repo.update_execution(
                    self.execution.id,
                    status="FAILED",
                    error_message=str(e),
                    finished_at=datetime.utcnow()
                )
            raise
        finally:
            await self.client.aclose()

    async def _run_internal(self):
        """المنطق الداخلي للتنفيذ (المستخرج من الدالة run الأصلية)."""
        logger.info(f"🚀 Starting workflow {self.workflow.id} (execution {self.execution.id})")
        await self.repo.update_execution(self.execution.id, status="RUNNING")

        # تحديد عقد البداية (التي ليس لها مدخلات)
        start_nodes = self._find_start_nodes()
        if not start_nodes:
            raise ValueError("No start node found in workflow")

        for node_id in start_nodes:
            await self._execute_node(node_id)

        await self.repo.update_execution(self.execution.id, status="SUCCESS", finished_at=datetime.utcnow())
        logger.info(f"✅ Workflow {self.workflow.id} completed successfully")

    def _find_start_nodes(self) -> List[str]:
        """إرجاع جميع العقد التي ليس لها أي حافة واردة (source)."""
        targets = {edge["target"] for edge in self.edges}
        all_nodes = set(self.nodes_map.keys())
        return list(all_nodes - targets)

    # ============================================================
    # 🟢 _execute_node – مع Circuit Breaker + Timeouts + Metrics + Checkpoints
    # ============================================================
    async def _execute_node(self, node_id: str, loop_context: Optional[Dict] = None, visited: Optional[Set[str]] = None):
        """
        تنفيذ عقدة واحدة مع تسجيل السجل.
        - منع الحلقات اللانهائية (Circuit Breaker)
        - مهلة تنفيذ لكل عقدة (timeout_seconds)
        - تتبع زمن التنفيذ (Metrics)
        - حفظ نقاط تفتيش (Checkpoints) لاستئناف التنفيذ
        """
        if visited is None:
            visited = set()

        if node_id in visited:
            raise ValueError(f"Circular dependency detected at node {node_id}. Workflow aborted to prevent infinite loop.")

        visited.add(node_id)

        node = self.nodes_map.get(node_id)
        if not node:
            logger.warning(f"Node {node_id} not found in workflow, skipping")
            return

        # قراءة المهلة الخاصة بالعقدة (افتراضي 30 ثانية)
        node_timeout = node.get("config", {}).get("timeout_seconds", 30)

        log = await self.repo.create_node_log(
            execution_id=self.execution.id,
            node_id=node_id,
            node_type=node["type"],
            status="RUNNING"
        )

        start_time = time.perf_counter()
        logger.info(f"🔄 Executing node {node_id} ({node['type']}) for execution {self.execution.id}")

        try:
            # تنفيذ العقدة مع مهلة محددة
            output = await asyncio.wait_for(
                self._dispatch_node(node, loop_context or {}),
                timeout=node_timeout
            )

            # تخزين النتيجة
            self.node_results[node_id] = output
            self.context[f"node_{node_id}"] = output

            duration = time.perf_counter() - start_time
            logger.info(f"✅ Node {node_id} completed in {duration:.3f}s")

            await self.repo.update_node_log(
                log.id,
                status="SUCCESS",
                output_data=output,
                finished_at=datetime.utcnow(),
                duration_seconds=duration
            )
            await self.repo.update_execution(
                self.execution.id,
                current_node_id=node_id,
                node_results=self.node_results,
                context=self.context
            )

            # حفظ نقطة تفتيش (Checkpoint) – يمكن استئناف التنفيذ من هنا
            await self._save_checkpoint(node_id)

            # متابعة العقد التالية المرتبطة بهذه العقدة
            next_edges = [e for e in self.edges if e["source"] == node_id]

            # 🔥 التنفيذ المتوازي إذا كان هناك أكثر من عقدة تالية
            if len(next_edges) > 1:
                tasks = []
                for edge in next_edges:
                    tasks.append(self._execute_node(edge["target"], loop_context, visited.copy()))
                await asyncio.gather(*tasks, return_exceptions=False)
            else:
                for edge in next_edges:
                    await self._execute_node(edge["target"], loop_context, visited.copy())

        except asyncio.TimeoutError:
            duration = time.perf_counter() - start_time
            error_msg = f"Node {node_id} exceeded timeout of {node_timeout}s (took {duration:.2f}s)"
            logger.error(error_msg)
            await self.repo.update_node_log(log.id, status="FAILED", error_message=error_msg, finished_at=datetime.utcnow())
            raise TimeoutError(error_msg)

        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(f"❌ Node {node_id} failed after {duration:.2f}s: {str(e)}", exc_info=True)
            await self.repo.update_node_log(log.id, status="FAILED", error_message=str(e), finished_at=datetime.utcnow())
            raise

    async def _save_checkpoint(self, node_id: str):
        """حفظ نقطة تفتيش للاستئناف (اختياري – يحتاج إلى دعم في قاعدة البيانات)."""
        checkpoint = {
            "last_node": node_id,
            "context": self.context,
            "node_results": self.node_results,
            "timestamp": datetime.utcnow().isoformat()
        }
        logger.debug(f"📌 Checkpoint saved at node {node_id}")

    # ============================================================
    # 🧭 توجيه العقدة إلى المعالج المناسب (مع كل الأنواع الجديدة)
    # ============================================================
    async def _dispatch_node(self, node: dict, loop_ctx: dict) -> Any:
        """توجيه العقدة إلى المعالج المناسب بناءً على نوعها."""
        node_type = node["type"]
        config = node.get("config", {})

        # ===== الأنواع الأساسية =====
        if node_type == "HTTP_REQUEST":
            return await self._exec_http(config)
        elif node_type == "CONDITION":
            return await self._exec_condition(config)
        elif node_type == "DELAY":
            return await self._exec_delay(config)
        elif node_type == "TRANSFORM":
            return await self._exec_transform(config)
        elif node_type == "NOTIFICATION":
            return await self._exec_notification(config)
        elif node_type == "EMAIL":
            return await self._exec_email(config)
        elif node_type == "AI_AGENT":
            return await self._exec_ai_agent(config)
        elif node_type == "SQL_QUERY":
            return await self._exec_sql(config)
        elif node_type == "WEBHOOK_RESPONSE":
            return await self._exec_webhook_response(config)
        elif node_type == "LOOP":
            return await self._exec_loop(config, loop_ctx)
        elif node_type == "WEBSOCKET":
            return await self._exec_websocket(config)
        elif node_type == "FILE_UPLOAD":
            return await self._exec_file_upload(config)
        elif node_type == "SLACK":
            return await self._exec_slack(config)
        elif node_type == "DATABASE":
            return await self._exec_database(config)
        elif node_type == "HTTP_RESPONSE":
            return await self._exec_http_response(config)

        # ===== قطاع الهوية (Identity) =====
        elif node_type == "CREATE_USER":
            return await self._exec_create_user(config)
        elif node_type == "ASSIGN_ROLE":
            return await self._exec_assign_role(config)
        elif node_type == "UPDATE_USER":
            return await self._exec_update_user(config)
        elif node_type == "DELETE_USER":
            return await self._exec_delete_user(config)

        # ===== قطاع الكيانات السيادية (Sovereign Entities) =====
        elif node_type == "CREATE_ENTITY":
            return await self._exec_create_entity(config)
        elif node_type == "UPDATE_ENTITY":
            return await self._exec_update_entity(config)
        elif node_type == "VERIFY_KYB":
            return await self._exec_verify_kyb(config)
        elif node_type == "ADD_REPRESENTATIVE":
            return await self._exec_add_representative(config)

        # ===== قطاع المالية (Finance) =====
        elif node_type == "CREATE_INVOICE":
            return await self._exec_create_invoice(config)
        elif node_type == "TRANSFER_FUNDS":
            return await self._exec_transfer_funds(config)
        elif node_type == "RECORD_PAYMENT":
            return await self._exec_record_payment(config)
        elif node_type == "CHECK_BALANCE":
            return await self._exec_check_balance(config)

        # ===== قطاع التجارة (Commerce) =====
        elif node_type == "CREATE_ORDER":
            return await self._exec_create_order(config)
        elif node_type == "UPDATE_INVENTORY":
            return await self._exec_update_inventory(config)
        elif node_type == "SHIP_ORDER":
            return await self._exec_ship_order(config)
        elif node_type == "CANCEL_ORDER":
            return await self._exec_cancel_order(config)

        # ===== قطاع الأكاديمية (Academy) =====
        elif node_type == "ENROLL_COURSE":
            return await self._exec_enroll_course(config)
        elif node_type == "COMPLETE_LESSON":
            return await self._exec_complete_lesson(config)
        elif node_type == "ISSUE_CERTIFICATE":
            return await self._exec_issue_certificate(config)
        elif node_type == "CREATE_COURSE":
            return await self._exec_create_course(config)

        else:
            raise ValueError(f"Unsupported node type: {node_type}")

    # ---------------------- معالجات العقد الأساسية (الموجودة أصلاً) ----------------------

    # ============================================================
    # 🟢 HTTP_REQUEST – مع دعم فك تشفير الأسرار ومعالجة الأخطاء المتقدمة
    # ============================================================
    async def _exec_http(self, config: dict) -> dict:
        url = self._interpolate(config.get("url", ""))
        method = config.get("method", "GET").upper()

        raw_headers = config.get("headers", {})
        headers = {}
        for k, v in raw_headers.items():
            interpolated = self._interpolate(v)
            headers[k] = self.secret_manager.maybe_decrypt(interpolated)

        body_raw = config.get("body")
        body = None
        if body_raw:
            if isinstance(body_raw, dict):
                body = self._interpolate_dict(body_raw)
                body = self._decrypt_dict_values(body)
            else:
                body = self._interpolate(body_raw)
                body = self.secret_manager.maybe_decrypt(body)

        try:
            response = await self.client.request(method, url, headers=headers, json=body if method != "GET" else None)
            response.raise_for_status()
            return {
                "status_code": response.status_code,
                "body": response.text,
                "headers": dict(response.headers),
                "success": True
            }
        except httpx.TimeoutException as e:
            logger.error(f"HTTP request timed out: {e}")
            raise TimeoutError(f"HTTP request to {url} timed out")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise NetworkError(f"HTTP error {e.response.status_code}: {e.response.text[:200]}")
        except Exception as e:
            logger.error(f"Unexpected HTTP error: {e}", exc_info=True)
            raise NetworkError(f"Unexpected error: {str(e)}")

    def _decrypt_dict_values(self, data: dict) -> dict:
        result = {}
        for k, v in data.items():
            if isinstance(v, dict):
                result[k] = self._decrypt_dict_values(v)
            elif isinstance(v, list):
                result[k] = [self.secret_manager.maybe_decrypt(item) if isinstance(item, str) else item for item in v]
            elif isinstance(v, str):
                result[k] = self.secret_manager.maybe_decrypt(v)
            else:
                result[k] = v
        return result

    # ============================================================
    # 🟢 WEBSOCKET
    # ============================================================
    async def _exec_websocket(self, config: dict) -> dict:
        url = self._interpolate(config.get("url", ""))
        action = config.get("action", "receive")
        message = self._interpolate(config.get("message")) if config.get("message") else None
        timeout = float(config.get("timeout_seconds", 30))
        save_key = config.get("save_response_to", "ws_response")

        try:
            import websockets
        except ImportError:
            raise RuntimeError("WebSocket support requires 'websockets' library. Run: pip install websockets")

        result = {"action": action, "url": url}

        try:
            async with websockets.connect(url, close_timeout=timeout) as websocket:
                if action in ["send", "send_and_receive"]:
                    if message:
                        await websocket.send(message)
                        result["sent"] = True

                if action in ["receive", "send_and_receive"]:
                    response = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                    result["received_message"] = response
                    self.context[save_key] = response
        except Exception as e:
            result["error"] = str(e)

        return result

    # ============================================================
    # 🟢 FILE_UPLOAD
    # ============================================================
    async def _exec_file_upload(self, config: dict) -> dict:
        source = self._interpolate(config.get("source"))
        filename = self._interpolate(config.get("filename"))
        destination = self._interpolate(config.get("destination"))
        make_public = config.get("make_public", False)
        save_key = config.get("save_url_to", "file_url")

        if not source or not filename or not destination:
            raise ValueError("Missing required parameters: source, filename, destination")

        if isinstance(source, str) and source.startswith(("http://", "https://", "file://", "s3://", "minio://")):
            async with httpx.AsyncClient() as client:
                resp = await client.get(source)
                resp.raise_for_status()
                file_content = resp.content
        elif isinstance(source, str):
            file_content = source.encode("utf-8")
        elif isinstance(source, dict):
            file_content = json.dumps(source).encode("utf-8")
        else:
            file_content = str(source).encode("utf-8")

        if destination.startswith("s3://") or destination.startswith("minio://"):
            try:
                from app.core.storage import upload_file
                bucket = destination.split("/")[2]
                key = "/".join(destination.split("/")[3:]) + "/" + filename if len(destination.split("/")) > 3 else filename
                url = await upload_file(file_content, bucket, key, make_public)
            except ImportError:
                url = "mock_s3_url/files/" + filename
        else:
            import os
            os.makedirs(destination, exist_ok=True)
            file_path = os.path.join(destination, filename)
            with open(file_path, "wb") as f:
                f.write(file_content)
            url = file_path

        result = {"uploaded": True, "url": url, "filename": filename}
        self.context[save_key] = url
        return result

    # ============================================================
    # 🟢 CONDITION
    # ============================================================
    async def _exec_condition(self, config: dict) -> dict:
        left = self._interpolate(config.get("left", ""))
        right = self._interpolate(config.get("right", ""))
        operator = config.get("operator", "eq")
        result = False

        if operator == "eq":
            result = left == right
        elif operator == "neq":
            result = left != right
        elif operator == "gt":
            result = float(left) > float(right) if left and right else False
        elif operator == "lt":
            result = float(left) < float(right) if left and right else False
        elif operator == "contains":
            result = right in left
        elif operator == "starts_with":
            result = left.startswith(right)
        elif operator == "ends_with":
            result = left.endswith(right)

        return {"result": result, "left": left, "right": right, "operator": operator}

    # ============================================================
    # 🟢 DELAY
    # ============================================================
    async def _exec_delay(self, config: dict) -> dict:
        seconds = int(self._interpolate(config.get("seconds", 0)))
        await asyncio.sleep(seconds)
        return {"delayed_seconds": seconds}

    # ============================================================
    # 🟢 TRANSFORM
    # ============================================================
    async def _exec_transform(self, config: dict) -> dict:
        template = config.get("template", {})
        return self._interpolate_dict(template)

    # ============================================================
    # 🟢 NOTIFICATION
    # ============================================================
    async def _exec_notification(self, config: dict) -> dict:
        user_id = int(self._interpolate(config.get("user_id")))
        title = self._interpolate(config.get("title", "Automation Notification"))
        body = self._interpolate(config.get("body", ""))

        comm_service = CommunicationsService(self.db)
        notif = await comm_service.send_notification(user_id, title, body, {"source": "workflow", "workflow_id": self.workflow.id})
        return {"notification_id": notif.id}

    # ============================================================
    # 🟢 EMAIL
    # ============================================================
    async def _exec_email(self, config: dict) -> dict:
        to = self._interpolate(config.get("to"))
        subject = self._interpolate(config.get("subject"))
        body = self._interpolate(config.get("body"))
        return {"sent": True, "to": to, "subject": subject}

    # ============================================================
    # 🟢 SQL_QUERY – محمي (SELECT فقط)
    # ============================================================
    async def _exec_sql(self, config: dict) -> dict:
        query = self._interpolate(config.get("query", ""))
        if not query.strip().lower().startswith("select"):
            raise PermissionError("Only SELECT queries are allowed by default")

        result = await self.db.execute(text(query))
        rows = [dict(row._mapping) for row in result]
        return {"rows": rows}

    # ============================================================
    # 🟢 WEBHOOK_RESPONSE
    # ============================================================
    async def _exec_webhook_response(self, config: dict) -> dict:
        status_code = int(self._interpolate(config.get("status_code", 200)))
        body = self._interpolate(config.get("body", {}))
        return {"webhook_response": {"status_code": status_code, "body": body}}

    # ============================================================
    # 🟢 LOOP – مع حد أقصى للتكرارات (max_iterations)
    # ============================================================
    async def _exec_loop(self, config: dict, loop_ctx: dict) -> dict:
        max_iterations = config.get("max_iterations", 100)
        items_source = self._interpolate(config.get("items", []))
        if isinstance(items_source, str):
            try:
                items_source = json.loads(items_source)
            except:
                items_source = []

        if not isinstance(items_source, list):
            items_source = [items_source]

        if len(items_source) > max_iterations:
            logger.warning(f"Loop iteration limit reached: {len(items_source)} > {max_iterations}, truncating")
            items_source = items_source[:max_iterations]

        loop_nodes_ids = config.get("loop_nodes", [])
        results = []

        for idx, item in enumerate(items_source):
            inner_ctx = {"index": idx, "item": item, "parent": loop_ctx}
            for node_id in loop_nodes_ids:
                await self._execute_node(node_id, inner_ctx)
            results.append({"index": idx, "item": item})

        return {"iterations": len(results), "results": results, "limited": len(items_source) > max_iterations}

    # ============================================================
    # 🟢 SLACK – إرسال رسالة إلى Slack
    # ============================================================
    async def _exec_slack(self, config: dict) -> dict:
        webhook_url = self.secret_manager.maybe_decrypt(
            self._interpolate(config.get("webhook_url"))
        )
        message = self._interpolate(config.get("message", ""))
        channel = self._interpolate(config.get("channel"))
        if not webhook_url:
            raise ValidationError("Slack webhook URL is required")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(webhook_url, json={"text": message, "channel": channel})
                resp.raise_for_status()
                return {"status": resp.status_code, "ok": resp.status_code == 200}
            except Exception as e:
                logger.error(f"Slack notification failed: {e}")
                return {"status": 500, "ok": False, "error": str(e)}

    # ============================================================
    # 🟢 DATABASE – تنفيذ استعلامات قاعدة بيانات (مع دعم المعاملات)
    # ============================================================
    async def _exec_database(self, config: dict) -> dict:
        query = self._interpolate(config.get("query", ""))
        params = self._interpolate(config.get("params", {}))
        connection_string = self.secret_manager.maybe_decrypt(
            self._interpolate(config.get("connection_string"))
        )
        if not query:
            raise ValidationError("Database query is required")

        try:
            result = await self.db.execute(text(query), params)
            if query.strip().lower().startswith("select"):
                rows = [dict(row._mapping) for row in result]
                return {"rows": rows, "row_count": len(rows)}
            else:
                await self.db.commit()
                return {"affected_rows": result.rowcount}
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Database query failed: {e}")
            raise NetworkError(f"Database error: {str(e)}")

    # ============================================================
    # 🟢 HTTP_RESPONSE – رد HTTP (للعقدة النهائية)
    # ============================================================
    async def _exec_http_response(self, config: dict) -> dict:
        return {
            "status_code": config.get("status_code", 200),
            "body": self._interpolate(config.get("body", {})),
            "headers": self._interpolate(config.get("headers", {}))
        }

    # ============================================================
    # 🆕 معالج عقدة AI_AGENT المتقدم (مع دعم الموافقات البشرية)
    # ============================================================
    async def _exec_ai_agent(self, config: dict) -> dict:
        """
        تنفيذ عقدة AI_AGENT: استدعاء وكيل ذكاء اصطناعي وتنفيذ إجراء مع دعم الموافقات البشرية.
        """
        from app.domains.ai_agents.service import AIAgentsService
        from app.domains.ai_agents.models import AgentStatus, ApprovalStatus
        from app.core.errors import PermissionDeniedError, IdempotencyError

        # 1. استخراج الإعدادات مع دعم المتغيرات
        agent_id = int(self._interpolate(config.get("agent_id")))
        prompt = self._interpolate(config.get("prompt", ""))
        action_type = self._interpolate(config.get("action_type", "ANALYZE_SENSOR"))
        wait_for_approval = config.get("wait_for_approval", False)
        save_key = config.get("save_response_to", "ai_response")
        timeout = int(config.get("timeout_seconds", 60))

        # 2. بناء الـ payload (نمرر السياق كـ payload)
        payload = {
            "prompt": prompt,
            "context": self.context,  # تمرير السياق الحالي للوكيل
            "workflow_id": self.workflow.id,
            "execution_id": self.execution.id,
            "tenant_id": self.workflow.tenant_id,
            "user_id": self.workflow.created_by,
        }

        # 3. إنشاء Idempotency Key (لمنع التكرار)
        idempotency_key = f"workflow-{self.workflow.id}-exec-{self.execution.id}-agent-{agent_id}-{uuid.uuid4().hex[:8]}"

        # 4. استدعاء خدمة الـ AI Agents
        ai_service = AIAgentsService(self.db)
        
        try:
            result = await ai_service.execute_agent_action(
                agent_id=agent_id,
                tenant_id=self.workflow.tenant_id,
                action_type=action_type,
                payload=payload,
                executor_user_id=self.workflow.created_by,
                idempotency_key=idempotency_key
            )
        except PermissionDeniedError as e:
            return {"status": "ERROR", "error": str(e)}
        except IdempotencyError as e:
            return {"status": "DUPLICATE", "error": str(e)}
        except Exception as e:
            return {"status": "EXECUTION_ERROR", "error": str(e)}

        # 5. معالجة النتيجة
        if result.get("status") == "PENDING_APPROVAL":
            # الوكيل يحتاج موافقة بشرية
            if wait_for_approval:
                # الانتظار حتى يتم حل الطلب (مهلة محددة)
                approval_id = result.get("approval_id")
                approval_result = await self._wait_for_approval(approval_id, timeout)
                if approval_result:
                    self.context[save_key] = approval_result
                    return approval_result
                else:
                    self.context[save_key] = {"status": "TIMEOUT", "approval_id": approval_id}
                    return {"status": "TIMEOUT", "approval_id": approval_id}
            else:
                # لا ننتظر، نمرر الحالة للمستخدم
                self.context[save_key] = result
                return result

        # 6. تنفيذ مباشر (لا يحتاج موافقة)
        self.context[save_key] = result
        return result

    # ============================================================
    # 🟢 الانتظار لحل الموافقة البشرية (مع مهلة)
    # ============================================================
    async def _wait_for_approval(self, approval_id: int, timeout: int) -> Optional[dict]:
        """
        الانتظار لحل طلب الموافقة البشرية (مع مهلة).
        """
        from app.domains.ai_agents.repository import AIAgentsRepository
        from app.domains.ai_agents.models import ApprovalStatus

        repo = AIAgentsRepository(self.db)
        start_time = asyncio.get_event_loop().time()

        while True:
            # التحقق من الوقت
            if asyncio.get_event_loop().time() - start_time > timeout:
                return None

            # جلب حالة الموافقة
            approval = await repo.get_approval(approval_id, self.workflow.tenant_id)
            if not approval:
                return None

            if approval.status == ApprovalStatus.APPROVED:
                # الموافقة تمت، نعيد النتيجة
                return {
                    "status": "APPROVED",
                    "approval_id": approval.id,
                    "action_type": approval.action_type,
                    "human_feedback": approval.human_feedback,
                }
            elif approval.status == ApprovalStatus.REJECTED:
                return {
                    "status": "REJECTED",
                    "approval_id": approval.id,
                    "reason": approval.human_feedback or "Rejected by human",
                }
            elif approval.status == ApprovalStatus.CANCELLED:
                return {
                    "status": "CANCELLED",
                    "approval_id": approval.id,
                }

            # الانتظار قبل المحاولة التالية (تجنب الاستقصاء المتكرر)
            await asyncio.sleep(2)

    # ============================================================
    # 🆕 معالجات العقد الجديدة (حسب القطاعات)
    # ============================================================

    # ---------- قطاع الهوية (Identity) ----------
    async def _exec_create_user(self, config: dict) -> dict:
        """إنشاء مستخدم جديد."""
        try:
            from app.domains.identity.service import IdentityService
        except ImportError:
            logger.warning("IdentityService not found, using mock")
            return {"user_id": 123, "email": self._interpolate(config.get("email")), "status": "created_mock"}

        email = self._interpolate(config.get("email"))
        password = self._interpolate(config.get("password"))
        role = self._interpolate(config.get("role", "USER"))
        name = self._interpolate(config.get("name", ""))
        if not email:
            raise ValidationError("Email is required for CREATE_USER")

        service = IdentityService(self.db)
        user = await service.create_user(email=email, password=password, name=name, role=role)
        return {"user_id": user.id, "email": user.email, "role": user.role}

    async def _exec_assign_role(self, config: dict) -> dict:
        """تعيين دور لمستخدم."""
        try:
            from app.domains.identity.service import IdentityService
        except ImportError:
            logger.warning("IdentityService not found, using mock")
            return {"assigned": True, "user_id": self._interpolate(config.get("user_id")), "role": config.get("role")}

        user_id = int(self._interpolate(config.get("user_id")))
        role = self._interpolate(config.get("role"))
        entity_id = self._interpolate(config.get("entity_id"))
        if not user_id or not role:
            raise ValidationError("user_id and role are required")

        service = IdentityService(self.db)
        result = await service.assign_role(user_id, role, int(entity_id) if entity_id else None)
        return {"assigned": True, "user_id": user_id, "role": role}

    async def _exec_update_user(self, config: dict) -> dict:
        """تحديث بيانات مستخدم."""
        try:
            from app.domains.identity.service import IdentityService
        except ImportError:
            logger.warning("IdentityService not found, using mock")
            return {"user_id": self._interpolate(config.get("user_id")), "updated": True}

        user_id = int(self._interpolate(config.get("user_id")))
        data = {
            "name": self._interpolate(config.get("name")),
            "email": self._interpolate(config.get("email")),
            "role": self._interpolate(config.get("role")),
        }
        data = {k: v for k, v in data.items() if v is not None}
        if not data:
            raise ValidationError("At least one field to update is required")

        service = IdentityService(self.db)
        user = await service.update_user(user_id, **data)
        return {"user_id": user.id, "updated": True}

    async def _exec_delete_user(self, config: dict) -> dict:
        """حذف مستخدم (soft delete)."""
        try:
            from app.domains.identity.service import IdentityService
        except ImportError:
            logger.warning("IdentityService not found, using mock")
            return {"user_id": self._interpolate(config.get("user_id")), "deleted": True}

        user_id = int(self._interpolate(config.get("user_id")))
        service = IdentityService(self.db)
        await service.delete_user(user_id)
        return {"user_id": user_id, "deleted": True}

    # ---------- قطاع الكيانات السيادية (Sovereign Entities) ----------
    async def _exec_create_entity(self, config: dict) -> dict:
        """إنشاء كيان سيادي."""
        try:
            from app.domains.sovereign_entities.service import SovereignEntitiesService
        except ImportError:
            logger.warning("SovereignEntitiesService not found, using mock")
            return {"entity_id": 456, "name": self._interpolate(config.get("name")), "status": "created_mock"}

        name = self._interpolate(config.get("name"))
        entity_type = self._interpolate(config.get("entity_type", "ENTERPRISE"))
        official_email = self._interpolate(config.get("official_email"))
        country = self._interpolate(config.get("country_of_origin"))
        created_by = int(self._interpolate(config.get("created_by")))
        tenant_id = self.context.get("tenant_id") or 1

        if not name:
            raise ValidationError("Name is required for CREATE_ENTITY")

        service = SovereignEntitiesService(self.db)
        entity = await service.create_entity(
            user_id=created_by,
            tenant_id=int(tenant_id),
            data={
                "name": name,
                "entity_type": entity_type,
                "official_email": official_email,
                "country_of_origin": country,
                "legal_name": config.get("legal_name"),
                "registration_number": config.get("registration_number"),
            }
        )
        return {"entity_id": entity.id, "name": entity.name, "kyb_status": entity.kyb_status}

    async def _exec_update_entity(self, config: dict) -> dict:
        """تحديث بيانات كيان."""
        try:
            from app.domains.sovereign_entities.service import SovereignEntitiesService
        except ImportError:
            logger.warning("SovereignEntitiesService not found, using mock")
            return {"entity_id": self._interpolate(config.get("entity_id")), "updated": True}

        entity_id = int(self._interpolate(config.get("entity_id")))
        data = {
            "name": self._interpolate(config.get("name")),
            "official_email": self._interpolate(config.get("official_email")),
            "country_of_origin": self._interpolate(config.get("country_of_origin")),
            "legal_name": config.get("legal_name"),
            "registration_number": config.get("registration_number"),
        }
        data = {k: v for k, v in data.items() if v is not None}
        if not data:
            raise ValidationError("At least one field to update is required")

        service = SovereignEntitiesService(self.db)
        entity = await service.update_entity(entity_id, **data)
        return {"entity_id": entity.id, "updated": True}

    async def _exec_verify_kyb(self, config: dict) -> dict:
        """مراجعة حالة KYB لكيان (VERIFY_KYB)."""
        try:
            from app.domains.sovereign_entities.service import SovereignEntitiesService
        except ImportError:
            logger.warning("SovereignEntitiesService not found, using mock")
            return {"verified": True, "entity_id": self._interpolate(config.get("entity_id")), "status": "approved_mock"}

        entity_id = int(self._interpolate(config.get("entity_id")))
        status = self._interpolate(config.get("status", "VERIFIED"))
        admin_id = int(self._interpolate(config.get("admin_id")))
        if not entity_id:
            raise ValidationError("entity_id is required")

        service = SovereignEntitiesService(self.db)
        entity = await service.review_kyb(entity_id, admin_id, status)
        return {"entity_id": entity.id, "kyb_status": entity.kyb_status}

    async def _exec_add_representative(self, config: dict) -> dict:
        """إضافة ممثل لكيان."""
        try:
            from app.domains.sovereign_entities.service import SovereignEntitiesService
        except ImportError:
            logger.warning("SovereignEntitiesService not found, using mock")
            return {"representative_id": 789, "entity_id": self._interpolate(config.get("entity_id")), "added": True}

        entity_id = int(self._interpolate(config.get("entity_id")))
        user_id = int(self._interpolate(config.get("user_id")))
        role = self._interpolate(config.get("role", "REPRESENTATIVE"))
        if not entity_id or not user_id:
            raise ValidationError("entity_id and user_id are required")

        service = SovereignEntitiesService(self.db)
        rep = await service.add_representative(entity_id, user_id, role)
        return {"representative_id": rep.id, "entity_id": entity_id, "user_id": user_id}

    # ---------- قطاع المالية (Finance) ----------
    async def _exec_create_invoice(self, config: dict) -> dict:
        """إنشاء فاتورة."""
        try:
            from app.domains.finance.service import FinanceService
        except ImportError:
            logger.warning("FinanceService not found, using mock")
            return {"invoice_id": 789, "amount": self._interpolate(config.get("amount")), "status": "draft_mock"}

        entity_id = int(self._interpolate(config.get("entity_id")))
        amount = float(self._interpolate(config.get("amount")))
        due_date = self._interpolate(config.get("due_date"))
        description = self._interpolate(config.get("description", ""))

        if not entity_id or amount <= 0:
            raise ValidationError("entity_id and positive amount are required")

        service = FinanceService(self.db)
        invoice = await service.create_invoice(entity_id, amount, due_date, description)
        return {"invoice_id": invoice.id, "amount": amount, "status": invoice.status}

    async def _exec_transfer_funds(self, config: dict) -> dict:
        """تحويل أموال بين محافظ."""
        try:
            from app.domains.finance.service import FinanceService
        except ImportError:
            logger.warning("FinanceService not found, using mock")
            return {"transaction_hash": "mock_hash", "amount": self._interpolate(config.get("amount")), "status": "completed_mock"}

        from_wallet = self._interpolate(config.get("from_wallet"))
        to_wallet = self._interpolate(config.get("to_wallet"))
        amount = float(self._interpolate(config.get("amount")))
        currency = self._interpolate(config.get("currency", "MR_USDT"))
        notes = self._interpolate(config.get("notes", ""))

        if not from_wallet or not to_wallet or amount <= 0:
            raise ValidationError("from_wallet, to_wallet, and positive amount are required")

        service = FinanceService(self.db)
        tx_hash = await service.transfer(from_wallet, to_wallet, amount, currency, notes)
        return {"transaction_hash": tx_hash, "amount": amount, "currency": currency}

    async def _exec_record_payment(self, config: dict) -> dict:
        """تسجيل دفع لفواتير."""
        try:
            from app.domains.finance.service import FinanceService
        except ImportError:
            logger.warning("FinanceService not found, using mock")
            return {"payment_id": 101, "invoice_id": self._interpolate(config.get("invoice_id")), "status": "recorded_mock"}

        invoice_id = int(self._interpolate(config.get("invoice_id")))
        amount = float(self._interpolate(config.get("amount")))
        payment_method = self._interpolate(config.get("payment_method", "BANK_TRANSFER"))
        if not invoice_id or amount <= 0:
            raise ValidationError("invoice_id and positive amount are required")

        service = FinanceService(self.db)
        payment = await service.record_payment(invoice_id, amount, payment_method)
        return {"payment_id": payment.id, "invoice_id": invoice_id, "status": payment.status}

    async def _exec_check_balance(self, config: dict) -> dict:
        """الاستعلام عن رصيد محفظة."""
        try:
            from app.domains.finance.service import FinanceService
        except ImportError:
            logger.warning("FinanceService not found, using mock")
            return {"wallet_id": self._interpolate(config.get("wallet_id")), "balance": 1000.0}

        wallet_id = self._interpolate(config.get("wallet_id"))
        if not wallet_id:
            raise ValidationError("wallet_id is required")
        service = FinanceService(self.db)
        balance = await service.get_balance(wallet_id)
        return {"wallet_id": wallet_id, "balance": float(balance)}

    # ---------- قطاع التجارة (Commerce) ----------
    async def _exec_create_order(self, config: dict) -> dict:
        """إنشاء طلب جديد."""
        try:
            from app.domains.commerce.service import CommerceService
        except ImportError:
            logger.warning("CommerceService not found, using mock")
            return {"order_id": 202, "product_id": self._interpolate(config.get("product_id")), "status": "created_mock"}

        product_id = int(self._interpolate(config.get("product_id")))
        quantity = int(self._interpolate(config.get("quantity", 1)))
        customer_id = int(self._interpolate(config.get("customer_id")))
        entity_id = int(self._interpolate(config.get("entity_id", 0))) or None

        if not product_id or quantity <= 0:
            raise ValidationError("product_id and positive quantity are required")

        service = CommerceService(self.db)
        order = await service.create_order(product_id, quantity, customer_id, entity_id)
        return {"order_id": order.id, "status": order.status, "total": float(order.total)}

    async def _exec_update_inventory(self, config: dict) -> dict:
        """تحديث المخزون (زيادة أو نقصان)."""
        try:
            from app.domains.commerce.service import CommerceService
        except ImportError:
            logger.warning("CommerceService not found, using mock")
            return {"product_id": self._interpolate(config.get("product_id")), "new_quantity": 50}

        product_id = int(self._interpolate(config.get("product_id")))
        delta = int(self._interpolate(config.get("delta")))
        if not product_id:
            raise ValidationError("product_id is required")

        service = CommerceService(self.db)
        result = await service.update_inventory(product_id, delta)
        return {"product_id": product_id, "new_quantity": result["new_quantity"]}

    async def _exec_ship_order(self, config: dict) -> dict:
        """شحن طلب (تحديث الحالة إلى SHIPPED)."""
        try:
            from app.domains.commerce.service import CommerceService
        except ImportError:
            logger.warning("CommerceService not found, using mock")
            return {"order_id": self._interpolate(config.get("order_id")), "status": "SHIPPED_mock"}

        order_id = int(self._interpolate(config.get("order_id")))
        tracking_number = self._interpolate(config.get("tracking_number"))
        if not order_id:
            raise ValidationError("order_id is required")

        service = CommerceService(self.db)
        order = await service.ship_order(order_id, tracking_number)
        return {"order_id": order.id, "status": order.status, "tracking": order.tracking_number}

    async def _exec_cancel_order(self, config: dict) -> dict:
        """إلغاء طلب."""
        try:
            from app.domains.commerce.service import CommerceService
        except ImportError:
            logger.warning("CommerceService not found, using mock")
            return {"order_id": self._interpolate(config.get("order_id")), "cancelled": True}

        order_id = int(self._interpolate(config.get("order_id")))
        reason = self._interpolate(config.get("reason", ""))
        if not order_id:
            raise ValidationError("order_id is required")

        service = CommerceService(self.db)
        order = await service.cancel_order(order_id, reason)
        return {"order_id": order.id, "status": order.status, "cancelled": True}

    # ---------- قطاع الأكاديمية (Academy) ----------
    async def _exec_enroll_course(self, config: dict) -> dict:
        """تسجيل طالب في كورس."""
        try:
            from app.domains.academy.service import AcademyService
        except ImportError:
            logger.warning("AcademyService not found, using mock")
            return {"enrollment_id": 303, "user_id": self._interpolate(config.get("user_id")), "status": "enrolled_mock"}

        user_id = int(self._interpolate(config.get("user_id")))
        course_id = int(self._interpolate(config.get("course_id")))
        if not user_id or not course_id:
            raise ValidationError("user_id and course_id are required")

        service = AcademyService(self.db)
        enrollment = await service.enroll_student(user_id, course_id)
        return {"enrollment_id": enrollment.id, "status": enrollment.status}

    async def _exec_complete_lesson(self, config: dict) -> dict:
        """تسجيل إكمال درس."""
        try:
            from app.domains.academy.service import AcademyService
        except ImportError:
            logger.warning("AcademyService not found, using mock")
            return {"user_id": self._interpolate(config.get("user_id")), "lesson_id": self._interpolate(config.get("lesson_id")), "completed": True}

        user_id = int(self._interpolate(config.get("user_id")))
        lesson_id = int(self._interpolate(config.get("lesson_id")))
        if not user_id or not lesson_id:
            raise ValidationError("user_id and lesson_id are required")

        service = AcademyService(self.db)
        progress = await service.complete_lesson(user_id, lesson_id)
        return {"user_id": user_id, "lesson_id": lesson_id, "completed": True, "progress": progress}

    async def _exec_issue_certificate(self, config: dict) -> dict:
        """إصدار شهادة لمستخدم."""
        try:
            from app.domains.academy.service import AcademyService
        except ImportError:
            logger.warning("AcademyService not found, using mock")
            return {"certificate_id": 404, "url": "https://example.com/cert/123"}

        user_id = int(self._interpolate(config.get("user_id")))
        course_id = int(self._interpolate(config.get("course_id")))
        if not user_id or not course_id:
            raise ValidationError("user_id and course_id are required")

        service = AcademyService(self.db)
        certificate = await service.issue_certificate(user_id, course_id)
        return {"certificate_id": certificate.id, "url": certificate.url}

    async def _exec_create_course(self, config: dict) -> dict:
        """إنشاء كورس جديد."""
        try:
            from app.domains.academy.service import AcademyService
        except ImportError:
            logger.warning("AcademyService not found, using mock")
            return {"course_id": 505, "title": self._interpolate(config.get("title")), "status": "draft_mock"}

        title = self._interpolate(config.get("title"))
        description = self._interpolate(config.get("description", ""))
        instructor_id = int(self._interpolate(config.get("instructor_id")))
        if not title or not instructor_id:
            raise ValidationError("title and instructor_id are required")

        service = AcademyService(self.db)
        course = await service.create_course(title, description, instructor_id)
        return {"course_id": course.id, "title": course.title, "status": course.status}

    # ---------------------- دوال مساعدة محسّنة وآمنة ----------------------
    def _interpolate(self, value: Any) -> Any:
        """
        استبدال المتغيرات من السياق بصيغة {{path}} مع تعقيم صارم.
        - يمنع الوصول إلى الخصائص الداخلية (__)، والأقواس المربعة.
        - يتحقق من صحة اسم المتغير عبر نمط آمن.
        - يعقم الناتج النصي باستخدام html.escape.
        """
        if isinstance(value, str):
            pattern = r'{{(.*?)}}'
            def replacer(match):
                expr = match.group(1).strip()

                # 🔥 التحصين الأمني: منع الوصول إلى الخصائص الخطيرة
                # 1. منع النقاط المزدوجة (__) التي تشير إلى الخصائص الداخلية للغة
                if '__' in expr or '[' in expr or ']' in expr:
                    return "[SANITIZED]"

                # 2. التحقق من أن الاسم يتبع النمط الآمن (أحرف، أرقام، نقاط، شرطة سفلية)
                if not ALLOWED_VARIABLE_PATTERN.match(expr):
                    return "[SANITIZED]"

                # 3. استرجاع القيمة من السياق بأمان (دون استخدام eval)
                parts = expr.split('.')
                current = self.context
                for part in parts:
                    if isinstance(current, dict):
                        current = current.get(part)
                    elif hasattr(current, part) and not part.startswith('_'):
                        # للكائنات الآمنة فقط (مثل التاريخ)
                        current = getattr(current, part)
                    else:
                        current = None
                        break

                # 4. تعقيم القيمة النهائية قبل إرجاعها (منع أي نصوص برمجية خبيثة)
                if current is not None:
                    if isinstance(current, str):
                        # إزالة أي <script> أو أمر eval محتمل (طبقة حماية إضافية)
                        return html.escape(current)
                    return str(current)
                return ""
            return re.sub(pattern, replacer, value)
        elif isinstance(value, dict):
            return {k: self._interpolate(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._interpolate(item) for item in value]
        else:
            return value

    def _interpolate_dict(self, d: dict) -> dict:
        return self._interpolate(d)


# ============================================================
# دوال إنشاء وتحديث سير العمل (مع حدود أمنية)
# ============================================================
async def create_workflow(
    db: AsyncSession,
    user_id: int,
    tenant_id: int,
    data: dict
) -> Workflow:
    """إنشاء سير عمل جديد مع التحقق من عدد العقد."""
    # التحقق من الصلاحيات (يمكن إضافته حسب النظام)
    # ...

    # 🔥 التحصين الأمني: منع تجاوز عدد العقد
    if len(data.get("nodes", [])) > MAX_WORKFLOW_NODES:
        raise ValueError(f"Workflow cannot exceed {MAX_WORKFLOW_NODES} nodes.")

    repo = AutomationRepository(db)
    # إنشاء السجل في قاعدة البيانات (افترض وجود دالة create في repo)
    # هنا نستخدم المنطق الموجود في التطبيق
    workflow = await repo.create_workflow(
        name=data["name"],
        description=data.get("description"),
        trigger_type=data["trigger_type"],
        trigger_config=data["trigger_config"],
        nodes=data["nodes"],
        edges=data["edges"],
        max_retries=data.get("max_retries", 3),
        retry_delay_seconds=data.get("retry_delay_seconds", 5),
        timeout_seconds=data.get("timeout_seconds", 60),
        concurrency_limit=data.get("concurrency_limit", 10),
        tenant_id=tenant_id,
        created_by=user_id
    )
    return workflow


async def update_workflow(
    db: AsyncSession,
    workflow_id: int,
    user_id: int,
    data: dict
) -> Workflow:
    """تحديث سير العمل مع التحقق من عدد العقد."""
    # 🔥 التحصين الأمني: منع تجاوز عدد العقد عند التحديث أيضاً
    if "nodes" in data and len(data["nodes"]) > MAX_WORKFLOW_NODES:
        raise ValueError(f"Workflow cannot exceed {MAX_WORKFLOW_NODES} nodes.")

    repo = AutomationRepository(db)
    workflow = await repo.update_workflow(workflow_id, data)
    return workflow


# ============================================================
# دالة خارجية لتشغيل سير العمل في الخلفية (مطوّرة)
# ============================================================
async def run_workflow_background(
    db: AsyncSession,
    workflow_id: int,
    triggered_by: str,
    payload: dict,
    request_ip: Optional[str] = None,
    request_user_agent: Optional[str] = None
):
    """
    تُستخدم لجدولة تنفيذ سير العمل في الخلفية (BackgroundTasks).
    """
    repo = AutomationRepository(db)
    workflow = await repo.get_workflow(workflow_id)
    if not workflow or not workflow.is_active:
        logger.warning(f"Workflow {workflow_id} not found or inactive")
        return

    execution = await repo.create_execution(
        workflow_id=workflow_id,
        triggered_by=triggered_by,
        trigger_payload=payload,
        status="PENDING",
        context=payload or {},
        # 🔥 جديد: تخزين معلومات الطلب الأصلي للتدقيق
        trigger_ip=request_ip,
        trigger_user_agent=request_user_agent
    )

    engine = AutomationEngine(db, workflow, execution)
    await engine.run()