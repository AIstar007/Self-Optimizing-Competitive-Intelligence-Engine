"""Market and competitive analysis for intelligence gathering."""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from enum import Enum

logger = logging.getLogger(__name__)


class MarketSegmentType(Enum):
    """Types of market segments."""

    GEOGRAPHIC = "geographic"
    DEMOGRAPHIC = "demographic"
    PSYCHOGRAPHIC = "psychographic"
    BEHAVIORAL = "behavioral"
    PRODUCT_BASED = "product_based"
    VALUE_BASED = "value_based"


class CompetitivePosition(Enum):
    """Competitive positions in market."""

    LEADER = "leader"
    CHALLENGER = "challenger"
    FOLLOWER = "follower"
    NICHE = "niche"


@dataclass
class MarketSegment:
    """Represents a market segment."""

    segment_id: str
    segment_type: MarketSegmentType
    name: str
    size: float
    growth_rate: float
    characteristics: Dict = field(default_factory=dict)
    competitors: List[str] = field(default_factory=list)
    market_share: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CompetitorProfile:
    """Represents a competitor profile."""

    competitor_id: str
    name: str
    position: CompetitivePosition
    market_share: float
    financial_metrics: Dict = field(default_factory=dict)
    product_portfolio: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recent_activities: List[Dict] = field(default_factory=list)
    threat_level: float = 0.0
    updated_at: datetime = field(default_factory=datetime.now)


class MarketSegmentation:
    """Segments and analyzes market."""

    def __init__(self):
        """Initialize segmentation."""
        self.segments: Dict[str, MarketSegment] = {}
        self.total_market_size: float = 0.0
        self.segmentation_history: List[Dict] = []

    def create_segment(
        self,
        segment_id: str,
        segment_type: MarketSegmentType,
        name: str,
        size: float,
        growth_rate: float,
    ) -> MarketSegment:
        """Create a market segment."""
        segment = MarketSegment(
            segment_id=segment_id,
            segment_type=segment_type,
            name=name,
            size=size,
            growth_rate=growth_rate,
        )
        self.segments[segment_id] = segment
        self.total_market_size += size

        logger.info(f"Created segment: {name} (size: {size})")

        return segment

    def add_competitor_to_segment(
        self, segment_id: str, competitor_id: str, market_share: float
    ) -> None:
        """Add competitor to segment."""
        if segment_id in self.segments:
            segment = self.segments[segment_id]
            segment.competitors.append(competitor_id)
            segment.market_share[competitor_id] = market_share

    def analyze_segment_dynamics(self, segment_id: str) -> Dict:
        """Analyze dynamics within a segment."""
        if segment_id not in self.segments:
            return {}

        segment = self.segments[segment_id]
        competitors_count = len(segment.competitors)

        # Concentration analysis
        hhi = sum(share ** 2 for share in segment.market_share.values())

        return {
            "segment_id": segment_id,
            "segment_name": segment.name,
            "size": segment.size,
            "growth_rate": segment.growth_rate,
            "competitor_count": competitors_count,
            "herfindahl_index": hhi,
            "is_concentrated": hhi > 0.25,
            "market_share_distribution": segment.market_share,
        }

    def get_segment_opportunities(self) -> List[Dict]:
        """Identify growth opportunities in segments."""
        opportunities = []

        for segment in self.segments.values():
            if segment.growth_rate > 0.15:  # High growth threshold
                opportunities.append(
                    {
                        "segment_id": segment.segment_id,
                        "segment_name": segment.name,
                        "growth_rate": segment.growth_rate,
                        "size": segment.size,
                        "opportunity_score": segment.size * segment.growth_rate,
                    }
                )

        return sorted(
            opportunities, key=lambda x: x["opportunity_score"], reverse=True
        )


class CompetitorAnalysis:
    """Analyzes competitive landscape."""

    def __init__(self):
        """Initialize analysis."""
        self.competitors: Dict[str, CompetitorProfile] = {}
        self.competitive_moves: List[Dict] = []
        self.positioning_map: Dict = {}

    def register_competitor(
        self,
        competitor_id: str,
        name: str,
        market_share: float,
        position: CompetitivePosition,
    ) -> CompetitorProfile:
        """Register a competitor."""
        profile = CompetitorProfile(
            competitor_id=competitor_id,
            name=name,
            market_share=market_share,
            position=position,
        )
        self.competitors[competitor_id] = profile

        logger.info(f"Registered competitor: {name} ({position.value})")

        return profile

    def update_competitor_metrics(
        self, competitor_id: str, metrics: Dict[str, float]
    ) -> None:
        """Update competitor financial metrics."""
        if competitor_id in self.competitors:
            self.competitors[competitor_id].financial_metrics.update(metrics)
            self.competitors[competitor_id].updated_at = datetime.now()

    def record_competitive_move(
        self, competitor_id: str, move_type: str, description: str, impact: float
    ) -> None:
        """Record competitive move."""
        move = {
            "competitor_id": competitor_id,
            "move_type": move_type,
            "description": description,
            "impact": impact,
            "timestamp": datetime.now().isoformat(),
        }
        self.competitive_moves.append(move)

        # Update threat level
        if competitor_id in self.competitors:
            competitor = self.competitors[competitor_id]
            competitor.recent_activities.append(move)
            competitor.threat_level = self._calculate_threat_level(competitor_id)

    def analyze_competitive_intensity(self) -> Dict:
        """Analyze overall competitive intensity."""
        if not self.competitors:
            return {"intensity": 0.0, "description": "No competitors analyzed"}

        market_shares = [c.market_share for c in self.competitors.values()]

        # HHI (Herfindahl Index) for market concentration
        hhi = sum(share ** 2 for share in market_shares)

        # Competitive intensity: inverse of concentration
        # Higher HHI = more concentrated = less intense
        intensity = 1.0 - (hhi / 10000.0)  # Normalize to [0, 1]

        # Average threat level
        avg_threat = np.mean(
            [c.threat_level for c in self.competitors.values()]
        )

        return {
            "herfindahl_index": hhi,
            "intensity_score": intensity,
            "competitor_count": len(self.competitors),
            "avg_threat_level": avg_threat,
            "market_leader": max(
                self.competitors.values(),
                key=lambda x: x.market_share,
                default=None,
            ).name
            if self.competitors
            else None,
        }

    def map_competitive_positioning(self, axis_x: str, axis_y: str) -> Dict:
        """Map competitors on positioning matrix."""
        positioning = {}

        for competitor in self.competitors.values():
            x_value = competitor.financial_metrics.get(axis_x, 0.0)
            y_value = competitor.financial_metrics.get(axis_y, 0.0)

            positioning[competitor.competitor_id] = {
                "name": competitor.name,
                "position": competitor.position.value,
                axis_x: x_value,
                axis_y: y_value,
            }

        self.positioning_map = {
            "axis_x": axis_x,
            "axis_y": axis_y,
            "competitors": positioning,
        }

        return self.positioning_map

    def _calculate_threat_level(self, competitor_id: str) -> float:
        """Calculate threat level for competitor."""
        if competitor_id not in self.competitors:
            return 0.0

        competitor = self.competitors[competitor_id]

        # Factors in threat calculation
        market_share_factor = competitor.market_share
        position_factor = {
            CompetitivePosition.LEADER: 1.0,
            CompetitivePosition.CHALLENGER: 0.8,
            CompetitivePosition.FOLLOWER: 0.5,
            CompetitivePosition.NICHE: 0.3,
        }.get(competitor.position, 0.5)

        # Recent activity factor
        recent_moves = len(competitor.recent_activities[-6:])
        activity_factor = min(recent_moves / 3.0, 1.0)  # Normalize to [0, 1]

        threat_level = (
            market_share_factor * 0.5 + position_factor * 0.3 + activity_factor * 0.2
        )

        return min(threat_level, 1.0)


class MarketShareCalculator:
    """Calculates and analyzes market share."""

    def __init__(self):
        """Initialize calculator."""
        self.market_share_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self.market_size_history: List[Tuple[datetime, float]] = []

    def record_market_share(
        self, competitor_id: str, market_share: float, timestamp: datetime = None
    ) -> None:
        """Record market share for competitor."""
        if timestamp is None:
            timestamp = datetime.now()

        if competitor_id not in self.market_share_history:
            self.market_share_history[competitor_id] = []

        self.market_share_history[competitor_id].append((timestamp, market_share))

    def record_market_size(self, size: float, timestamp: datetime = None) -> None:
        """Record total market size."""
        if timestamp is None:
            timestamp = datetime.now()

        self.market_size_history.append((timestamp, size))

    def calculate_share_change(self, competitor_id: str, periods: int = 1) -> float:
        """Calculate market share change over periods."""
        if competitor_id not in self.market_share_history:
            return 0.0

        history = self.market_share_history[competitor_id]
        if len(history) < periods + 1:
            return 0.0

        current = history[-1][1]
        previous = history[-periods - 1][1]

        return current - previous

    def calculate_share_growth_rate(
        self, competitor_id: str, periods: int = 6
    ) -> float:
        """Calculate market share growth rate."""
        if competitor_id not in self.market_share_history:
            return 0.0

        history = self.market_share_history[competitor_id]
        if len(history) < periods + 1:
            return 0.0

        recent = history[-periods:]
        if len(recent) < 2:
            return 0.0

        shares = [s for _, s in recent]
        growth_rate = (shares[-1] - shares[0]) / shares[0] if shares[0] != 0 else 0.0

        return growth_rate

    def identify_share_gainers(self, threshold: float = 0.02) -> List[str]:
        """Identify competitors gaining market share."""
        gainers = []

        for competitor_id, history in self.market_share_history.items():
            if len(history) >= 2:
                change = history[-1][1] - history[-2][1]
                if change > threshold:
                    gainers.append(competitor_id)

        return gainers

    def identify_share_losers(self, threshold: float = 0.02) -> List[str]:
        """Identify competitors losing market share."""
        losers = []

        for competitor_id, history in self.market_share_history.items():
            if len(history) >= 2:
                change = history[-1][1] - history[-2][1]
                if change < -threshold:
                    losers.append(competitor_id)

        return losers

    def get_market_share_snapshot(self) -> Dict[str, float]:
        """Get current market share snapshot."""
        snapshot = {}

        for competitor_id, history in self.market_share_history.items():
            if history:
                snapshot[competitor_id] = history[-1][1]

        return snapshot


class TrendAnalyzer:
    """Analyzes market trends."""

    def __init__(self):
        """Initialize analyzer."""
        self.trend_history: Dict[str, List[float]] = {}
        self.detected_trends: List[Dict] = []

    def record_trend_data(self, trend_name: str, value: float) -> None:
        """Record trend data point."""
        if trend_name not in self.trend_history:
            self.trend_history[trend_name] = []

        self.trend_history[trend_name].append(value)

    def detect_trend(
        self, trend_name: str, window: int = 6, min_points: int = 3
    ) -> Dict:
        """Detect trend direction and strength."""
        if trend_name not in self.trend_history:
            return {"status": "no_data"}

        data = self.trend_history[trend_name]
        if len(data) < min_points:
            return {"status": "insufficient_data"}

        recent_data = data[-window:] if len(data) >= window else data

        # Calculate trend using linear regression
        x = np.arange(len(recent_data))
        y = np.array(recent_data)

        slope = np.polyfit(x, y, 1)[0]
        correlation = np.corrcoef(x, y)[0, 1]

        # Determine trend direction
        if slope > 0.01:
            direction = "upward"
        elif slope < -0.01:
            direction = "downward"
        else:
            direction = "stable"

        trend_strength = min(abs(slope * 10), 1.0)  # Normalize to [0, 1]

        trend = {
            "trend_name": trend_name,
            "direction": direction,
            "strength": trend_strength,
            "slope": slope,
            "correlation": correlation,
            "recent_average": float(np.mean(recent_data)),
            "detected_at": datetime.now().isoformat(),
        }

        self.detected_trends.append(trend)

        return trend

    def analyze_emerging_trends(self) -> List[Dict]:
        """Analyze emerging trends in market."""
        emerging = []

        for trend_name in self.trend_history:
            trend_data = self.detect_trend(trend_name)

            if (
                trend_data.get("direction") == "upward"
                and trend_data.get("strength", 0) > 0.5
            ):
                emerging.append(
                    {
                        "trend": trend_name,
                        "growth_potential": trend_data.get("strength", 0),
                        "slope": trend_data.get("slope", 0),
                    }
                )

        return sorted(emerging, key=lambda x: x["growth_potential"], reverse=True)

    def compare_trend_trajectories(
        self, trend_names: List[str]
    ) -> Dict[str, List[float]]:
        """Compare trajectories of multiple trends."""
        trajectories = {}

        max_length = max(
            len(self.trend_history.get(name, [])) for name in trend_names
        )

        for trend_name in trend_names:
            data = self.trend_history.get(trend_name, [])

            # Normalize to common length
            if len(data) < max_length:
                data = [data[0]] * (max_length - len(data)) + data

            trajectories[trend_name] = data

        return trajectories
