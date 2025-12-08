#payments/jobs.py
import datetime
from datetime import timedelta
from telegram.ext import JobQueue
from database import db

async def auto_cancel_old_payments(context):
    cutoff_time = datetime.datetime.now() - timedelta(minutes=10)
    result = db.execute_query("""
        UPDATE vip_payments 
        SET status = 'canceled', expires_at = NOW() 
        WHERE status = 'pending' AND created_at < %s
    """, (cutoff_time,))
    if isinstance(result, int) and result > 0:
        print(f"✅ Автоматически отменено {result} старых платежей.")

def setup_jobs(job_queue: JobQueue):
    job_queue.run_repeating(auto_cancel_old_payments, interval=300, first=10)