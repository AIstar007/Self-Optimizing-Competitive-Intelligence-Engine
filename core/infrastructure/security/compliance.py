"""Compliance models and validators for GDPR, SOC2, and data privacy."""

import logging
from enum import Enum
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ComplianceFramework(Enum):
    """Compliance frameworks."""

    GDPR = "gdpr"
    SOC2 = "soc2"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    ISO_27001 = "iso_27001"
    CCPA = "ccpa"
    CUSTOM = "custom"


class DataClassification(Enum):
    """Data sensitivity classification."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class ConsentType(Enum):
    """Types of user consent."""

    MARKETING = "marketing"
    ANALYTICS = "analytics"
    DATA_PROCESSING = "data_processing"
    PROFILING = "profiling"
    THIRD_PARTY_SHARING = "third_party_sharing"
    COOKIES = "cookies"


@dataclass
class ComplianceRequirement:
    """Compliance requirement definition."""

    requirement_id: str
    framework: ComplianceFramework
    title: str
    description: str
    implementation_status: str  # not_started, in_progress, implemented, verified
    evidence: List[str]  # Evidence documents/links
    responsible_team: str
    due_date: Optional[datetime]
    last_verified: Optional[datetime]
    compliance_percentage: float  # 0-100


@dataclass
class GDPRCompliance:
    """GDPR compliance tracking."""

    organization_id: str
    privacy_officer: str
    dpia_required: bool  # Data Protection Impact Assessment
    dpia_completed: bool
    dpia_date: Optional[datetime]
    legitimate_interests_assessed: bool
    standard_contractual_clauses: bool
    data_processing_agreements: List[str]
    retention_periods: Dict[str, int]  # Field -> days
    right_to_be_forgotten_implemented: bool
    data_portability_implemented: bool
    breach_notification_procedure: str
    last_audit: Optional[datetime]
    audit_findings: List[str]

    def get_compliance_percentage(self) -> float:
        """Calculate GDPR compliance percentage."""
        checks = [
            self.dpia_completed,
            self.legitimate_interests_assessed,
            self.standard_contractual_clauses,
            bool(self.data_processing_agreements),
            self.right_to_be_forgotten_implemented,
            self.data_portability_implemented,
            bool(self.breach_notification_procedure),
        ]

        return (sum(checks) / len(checks)) * 100 if checks else 0


@dataclass
class SOC2Compliance:
    """SOC2 compliance tracking."""

    organization_id: str
    audit_firm: str
    audit_scope: str
    certification_date: Optional[datetime]
    expiration_date: Optional[datetime]
    type_i: bool  # Type I certification
    type_ii: bool  # Type II certification
    categories: List[str]  # CC, C, A, PO, PT
    control_status: Dict[str, str]  # Control ID -> status
    findings: List[str]
    remediation_plans: Dict[str, str]  # Finding -> plan
    last_assessment: Optional[datetime]

    def is_current(self) -> bool:
        """Check if certification is current."""
        if not self.expiration_date:
            return False
        return datetime.utcnow() <= self.expiration_date


@dataclass
class DataRetentionPolicy:
    """Data retention policy."""

    policy_id: str
    data_type: str
    retention_period_days: int
    retention_reason: str
    deletion_method: str  # immediate, secure_wipe, anonymization
    exceptions: List[str]
    created_date: datetime
    last_reviewed: datetime
    next_review: datetime

    def is_data_expired(self, creation_date: datetime) -> bool:
        """Check if data should be deleted."""
        expiration = creation_date + timedelta(days=self.retention_period_days)
        return datetime.utcnow() >= expiration


@dataclass
class UserConsent:
    """User consent record."""

    consent_id: str
    user_id: str
    consent_type: ConsentType
    given: bool
    timestamp: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    version: str  # Policy version
    expires_at: Optional[datetime]
    withdrawn_at: Optional[datetime]

    def is_valid(self) -> bool:
        """Check if consent is still valid."""
        if not self.given or self.withdrawn_at:
            return False

        if self.expires_at and datetime.utcnow() >= self.expires_at:
            return False

        return True

    def withdraw(self) -> None:
        """Withdraw consent."""
        self.withdrawn_at = datetime.utcnow()


class PrivacyValidator:
    """Validator for privacy and compliance requirements."""

    @staticmethod
    def validate_data_classification(data: Dict) -> bool:
        """Validate that data is properly classified."""
        required_fields = ["data_type", "classification", "owner"]
        return all(field in data for field in required_fields)

    @staticmethod
    def validate_consent_requirement(consent_type: ConsentType) -> bool:
        """Validate consent type is recognized."""
        return isinstance(consent_type, ConsentType)

    @staticmethod
    def validate_retention_policy(policy: DataRetentionPolicy) -> List[str]:
        """Validate retention policy."""
        errors = []

        if policy.retention_period_days <= 0:
            errors.append("Retention period must be positive")

        if policy.retention_period_days > 2555:  # 7 years
            errors.append("Retention period exceeds 7 years - verify necessity")

        if not policy.deletion_method:
            errors.append("Deletion method must be specified")

        if policy.next_review <= policy.last_reviewed:
            errors.append("Next review must be after last review")

        return errors

    @staticmethod
    def validate_user_consent(consent: UserConsent) -> List[str]:
        """Validate user consent record."""
        errors = []

        if not consent.user_id:
            errors.append("User ID is required")

        if not consent.timestamp:
            errors.append("Consent timestamp is required")

        if consent.given and consent.withdrawn_at:
            if consent.withdrawn_at < consent.timestamp:
                errors.append("Withdrawal cannot be before consent")

        if consent.expires_at and consent.expires_at < consent.timestamp:
            errors.append("Expiration cannot be before consent")

        return errors

    @staticmethod
    def validate_gdpr_dpia(dpia_data: Dict) -> List[str]:
        """Validate GDPR DPIA requirements."""
        errors = []
        required_fields = [
            "purpose",
            "necessity_assessment",
            "risk_assessment",
            "mitigation_measures",
        ]

        for field in required_fields:
            if field not in dpia_data or not dpia_data[field]:
                errors.append(f"DPIA requires {field}")

        return errors


class ComplianceManager:
    """Manage compliance across frameworks."""

    def __init__(self):
        """Initialize compliance manager."""
        self.requirements: Dict[str, ComplianceRequirement] = {}
        self.gdpr_data: Optional[GDPRCompliance] = None
        self.soc2_data: Optional[SOC2Compliance] = None
        self.retention_policies: Dict[str, DataRetentionPolicy] = {}
        self.user_consents: Dict[str, UserConsent] = {}
        self.validator = PrivacyValidator()

    def add_requirement(self, requirement: ComplianceRequirement) -> None:
        """Add compliance requirement."""
        self.requirements[requirement.requirement_id] = requirement
        logger.info(f"Added requirement {requirement.requirement_id}")

    def update_requirement_status(
        self, requirement_id: str, status: str, evidence: Optional[List[str]] = None
    ) -> bool:
        """Update requirement status."""
        if requirement_id not in self.requirements:
            return False

        req = self.requirements[requirement_id]
        req.implementation_status = status

        if evidence:
            req.evidence.extend(evidence)

        if status == "verified":
            req.last_verified = datetime.utcnow()

        logger.info(f"Updated requirement {requirement_id} to {status}")
        return True

    def register_gdpr_compliance(self, compliance: GDPRCompliance) -> None:
        """Register GDPR compliance info."""
        self.gdpr_data = compliance
        logger.info("Registered GDPR compliance")

    def register_soc2_compliance(self, compliance: SOC2Compliance) -> None:
        """Register SOC2 compliance info."""
        self.soc2_data = compliance
        logger.info("Registered SOC2 compliance")

    def add_retention_policy(self, policy: DataRetentionPolicy) -> None:
        """Add data retention policy."""
        self.retention_policies[policy.policy_id] = policy
        logger.info(f"Added retention policy {policy.policy_id}")

    def record_consent(self, consent: UserConsent) -> bool:
        """Record user consent."""
        errors = self.validator.validate_user_consent(consent)
        if errors:
            logger.warning(f"Invalid consent: {errors}")
            return False

        self.user_consents[consent.consent_id] = consent
        logger.info(f"Recorded consent {consent.consent_id}")
        return True

    def get_user_consents(self, user_id: str) -> Dict[ConsentType, UserConsent]:
        """Get all consents for user."""
        result = {}
        for consent in self.user_consents.values():
            if consent.user_id == user_id:
                result[consent.consent_type] = consent

        return result

    def check_user_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """Check if user has valid consent."""
        consents = self.get_user_consents(user_id)
        consent = consents.get(consent_type)
        return consent and consent.is_valid() if consent else False

    def get_compliance_status(self) -> Dict:
        """Get overall compliance status."""
        status = {
            "frameworks": {},
            "requirements": {},
            "overall_percentage": 0,
        }

        # GDPR status
        if self.gdpr_data:
            status["frameworks"]["gdpr"] = {
                "compliant": self.gdpr_data.get_compliance_percentage() >= 80,
                "percentage": self.gdpr_data.get_compliance_percentage(),
            }

        # SOC2 status
        if self.soc2_data:
            status["frameworks"]["soc2"] = {
                "current": self.soc2_data.is_current(),
                "expiration": self.soc2_data.expiration_date.isoformat() if self.soc2_data.expiration_date else None,
            }

        # Requirements
        total_reqs = len(self.requirements)
        verified_reqs = sum(
            1
            for r in self.requirements.values()
            if r.implementation_status == "verified"
        )

        status["requirements"] = {
            "total": total_reqs,
            "verified": verified_reqs,
            "percentage": (verified_reqs / total_reqs * 100) if total_reqs > 0 else 0,
        }

        # Overall
        percentages = []
        if "gdpr" in status["frameworks"]:
            percentages.append(status["frameworks"]["gdpr"]["percentage"])
        if status["requirements"]["percentage"]:
            percentages.append(status["requirements"]["percentage"])

        status["overall_percentage"] = (
            sum(percentages) / len(percentages) if percentages else 0
        )

        return status


# Global instance
_compliance_manager: Optional[ComplianceManager] = None


def get_compliance_manager() -> ComplianceManager:
    """Get or create global compliance manager."""
    global _compliance_manager
    if _compliance_manager is None:
        _compliance_manager = ComplianceManager()
    return _compliance_manager
