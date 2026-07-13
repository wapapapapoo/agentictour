import asyncio
import logging

from database import SessionLocal
from services.reminder_service import run_periodic_agent_jobs, scan_due_reminders

logger = logging.getLogger(__name__)


async def reminder_loop() -> None:
    while True:
        db = SessionLocal()
        try:
            await asyncio.to_thread(scan_due_reminders, db)
            await asyncio.to_thread(run_periodic_agent_jobs, db)
        except Exception:
            db.rollback()
            logger.exception("reminder scan failed")
        finally:
            db.close()
        await asyncio.sleep(60)
