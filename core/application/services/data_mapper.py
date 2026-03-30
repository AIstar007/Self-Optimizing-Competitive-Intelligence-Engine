"""Data mapping and transformation service for integrations."""

import json
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FieldMapping:
    """Field mapping definition."""

    source_field: str
    target_field: str
    transformer: Optional[Callable] = None
    default_value: Any = None
    required: bool = False


@dataclass
class EntityMapping:
    """Entity-level mapping definition."""

    source_entity: str
    target_entity: str
    field_mappings: List[FieldMapping]
    pre_transform: Optional[Callable] = None
    post_transform: Optional[Callable] = None


class DataMapper:
    """Maps data between external systems and internal format."""

    def __init__(self):
        """Initialize data mapper."""
        self.entity_mappings: Dict[str, EntityMapping] = {}
        self.field_transformers: Dict[str, Callable] = {}
        self.custom_transformers: Dict[str, Callable] = {}

    def register_entity_mapping(self, mapping: EntityMapping) -> None:
        """Register entity mapping."""
        self.entity_mappings[f"{mapping.source_entity}_to_{mapping.target_entity}"] = mapping
        logger.debug(
            f"Registered mapping: {mapping.source_entity} -> {mapping.target_entity}"
        )

    def register_field_transformer(
        self, name: str, transformer: Callable
    ) -> None:
        """Register field transformer."""
        self.field_transformers[name] = transformer
        logger.debug(f"Registered field transformer: {name}")

    def register_custom_transformer(
        self, name: str, transformer: Callable
    ) -> None:
        """Register custom transformation function."""
        self.custom_transformers[name] = transformer
        logger.debug(f"Registered custom transformer: {name}")

    def map_entity(
        self,
        source_entity: str,
        target_entity: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Map entity from source to target format."""
        mapping_key = f"{source_entity}_to_{target_entity}"

        if mapping_key not in self.entity_mappings:
            logger.warning(f"No mapping found for {mapping_key}")
            return data

        mapping = self.entity_mappings[mapping_key]

        # Apply pre-transformation
        if mapping.pre_transform:
            data = mapping.pre_transform(data)

        # Map fields
        result = {}

        for field_mapping in mapping.field_mappings:
            value = self._get_nested_value(data, field_mapping.source_field)

            if value is None:
                if field_mapping.required:
                    logger.warning(
                        f"Required field missing: {field_mapping.source_field}"
                    )
                if field_mapping.default_value is not None:
                    value = field_mapping.default_value
                else:
                    continue

            # Apply transformer if specified
            if field_mapping.transformer:
                try:
                    value = field_mapping.transformer(value)
                except Exception as e:
                    logger.error(f"Transformer error: {e}")
                    if field_mapping.required:
                        raise

            self._set_nested_value(result, field_mapping.target_field, value)

        # Apply post-transformation
        if mapping.post_transform:
            result = mapping.post_transform(result)

        return result

    def batch_map_entities(
        self,
        source_entity: str,
        target_entity: str,
        data_list: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Map multiple entities."""
        return [self.map_entity(source_entity, target_entity, item) for item in data_list]

    def transform(self, transformer_name: str, data: Any) -> Any:
        """Apply custom transformation."""
        if transformer_name not in self.custom_transformers:
            logger.warning(f"Transformer not found: {transformer_name}")
            return data

        try:
            transformer = self.custom_transformers[transformer_name]
            return transformer(data)
        except Exception as e:
            logger.error(f"Transformation error: {e}")
            return data

    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = path.split(".")
        value = data

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return None
            else:
                return None

        return value

    def _set_nested_value(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set value in nested dictionary using dot notation."""
        keys = path.split(".")

        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]

        current[keys[-1]] = value

    def get_mapping_info(self, source_entity: str, target_entity: str) -> Optional[Dict]:
        """Get mapping information."""
        mapping_key = f"{source_entity}_to_{target_entity}"

        if mapping_key not in self.entity_mappings:
            return None

        mapping = self.entity_mappings[mapping_key]

        return {
            "source_entity": mapping.source_entity,
            "target_entity": mapping.target_entity,
            "field_mappings": [
                {
                    "source": fm.source_field,
                    "target": fm.target_field,
                    "required": fm.required,
                    "has_transformer": fm.transformer is not None,
                    "has_default": fm.default_value is not None,
                }
                for fm in mapping.field_mappings
            ],
        }


class DataTransformer:
    """Transforms data using configurable rules."""

    def __init__(self):
        """Initialize transformer."""
        self.rules: Dict[str, Dict[str, Any]] = {}

    def register_rule(self, rule_name: str, rule: Dict[str, Any]) -> None:
        """Register transformation rule."""
        self.rules[rule_name] = rule
        logger.debug(f"Registered transformation rule: {rule_name}")

    def apply_rule(self, rule_name: str, data: Any) -> Any:
        """Apply transformation rule to data."""
        if rule_name not in self.rules:
            logger.warning(f"Rule not found: {rule_name}")
            return data

        rule = self.rules[rule_name]

        try:
            if rule.get("type") == "filter":
                return self._apply_filter(data, rule)
            elif rule.get("type") == "map":
                return self._apply_map(data, rule)
            elif rule.get("type") == "aggregate":
                return self._apply_aggregate(data, rule)
            elif rule.get("type") == "transform":
                return self._apply_transform(data, rule)
            else:
                return data
        except Exception as e:
            logger.error(f"Rule application error: {e}")
            return data

    def _apply_filter(self, data: Any, rule: Dict) -> Any:
        """Apply filter rule."""
        if not isinstance(data, list):
            return data

        condition = rule.get("condition")
        if not condition:
            return data

        return [item for item in data if self._evaluate_condition(item, condition)]

    def _apply_map(self, data: Any, rule: Dict) -> Any:
        """Apply map rule."""
        mapping = rule.get("mapping", {})

        if isinstance(data, dict):
            return {mapping.get(k, k): v for k, v in data.items()}
        elif isinstance(data, list):
            return [self._apply_map(item, {"mapping": mapping, "type": "map"}) for item in data]
        else:
            return data

    def _apply_aggregate(self, data: Any, rule: Dict) -> Any:
        """Apply aggregation rule."""
        if not isinstance(data, list):
            return data

        agg_type = rule.get("aggregation_type", "sum")
        field = rule.get("field")

        if not field:
            return data

        values = [item.get(field) for item in data if isinstance(item, dict) and field in item]

        if agg_type == "sum":
            return sum(v for v in values if isinstance(v, (int, float)))
        elif agg_type == "count":
            return len(values)
        elif agg_type == "avg":
            return sum(v for v in values if isinstance(v, (int, float))) / len(values) if values else 0
        elif agg_type == "min":
            return min(values) if values else None
        elif agg_type == "max":
            return max(values) if values else None
        else:
            return data

    def _apply_transform(self, data: Any, rule: Dict) -> Any:
        """Apply transformation rule."""
        transformer_func = rule.get("transformer")
        if not transformer_func:
            return data

        try:
            return transformer_func(data)
        except Exception as e:
            logger.error(f"Transformation error: {e}")
            return data

    def _evaluate_condition(self, item: Any, condition: str) -> bool:
        """Evaluate condition expression."""
        try:
            # Simple condition evaluation
            return eval(condition, {"__builtins__": {}}, {"item": item})
        except Exception as e:
            logger.error(f"Condition evaluation error: {e}")
            return False


# Global instances
_data_mapper: Optional[DataMapper] = None
_data_transformer: Optional[DataTransformer] = None


def get_data_mapper() -> DataMapper:
    """Get or create global data mapper."""
    global _data_mapper
    if _data_mapper is None:
        _data_mapper = DataMapper()
    return _data_mapper


def get_data_transformer() -> DataTransformer:
    """Get or create global data transformer."""
    global _data_transformer
    if _data_transformer is None:
        _data_transformer = DataTransformer()
    return _data_transformer
