#!/usr/bin/env python3
"""
iDrive e2 Prometheus Exporter - Improved with better logging
"""

import os
import boto3
from prometheus_client import start_http_server, Gauge, Info
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment
ENDPOINT_URL = os.getenv('ENDPOINT_URL', 'https://s3.idrivee2.com')
ACCESS_KEY = os.getenv('ACCESS_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
REGION_NAME = os.getenv('REGION_NAME', 'default')
BUCKETS = os.getenv('BUCKETS', '').split(',')
SCRAPE_INTERVAL = int(os.getenv('SCRAPE_INTERVAL', '300'))  # 5 minutes default

# Validate configuration
logger.info("=" * 60)
logger.info("iDrive e2 Prometheus Exporter Starting...")
logger.info("=" * 60)
logger.info(f"Endpoint: {ENDPOINT_URL}")
logger.info(f"Buckets: {BUCKETS}")
logger.info(f"Scrape interval: {SCRAPE_INTERVAL} seconds")

if not ACCESS_KEY or not SECRET_KEY:
    logger.error("ERROR: ACCESS_KEY and SECRET_KEY must be set!")
    logger.error("Please set these environment variables in CapRover.")
    exit(1)

if not BUCKETS or BUCKETS == ['']:
    logger.error("ERROR: BUCKETS environment variable must be set!")
    logger.error("Example: BUCKETS=bucket1,bucket2,bucket3")
    exit(1)

logger.info(f"Access Key: {ACCESS_KEY[:8]}...{ACCESS_KEY[-4:]}")
logger.info("=" * 60)

# Setup S3 client
try:
    s3 = boto3.client('s3',
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name='eu-west-4',
        config=boto3.session.Config(
            signature_version='s3v4',
            retries={'max_attempts': 3, 'mode': 'standard'}
        )
    )
    logger.info("✓ S3 client created successfully")
except Exception as e:
    logger.error(f"✗ Failed to create S3 client: {e}")
    exit(1)

# Prometheus metrics
bucket_size = Gauge('idrive_bucket_size_bytes', 
                    'Total size of bucket in bytes', 
                    ['bucket'])
object_count = Gauge('idrive_bucket_object_count', 
                     'Number of objects in bucket', 
                     ['bucket'])
last_modified = Gauge('idrive_bucket_last_modified', 
                      'Timestamp of last modified object', 
                      ['bucket'])
scrape_duration = Gauge('idrive_scrape_duration_seconds',
                        'Time taken to scrape metrics',
                        ['bucket'])
scrape_success = Gauge('idrive_scrape_success',
                       'Whether the last scrape was successful',
                       ['bucket'])
exporter_info = Info('idrive_exporter', 'Exporter information')

# Set exporter info
exporter_info.info({
    'version': '1.0',
    'endpoint': ENDPOINT_URL,
    'buckets': ','.join(BUCKETS)
})

def test_connection():
    """Test S3 connection by listing buckets"""
    try:
        logger.info("Testing connection by listing buckets...")
        response = s3.list_buckets()
        available_buckets = [b['Name'] for b in response.get('Buckets', [])]
        logger.info(f"✓ Connection successful! Found {len(available_buckets)} bucket(s):")
        for bucket in available_buckets:
            logger.info(f"  - {bucket}")
        
        # Check if configured buckets exist
        for bucket in BUCKETS:
            bucket = bucket.strip()
            if bucket and bucket not in available_buckets:
                logger.warning(f"⚠ Bucket '{bucket}' not found in account!")
        
        return True
    except Exception as e:
        logger.error(f"✗ Connection test failed: {e}")
        return False

def collect_bucket_metrics(bucket_name):
    """Collect metrics for a single bucket"""
    bucket_name = bucket_name.strip()
    if not bucket_name:
        return
    
    start_time = time.time()
    logger.info(f"→ Collecting metrics for: {bucket_name}")
    
    try:
        total_size = 0
        total_objects = 0
        latest_modified = 0
        
        # List all objects with pagination
        paginator = s3.get_paginator('list_objects_v2')
        page_count = 0
        
        for page in paginator.paginate(Bucket=bucket_name):
            page_count += 1
            
            if 'Contents' in page:
                for obj in page['Contents']:
                    total_size += obj['Size']
                    total_objects += 1
                    
                    # Track latest modification
                    obj_modified = obj['LastModified'].timestamp()
                    if obj_modified > latest_modified:
                        latest_modified = obj_modified
                
                # Log progress every 10 pages
                if page_count % 10 == 0:
                    logger.info(f"  Processing page {page_count}... "
                              f"({total_objects} objects so far)")
        
        # Update metrics
        bucket_size.labels(bucket=bucket_name).set(total_size)
        object_count.labels(bucket=bucket_name).set(total_objects)
        
        if latest_modified > 0:
            last_modified.labels(bucket=bucket_name).set(latest_modified)
            last_mod_str = datetime.fromtimestamp(latest_modified).strftime('%Y-%m-%d %H:%M:%S')
        else:
            last_mod_str = "N/A"
        
        scrape_success.labels(bucket=bucket_name).set(1)
        
        duration = time.time() - start_time
        scrape_duration.labels(bucket=bucket_name).set(duration)
        
        logger.info(f"✓ {bucket_name}:")
        logger.info(f"  - Objects: {total_objects:,}")
        logger.info(f"  - Size: {total_size / (1024**3):.2f} GB")
        logger.info(f"  - Last modified: {last_mod_str}")
        logger.info(f"  - Collection time: {duration:.2f}s")
        
    except s3.exceptions.NoSuchBucket:
        logger.error(f"✗ Bucket '{bucket_name}' does not exist!")
        scrape_success.labels(bucket=bucket_name).set(0)
    except Exception as e:
        logger.error(f"✗ Error collecting metrics for {bucket_name}: {e}")
        scrape_success.labels(bucket=bucket_name).set(0)

def collect_all_metrics():
    """Collect metrics for all configured buckets"""
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Starting metrics collection at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    for bucket in BUCKETS:
        collect_bucket_metrics(bucket)
    
    total_duration = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"Collection completed in {total_duration:.2f}s")
    logger.info(f"Next collection in {SCRAPE_INTERVAL} seconds")
    logger.info("=" * 60)

def main():
    # Test connection first
    if not test_connection():
        logger.error("Initial connection test failed. Please check your credentials.")
        logger.error("Exiting...")
        exit(1)
    
    # Start Prometheus HTTP server
    try:
        start_http_server(8000)
        logger.info("")
        logger.info("✓ Prometheus exporter started on port 8000")
        logger.info("  Metrics available at: http://localhost:8000/metrics")
        logger.info("")
    except Exception as e:
        logger.error(f"Failed to start HTTP server: {e}")
        exit(1)
    
    # Initial collection
    collect_all_metrics()
    
    # Keep running and collect periodically
    while True:
        try:
            time.sleep(SCRAPE_INTERVAL)
            collect_all_metrics()
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(60)  # Wait a bit before retrying

if __name__ == '__main__':
    main()