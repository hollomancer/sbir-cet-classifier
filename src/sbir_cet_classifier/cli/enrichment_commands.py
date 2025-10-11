"""CLI commands for SAM.gov enrichment operations."""

import typer
from typing import List, Optional
from rich.console import Console
from rich.table import Table

from ..common.config import load_config
from ..data.enrichment.sam_client import SAMClient
from ..data.enrichment.enrichers import EnrichmentService, EnrichmentType

app = typer.Typer(name="enrich", help="SAM.gov enrichment commands")
console = Console()


@app.command("award")
def enrich_single_award(
    award_id: str = typer.Argument(..., help="Award ID to enrich"),
    types: List[str] = typer.Option(
        ["awardee"], 
        "--type", 
        help="Enrichment types: awardee, program_office, solicitation, modifications"
    ),
    confidence_threshold: float = typer.Option(0.7, help="Minimum confidence threshold")
):
    """Enrich a single award with SAM.gov data."""
    config = load_config()
    
    if not config.enrichment:
        console.print("[red]Error: SAM.gov API configuration not found. Set SAM_API_KEY environment variable.[/red]")
        raise typer.Exit(1)
    
    # Convert string types to EnrichmentType enum
    enrichment_types = []
    for type_str in types:
        try:
            enrichment_types.append(EnrichmentType(type_str))
        except ValueError:
            console.print(f"[red]Error: Invalid enrichment type '{type_str}'[/red]")
            raise typer.Exit(1)
    
    # Initialize services
    sam_client = SAMClient(config.enrichment)
    enrichment_service = EnrichmentService(sam_client)
    
    console.print(f"[blue]Enriching award {award_id} with types: {', '.join(types)}[/blue]")
    
    try:
        result = enrichment_service.enrich_award(award_id, enrichment_types)
        
        if result.success:
            console.print(f"[green]✓ Enrichment successful[/green]")
            console.print(f"Confidence: {result.confidence:.2f}")
            console.print(f"Processing time: {result.processing_time_ms}ms")
            
            if result.confidence < confidence_threshold:
                console.print(f"[yellow]⚠ Warning: Confidence {result.confidence:.2f} below threshold {confidence_threshold}[/yellow]")
            
            # Display enriched data
            if result.data:
                table = Table(title="Enriched Data")
                table.add_column("Field", style="cyan")
                table.add_column("Value", style="green")
                
                for key, value in result.data.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            table.add_row(f"{key}.{sub_key}", str(sub_value))
                    else:
                        table.add_row(key, str(value))
                
                console.print(table)
        else:
            console.print(f"[red]✗ Enrichment failed: {result.error_message}[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Error during enrichment: {e}[/red]")
        raise typer.Exit(1)


@app.command("batch")
def enrich_batch_awards(
    award_ids: List[str] = typer.Argument(..., help="Award IDs to enrich"),
    types: List[str] = typer.Option(
        ["awardee"], 
        "--type", 
        help="Enrichment types: awardee, program_office, solicitation, modifications"
    ),
    output_file: Optional[str] = typer.Option(None, help="Output file for results")
):
    """Enrich multiple awards with SAM.gov data."""
    config = load_config()
    
    if not config.enrichment:
        console.print("[red]Error: SAM.gov API configuration not found.[/red]")
        raise typer.Exit(1)
    
    # Convert string types to EnrichmentType enum
    enrichment_types = []
    for type_str in types:
        try:
            enrichment_types.append(EnrichmentType(type_str))
        except ValueError:
            console.print(f"[red]Error: Invalid enrichment type '{type_str}'[/red]")
            raise typer.Exit(1)
    
    # Initialize services
    sam_client = SAMClient(config.enrichment)
    enrichment_service = EnrichmentService(sam_client)
    
    console.print(f"[blue]Enriching {len(award_ids)} awards...[/blue]")
    
    try:
        results = enrichment_service.enrich_awards(award_ids, enrichment_types)
        
        # Display summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        console.print(f"[green]✓ Successful: {successful}[/green]")
        if failed > 0:
            console.print(f"[red]✗ Failed: {failed}[/red]")
        
        # Display results table
        table = Table(title="Enrichment Results")
        table.add_column("Award ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Confidence", style="yellow")
        table.add_column("Time (ms)", style="blue")
        
        for result in results:
            status = "✓ Success" if result.success else f"✗ {result.error_message}"
            confidence = f"{result.confidence:.2f}" if result.success else "N/A"
            
            table.add_row(
                result.award_id,
                status,
                confidence,
                str(result.processing_time_ms)
            )
        
        console.print(table)
        
        if output_file:
            # Save results to file (implementation would depend on format)
            console.print(f"[blue]Results saved to {output_file}[/blue]")
            
    except Exception as e:
        console.print(f"[red]Error during batch enrichment: {e}[/red]")
        raise typer.Exit(1)


@app.command("status")
def show_enrichment_status():
    """Show enrichment system status and configuration."""
    config = load_config()
    
    table = Table(title="Enrichment Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    if config.enrichment:
        table.add_row("API Key", "***" + config.enrichment.api_key[-4:] if len(config.enrichment.api_key) > 4 else "Set")
        table.add_row("Base URL", config.enrichment.base_url)
        table.add_row("Rate Limit", f"{config.enrichment.rate_limit} req/min")
        table.add_row("Timeout", f"{config.enrichment.timeout}s")
        table.add_row("Max Retries", str(config.enrichment.max_retries))
        table.add_row("Batch Size", str(config.enrichment.batch_size))
        table.add_row("Confidence Threshold", str(config.enrichment.confidence_threshold))
    else:
        table.add_row("Status", "[red]Not configured[/red]")
        table.add_row("Required", "Set SAM_API_KEY environment variable")
    
    console.print(table)


if __name__ == "__main__":
    app()
