"""Job board connectors for Role Radar."""

from role_radar.connectors.base import BaseConnector
from role_radar.connectors.greenhouse import GreenhouseConnector
from role_radar.connectors.lever import LeverConnector
from role_radar.connectors.smartrecruiters import SmartRecruitersConnector
from role_radar.connectors.generic_html import GenericHTMLConnector
from role_radar.connectors.registry import ConnectorRegistry

__all__ = [
    "BaseConnector",
    "GreenhouseConnector",
    "LeverConnector",
    "SmartRecruitersConnector",
    "GenericHTMLConnector",
    "ConnectorRegistry",
]
