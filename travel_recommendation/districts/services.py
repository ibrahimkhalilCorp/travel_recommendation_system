import aiohttp
import asyncio
from django.core.cache import cache
import json
import os
from django.conf import settings
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from asyncio import Semaphore

logger = logging.getLogger(__name__)

METRICS_CACHE_KEY = 'district_metrics'
MAX_CONCURRENT_REQUESTS = 2 

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

async def fetch_weather_data(session, latitude, longitude, semaphore):
    cache_key = f"weather_{latitude}_{longitude}"
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.debug(f"Returning cached weather data for {latitude}, {longitude}")
        return cached_data

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m",
        "timezone": "Asia/Dhaka",
        "forecast_days": 7
    }
    retries = 3
    for attempt in range(retries):
        async with semaphore:  # Limit concurrent requests
            try:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    response.raise_for_status()
                    data = await response.json()
                    cache.set(cache_key, data, timeout=86400)  # Cache for 24 hours
                    return data
            except aiohttp.ClientResponseError as e:
                if e.status == 429 and attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"429 error for {latitude}, {longitude}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Failed to fetch weather data for {latitude}, {longitude}: {e}")
                return None
            except Exception as e:
                logger.error(f"Failed to fetch weather data for {latitude}, {longitude}: {e}")
                return None
    return None

async def fetch_air_quality_data(session, latitude, longitude, semaphore):
    cache_key = f"air_quality_{latitude}_{longitude}"
    cached_data = cache.get(cache_key)
    if cached_data:
        logger.debug(f"Returning cached air quality data for {latitude}, {longitude}")
        return cached_data

    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "pm2_5",
        "timezone": "Asia/Dhaka",
        "forecast_days": 7
    }
    retries = 3
    for attempt in range(retries):
        async with semaphore:
            try:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if 'hourly' not in data or 'pm2_5' not in data['hourly']:
                        logger.warning(f"No valid PM2.5 data for {latitude}, {longitude}")
                        return None
                    cache.set(cache_key, data, timeout=86400)
                    return data
            except aiohttp.ClientResponseError as e:
                if e.status == 429 and attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"429 error for {latitude}, {longitude}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Failed to fetch air quality data for {latitude}, {longitude}: {e}")
                return None
            except Exception as e:
                logger.error(f"Failed to fetch air quality data for {latitude}, {longitude}: {e}")
                return None
    return None

def get_avg_temperature_at_2pm(data):
    if not data or 'hourly' not in data or 'temperature_2m' not in data['hourly']:
        return 35.0
    temperatures = [temp for time, temp in zip(data['hourly']['time'], data['hourly']['temperature_2m'])
                    if time.endswith("14:00") and temp is not None]
    return sum(temperatures) / len(temperatures) if temperatures else 35.0

def get_avg_pm25_at_2pm(data):
    if not data or 'hourly' not in data or 'pm2_5' not in data['hourly']:
        return 50.0
    pm25_values = [pm25 for time, pm25 in zip(data['hourly']['time'], data['hourly']['pm2_5'])
                   if time.endswith("14:00") and pm25 is not None]
    return sum(pm25_values) / len(pm25_values) if pm25_values else 50.0

def get_temperature_at_2pm(data, travel_date):
    if not data or 'hourly' not in data or 'temperature_2m' not in data['hourly']:
        return None
    target_date = travel_date.strftime("%Y-%m-%d")
    target_time = f"{target_date}T14:00"
    if target_time not in data['hourly']['time']:
        return None
    index = data['hourly']['time'].index(target_time)
    temp = data['hourly']['temperature_2m'][index]
    return temp if temp is not None else None

def get_pm25_at_2pm(data, travel_date):
    if not data or 'hourly' not in data or 'pm2_5' not in data['hourly']:
        return 50.0
    target_date = travel_date.strftime("%Y-%m-%d")
    target_time = f"{target_date}T14:00"
    if target_time not in data['hourly']['time']:
        return 50.0
    index = data['hourly']['time'].index(target_time)
    pm25 = data['hourly']['pm2_5'][index]
    return pm25 if pm25 is not None else 50.0

async def fetch_district_metrics(session, district, semaphore):
    weather_data = await fetch_weather_data(session, district['latitude'], district['longitude'], semaphore)
    air_quality_data = await fetch_air_quality_data(session, district['latitude'], district['longitude'], semaphore)
    avg_temp = get_avg_temperature_at_2pm(weather_data)
    avg_pm25 = get_avg_pm25_at_2pm(air_quality_data)
    return {
        'name': district['name'],
        'latitude': district['latitude'],
        'longitude': district['longitude'],
        'avg_temperature': round(avg_temp, 2),
        'avg_pm25': round(avg_pm25, 2)
    }

async def fetch_travel_data(session, district, travel_date, semaphore):
    weather_data = await fetch_weather_data(session, district['latitude'], district['longitude'], semaphore)
    air_quality_data = await fetch_air_quality_data(session, district['latitude'], district['longitude'], semaphore)
    temp = get_temperature_at_2pm(weather_data, travel_date)
    pm25 = get_pm25_at_2pm(air_quality_data, travel_date)
    return {
        'temp': temp if temp is not None else 35.0,
        'pm25': pm25 if pm25 is not None else 50.0
    }

async def fetch_all_district_metrics(districts):
    semaphore = Semaphore(MAX_CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_district_metrics(session, district, semaphore) for district in districts]
        return await asyncio.gather(*tasks)

async def fetch_travel_metrics(current_district, destination_district, travel_date):
    semaphore = Semaphore(MAX_CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_travel_data(session, current_district, travel_date, semaphore),
            fetch_travel_data(session, destination_district, travel_date, semaphore)
        ]
        return await asyncio.gather(*tasks)

def run_async_fetch_districts(districts):
    return asyncio.run(fetch_all_district_metrics(districts))

def run_async_fetch_travel(current_district, destination_district, travel_date):
    return asyncio.run(fetch_travel_metrics(current_district, destination_district, travel_date))

def get_district_metrics():
    cached_metrics = cache.get(METRICS_CACHE_KEY)
    if cached_metrics:
        logger.info("Returning cached district metrics")
        return cached_metrics
    
    districts = fetch_districts_data()
    if not districts:
        return []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        metrics = executor.submit(run_async_fetch_districts, districts).result()
    
    cache.set(METRICS_CACHE_KEY, metrics, timeout=86400)
    logger.info("Precomputed metrics stored in cache")
    return metrics