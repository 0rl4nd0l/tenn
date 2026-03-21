import os
from celery import Celery
celery=Celery('financial_engine', broker=os.environ['CELERY_BROKER_URL'], backend=os.environ['CELERY_RESULT_BACKEND'])
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    task_soft_time_limit=900,   # 15 min soft limit: task gets SoftTimeLimitExceeded
    task_time_limit=960,        # 16 min hard limit: worker process killed
    result_expires=86400,       # results expire after 24h
)
