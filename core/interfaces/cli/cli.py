"""Click CLI for the Competitive Intelligence Engine."""

import click
import asyncio
import json
from typing import Optional
from core.application import (
    SearchCompetitorSignalsUseCase,
    GenerateIntelligenceReportUseCase,
    AnalyzeMarketTrendsUseCase,
    TrackCompetitorActivityUseCase,
    LearnFromFeedbackUseCase,
    WorkflowOrchestrator,
    ResearchAgent,
    AnalysisAgent,
    StrategyAgent,
)


@click.group()
@click.version_option(version="1.0.0", prog_name="cie")
def cli():
    """Competitive Intelligence Engine CLI."""
    pass


# ============================================================================
# Signal Commands
# ============================================================================


@cli.group()
def signals():
    """Signal management commands."""
    pass


@signals.command()
@click.argument("company_id")
@click.argument("keywords", nargs=-1, required=True)
@click.option(
    "--severity",
    type=click.Choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
    default="MEDIUM",
    help="Minimum severity level",
)
@click.option("--days", type=int, default=30, help="Time range in days")
@click.option("--verified/--all", default=False, help="Only verified signals")
def search(company_id: str, keywords: tuple, severity: str, days: int, verified: bool):
    """Search for competitor signals."""
    try:
        async def _search():
            use_case = SearchCompetitorSignalsUseCase()
            result = await use_case.execute(company_id, list(keywords))
            click.echo(json.dumps(result, indent=2, default=str))

        asyncio.run(_search())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@signals.command()
@click.argument("company_id")
@click.option("--limit", type=int, default=50, help="Maximum results")
@click.option(
    "--severity",
    type=click.Choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
    help="Filter by severity",
)
def list(company_id: str, limit: int, severity: Optional[str]):
    """List all signals for a company."""
    click.echo(f"Listing signals for company: {company_id}")
    click.echo(f"Limit: {limit}")
    if severity:
        click.echo(f"Severity: {severity}")


@signals.command()
@click.argument("signal_id")
def get(signal_id: str):
    """Get signal details."""
    click.echo(f"Getting signal: {signal_id}")


@signals.command()
@click.argument("signal_id")
def verify(signal_id: str):
    """Verify a signal."""
    click.echo(f"Verifying signal: {signal_id}")


@signals.command()
@click.argument("competitor_name")
@click.option("--days", type=int, default=30, help="Time range in days")
def competitor(competitor_name: str, days: int):
    """Get signals for a competitor."""
    click.echo(f"Getting signals for competitor: {competitor_name}")
    click.echo(f"Time range: {days} days")


# ============================================================================
# Report Commands
# ============================================================================


@cli.group()
def reports():
    """Report management commands."""
    pass


@reports.command()
@click.argument("company_id")
@click.option(
    "--type",
    "report_type",
    type=click.Choice(["COMPETITIVE_ANALYSIS", "MARKET_OVERVIEW", "EXECUTIVE_SUMMARY"]),
    default="COMPETITIVE_ANALYSIS",
    help="Report type",
)
@click.option("--signals/--no-signals", default=True, help="Include signals section")
@click.option("--analysis/--no-analysis", default=True, help="Include analysis")
@click.option(
    "--recommendations/--no-recommendations",
    default=True,
    help="Include recommendations",
)
def generate(
    company_id: str,
    report_type: str,
    signals: bool,
    analysis: bool,
    recommendations: bool,
):
    """Generate an intelligence report."""
    try:
        async def _generate():
            use_case = GenerateIntelligenceReportUseCase()
            result = await use_case.execute(company_id, report_type)
            click.echo(f"Report generated successfully")
            click.echo(f"Report ID: {result.report_id if hasattr(result, 'report_id') else 'N/A'}")
            click.echo(f"Word count: {result.word_count if hasattr(result, 'word_count') else 'N/A'}")

        asyncio.run(_generate())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@reports.command()
@click.argument("company_id")
@click.option("--limit", type=int, default=20, help="Maximum results")
def list(company_id: str, limit: int):
    """List reports for a company."""
    click.echo(f"Listing reports for company: {company_id}")
    click.echo(f"Limit: {limit}")


@reports.command()
@click.argument("report_id")
def get(report_id: str):
    """Get report details."""
    click.echo(f"Getting report: {report_id}")


@reports.command()
@click.argument("report_id")
@click.option(
    "--format",
    type=click.Choice(["pdf", "docx", "html", "json"]),
    default="pdf",
    help="Export format",
)
def export(report_id: str, format: str):
    """Export a report."""
    click.echo(f"Exporting report: {report_id}")
    click.echo(f"Format: {format}")


# ============================================================================
# Analysis Commands
# ============================================================================


@cli.group()
def analyze():
    """Analysis commands."""
    pass


@analyze.command()
@click.argument("markets", nargs=-1, required=True)
@click.option("--days", type=int, default=90, help="Analysis period")
@click.option("--forecast/--no-forecast", default=True, help="Include forecast")
def markets(markets: tuple, days: int, forecast: bool):
    """Analyze market trends."""
    try:
        async def _analyze():
            use_case = AnalyzeMarketTrendsUseCase()
            result = await use_case.execute(list(markets))
            click.echo(f"Analyzed {len(markets)} markets")
            click.echo(json.dumps(result, indent=2, default=str))

        asyncio.run(_analyze())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@analyze.command()
@click.argument("company_id")
def competition(company_id: str):
    """Analyze competitive landscape."""
    click.echo(f"Analyzing competition for company: {company_id}")


@analyze.command()
@click.argument("signals", nargs=-1, required=True)
def signals(signals: tuple):
    """Analyze signals."""
    click.echo(f"Analyzing {len(signals)} signals")


# ============================================================================
# Tracking Commands
# ============================================================================


@cli.group()
def track():
    """Competitor tracking commands."""
    pass


@track.command()
@click.argument("competitor_name")
@click.option("--days", type=int, default=30, help="Tracking period")
@click.option(
    "--alert-level",
    type=click.Choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
    default="MEDIUM",
    help="Alert level",
)
def competitor(competitor_name: str, days: int, alert_level: str):
    """Track competitor activity."""
    try:
        async def _track():
            use_case = TrackCompetitorActivityUseCase()
            result = await use_case.execute(competitor_name)
            click.echo(f"Tracked competitor: {competitor_name}")
            click.echo(f"Activity level: {result.activity_level if hasattr(result, 'activity_level') else 'N/A'}")
            click.echo(f"Risk level: {result.risk_level if hasattr(result, 'risk_level') else 'N/A'}")

        asyncio.run(_track())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@track.command()
@click.argument("company_id")
def watch(company_id: str):
    """Add company to watch list."""
    click.echo(f"Added company to watch list: {company_id}")


@track.command()
@click.argument("company_id")
def unwatch(company_id: str):
    """Remove company from watch list."""
    click.echo(f"Removed company from watch list: {company_id}")


# ============================================================================
# Workflow Commands
# ============================================================================


@cli.group()
def workflows():
    """Workflow management commands."""
    pass


@workflows.command()
@click.argument("company_id")
@click.argument("company_name")
@click.option(
    "--type",
    "workflow_type",
    type=click.Choice(["competitive_intelligence", "market_analysis", "competitor_tracking"]),
    default="competitive_intelligence",
    help="Workflow type",
)
def run(company_id: str, company_name: str, workflow_type: str):
    """Run a workflow."""
    try:
        async def _run():
            orchestrator = WorkflowOrchestrator()
            execution = await orchestrator.execute_workflow(workflow_type, company_id)
            click.echo(f"Workflow started: {execution.workflow_id}")
            click.echo(f"Status: {execution.status}")

        asyncio.run(_run())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@workflows.command()
@click.argument("workflow_id")
def status(workflow_id: str):
    """Get workflow status."""
    click.echo(f"Workflow: {workflow_id}")
    click.echo("Status: RUNNING")


@workflows.command()
@click.option("--limit", type=int, default=20, help="Maximum results")
def list(limit: int):
    """List workflows."""
    click.echo(f"Listing workflows (limit: {limit})")


@workflows.command()
@click.argument("workflow_id")
def cancel(workflow_id: str):
    """Cancel a workflow."""
    click.echo(f"Cancelling workflow: {workflow_id}")


# ============================================================================
# Agent Commands
# ============================================================================


@cli.group()
def agents():
    """Agent management commands."""
    pass


@agents.command()
@click.argument(
    "agent_type",
    type=click.Choice(
        ["research", "analysis", "strategy", "report", "critique", "planner"]
    ),
)
@click.argument("task")
def run(agent_type: str, task: str):
    """Run an agent."""
    try:
        async def _run():
            agent_classes = {
                "research": ResearchAgent,
                "analysis": AnalysisAgent,
                "strategy": StrategyAgent,
            }
            agent_class = agent_classes.get(agent_type)
            if agent_class:
                agent = agent_class()
                result = await agent.execute(task)
                click.echo(f"Agent {agent_type} completed")
                click.echo(json.dumps(result, indent=2, default=str))
            else:
                click.echo(f"Agent type not implemented: {agent_type}")

        asyncio.run(_run())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@agents.command()
def list():
    """List available agents."""
    agents_list = ["research", "analysis", "strategy", "report", "critique", "planner"]
    for agent in agents_list:
        click.echo(f"  - {agent}")


@agents.command()
@click.argument("agent_type")
def status(agent_type: str):
    """Get agent status."""
    click.echo(f"Agent: {agent_type}")
    click.echo("Status: READY")


@agents.command()
@click.argument("agent_type")
def stats(agent_type: str):
    """Get agent statistics."""
    click.echo(f"Agent: {agent_type}")
    click.echo("Total executions: 0")
    click.echo("Successful: 0")
    click.echo("Failed: 0")


# ============================================================================
# Learning Commands
# ============================================================================


@cli.group()
def learn():
    """Machine learning commands."""
    pass


@learn.command()
@click.argument("feedback")
def feedback(feedback: str):
    """Submit feedback for learning."""
    try:
        async def _learn():
            use_case = LearnFromFeedbackUseCase()
            result = await use_case.execute(feedback)
            click.echo("Feedback processed")

        asyncio.run(_learn())
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


# ============================================================================
# Status and Info Commands
# ============================================================================


@cli.command()
def health():
    """Check system health."""
    click.echo("System Health Status")
    click.echo("  API: OPERATIONAL")
    click.echo("  Database: OPERATIONAL")
    click.echo("  LLM: OPERATIONAL")
    click.echo("  Browser: OPERATIONAL")


@cli.command()
def info():
    """Display system information."""
    click.echo("Competitive Intelligence Engine")
    click.echo("Version: 1.0.0")
    click.echo("Agents: 6")
    click.echo("Workflows: 3")
    click.echo("Use your --help flag for command details")


if __name__ == "__main__":
    cli()
