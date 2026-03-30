"""Unit tests for domain entities."""

import pytest
from datetime import datetime
from core.domain.entities import Signal, Report, Company, MarketEvent, AgentPolicy
from core.domain.value_objects import EntityID, Money, Timestamp, Confidence


# ============================================================================
# Signal Entity Tests
# ============================================================================


class TestSignalEntity:
    """Test Signal entity."""

    def test_signal_creation(self, sample_signal_data):
        """Test creating a signal."""
        signal = Signal(
            id=sample_signal_data["id"],
            title=sample_signal_data["title"],
            source=sample_signal_data["source"],
            severity=sample_signal_data["severity"],
            signal_type=sample_signal_data["signal_type"],
            verified=sample_signal_data["verified"],
        )
        
        assert signal.id == sample_signal_data["id"]
        assert signal.title == sample_signal_data["title"]
        assert signal.severity == sample_signal_data["severity"]
        assert signal.verified is True

    def test_signal_verification(self, sample_signal_data):
        """Test signal verification."""
        signal = Signal(
            id=sample_signal_data["id"],
            title=sample_signal_data["title"],
            source=sample_signal_data["source"],
            severity=sample_signal_data["severity"],
            signal_type=sample_signal_data["signal_type"],
            verified=False,
        )
        
        assert signal.verified is False
        signal.verify()
        assert signal.verified is True

    def test_signal_enrichment(self, sample_signal_data):
        """Test signal enrichment."""
        signal = Signal(
            id=sample_signal_data["id"],
            title=sample_signal_data["title"],
            source=sample_signal_data["source"],
            severity=sample_signal_data["severity"],
            signal_type=sample_signal_data["signal_type"],
            verified=sample_signal_data["verified"],
        )
        
        enrichment_data = {
            "sentiment": "POSITIVE",
            "entities": ["Company A", "Company B"],
            "keywords": ["partnership", "expansion"],
        }
        
        signal.enrich(enrichment_data)
        assert signal.enrichment_data == enrichment_data


# ============================================================================
# Report Entity Tests
# ============================================================================


class TestReportEntity:
    """Test Report entity."""

    def test_report_creation(self, sample_report_data):
        """Test creating a report."""
        report = Report(
            id=sample_report_data["id"],
            company_id="comp_123",
            report_type=sample_report_data["report_type"],
            content=sample_report_data["content"],
        )
        
        assert report.id == sample_report_data["id"]
        assert report.company_id == "comp_123"
        assert report.report_type == sample_report_data["report_type"]

    def test_report_sections(self, sample_report_data):
        """Test report sections."""
        report = Report(
            id=sample_report_data["id"],
            company_id="comp_123",
            report_type=sample_report_data["report_type"],
            content=sample_report_data["content"],
        )
        
        report.add_section("executive_summary", "Summary content here")
        report.add_section("analysis", "Analysis content here")
        
        assert "executive_summary" in report.sections
        assert "analysis" in report.sections
        assert len(report.sections) == 2


# ============================================================================
# Company Entity Tests
# ============================================================================


class TestCompanyEntity:
    """Test Company entity."""

    def test_company_creation(self, sample_company_data):
        """Test creating a company."""
        company = Company(
            id=sample_company_data["id"],
            name=sample_company_data["name"],
            domain=sample_company_data["domain"],
            status=sample_company_data["status"],
        )
        
        assert company.id == sample_company_data["id"]
        assert company.name == sample_company_data["name"]
        assert company.domain == sample_company_data["domain"]

    def test_company_competitors(self, sample_company_data):
        """Test managing company competitors."""
        company = Company(
            id=sample_company_data["id"],
            name=sample_company_data["name"],
            domain=sample_company_data["domain"],
            status=sample_company_data["status"],
        )
        
        company.add_competitor("CompetitorA")
        company.add_competitor("CompetitorB")
        
        assert "CompetitorA" in company.competitors
        assert "CompetitorB" in company.competitors

    def test_company_markets(self, sample_company_data):
        """Test managing company markets."""
        company = Company(
            id=sample_company_data["id"],
            name=sample_company_data["name"],
            domain=sample_company_data["domain"],
            status=sample_company_data["status"],
        )
        
        company.add_market("SaaS")
        company.add_market("AI/ML")
        
        assert "SaaS" in company.markets
        assert "AI/ML" in company.markets


# ============================================================================
# MarketEvent Entity Tests
# ============================================================================


class TestMarketEventEntity:
    """Test MarketEvent entity."""

    def test_market_event_creation(self):
        """Test creating a market event."""
        event = MarketEvent(
            id="event_123",
            market="SaaS",
            event_type="ACQUISITION",
            description="Company acquired startup",
            importance="HIGH",
        )
        
        assert event.id == "event_123"
        assert event.market == "SaaS"
        assert event.event_type == "ACQUISITION"

    def test_market_event_impact(self):
        """Test market event impact."""
        event = MarketEvent(
            id="event_123",
            market="SaaS",
            event_type="ACQUISITION",
            description="Company acquired startup",
            importance="HIGH",
        )
        
        event.set_impact_score(8.5)
        assert event.impact_score == 8.5


# ============================================================================
# AgentPolicy Entity Tests
# ============================================================================


class TestAgentPolicyEntity:
    """Test AgentPolicy entity."""

    def test_policy_creation(self):
        """Test creating an agent policy."""
        policy = AgentPolicy(
            id="policy_123",
            agent_type="research",
            rules={"max_searches": 10, "timeout": 300},
        )
        
        assert policy.id == "policy_123"
        assert policy.agent_type == "research"
        assert policy.rules["max_searches"] == 10

    def test_policy_enable_disable(self):
        """Test enabling/disabling policy."""
        policy = AgentPolicy(
            id="policy_123",
            agent_type="research",
            rules={},
        )
        
        assert policy.enabled is True
        policy.disable()
        assert policy.enabled is False
        policy.enable()
        assert policy.enabled is True


# ============================================================================
# Value Object Tests
# ============================================================================


class TestEntityID:
    """Test EntityID value object."""

    def test_id_creation(self):
        """Test creating an ID."""
        id_obj = EntityID("comp_123")
        assert id_obj.value == "comp_123"

    def test_id_equality(self):
        """Test ID equality."""
        id1 = EntityID("comp_123")
        id2 = EntityID("comp_123")
        id3 = EntityID("comp_456")
        
        assert id1 == id2
        assert id1 != id3

    def test_id_immutable(self):
        """Test ID immutability."""
        id_obj = EntityID("comp_123")
        
        with pytest.raises(AttributeError):
            id_obj.value = "comp_456"


class TestMoney:
    """Test Money value object."""

    def test_money_creation(self):
        """Test creating money object."""
        money = Money(1000.00, "USD")
        assert money.amount == 1000.00
        assert money.currency == "USD"

    def test_money_addition(self):
        """Test money addition."""
        money1 = Money(100.00, "USD")
        money2 = Money(50.00, "USD")
        
        result = money1 + money2
        assert result.amount == 150.00
        assert result.currency == "USD"

    def test_money_comparison(self):
        """Test money comparison."""
        money1 = Money(100.00, "USD")
        money2 = Money(50.00, "USD")
        
        assert money1 > money2
        assert money2 < money1


class TestTimestamp:
    """Test Timestamp value object."""

    def test_timestamp_creation(self):
        """Test creating timestamp."""
        now = datetime.now()
        ts = Timestamp(now)
        assert ts.value == now

    def test_timestamp_string_representation(self):
        """Test timestamp string conversion."""
        now = datetime.now()
        ts = Timestamp(now)
        assert str(ts) == now.isoformat()


class TestConfidence:
    """Test Confidence value object."""

    def test_confidence_creation(self):
        """Test creating confidence."""
        conf = Confidence(0.85)
        assert conf.value == 0.85

    def test_confidence_validation(self):
        """Test confidence validation."""
        with pytest.raises(ValueError):
            Confidence(1.5)  # > 1.0
        
        with pytest.raises(ValueError):
            Confidence(-0.1)  # < 0.0

    def test_confidence_levels(self):
        """Test confidence level categorization."""
        low = Confidence(0.3)
        medium = Confidence(0.6)
        high = Confidence(0.9)
        
        assert low.level == "LOW"
        assert medium.level == "MEDIUM"
        assert high.level == "HIGH"
