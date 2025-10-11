"""CLI commands for enrichment operations."""

import asyncio
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..data.enrichment.solicitation_service import SolicitationService
from ..data.enrichment.batch_processor import SolicitationBatchProcessor
from ..data.storage import SolicitationStorage
from ..data.enrichment.sam_client import SAMClient

console = Console()
app = typer.Typer(name="enrich", help="Enrichment commands for SAM.gov data")


@app.command("solicitation")
def enrich_solicitation(
    solicitation_number: str = typer.Argument(..., help="Solicitation number to enrich"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="SAM.gov API key"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
):
    """Enrich a single solicitation with SAM.gov data."""
    
    if verbose:
        console.print(f"[blue]Enriching solicitation: {solicitation_number}[/blue]")
    
    # Initialize components
    sam_client = SAMClient(api_key=api_key or "demo_key")
    solicitation_service = SolicitationService(sam_client)
    
    # Set up storage
    if output_file:
        storage = SolicitationStorage(output_file)
    else:
        storage = SolicitationStorage(Path("data/processed/solicitations.parquet"))
    
    async def enrich_single():
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Retrieving solicitation data...", total=None)
                
                solicitation = await solicitation_service.get_solicitation_by_number(solicitation_number)
                
                if not solicitation:
                    console.print(f"[red]Solicitation {solicitation_number} not found[/red]")
                    return
                
                progress.update(task, description="Saving to storage...")
                storage.save_solicitations([solicitation])
                
                progress.update(task, description="Complete!")
                
                if verbose:
                    # Display solicitation details
                    table = Table(title=f"Solicitation {solicitation_number}")
                    table.add_column("Field", style="cyan")
                    table.add_column("Value", style="white")
                    
                    table.add_row("Title", solicitation.title)
                    table.add_row("Agency", solicitation.agency_code)
                    table.add_row("Type", solicitation.solicitation_type)
                    table.add_row("Funding Range", f"${solicitation.funding_range_min:,.0f} - ${solicitation.funding_range_max:,.0f}")
                    table.add_row("Performance Period", f"{solicitation.performance_period} months")
                    table.add_row("Keywords", ", ".join(solicitation.keywords[:5]))
                    
                    console.print(table)
                
                console.print(f"[green]Successfully enriched solicitation {solicitation_number}[/green]")
                
        except Exception as e:
            console.print(f"[red]Error enriching solicitation: {str(e)}[/red]")
            raise typer.Exit(1)
    
    # Run async function
    asyncio.run(enrich_single())


@app.command("batch-solicitations")
def enrich_batch_solicitations(
    input_file: Path = typer.Argument(..., help="Input CSV file with award data"),
    output_dir: Path = typer.Option(Path("data/processed"), "--output-dir", "-o", help="Output directory"),
    batch_size: int = typer.Option(10, "--batch-size", "-b", help="Batch size for processing"),
    max_concurrent: int = typer.Option(3, "--max-concurrent", "-c", help="Maximum concurrent requests"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="SAM.gov API key"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--no-skip-existing", help="Skip existing solicitations"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
):
    """Batch enrich solicitations from award data."""
    
    if not input_file.exists():
        console.print(f"[red]Input file not found: {input_file}[/red]")
        raise typer.Exit(1)
    
    # Load award data
    import pandas as pd
    try:
        df = pd.read_csv(input_file)
        awards = df.to_dict('records')
    except Exception as e:
        console.print(f"[red]Error reading input file: {str(e)}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[blue]Processing {len(awards)} awards for solicitation enrichment[/blue]")
    
    # Initialize components
    sam_client = SAMClient(api_key=api_key or "demo_key")
    output_dir.mkdir(parents=True, exist_ok=True)
    storage = SolicitationStorage(output_dir / "solicitations.parquet")
    
    batch_processor = SolicitationBatchProcessor(
        sam_client=sam_client,
        storage=storage,
        batch_size=batch_size,
        max_concurrent=max_concurrent
    )
    
    async def process_batch():
        try:
            with Progress(console=console) as progress:
                task = progress.add_task("Processing solicitations...", total=len(awards))
                
                def progress_callback(current, total, status):
                    progress.update(task, completed=current)
                
                results = await batch_processor.process_batch(
                    awards,
                    skip_existing=skip_existing,
                    save_to_storage=True,
                    max_retries=2,
                    progress_callback=progress_callback
                )
                
                # Display results
                console.print(f"\n[green]{results.get_summary()}[/green]")
                
                if verbose and results.failed:
                    console.print("\n[red]Failed solicitations:[/red]")
                    for award_id, error in results.failed:
                        console.print(f"  {award_id}: {error}")
                
                if results.success_rate < 0.8:
                    console.print(f"[yellow]Warning: Low success rate ({results.success_rate:.1%})[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error during batch processing: {str(e)}[/red]")
            raise typer.Exit(1)
    
    # Run async function
    asyncio.run(process_batch())


@app.command("status")
def enrichment_status(
    data_dir: Path = typer.Option(Path("data/processed"), "--data-dir", "-d", help="Data directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
):
    """Show enrichment status and statistics."""
    
    # Check for enrichment files
    solicitations_file = data_dir / "solicitations.parquet"
    
    table = Table(title="Enrichment Status")
    table.add_column("Data Type", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Records", style="green")
    table.add_column("File Size", style="blue")
    
    if solicitations_file.exists():
        try:
            storage = SolicitationStorage(solicitations_file)
            solicitations = storage.load_solicitations()
            file_size = solicitations_file.stat().st_size
            
            table.add_row(
                "Solicitations",
                "✓ Available",
                str(len(solicitations)),
                f"{file_size / 1024 / 1024:.1f} MB"
            )
            
            if verbose and solicitations:
                # Show sample data
                console.print(table)
                console.print("\n[blue]Sample solicitations:[/blue]")
                
                sample_table = Table()
                sample_table.add_column("ID", style="cyan")
                sample_table.add_column("Title", style="white")
                sample_table.add_column("Agency", style="green")
                sample_table.add_column("Keywords", style="blue")
                
                for sol in solicitations[:5]:
                    sample_table.add_row(
                        sol.solicitation_id,
                        sol.title[:50] + "..." if len(sol.title) > 50 else sol.title,
                        sol.agency_code,
                        ", ".join(sol.keywords[:3])
                    )
                
                console.print(sample_table)
                return
                
        except Exception as e:
            table.add_row("Solicitations", f"✗ Error: {str(e)}", "0", "0 MB")
    else:
        table.add_row("Solicitations", "✗ Not found", "0", "0 MB")
    
    console.print(table)


if __name__ == "__main__":
    app()
