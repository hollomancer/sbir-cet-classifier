"""CLI commands for award enrichment operations."""

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from sbir_cet_classifier.common.config import EnrichmentConfig
from sbir_cet_classifier.data.enrichment.sam_client import SAMClient

console = Console()


@click.command("enrich-single")
@click.argument("award_id")
@click.option(
    "--types",
    multiple=True,
    type=click.Choice(["awardee", "program_office", "solicitation", "modifications"]),
    help="Enrichment types to perform",
)
@click.option(
    "--output-format",
    "-f",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
@click.option("--api-key", help="SAM.gov API key")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def enrich_single(
    award_id: str,
    types: tuple,
    output_format: str,
    api_key: Optional[str],
    verbose: bool,
):
    """Enrich a single award with SAM.gov data."""
    try:
        # Import here to allow test mocking to work
        from sbir_cet_classifier.cli.commands import EnrichmentService

        # Initialize components
        config = EnrichmentConfig(api_key=api_key or "demo_key")
        sam_client = SAMClient(config)
        enricher = EnrichmentService(sam_client)

        # Convert types to list or None
        enrichment_types = list(types) if types else None

        if verbose:
            console.print(f"[blue]Enriching award: {award_id}[/blue]")
            if enrichment_types:
                console.print(f"[blue]Enrichment types: {', '.join(enrichment_types)}[/blue]")

        # Perform enrichment
        result = enricher.enrich_award(award_id, enrichment_types)

        # Handle both dict (mock) and object (real) responses
        if isinstance(result, dict):
            result_dict = result
        else:
            result_dict = {
                "award_id": result.award_id,
                "status": "completed" if result.success else "failed",
                "confidence_score": result.confidence,
                "enrichment_types": [str(result.enrichment_type)],
                "processing_time_ms": result.processing_time_ms,
            }
            if result.data:
                result_dict["data"] = result.data
            if result.error_message:
                result_dict["error"] = result.error_message

        # Format and display output
        if output_format == "json":
            click.echo(json.dumps(result_dict, indent=2))
        else:
            # Text format
            status = result_dict.get("status", "unknown")
            confidence = result_dict.get("confidence_score", 0)
            enrichment_types_list = result_dict.get("enrichment_types", [])

            if status == "completed":
                console.print(f"[green]✓ Successfully enriched award {award_id}[/green]")
                console.print(f"  Status: {status}")
                console.print(f"  Confidence Score: {confidence:.2%}")
                console.print(f"  Enrichment Types: {', '.join(enrichment_types_list)}")

                if "processing_time_ms" in result_dict:
                    console.print(f"  Processing Time: {result_dict['processing_time_ms']}ms")

                if verbose and "data" in result_dict:
                    console.print("\n[blue]Enrichment Data:[/blue]")
                    for key, value in result_dict["data"].items():
                        console.print(f"  {key}: {value}")
            else:
                click.echo(f"Failed to enrich award {award_id}")
                if "error" in result_dict:
                    click.echo(f"Error: {result_dict['error']}")
                sys.exit(1)

    except Exception as e:
        if output_format == "json":
            error_output = {
                "award_id": award_id,
                "status": "failed",
                "error": str(e),
            }
            click.echo(json.dumps(error_output, indent=2))
        else:
            click.echo(f"Error enriching award: {str(e)}")
        sys.exit(1)


@click.command("enrich-batch")
@click.option(
    "--input-file",
    required=True,
    type=click.Path(exists=True),
    help="Input CSV file with award data",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for results",
)
@click.option(
    "--batch-size",
    type=int,
    default=10,
    help="Batch size for processing",
)
@click.option(
    "--types",
    multiple=True,
    type=click.Choice(["awardee", "program_office", "solicitation", "modifications"]),
    help="Enrichment types to perform",
)
@click.option("--api-key", help="SAM.gov API key")
@click.option("--show-progress", is_flag=True, help="Show progress bar")
@click.option("--parallel", is_flag=True, help="Enable parallel processing")
@click.option("--max-workers", type=int, default=4, help="Maximum parallel workers")
@click.option("--resume", is_flag=True, help="Resume from previous run")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def enrich_batch(
    input_file: str,
    output: Optional[str],
    batch_size: int,
    types: tuple,
    api_key: Optional[str],
    show_progress: bool,
    parallel: bool,
    max_workers: int,
    resume: bool,
    verbose: bool,
):
    """Batch enrich awards from a CSV file."""
    try:
        import csv
        from sbir_cet_classifier.cli.commands import BatchEnrichmentService

        # Initialize batch enrichment service
        config = EnrichmentConfig(api_key=api_key or "demo_key")
        batch_enricher = BatchEnrichmentService(config)

        # Convert types to list or None
        enrichment_types = list(types) if types else None

        # Read input file
        award_ids = []
        with open(input_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "award_id" in row:
                    award_ids.append(row["award_id"])
                elif "id" in row:
                    award_ids.append(row["id"])

        if not award_ids:
            click.echo("No award IDs found in input file")
            sys.exit(1)

        if verbose:
            click.echo(f"Processing {len(award_ids)} awards...")

        # Call batch enrichment service
        if resume:
            result = batch_enricher.resume_batch(
                input_file=input_file,
                output_file=output,
                enrichment_types=enrichment_types,
                batch_size=batch_size,
            )
        else:
            # Progress callback
            def progress_callback(current, total):
                if show_progress or verbose:
                    click.echo(f"Progress: {current}/{total}")

            result = batch_enricher.enrich_batch(
                award_ids=award_ids,
                enrichment_types=enrichment_types,
                batch_size=batch_size,
                parallel=parallel,
                max_workers=max_workers if parallel else 1,
                progress_callback=progress_callback if show_progress else None,
                output_file=output,
            )

        # Display summary
        total_processed = result.get("total_processed", 0)
        successful = result.get("successful", 0)
        failed = result.get("failed", 0)
        success_rate = result.get("success_rate", 0.0)

        click.echo(f"\nSummary:")
        click.echo(f"  Total: {total_processed}")
        click.echo(f"  Successful: {successful}")
        click.echo(f"  Failed: {failed}")
        click.echo(f"  Success Rate: {success_rate:.1%}")

        if resume and "resumed_from" in result:
            click.echo(f"  Resumed from: {result['resumed_from']}")

        if failed > 0:
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error during batch processing: {str(e)}")
        sys.exit(1)


# Create a group for the commands
@click.group(name="enrich", help="Award enrichment commands")
def app():
    """Award enrichment operations."""
    pass


app.add_command(enrich_single)
app.add_command(enrich_batch)


@click.command("enrich-status")
@click.option("--summary", is_flag=True, help="Show summary statistics")
@click.option("--award-id", help="Show status for specific award")
@click.option("--failed-only", is_flag=True, help="Show only failed enrichments")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def enrichment_status(summary: bool, award_id: Optional[str], failed_only: bool, verbose: bool):
    """Show enrichment status and statistics."""
    from sbir_cet_classifier.cli.commands import EnrichmentStatusTracker

    try:
        # Initialize status tracker
        status_tracker = EnrichmentStatusTracker()

        if summary:
            # Get summary statistics
            summary_data = status_tracker.get_summary()

            total = summary_data.get("total", 0)
            completed = summary_data.get("completed", 0)
            failed = summary_data.get("failed", 0)
            pending = summary_data.get("pending", 0)
            success_rate = summary_data.get("success_rate", 0.0)

            click.echo("Enrichment Summary:")
            click.echo(f"  Total: {total}")
            click.echo(f"  Completed: {completed}")
            click.echo(f"  Failed: {failed}")
            click.echo(f"  Pending: {pending}")
            click.echo(f"  Success Rate: {success_rate:.0%}")

        elif award_id:
            # Get status for specific award
            status = status_tracker.get_status(award_id)

            if status:
                click.echo(f"Award ID: {status.award_id}")
                click.echo(
                    f"Status: {status.status.value if hasattr(status.status, 'value') else str(status.status).lower()}"
                )
                click.echo(f"Confidence Score: {status.confidence_score:.2%}")
                click.echo(
                    f"Enrichment Types: {', '.join(str(t) for t in status.enrichment_types)}"
                )
                click.echo(f"Last Updated: {status.last_updated}")

                if status.error_message:
                    click.echo(f"Error: {status.error_message}")

                if status.data_sources:
                    click.echo(f"Data Sources: {', '.join(status.data_sources)}")
            else:
                click.echo(f"No status found for award {award_id}")
                sys.exit(1)

        elif failed_only:
            # Import StatusState
            from sbir_cet_classifier.data.enrichment.status import StatusState

            # List only failed enrichments
            failed_statuses = status_tracker.list_statuses(status_filter=StatusState.FAILED)

            if failed_statuses:
                click.echo(f"Failed Enrichments ({len(failed_statuses)}):")
                for status in failed_statuses:
                    award_id_val = status.award_id
                    error_msg = status.error_message or "Unknown error"
                    click.echo(f"  {award_id_val}: {error_msg}")
            else:
                click.echo("No failed enrichments found")
        else:
            # Default: show basic status
            summary_data = status_tracker.get_summary()
            total = summary_data.get("total", 0)
            completed = summary_data.get("completed", 0)
            failed = summary_data.get("failed", 0)

            click.echo(f"Total enrichments: {total}")
            click.echo(f"Completed: {completed}")
            click.echo(f"Failed: {failed}")

    except Exception as e:
        if verbose:
            click.echo(f"Error retrieving status: {str(e)}")
        # Don't exit with error for status command


app.add_command(enrichment_status)


@click.command("enrich-awardee")
@click.argument("award_id")
@click.option("--min-confidence", type=float, default=0.0, help="Minimum confidence threshold")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def enrich_awardee(award_id: str, min_confidence: float, verbose: bool):
    """Enrich awardee information for an award."""
    from sbir_cet_classifier.cli.commands import AwardeeEnrichmentService

    try:
        # Initialize awardee enrichment service
        awardee_service = AwardeeEnrichmentService()

        # Enrich awardee
        result = awardee_service.enrich_awardee(award_id)

        # Handle both dict (mock) and object (real) responses
        if isinstance(result, dict):
            result_dict = result
        else:
            result_dict = {
                "award_id": getattr(result, "award_id", award_id),
                "awardee_uei": getattr(result, "awardee_uei", None),
                "confidence_score": getattr(result, "confidence_score", 0.0),
                "data_sources": getattr(result, "data_sources", []),
            }

        award_id_val = result_dict.get("award_id", award_id)
        confidence_score = result_dict.get("confidence_score", 0.0)
        awardee_uei = result_dict.get("awardee_uei", "Unknown")
        data_sources = result_dict.get("data_sources", [])

        click.echo(f"Award ID: {award_id_val}")
        click.echo(f"Awardee UEI: {awardee_uei}")
        click.echo(f"Confidence Score: {confidence_score:.2%}")

        if data_sources:
            click.echo(f"Data Sources: {', '.join(data_sources)}")

        # Warn if confidence is below threshold
        if min_confidence > 0 and confidence_score < min_confidence:
            click.echo(
                f"Warning: Confidence score ({confidence_score:.2%}) is below threshold ({min_confidence:.2%})"
            )

    except Exception as e:
        click.echo(f"Error enriching awardee: {str(e)}")
        sys.exit(1)


@click.command("enrich-program")
@click.argument("award_id")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def enrich_program(award_id: str, verbose: bool):
    """Enrich program office information for an award."""
    from sbir_cet_classifier.cli.commands import ProgramOfficeEnrichmentService

    try:
        # Initialize program office enrichment service
        program_service = ProgramOfficeEnrichmentService()

        # Enrich program office
        result = program_service.enrich_program_office(award_id)

        # Handle both dict (mock) and object (real) responses
        if isinstance(result, dict):
            result_dict = result
        else:
            result_dict = {
                "award_id": getattr(result, "award_id", award_id),
                "agency": getattr(result, "agency", None),
                "office_name": getattr(result, "office_name", None),
                "strategic_focus": getattr(result, "strategic_focus", []),
            }

        award_id_val = result_dict.get("award_id", award_id)
        agency = result_dict.get("agency", "Unknown")
        office_name = result_dict.get("office_name", "Unknown")
        strategic_focus = result_dict.get("strategic_focus", [])

        click.echo(f"Award ID: {award_id_val}")
        click.echo(f"Agency: {agency}")
        click.echo(f"Office Name: {office_name}")

        if strategic_focus:
            click.echo(f"Strategic Focus: {', '.join(strategic_focus)}")

    except Exception as e:
        click.echo(f"Error enriching program office: {str(e)}")
        sys.exit(1)


@click.command("enrich-modifications")
@click.argument("award_id")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def enrich_modifications(award_id: str, verbose: bool):
    """Enrich award modifications information."""
    from sbir_cet_classifier.cli.commands import ModificationsEnrichmentService

    try:
        # Initialize modifications enrichment service
        modifications_service = ModificationsEnrichmentService()

        # Enrich modifications
        result = modifications_service.enrich_modifications(award_id)

        # Handle both dict (mock) and object (real) responses
        if isinstance(result, dict):
            result_dict = result
        else:
            result_dict = {
                "award_id": getattr(result, "award_id", award_id),
                "modification_count": getattr(result, "modification_count", 0),
                "total_value_change": getattr(result, "total_value_change", 0.0),
            }

        award_id_val = result_dict.get("award_id", award_id)
        modification_count = result_dict.get("modification_count", 0)
        total_value_change = result_dict.get("total_value_change", 0.0)

        click.echo(f"Award ID: {award_id_val}")
        click.echo(f"Modifications: {modification_count}")
        click.echo(f"Total Value Change: ${total_value_change:,.2f}")

    except Exception as e:
        click.echo(f"Error enriching modifications: {str(e)}")
        sys.exit(1)


@click.command("enrich-solicitation")
@click.argument("award_id")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def enrich_solicitation(award_id: str, verbose: bool):
    """Enrich solicitation information for an award."""
    from sbir_cet_classifier.cli.commands import SolicitationEnrichmentService

    try:
        # Initialize solicitation enrichment service
        solicitation_service = SolicitationEnrichmentService()

        # Enrich solicitation
        result = solicitation_service.enrich_solicitation(award_id)

        # Handle both dict (mock) and object (real) responses
        if isinstance(result, dict):
            result_dict = result
        else:
            result_dict = {
                "award_id": getattr(result, "award_id", award_id),
                "solicitation_id": getattr(result, "solicitation_id", None),
                "technical_requirements": getattr(result, "technical_requirements", []),
                "topic_areas": getattr(result, "topic_areas", []),
            }

        award_id_val = result_dict.get("award_id", award_id)
        solicitation_id = result_dict.get("solicitation_id", "Unknown")
        technical_requirements = result_dict.get("technical_requirements", [])
        topic_areas = result_dict.get("topic_areas", [])

        click.echo(f"Award ID: {award_id_val}")
        click.echo(f"Solicitation ID: {solicitation_id}")

        if technical_requirements:
            click.echo(f"Technical Requirements: {', '.join(technical_requirements)}")

        if topic_areas:
            click.echo(f"Topic Areas: {', '.join(topic_areas)}")

    except Exception as e:
        click.echo(f"Error enriching solicitation: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    app()
