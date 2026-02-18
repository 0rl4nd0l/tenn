import os
from celery import Celery
celery=Celery('financial_engine', broker=os.environ['CELERY_BROKER_URL'], backend=os.environ['CELERY_RESULT_BACKEND'])
celery.conf.update(task_serializer='json',accept_content=['json'],result_serializer='json')
