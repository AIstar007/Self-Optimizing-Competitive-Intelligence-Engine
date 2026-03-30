"""Machine learning pipeline for data preprocessing and feature engineering."""

import logging
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from enum import Enum

logger = logging.getLogger(__name__)


class FeatureType(Enum):
    """Feature types for different data aspects."""

    NUMERICAL = "numerical"
    CATEGORICAL = "categorical"
    TEMPORAL = "temporal"
    TREND = "trend"
    VOLATILITY = "volatility"
    SENTIMENT = "sentiment"
    NETWORK = "network"


@dataclass
class Feature:
    """Represents a feature with metadata."""

    name: str
    feature_type: FeatureType
    value: Any
    importance: float = 0.0
    is_null: bool = False
    created_at: datetime = None

    def __post_init__(self):
        """Initialize default values."""
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class ProcessedDataPoint:
    """Represents a processed data point with features."""

    entity_id: str
    timestamp: datetime
    features: List[Feature]
    raw_data: Dict = None
    processing_metadata: Dict = None

    def get_feature_dict(self) -> Dict[str, Any]:
        """Get features as dictionary."""
        return {f.name: f.value for f in self.features}

    def get_feature_values(self) -> np.ndarray:
        """Get feature values as numpy array."""
        return np.array([f.value for f in self.features if not f.is_null])


class FeatureExtractor:
    """Extracts features from raw data."""

    def __init__(self):
        """Initialize extractor."""
        self.extracted_features: List[str] = []

    def extract_temporal_features(
        self, timestamp: datetime
    ) -> Dict[str, float]:
        """Extract temporal features from timestamp."""
        features = {
            "hour": float(timestamp.hour),
            "day_of_week": float(timestamp.weekday()),
            "day_of_month": float(timestamp.day),
            "month": float(timestamp.month),
            "quarter": float((timestamp.month - 1) // 3 + 1),
            "day_of_year": float(timestamp.timetuple().tm_yday),
            "week_of_year": float(timestamp.isocalendar()[1]),
            "is_weekend": float(timestamp.weekday() >= 5),
        }
        return features

    def extract_statistical_features(
        self, data: List[float], window: int = 30
    ) -> Dict[str, float]:
        """Extract statistical features from numerical data."""
        if len(data) < 2:
            return {}

        data_array = np.array(data[-window:])
        features = {
            "mean": float(np.mean(data_array)),
            "std": float(np.std(data_array)),
            "min": float(np.min(data_array)),
            "max": float(np.max(data_array)),
            "median": float(np.median(data_array)),
            "q25": float(np.percentile(data_array, 25)),
            "q75": float(np.percentile(data_array, 75)),
            "skewness": float(self._skewness(data_array)),
            "kurtosis": float(self._kurtosis(data_array)),
            "range": float(np.max(data_array) - np.min(data_array)),
        }
        return features

    def extract_trend_features(
        self, data: List[float], window: int = 30
    ) -> Dict[str, float]:
        """Extract trend features from time series data."""
        if len(data) < 2:
            return {}

        data_array = np.array(data[-window:])
        features = {
            "trend": self._calculate_trend(data_array),
            "momentum": self._calculate_momentum(data_array),
            "acceleration": self._calculate_acceleration(data_array),
            "moving_avg_short": float(np.mean(data_array[-7:])),
            "moving_avg_long": float(np.mean(data_array)),
            "exponential_smoothing": float(self._exponential_smoothing(data_array)),
        }
        return features

    def extract_volatility_features(
        self, data: List[float], window: int = 30
    ) -> Dict[str, float]:
        """Extract volatility features."""
        if len(data) < 2:
            return {}

        data_array = np.array(data[-window:])
        returns = np.diff(data_array) / data_array[:-1]

        features = {
            "volatility": float(np.std(returns)),
            "downside_volatility": float(np.std(returns[returns < 0])) if len(returns[returns < 0]) > 0 else 0.0,
            "upside_volatility": float(np.std(returns[returns > 0])) if len(returns[returns > 0]) > 0 else 0.0,
            "max_drawdown": float(self._max_drawdown(data_array)),
            "sharpe_ratio": float(self._sharpe_ratio(returns)),
        }
        return features

    def extract_text_features(self, text: str) -> Dict[str, float]:
        """Extract text-based features."""
        if not text:
            return {}

        words = text.split()
        features = {
            "text_length": float(len(text)),
            "word_count": float(len(words)),
            "avg_word_length": float(np.mean([len(w) for w in words])) if words else 0.0,
            "unique_words": float(len(set(words))),
            "lexical_diversity": float(len(set(words)) / len(words)) if words else 0.0,
        }
        return features

    def extract_categorical_features(
        self, data: List[str]
    ) -> Dict[str, float]:
        """Extract categorical features."""
        if not data:
            return {}

        unique_count = len(set(data))
        most_common = max(set(data), key=data.count)

        features = {
            "unique_categories": float(unique_count),
            "most_common_frequency": float(data.count(most_common) / len(data)),
            "diversity": float(unique_count / len(data)),
        }
        return features

    @staticmethod
    def _skewness(data: np.ndarray) -> float:
        """Calculate skewness."""
        if len(data) < 3:
            return 0.0
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        return np.mean(((data - mean) / std) ** 3)

    @staticmethod
    def _kurtosis(data: np.ndarray) -> float:
        """Calculate kurtosis."""
        if len(data) < 4:
            return 0.0
        mean = np.mean(data)
        std = np.std(data)
        if std == 0:
            return 0.0
        return np.mean(((data - mean) / std) ** 4) - 3

    @staticmethod
    def _calculate_trend(data: np.ndarray) -> float:
        """Calculate trend using linear regression."""
        if len(data) < 2:
            return 0.0
        x = np.arange(len(data))
        slope = np.polyfit(x, data, 1)[0]
        return float(slope)

    @staticmethod
    def _calculate_momentum(data: np.ndarray) -> float:
        """Calculate momentum."""
        if len(data) < 2:
            return 0.0
        return float((data[-1] - data[0]) / data[0]) if data[0] != 0 else 0.0

    @staticmethod
    def _calculate_acceleration(data: np.ndarray) -> float:
        """Calculate acceleration of change."""
        if len(data) < 3:
            return 0.0
        diff1 = np.diff(data)
        diff2 = np.diff(diff1)
        return float(np.mean(diff2)) if len(diff2) > 0 else 0.0

    @staticmethod
    def _exponential_smoothing(data: np.ndarray, alpha: float = 0.3) -> float:
        """Calculate exponential smoothing."""
        if len(data) == 0:
            return 0.0
        result = data[0]
        for val in data[1:]:
            result = alpha * val + (1 - alpha) * result
        return float(result)

    @staticmethod
    def _max_drawdown(data: np.ndarray) -> float:
        """Calculate maximum drawdown."""
        if len(data) < 2:
            return 0.0
        cummax = np.maximum.accumulate(data)
        drawdown = (data - cummax) / cummax
        return float(np.min(drawdown)) if len(drawdown) > 0 else 0.0

    @staticmethod
    def _sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
        excess_returns = returns - risk_free_rate / 252  # 252 trading days
        if np.std(excess_returns) == 0:
            return 0.0
        return float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252))


class FeatureScaler:
    """Scales and normalizes features."""

    def __init__(self):
        """Initialize scaler."""
        self.min_values: Dict[str, float] = {}
        self.max_values: Dict[str, float] = {}
        self.mean_values: Dict[str, float] = {}
        self.std_values: Dict[str, float] = {}

    def fit(self, features: List[Dict[str, float]]) -> None:
        """Fit scaler to features."""
        if not features:
            return

        all_feature_names = set()
        for feat_dict in features:
            all_feature_names.update(feat_dict.keys())

        for feature_name in all_feature_names:
            values = [
                f[feature_name]
                for f in features
                if feature_name in f and f[feature_name] is not None
            ]

            if values:
                self.min_values[feature_name] = float(np.min(values))
                self.max_values[feature_name] = float(np.max(values))
                self.mean_values[feature_name] = float(np.mean(values))
                self.std_values[feature_name] = float(np.std(values))

    def normalize(self, features: Dict[str, float]) -> Dict[str, float]:
        """Min-max normalization to [0, 1]."""
        normalized = {}
        for name, value in features.items():
            if name in self.min_values and name in self.max_values:
                min_val = self.min_values[name]
                max_val = self.max_values[name]
                if max_val - min_val != 0:
                    normalized[name] = (value - min_val) / (max_val - min_val)
                else:
                    normalized[name] = 0.0
            else:
                normalized[name] = value

        return normalized

    def standardize(self, features: Dict[str, float]) -> Dict[str, float]:
        """Standardization (z-score normalization)."""
        standardized = {}
        for name, value in features.items():
            if name in self.mean_values and name in self.std_values:
                mean = self.mean_values[name]
                std = self.std_values[name]
                if std != 0:
                    standardized[name] = (value - mean) / std
                else:
                    standardized[name] = 0.0
            else:
                standardized[name] = value

        return standardized


class DataPreprocessor:
    """Preprocesses raw data for ML pipeline."""

    def __init__(self):
        """Initialize preprocessor."""
        self.feature_extractor = FeatureExtractor()
        self.feature_scaler = FeatureScaler()
        self.missing_value_strategy = "mean"

    def handle_missing_values(
        self, data: List[float], strategy: str = "mean"
    ) -> List[float]:
        """Handle missing values in data."""
        if not data:
            return []

        data_array = np.array(data, dtype=float)

        if strategy == "mean":
            fill_value = np.nanmean(data_array)
        elif strategy == "median":
            fill_value = np.nanmedian(data_array)
        elif strategy == "forward_fill":
            fill_value = None
        elif strategy == "zero":
            fill_value = 0.0
        else:
            fill_value = np.nanmean(data_array)

        if fill_value is not None:
            data_array = np.where(np.isnan(data_array), fill_value, data_array)
        else:
            # Forward fill
            for i in range(len(data_array)):
                if np.isnan(data_array[i]):
                    if i > 0:
                        data_array[i] = data_array[i - 1]
                    else:
                        data_array[i] = 0.0

        return data_array.tolist()

    def remove_outliers(
        self, data: List[float], method: str = "iqr", threshold: float = 1.5
    ) -> Tuple[List[float], List[int]]:
        """Remove or flag outliers."""
        if len(data) < 4:
            return data, []

        data_array = np.array(data)
        outlier_indices = []

        if method == "iqr":
            q1 = np.percentile(data_array, 25)
            q3 = np.percentile(data_array, 75)
            iqr = q3 - q1
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr

            outlier_indices = [
                i
                for i, val in enumerate(data_array)
                if val < lower_bound or val > upper_bound
            ]

        elif method == "zscore":
            mean = np.mean(data_array)
            std = np.std(data_array)
            outlier_indices = [
                i
                for i, val in enumerate(data_array)
                if abs((val - mean) / std) > threshold
            ]

        cleaned_data = [
            val for i, val in enumerate(data) if i not in outlier_indices
        ]
        return cleaned_data, outlier_indices

    def normalize_data(self, data: List[float]) -> List[float]:
        """Normalize data to [0, 1] range."""
        if not data or len(data) < 2:
            return data

        data_array = np.array(data, dtype=float)
        min_val = np.min(data_array)
        max_val = np.max(data_array)

        if max_val - min_val == 0:
            return [0.0] * len(data)

        return ((data_array - min_val) / (max_val - min_val)).tolist()

    def resample_data(
        self, data: List[float], original_freq: str, target_freq: str
    ) -> List[float]:
        """Resample time series data."""
        if original_freq == target_freq:
            return data

        # Simple resampling by averaging
        if target_freq == "daily" and original_freq == "hourly":
            return [np.mean(data[i : i + 24]) for i in range(0, len(data), 24)]
        elif target_freq == "weekly" and original_freq == "daily":
            return [np.mean(data[i : i + 7]) for i in range(0, len(data), 7)]

        return data

    def create_sequences(
        self, data: List[float], sequence_length: int = 30
    ) -> List[List[float]]:
        """Create sequences for time series prediction."""
        sequences = []
        for i in range(len(data) - sequence_length + 1):
            sequences.append(data[i : i + sequence_length])
        return sequences


class PipelineOrchestrator:
    """Orchestrates the entire ML pipeline."""

    def __init__(self):
        """Initialize orchestrator."""
        self.feature_extractor = FeatureExtractor()
        self.preprocessor = DataPreprocessor()
        self.scaler = FeatureScaler()
        self.pipeline_history: List[Dict] = []

    def process_raw_data(
        self, entity_id: str, raw_data: Dict, timestamp: datetime
    ) -> ProcessedDataPoint:
        """Process raw data through entire pipeline."""
        features = []

        # Extract temporal features
        temporal_features = self.feature_extractor.extract_temporal_features(
            timestamp
        )
        for name, value in temporal_features.items():
            features.append(Feature(name=f"temporal_{name}", feature_type=FeatureType.TEMPORAL, value=value))

        # Extract other features based on raw data
        for key, value in raw_data.items():
            if isinstance(value, (int, float)):
                features.append(
                    Feature(
                        name=f"raw_{key}",
                        feature_type=FeatureType.NUMERICAL,
                        value=float(value),
                    )
                )
            elif isinstance(value, str):
                features.append(
                    Feature(
                        name=f"raw_{key}",
                        feature_type=FeatureType.CATEGORICAL,
                        value=value,
                    )
                )
            elif isinstance(value, list) and len(value) > 0:
                if isinstance(value[0], (int, float)):
                    # Statistical features
                    stat_features = self.feature_extractor.extract_statistical_features(
                        value
                    )
                    for name, val in stat_features.items():
                        features.append(
                            Feature(
                                name=f"{key}_{name}",
                                feature_type=FeatureType.NUMERICAL,
                                value=val,
                            )
                        )

        # Create processed data point
        processed_point = ProcessedDataPoint(
            entity_id=entity_id,
            timestamp=timestamp,
            features=features,
            raw_data=raw_data,
            processing_metadata={
                "feature_count": len(features),
                "processed_at": datetime.now().isoformat(),
            },
        )

        # Record in history
        self.pipeline_history.append(
            {
                "entity_id": entity_id,
                "timestamp": timestamp,
                "feature_count": len(features),
                "status": "success",
            }
        )

        return processed_point

    def batch_process(
        self, data_points: List[Tuple[str, Dict, datetime]]
    ) -> List[ProcessedDataPoint]:
        """Process batch of data points."""
        processed = []
        for entity_id, raw_data, timestamp in data_points:
            try:
                processed_point = self.process_raw_data(entity_id, raw_data, timestamp)
                processed.append(processed_point)
            except Exception as e:
                logger.error(f"Error processing {entity_id}: {e}")
                self.pipeline_history.append(
                    {
                        "entity_id": entity_id,
                        "timestamp": timestamp,
                        "status": "error",
                        "error": str(e),
                    }
                )

        return processed

    def get_pipeline_statistics(self) -> Dict:
        """Get pipeline statistics."""
        if not self.pipeline_history:
            return {"total_processed": 0, "success_count": 0, "error_count": 0}

        total = len(self.pipeline_history)
        success = sum(1 for p in self.pipeline_history if p.get("status") == "success")
        errors = total - success

        return {
            "total_processed": total,
            "success_count": success,
            "error_count": errors,
            "success_rate": success / total if total > 0 else 0.0,
            "avg_features_per_point": np.mean(
                [p.get("feature_count", 0) for p in self.pipeline_history]
            ),
        }
