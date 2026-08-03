"""Adapter registry. Add new government-record adapters here."""

from __future__ import annotations

from typing import Any

from app.source_adapters.base import SourceDescriptor
from app.source_adapters.csv_adapter import CSVUploadAdapter
from app.source_adapters.demo_adapter import DemoDataAdapter
from app.source_adapters.json_api_adapter import GenericJSONAPIAdapter
from app.source_adapters.pdf_adapter import PDFUploadAdapter
from app.source_adapters.rss_adapter import GenericRSSAdapter

ADAPTER_CLASSES = {
    CSVUploadAdapter.descriptor.source_key: CSVUploadAdapter,
    PDFUploadAdapter.descriptor.source_key: PDFUploadAdapter,
    GenericJSONAPIAdapter.descriptor.source_key: GenericJSONAPIAdapter,
    GenericRSSAdapter.descriptor.source_key: GenericRSSAdapter,
    DemoDataAdapter.descriptor.source_key: DemoDataAdapter,
}


def list_descriptors() -> list[SourceDescriptor]:
    return [cls.descriptor for cls in ADAPTER_CLASSES.values()]


def get_adapter(source_key: str, **kwargs: Any):
    cls = ADAPTER_CLASSES.get(source_key)
    if cls is None:
        raise KeyError(f"Unknown source adapter: {source_key}")
    return cls(**kwargs)


def descriptor_to_dict(d: SourceDescriptor) -> dict:
    return {
        "source_key": d.source_key,
        "source_name": d.source_name,
        "source_type": d.source_type.value,
        "access_method": d.access_method.value,
        "jurisdiction": d.jurisdiction,
        "supported_record_types": d.supported_record_types,
        "terms_notes": d.terms_notes,
        "attribution": d.attribution,
        "requires_auth": d.requires_auth,
        "rate_limit_per_minute": d.rate_limit_per_minute,
    }
