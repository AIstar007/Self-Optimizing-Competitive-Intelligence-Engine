"""Predictive models for market forecasting and trend prediction."""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from enum import Enum

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Types of predictive models."""

    ARIMA = "arima"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    LINEAR_REGRESSION = "linear_regression"
    LSTM = "lstm"
    PROPHET = "prophet"
    ENSEMBLE = "ensemble"


@dataclass
class Prediction:
    """Represents a model prediction."""

    value: float
    lower_bound: float
    upper_bound: float
    confidence: float
    timestamp: datetime
    model_type: ModelType
    feature_importance: Dict[str, float] = None


@dataclass
class ModelMetrics:
    """Model evaluation metrics."""

    mae: float  # Mean Absolute Error
    rmse: float  # Root Mean Squared Error
    mape: float  # Mean Absolute Percentage Error
    r_squared: float  # R-squared
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    model_type: ModelType


class TimeSeriesForecaster:
    """Forecasts time series using multiple methods."""

    def __init__(self):
        """Initialize forecaster."""
        self.training_data: List[float] = []
        self.model_params: Dict = {}
        self.is_fitted: bool = False

    def fit(self, data: List[float], model_type: ModelType = ModelType.EXPONENTIAL_SMOOTHING) -> None:
        """Fit model to training data."""
        if len(data) < 2:
            logger.warning("Insufficient data for forecasting")
            return

        self.training_data = data
        self.is_fitted = True

        if model_type == ModelType.EXPONENTIAL_SMOOTHING:
            self.model_params = self._fit_exponential_smoothing(data)
        elif model_type == ModelType.LINEAR_REGRESSION:
            self.model_params = self._fit_linear_regression(data)
        elif model_type == ModelType.ARIMA:
            self.model_params = self._fit_arima(data)

        logger.info(f"Model fitted with {len(data)} data points")

    def forecast(
        self, periods: int = 30, confidence: float = 0.95
    ) -> List[Prediction]:
        """Generate forecasts for specified periods."""
        if not self.is_fitted or not self.training_data:
            logger.warning("Model not fitted, returning empty predictions")
            return []

        predictions = []
        current_data = self.training_data.copy()
        base_timestamp = datetime.now()

        for i in range(periods):
            pred_value = self._forecast_next_value(current_data)
            uncertainty = self._calculate_uncertainty(current_data)

            margin = uncertainty * (1 - confidence)
            lower = pred_value - margin
            upper = pred_value + margin

            predictions.append(
                Prediction(
                    value=pred_value,
                    lower_bound=lower,
                    upper_bound=upper,
                    confidence=confidence,
                    timestamp=base_timestamp + timedelta(days=i + 1),
                    model_type=ModelType.EXPONENTIAL_SMOOTHING,
                )
            )

            current_data.append(pred_value)

        return predictions

    def update(self, new_data: List[float]) -> None:
        """Update model with new data."""
        self.training_data.extend(new_data)
        self.fit(self.training_data)

    def _fit_exponential_smoothing(self, data: List[float]) -> Dict:
        """Fit exponential smoothing model."""
        alpha = 0.3
        beta = 0.1
        return {"alpha": alpha, "beta": beta, "trend": self._calculate_trend(data)}

    def _fit_linear_regression(self, data: List[float]) -> Dict:
        """Fit linear regression model."""
        x = np.arange(len(data))
        y = np.array(data)

        slope = np.polyfit(x, y, 1)[0]
        intercept = np.polyfit(x, y, 1)[1]

        return {"slope": float(slope), "intercept": float(intercept)}

    def _fit_arima(self, data: List[float]) -> Dict:
        """Simplified ARIMA-like fitting."""
        # Using differencing for trend removal
        if len(data) > 1:
            diff = np.diff(data)
            ar_coef = np.correlate(diff, diff, mode="full")[
                len(diff) - 1 : len(diff) + 1
            ]
        else:
            ar_coef = [0.0]

        return {"ar_coefficients": ar_coef.tolist()}

    def _forecast_next_value(self, current_data: List[float]) -> float:
        """Forecast next value using current model parameters."""
        if not self.model_params:
            return np.mean(current_data[-5:]) if current_data else 0.0

        if "alpha" in self.model_params:
            # Exponential smoothing
            alpha = self.model_params["alpha"]
            trend = self.model_params.get("trend", 0)
            return current_data[-1] * alpha + np.mean(current_data[-5:]) * (1 - alpha) + trend

        elif "slope" in self.model_params:
            # Linear regression
            x_next = len(current_data)
            slope = self.model_params["slope"]
            intercept = self.model_params["intercept"]
            return slope * x_next + intercept

        return np.mean(current_data[-5:]) if current_data else 0.0

    def _calculate_uncertainty(self, data: List[float]) -> float:
        """Calculate prediction uncertainty."""
        if len(data) < 2:
            return 0.1

        residuals = np.diff(data)
        std_dev = np.std(residuals)
        return max(std_dev, 0.01)  # Minimum uncertainty

    @staticmethod
    def _calculate_trend(data: List[float]) -> float:
        """Calculate trend component."""
        if len(data) < 2:
            return 0.0

        x = np.arange(len(data))
        slope = np.polyfit(x, data, 1)[0]
        return float(slope)


class MarketPredictor:
    """Predicts market movements and conditions."""

    def __init__(self):
        """Initialize predictor."""
        self.forecaster = TimeSeriesForecaster()
        self.market_indicators: Dict[str, float] = {}
        self.prediction_history: List[Prediction] = []

    def predict_market_movement(
        self, price_data: List[float], volume_data: List[float], periods: int = 30
    ) -> List[Prediction]:
        """Predict future market movement."""
        if len(price_data) < 5:
            logger.warning("Insufficient price data")
            return []

        # Combine price and volume signals
        price_predictions = self._forecast_with_data(price_data, periods)

        # Calculate confidence based on volume
        volume_confidence = self._calculate_volume_confidence(volume_data)

        for pred in price_predictions:
            pred.confidence *= volume_confidence

        self.prediction_history.extend(price_predictions)
        return price_predictions

    def predict_market_size(
        self, historical_sizes: List[float], growth_factors: List[float], periods: int = 12
    ) -> List[Prediction]:
        """Predict future market size."""
        if not historical_sizes:
            return []

        self.forecaster.fit(historical_sizes)
        predictions = self.forecaster.forecast(periods)

        # Adjust for growth factors
        for i, pred in enumerate(predictions):
            if i < len(growth_factors):
                adjustment = 1.0 + growth_factors[i]
                pred.value *= adjustment
                pred.lower_bound *= adjustment
                pred.upper_bound *= adjustment

        return predictions

    def predict_competitor_share(
        self, market_share_data: List[float], competitor_count: int, periods: int = 12
    ) -> List[Prediction]:
        """Predict competitor market share evolution."""
        self.forecaster.fit(market_share_data)
        predictions = self.forecaster.forecast(periods)

        # Normalize by number of competitors
        for pred in predictions:
            pred.value = min(pred.value / competitor_count, 1.0)
            pred.lower_bound = max(pred.lower_bound / competitor_count, 0.0)
            pred.upper_bound = min(pred.upper_bound / competitor_count, 1.0)

        return predictions

    def calculate_market_indicators(
        self, price_data: List[float], volume_data: List[float]
    ) -> Dict[str, float]:
        """Calculate market technical indicators."""
        indicators = {}

        if len(price_data) >= 14:
            indicators["rsi"] = self._calculate_rsi(price_data)
            indicators["macd"] = self._calculate_macd(price_data)

        if len(volume_data) >= 2:
            indicators["volume_trend"] = float(volume_data[-1] - volume_data[-2])
            indicators["avg_volume"] = float(np.mean(volume_data[-20:]))

        if len(price_data) >= 2:
            indicators["volatility"] = float(np.std(np.diff(price_data)))
            indicators["momentum"] = float((price_data[-1] - price_data[0]) / price_data[0]) if price_data[0] != 0 else 0.0

        self.market_indicators = indicators
        return indicators

    def _forecast_with_data(
        self, data: List[float], periods: int
    ) -> List[Prediction]:
        """Forecast using provided data."""
        self.forecaster.fit(data)
        return self.forecaster.forecast(periods)

    def _calculate_volume_confidence(self, volume_data: List[float]) -> float:
        """Calculate confidence adjustment based on volume."""
        if len(volume_data) < 2:
            return 1.0

        volume_array = np.array(volume_data[-10:])
        avg_volume = np.mean(volume_array)
        std_volume = np.std(volume_array)

        if avg_volume > 0:
            cv = std_volume / avg_volume
            return 1.0 / (1.0 + cv)
        return 1.0

    @staticmethod
    def _calculate_rsi(data: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        if len(data) < period + 1:
            return 50.0

        deltas = np.diff(data[-period - 1 :])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0

        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))

    @staticmethod
    def _calculate_macd(data: List[float]) -> float:
        """Calculate MACD value."""
        if len(data) < 26:
            return 0.0

        ema_12 = np.mean(data[-12:])  # Simplified EMA
        ema_26 = np.mean(data[-26:])

        return float(ema_12 - ema_26)


class CompetitiveForecaster:
    """Forecasts competitive movements and market dynamics."""

    def __init__(self):
        """Initialize forecaster."""
        self.market_predictor = MarketPredictor()
        self.competitor_trends: Dict[str, List[float]] = {}
        self.competitive_alerts: List[Dict] = []

    def forecast_competitor_movement(
        self, competitor_id: str, historical_activity: List[float], periods: int = 30
    ) -> List[Prediction]:
        """Forecast competitor movement patterns."""
        if len(historical_activity) < 5:
            logger.warning(f"Insufficient data for competitor {competitor_id}")
            return []

        predictions = self.market_predictor._forecast_with_data(
            historical_activity, periods
        )

        # Calculate competitor-specific confidence
        volatility = np.std(np.diff(historical_activity))
        predictability = 1.0 / (1.0 + volatility)

        for pred in predictions:
            pred.confidence *= predictability
            pred.model_type = ModelType.ENSEMBLE

        return predictions

    def predict_market_consolidation(
        self, competitor_count: List[int], market_changes: List[float]
    ) -> Dict[str, any]:
        """Predict market consolidation trends."""
        if len(competitor_count) < 2:
            return {}

        consolidation_rate = float(
            (competitor_count[0] - competitor_count[-1]) / competitor_count[0]
        ) if competitor_count[0] > 0 else 0.0

        trend_direction = float(np.mean(np.diff(competitor_count)))

        return {
            "consolidation_rate": consolidation_rate,
            "trend_direction": trend_direction,
            "is_consolidating": consolidation_rate > 0.05,
            "market_changes_avg": float(np.mean(market_changes)),
        }

    def detect_competitive_threats(
        self, competitor_metrics: Dict[str, List[float]], threat_threshold: float = 0.7
    ) -> List[Dict]:
        """Detect emerging competitive threats."""
        threats = []

        for competitor_id, metrics in competitor_metrics.items():
            if len(metrics) < 3:
                continue

            growth_rate = (metrics[-1] - metrics[0]) / metrics[0] if metrics[0] != 0 else 0.0
            acceleration = np.mean(np.diff(metrics[-3:]))

            threat_score = 0.0
            threat_score += min(growth_rate, 1.0) * 0.5  # Growth component
            threat_score += min(acceleration, 1.0) * 0.3  # Acceleration component
            threat_score += (1.0 - (1.0 / (1.0 + np.std(metrics)))) * 0.2  # Volatility

            if threat_score >= threat_threshold:
                threats.append(
                    {
                        "competitor_id": competitor_id,
                        "threat_score": threat_score,
                        "growth_rate": growth_rate,
                        "acceleration": acceleration,
                        "detected_at": datetime.now().isoformat(),
                    }
                )

        self.competitive_alerts.extend(threats)
        return threats

    def predict_market_entry_likelihood(
        self, market_conditions: Dict[str, float], historical_entries: List[int]
    ) -> float:
        """Predict likelihood of new competitor market entry."""
        entry_rate = len(historical_entries) / len(historical_entries) if historical_entries else 0.0

        barrier_to_entry = market_conditions.get("barrier_to_entry", 0.5)
        market_attractiveness = market_conditions.get("market_attractiveness", 0.5)
        market_growth = market_conditions.get("market_growth", 0.0)

        # Entry likelihood components
        attractiveness_factor = market_attractiveness * (1.0 - barrier_to_entry)
        growth_factor = max(0.0, market_growth)  # Normalize to [0, 1]

        entry_likelihood = (
            attractiveness_factor * 0.5 + growth_factor * 0.3 + entry_rate * 0.2
        )

        return min(entry_likelihood, 1.0)

    def get_competitive_dashboard(self) -> Dict:
        """Get competitive intelligence dashboard metrics."""
        return {
            "active_alerts": len(self.competitive_alerts),
            "high_threat_competitors": len(
                [a for a in self.competitive_alerts if a.get("threat_score", 0) > 0.8]
            ),
            "market_indicators": self.market_predictor.market_indicators,
            "recent_alerts": self.competitive_alerts[-5:],
        }


def evaluate_model(
    actual: List[float], predicted: List[float], model_type: ModelType = ModelType.EXPONENTIAL_SMOOTHING
) -> ModelMetrics:
    """Evaluate model performance."""
    if len(actual) != len(predicted) or len(actual) == 0:
        return ModelMetrics(
            mae=float("inf"),
            rmse=float("inf"),
            mape=float("inf"),
            r_squared=0.0,
            accuracy=0.0,
            precision=0.0,
            recall=0.0,
            f1_score=0.0,
            model_type=model_type,
        )

    actual_array = np.array(actual)
    predicted_array = np.array(predicted)

    mae = float(np.mean(np.abs(actual_array - predicted_array)))
    rmse = float(np.sqrt(np.mean((actual_array - predicted_array) ** 2)))

    # MAPE
    mape = float(
        np.mean(np.abs((actual_array - predicted_array) / actual_array)) * 100
    ) if np.all(actual_array != 0) else float("inf")

    # R-squared
    ss_res = np.sum((actual_array - predicted_array) ** 2)
    ss_tot = np.sum((actual_array - np.mean(actual_array)) ** 2)
    r_squared = float(1 - (ss_res / ss_tot)) if ss_tot != 0 else 0.0

    return ModelMetrics(
        mae=mae,
        rmse=rmse,
        mape=mape,
        r_squared=r_squared,
        accuracy=1.0 / (1.0 + mae),
        precision=1.0 / (1.0 + mae),
        recall=1.0 / (1.0 + mae),
        f1_score=1.0 / (1.0 + mae),
        model_type=model_type,
    )
