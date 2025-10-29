"""CLI commands for award enrichment operations."""

import json
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
                console.print(f"[red]✗ Failed to enrich award {award_id}[/red]")
                if "error" in result_dict:
                    console.print(f"  Error: {result_dict['error']}")
                raise click.Exit(1)

    except click.Exit:
        raise
    except Exception as e:
        if output_format == "json":
            error_output = {
                "award_id": award_id,
                "status": "failed",
                "error": str(e),
            }
            click.echo(json.dumps(error_output, indent=2))
        else:
            console.print(f"[red]Error enriching award: {str(e)}[/red]")
        raise click.Exit(1)


@click.command("enrich-batch")
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file for results",
)
@click.option(
    "--types",
    multiple=True,
    type=click.Choice(["awardee", "program_office", "solicitation", "modifications"]),
    help="Enrichment types to perform",
)
@click.option("--api-key", help="SAM.gov API key")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def enrich_batch(
    input_file: str,
    output: Optional[str],
    types: tuple,
    api_key: Optional[str],
    verbose: bool,
):
    """Batch enrich awards from a CSV file."""
    try:
        import csv
        from sbir_cet_classifier.cli.commands import EnrichmentService

        # Initialize components
        config = EnrichmentConfig(api_key=api_key or "demo_key")
        sam_client = SAMClient(config)
        enricher = EnrichmentService(sam_client)

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
            console.print("[red]No award IDs found in input file[/red]")
            raise click.Exit(1)

        console.print(f"[blue]Processing {len(award_ids)} awards...[/blue]")

        # Process awards
        results = []
        successful = 0
        failed = 0

        for i, award_id in enumerate(award_ids, 1):
            try:
                result = enricher.enrich_award(award_id, enrichment_types)

                # Handle both dict (mock) and object (real) responses
                if isinstance(result, dict):
                    result_dict = result
                    result_success = result_dict.get("status") == "completed"
                else:
                    result_success = result.success
                    result_dict = {
                        "award_id": result.award_id,
                        "status": "completed" if result.success else "failed",
                        "confidence_score": result.confidence,
                        "error": result.error_message,
                    }

                results.append(result_dict)

                if result_success:
                    successful += 1
                    if verbose:
                        console.print(f"  [{i}/{len(award_ids)}] ✓ {award_id}")
                else:
                    failed += 1
                    error_msg = result_dict.get("error", "Unknown error")
                    if verbose:
                        console.print(f"  [{i}/{len(award_ids)}] ✗ {award_id}: {error_msg}")
            except Exception as e:
                failed += 1
                results.append(
                    {
                        "award_id": award_id,
                        "status": "failed",
                        "error": str(e),
                    }
                )
                if verbose:
                    console.print(f"  [{i}/{len(award_ids)}] ✗ {award_id}: {str(e)}")

        # Output results
        if output:
            with open(output, "w") as f:
                json.dump(results, f, indent=2)
            console.print(f"[green]Results saved to {output}[/green]")

        # Display summary
        console.print(f"\n[blue]Summary:[/blue]")
        console.print(f"  Total: {len(award_ids)}")
        console.print(f"  [green]Successful: {successful}[/green]")
        console.print(f"  [red]Failed: {failed}[/red]")
        console.print(f"  Success Rate: {(successful / len(award_ids)):.1%}")

        if failed > 0:
            raise click.Exit(1)

    except click.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error during batch processing: {str(e)}[/red]")
        raise click.Exit(1)


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
