import requests
from datetime import datetime, timedelta
from django.core.cache import cache
import json
import os
from django.conf import settings
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

def fetch_districts_data():
    json_path = os.path.join(settings.BASE_DIR, 'data', 'bd-districts.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        districts = [
            {
                'name': district['name'],
                'latitude': float(district['lat']),
                'longitude': float(district['long'])
            }
            for district in data.get('districts', [])
        ]
        logger.info(f"Loaded {len(districts)} districts from JSON")
        return districts
    except Exception as e:
        logger.error(f"Error loading districts data: {e}")
        return []