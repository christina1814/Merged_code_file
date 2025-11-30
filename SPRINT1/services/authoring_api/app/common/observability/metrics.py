# app/common/observability/metrics.py
from typing import Optional, Dict
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST


# Autosave-specific metrics
autosave_success_counter = Counter(
    'authoring_autosave_success_total',
    'Total successful autosaves',
    ['tenant_id', 'status']
)

autosave_failure_counter = Counter(
    'authoring_autosave_failure_total',
    'Total failed autosaves',
    ['tenant_id', 'error_code']
)

conflict_events_counter = Counter(
    'authoring_conflict_events_total',
    'Total version conflicts',
    ['tenant_id']
)

autosave_latency_histogram = Histogram(
    'authoring_autosave_latency_ms',
    'Autosave latency',
    ['tenant_id', 'status'],
    buckets=(10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)
)

# Generic metrics (usable by ALL features)
api_requests_counter = Counter(
    'authoring_api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

api_latency_histogram = Histogram(
    'authoring_api_latency_ms',
    'API request latency',
    ['endpoint', 'method'],
    buckets=(10, 25, 50, 100, 250, 500, 1000, 2500, 5000)
)

db_operation_latency_histogram = Histogram(
    'authoring_db_operation_latency_ms',
    'Database operation latency',
    ['operation', 'tenant_id'],
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2500)
)

blob_operation_counter = Counter(
    'authoring_blob_operations_total',
    'Total blob operations',
    ['operation', 'status', 'tenant_id']  # ADDED tenant_id
)

blob_fetch_latency_histogram = Histogram(
    'authoring_blob_fetch_latency_ms',
    'Blob fetch operation latency',
    ['tenant_id'],
    buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000)
)

blob_save_latency_histogram = Histogram(
    'authoring_blob_save_latency_ms',
    'Blob save operation latency',
    ['tenant_id'],
    buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000)
)

blob_delete_latency_histogram = Histogram(
    'authoring_blob_delete_latency_ms',
    'Blob delete operation latency',
    ['tenant_id'],
    buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000)
)

upload_latency_histogram = Histogram(
    'authoring_upload_latency_ms',
    'Upload SAS generation latency',
    ['tenant_id'],
    buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000)
)


class MetricsService:
    """Generic metrics service for all features"""
    
    def increment_counter(
        self, 
        name: str, 
        value: int = 1, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment any counter by name"""
        labels = labels or {}
        
        if name == "autosave_success_total":
            autosave_success_counter.labels(**labels).inc(value)
        elif name == "autosave_failure_total":
            autosave_failure_counter.labels(**labels).inc(value)
        elif name == "conflict_events_total":
            conflict_events_counter.labels(**labels).inc(value)
        elif name == "api_requests_total":
            api_requests_counter.labels(**labels).inc(value)
        elif name == "blob_operations_total":
            blob_operation_counter.labels(**labels).inc(value)
    
    def record_histogram(
        self, 
        name: str, 
        value: float, 
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record histogram value for any metric"""
        labels = labels or {}
        
        if name == "autosave_latency_ms":
            autosave_latency_histogram.labels(**labels).observe(value)
        elif name == "db_operation_latency_ms":
            db_operation_latency_histogram.labels(**labels).observe(value)
        elif name == "blob_operation_latency_ms":
            # Legacy support - map to specific histograms
            operation = labels.get('operation', 'fetch')
            tenant_id = labels.get('tenant_id', 'unknown')
            if operation == 'fetch':
                blob_fetch_latency_histogram.labels(tenant_id=tenant_id).observe(value)
            elif operation == 'save':
                blob_save_latency_histogram.labels(tenant_id=tenant_id).observe(value)
            elif operation == 'delete':
                blob_delete_latency_histogram.labels(tenant_id=tenant_id).observe(value)
        elif name == "blob_fetch_latency_ms":
            blob_fetch_latency_histogram.labels(**labels).observe(value)
        elif name == "blob_save_latency_ms":
            blob_save_latency_histogram.labels(**labels).observe(value)
        elif name == "blob_delete_latency_ms":
            blob_delete_latency_histogram.labels(**labels).observe(value)
        elif name == "upload_latency_ms":
            upload_latency_histogram.labels(**labels).observe(value)
        elif name == "api_latency_ms":
            api_latency_histogram.labels(**labels).observe(value)
    
    def get_metrics_text(self) -> str:
        """Export all metrics in Prometheus format"""
        return generate_latest().decode('utf-8')
    
    def get_content_type(self) -> str:
        """Get Prometheus content type"""
        return CONTENT_TYPE_LATEST


# Global instance
metrics = MetricsService()


# ============================================================================
# STANDALONE HELPER FUNCTIONS (for base services to use directly)
# ============================================================================

def increment_counter(name: str, labels: Optional[Dict[str, str]] = None, value: int = 1) -> None:
    """
    Standalone function to increment counters.
    Used by base services (fetch, save, upload, delete).
    """
    metrics.increment_counter(name, value, labels)


def record_histogram(name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
    """
    Standalone function to record histograms.
    Used by base services (fetch, save, upload, delete).
    """
    metrics.record_histogram(name, value, labels)


def get_metrics_text() -> str:
    """
    Standalone function to get metrics text.
    Used by main.py /metrics endpoint.
    """
    return metrics.get_metrics_text()