"""Anomaly detection for identifying unusual patterns and events."""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from enum import Enum

logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    """Types of anomalies."""

    POINT_ANOMALY = "point_anomaly"
    CONTEXTUAL_ANOMALY = "contextual_anomaly"
    COLLECTIVE_ANOMALY = "collective_anomaly"
    TREND_ANOMALY = "trend_anomaly"
    SPIKE = "spike"
    DROP = "drop"


class AnomalySeverity(Enum):
    """Severity levels for anomalies."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Anomaly:
    """Represents an anomaly detection result."""

    anomaly_id: str
    timestamp: datetime
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    value: float
    expected_value: float
    deviation: float
    confidence: float
    context: Dict = None
    description: str = ""

    def get_deviation_percentage(self) -> float:
        """Get deviation as percentage."""
        if self.expected_value == 0:
            return 0.0
        return abs(self.deviation / self.expected_value) * 100


class StatisticalAnomalyDetector:
    """Detects anomalies using statistical methods."""

    def __init__(self, sensitivity: float = 2.0):
        """Initialize detector.

        Args:
            sensitivity: Standard deviations for threshold (higher = less sensitive)
        """
        self.sensitivity = sensitivity
        self.baseline_mean: Optional[float] = None
        self.baseline_std: Optional[float] = None
        self.anomalies: List[Anomaly] = []

    def fit(self, data: List[float]) -> None:
        """Fit detector to baseline data."""
        if len(data) < 2:
            logger.warning("Insufficient data for fitting")
            return

        self.baseline_mean = float(np.mean(data))
        self.baseline_std = float(np.std(data))

        logger.info(
            f"Detector fitted with mean={self.baseline_mean:.2f}, std={self.baseline_std:.2f}"
        )

    def detect(self, data: List[float], entity_id: str = "unknown") -> List[Anomaly]:
        """Detect anomalies in data."""
        if self.baseline_mean is None or self.baseline_std is None:
            logger.warning("Detector not fitted")
            return []

        detected_anomalies = []

        for i, value in enumerate(data):
            z_score = abs((value - self.baseline_mean) / self.baseline_std) if self.baseline_std > 0 else 0.0

            if z_score > self.sensitivity:
                confidence = min(z_score / (self.sensitivity * 2), 1.0)
                deviation = value - self.baseline_mean

                anomaly = Anomaly(
                    anomaly_id=f"{entity_id}_{i}_{datetime.now().timestamp()}",
                    timestamp=datetime.now(),
                    anomaly_type=AnomalyType.POINT_ANOMALY,
                    severity=self._calculate_severity(z_score),
                    value=value,
                    expected_value=self.baseline_mean,
                    deviation=deviation,
                    confidence=confidence,
                    description=f"Z-score: {z_score:.2f}",
                )

                detected_anomalies.append(anomaly)

        self.anomalies.extend(detected_anomalies)
        return detected_anomalies

    def _calculate_severity(self, z_score: float) -> AnomalySeverity:
        """Calculate anomaly severity based on z-score."""
        if z_score >= 4.0:
            return AnomalySeverity.CRITICAL
        elif z_score >= 3.0:
            return AnomalySeverity.HIGH
        elif z_score >= 2.5:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW


class IsolationForestDetector:
    """Detects anomalies using isolation forest algorithm."""

    def __init__(self, contamination: float = 0.1):
        """Initialize detector.

        Args:
            contamination: Expected proportion of anomalies (0-1)
        """
        self.contamination = contamination
        self.training_data: List[List[float]] = []
        self.anomalies: List[Anomaly] = []
        self.anomaly_scores: Dict[int, float] = {}

    def fit(self, features: List[Dict[str, float]]) -> None:
        """Fit detector to training data."""
        if not features:
            logger.warning("No training data provided")
            return

        # Convert features to matrix form
        self.training_data = [
            [v for v in f.values()] for f in features if f
        ]
        logger.info(f"Isolation Forest fitted with {len(self.training_data)} samples")

    def detect(self, features: List[Dict[str, float]], entity_id: str = "unknown") -> List[Anomaly]:
        """Detect anomalies in features."""
        if not self.training_data:
            logger.warning("Detector not fitted")
            return []

        detected_anomalies = []
        threshold = self._calculate_threshold()

        for i, feature_dict in enumerate(features):
            if not feature_dict:
                continue

            feature_vector = [v for v in feature_dict.values()]
            anomaly_score = self._calculate_isolation_score(feature_vector)
            self.anomaly_scores[i] = anomaly_score

            if anomaly_score > threshold:
                severity = self._calculate_severity(anomaly_score)

                anomaly = Anomaly(
                    anomaly_id=f"{entity_id}_{i}_{datetime.now().timestamp()}",
                    timestamp=datetime.now(),
                    anomaly_type=AnomalyType.CONTEXTUAL_ANOMALY,
                    severity=severity,
                    value=anomaly_score,
                    expected_value=threshold,
                    deviation=anomaly_score - threshold,
                    confidence=min(anomaly_score, 1.0),
                    description=f"Isolation score: {anomaly_score:.3f}",
                )

                detected_anomalies.append(anomaly)

        self.anomalies.extend(detected_anomalies)
        return detected_anomalies

    def _calculate_isolation_score(self, feature_vector: List[float]) -> float:
        """Calculate isolation score for a feature vector."""
        if not self.training_data:
            return 0.0

        # Simplified isolation score: distance to nearest neighbor
        distances = [
            np.sqrt(np.sum((np.array(fv) - np.array(feature_vector)) ** 2))
            for fv in self.training_data
        ]

        if distances:
            min_distance = min(distances)
            avg_distance = np.mean(distances)
            return min_distance / avg_distance if avg_distance > 0 else 0.0

        return 0.0

    def _calculate_threshold(self) -> float:
        """Calculate anomaly threshold based on contamination."""
        if not self.anomaly_scores:
            return 1.0

        scores = sorted(self.anomaly_scores.values())
        threshold_idx = int(len(scores) * (1 - self.contamination))
        return float(scores[threshold_idx]) if threshold_idx < len(scores) else 1.0

    def _calculate_severity(self, score: float) -> AnomalySeverity:
        """Calculate severity based on anomaly score."""
        if score >= 0.9:
            return AnomalySeverity.CRITICAL
        elif score >= 0.7:
            return AnomalySeverity.HIGH
        elif score >= 0.5:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW


class SequenceAnomalyDetector:
    """Detects anomalies in sequences and patterns."""

    def __init__(self):
        """Initialize detector."""
        self.normal_sequences: List[List[float]] = []
        self.anomalies: List[Anomaly] = []
        self.sequence_length: int = 5

    def fit(self, sequences: List[List[float]]) -> None:
        """Fit detector to normal sequences."""
        if not sequences:
            return

        self.normal_sequences = sequences
        self.sequence_length = len(sequences[0]) if sequences else 5
        logger.info(f"Sequence detector fitted with {len(sequences)} sequences")

    def detect(self, sequence: List[float], entity_id: str = "unknown") -> List[Anomaly]:
        """Detect if sequence is anomalous."""
        if not self.normal_sequences:
            return []

        detected_anomalies = []

        # Check for trend anomalies
        trend_anomaly = self._detect_trend_anomaly(sequence)
        if trend_anomaly:
            detected_anomalies.append(trend_anomaly)

        # Check for spike anomalies
        spike_anomalies = self._detect_spikes(sequence)
        detected_anomalies.extend(spike_anomalies)

        # Check for statistical anomalies in sequence
        pattern_anomaly = self._detect_pattern_anomaly(sequence)
        if pattern_anomaly:
            detected_anomalies.append(pattern_anomaly)

        # Add entity_id and timestamp
        for anomaly in detected_anomalies:
            anomaly.anomaly_id = f"{entity_id}_{anomaly.anomaly_id}_{datetime.now().timestamp()}"
            anomaly.timestamp = datetime.now()

        self.anomalies.extend(detected_anomalies)
        return detected_anomalies

    def _detect_trend_anomaly(self, sequence: List[float]) -> Optional[Anomaly]:
        """Detect anomalous trends."""
        if len(sequence) < 3:
            return None

        # Calculate trend
        x = np.arange(len(sequence))
        trend = np.polyfit(x, sequence, 1)[0]

        # Compare with normal trend
        normal_trends = []
        for seq in self.normal_sequences:
            x = np.arange(len(seq))
            normal_trends.append(np.polyfit(x, seq, 1)[0])

        avg_normal_trend = np.mean(normal_trends)
        trend_deviation = abs(trend - avg_normal_trend)
        trend_std = np.std(normal_trends)

        if trend_std > 0 and trend_deviation > 2.0 * trend_std:
            return Anomaly(
                anomaly_id="trend_anomaly",
                timestamp=datetime.now(),
                anomaly_type=AnomalyType.TREND_ANOMALY,
                severity=AnomalySeverity.MEDIUM,
                value=trend,
                expected_value=avg_normal_trend,
                deviation=trend_deviation,
                confidence=min(trend_deviation / trend_std, 1.0),
                description=f"Unusual trend detected: {trend:.3f} vs expected {avg_normal_trend:.3f}",
            )

        return None

    def _detect_spikes(self, sequence: List[float]) -> List[Anomaly]:
        """Detect spikes in sequence."""
        spikes = []

        if len(sequence) < 3:
            return spikes

        for i in range(1, len(sequence) - 1):
            prev_val = sequence[i - 1]
            curr_val = sequence[i]
            next_val = sequence[i + 1]

            # Check for spike (sudden increase followed by decrease)
            if prev_val > 0 and next_val > 0:
                change_up = (curr_val - prev_val) / prev_val
                change_down = (next_val - curr_val) / curr_val

                if change_up > 0.5 and change_down < -0.3:
                    spikes.append(
                        Anomaly(
                            anomaly_id=f"spike_{i}",
                            timestamp=datetime.now(),
                            anomaly_type=AnomalyType.SPIKE,
                            severity=AnomalySeverity.MEDIUM if change_up > 1.0 else AnomalySeverity.LOW,
                            value=curr_val,
                            expected_value=(prev_val + next_val) / 2,
                            deviation=curr_val - (prev_val + next_val) / 2,
                            confidence=min(abs(change_up), 1.0),
                            description=f"Spike detected: {change_up:.1%} increase",
                        )
                    )

        return spikes

    def _detect_pattern_anomaly(self, sequence: List[float]) -> Optional[Anomaly]:
        """Detect statistical anomalies in pattern."""
        sequence_mean = np.mean(sequence)
        sequence_std = np.std(sequence)

        # Compare with normal patterns
        normal_means = [np.mean(seq) for seq in self.normal_sequences]
        normal_stds = [np.std(seq) for seq in self.normal_sequences]

        avg_normal_mean = np.mean(normal_means)
        avg_normal_std = np.mean(normal_stds)

        mean_deviation = abs(sequence_mean - avg_normal_mean)
        std_deviation = abs(sequence_std - avg_normal_std)

        if mean_deviation > 2.0 * np.std(normal_means):
            return Anomaly(
                anomaly_id="pattern_anomaly",
                timestamp=datetime.now(),
                anomaly_type=AnomalyType.COLLECTIVE_ANOMALY,
                severity=AnomalySeverity.MEDIUM,
                value=sequence_mean,
                expected_value=avg_normal_mean,
                deviation=mean_deviation,
                confidence=min(mean_deviation / (np.std(normal_means) + 1e-6), 1.0),
                description=f"Unusual pattern detected",
            )

        return None


class RealTimeAnomalyDetector:
    """Real-time anomaly detection combining multiple methods."""

    def __init__(self):
        """Initialize detector."""
        self.statistical_detector = StatisticalAnomalyDetector(sensitivity=2.5)
        self.isolation_detector = IsolationForestDetector(contamination=0.1)
        self.sequence_detector = SequenceAnomalyDetector()
        self.all_anomalies: List[Anomaly] = []
        self.alert_history: List[Dict] = []

    def setup(
        self,
        baseline_data: List[float],
        training_features: List[Dict[str, float]],
        training_sequences: List[List[float]],
    ) -> None:
        """Setup detectors with training data."""
        self.statistical_detector.fit(baseline_data)
        self.isolation_detector.fit(training_features)
        self.sequence_detector.fit(training_sequences)

    def detect(
        self,
        current_data: List[float],
        current_features: Dict[str, float],
        entity_id: str = "unknown",
    ) -> List[Anomaly]:
        """Detect anomalies using all methods."""
        anomalies = []

        # Statistical anomaly detection
        stat_anomalies = self.statistical_detector.detect(current_data[-1:], entity_id)
        anomalies.extend(stat_anomalies)

        # Isolation forest detection
        iso_anomalies = self.isolation_detector.detect([current_features], entity_id)
        anomalies.extend(iso_anomalies)

        # Combine and deduplicate
        combined_anomalies = self._combine_anomalies(anomalies)
        self.all_anomalies.extend(combined_anomalies)

        # Create alerts for high confidence anomalies
        for anomaly in combined_anomalies:
            if anomaly.confidence > 0.8 or anomaly.severity in [
                AnomalySeverity.HIGH,
                AnomalySeverity.CRITICAL,
            ]:
                self.alert_history.append(
                    {
                        "entity_id": entity_id,
                        "anomaly_type": anomaly.anomaly_type.value,
                        "severity": anomaly.severity.value,
                        "confidence": anomaly.confidence,
                        "timestamp": anomaly.timestamp.isoformat(),
                    }
                )

        return combined_anomalies

    def _combine_anomalies(self, anomalies: List[Anomaly]) -> List[Anomaly]:
        """Combine anomalies from multiple detectors."""
        if not anomalies:
            return []

        # Simple combination: average confidence of similar anomalies
        combined = {}
        for anomaly in anomalies:
            key = (anomaly.anomaly_type, anomaly.severity)
            if key not in combined:
                combined[key] = anomaly
            else:
                # Increase confidence for corroborating detectors
                combined[key].confidence = min(
                    (combined[key].confidence + anomaly.confidence) / 2, 1.0
                )

        return list(combined.values())

    def get_statistics(self) -> Dict:
        """Get detection statistics."""
        if not self.all_anomalies:
            return {
                "total_anomalies": 0,
                "by_type": {},
                "by_severity": {},
                "recent_alerts": [],
            }

        by_type = {}
        by_severity = {}

        for anomaly in self.all_anomalies:
            atype = anomaly.anomaly_type.value
            severity = anomaly.severity.value

            by_type[atype] = by_type.get(atype, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1

        return {
            "total_anomalies": len(self.all_anomalies),
            "by_type": by_type,
            "by_severity": by_severity,
            "recent_alerts": self.alert_history[-10:],
        }
