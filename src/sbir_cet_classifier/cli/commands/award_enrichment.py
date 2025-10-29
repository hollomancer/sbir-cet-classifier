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
@click.option(
    "--data-dir",
    "-d",
    type=click.Path(),
    default="data/processed",
    help="Data directory",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def enrichment_status(data_dir: str, verbose: bool):
    """Show enrichment status and statistics."""
    from pathlib import Path
    from rich.table import Table

    data_path = Path(data_dir)

    table = Table(title="Enrichment Status")
    table.add_column("Data Type", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Records", style="green")
    table.add_column("File Size", style="blue")

    # Check for enrichment files
    enrichment_file = data_path / "enrichment_results.json"

    if enrichment_file.exists():
        try:
            with open(enrichment_file, "r") as f:
                results = json.load(f)

            file_size = enrichment_file.stat().st_size
            successful = sum(1 for r in results if r.get("status") == "completed")

            table.add_row(
                "Enrichment Results",
                "✓ Available",
                str(len(results)),
                f"{file_size / 1024:.1f} KB",
            )

            if verbose:
                console.print(table)
                console.print(f"\n[cyan]Enrichment Summary:[/cyan]")
                console.print(f"  Total records: {len(results)}")
                console.print(f"  Successful: {successful}")
                console.print(f"  Failed: {len(results) - successful}")

                if results:
                    avg_confidence = sum(r.get("confidence_score", 0) for r in results) / len(
                        results
                    )
                    console.print(f"  Average confidence: {avg_confidence:.1%}")
                return
        except Exception as e:
            table.add_row("Enrichment Results", f"✗ Error: {str(e)}", "0", "0 KB")
    else:
        table.add_row("Enrichment Results", "✗ Not found", "0", "0 KB")

    console.print(table)


app.add_command(enrichment_status)


if __name__ == "__main__":
    app()
