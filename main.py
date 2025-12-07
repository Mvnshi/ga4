#!/usr/bin/env python3
"""
Nonprofit Analytics Platform
=============================
Professional quarterly report generator for GA4 and Search Console.

Usage:
    python main.py generate Q4 2024 --client bee_conservancy
    python main.py generate Q1 2025 --client bee_conservancy --export all
    python main.py list-clients
    python main.py clear-cache

For the dashboard:
    streamlit run dashboard.py
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from pathlib import Path

from config.settings import get_settings, CLIENTS_DIR, ClientConfig
from src.reports.report_generator import ReportGenerator
from src.utils.cache import clear_client_cache, clear_all_cache

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    🐝 Nonprofit Analytics Platform
    
    Generate professional quarterly analytics reports for your nonprofit clients.
    Pulls data from Google Analytics 4 and Google Search Console.
    """
    pass


@cli.command()
@click.argument('quarter', type=click.Choice(['Q1', 'Q2', 'Q3', 'Q4']))
@click.argument('year', type=int)
@click.option('--client', '-c', required=True, help='Client configuration name')
@click.option('--comparison', '-cmp', default='yoy', 
              type=click.Choice(['yoy', 'qoq']),
              help='Comparison type: yoy (year-over-year) or qoq (quarter-over-quarter)')
@click.option('--export', '-e', default='all',
              type=click.Choice(['all', 'excel', 'powerpoint', 'json', 'none']),
              help='Export format')
@click.option('--output-dir', '-o', type=click.Path(), 
              help='Custom output directory')
def generate(quarter: str, year: int, client: str, comparison: str, export: str, output_dir: str):
    """
    Generate a quarterly analytics report.
    
    Examples:
    
        python main.py generate Q4 2024 --client bee_conservancy
        
        python main.py generate Q1 2025 -c my_client --export excel
    """
    console.print(Panel.fit(
        f"[bold green]Generating {quarter} {year} Report[/bold green]\n"
        f"Client: {client} | Comparison: {comparison.upper()}",
        title="🐝 Nonprofit Analytics Platform"
    ))
    
    try:
        # Load client config
        settings = get_settings()
        client_config = settings.load_client(client)
        
        # Generate report
        generator = ReportGenerator(client_config)
        report = generator.generate(quarter, year, comparison)
        
        # Print summary
        generator.print_summary(report)
        
        # Export
        if export != 'none':
            console.print("\n[bold]📁 Exporting Reports[/bold]")
            
            if export == 'all':
                paths = generator.export_all(report)
                for format_name, path in paths.items():
                    console.print(f"  ✅ {format_name.upper()}: {path}")
            elif export == 'excel':
                path = generator.export_excel(report)
                console.print(f"  ✅ Excel: {path}")
            elif export == 'powerpoint':
                path = generator.export_powerpoint(report)
                console.print(f"  ✅ PowerPoint: {path}")
            elif export == 'json':
                path = report.save_json()
                console.print(f"  ✅ JSON: {path}")
        
        console.print("\n[bold green]✨ Report generation complete![/bold green]")
        
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print(f"\nAvailable clients: {', '.join(get_settings().list_clients())}")
        console.print(f"Client configs are stored in: {CLIENTS_DIR}")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise SystemExit(1)


@cli.command('list-clients')
def list_clients():
    """List all configured clients."""
    settings = get_settings()
    clients = settings.list_clients()
    
    if not clients:
        console.print("[yellow]No clients configured.[/yellow]")
        console.print(f"\nTo add a client, create a YAML file in: {CLIENTS_DIR}")
        console.print("Use config/clients/example_client.yaml as a template.")
        return
    
    table = Table(title="Configured Clients")
    table.add_column("Name", style="cyan")
    table.add_column("Display Name", style="green")
    table.add_column("GA4 Property", style="yellow")
    table.add_column("GSC Site", style="blue")
    
    for client_name in clients:
        try:
            config = settings.load_client(client_name)
            table.add_row(
                config.name,
                config.display_name,
                config.ga4_property_id,
                config.gsc_site_url[:40] + "..." if len(config.gsc_site_url) > 40 else config.gsc_site_url
            )
        except Exception as e:
            table.add_row(client_name, f"[red]Error: {e}[/red]", "", "")
    
    console.print(table)


@cli.command('clear-cache')
@click.option('--client', '-c', help='Clear cache for specific client only')
@click.confirmation_option(prompt='Are you sure you want to clear the cache?')
def clear_cache(client: str):
    """Clear cached API responses."""
    if client:
        clear_client_cache(client)
        console.print(f"[green]✓ Cleared cache for client: {client}[/green]")
    else:
        clear_all_cache()
        console.print("[green]✓ Cleared all cache data[/green]")


@cli.command('setup')
@click.argument('client_name')
def setup_client(client_name: str):
    """Interactive setup for a new client."""
    console.print(Panel.fit(
        f"[bold]Setting up new client: {client_name}[/bold]",
        title="🐝 Client Setup"
    ))
    
    # Prompt for details
    display_name = click.prompt("Organization display name")
    ga4_property_id = click.prompt("GA4 Property ID (from GA4 Admin → Property Settings)")
    gsc_site_url = click.prompt("Search Console Site URL (e.g., https://example.org/)")
    credentials_file = click.prompt("Credentials filename", default=f"{client_name}_credentials.json")
    
    # Create config content
    config_content = f"""# {display_name} Configuration
# Generated by Nonprofit Analytics Platform

name: "{client_name}"
display_name: "{display_name}"
ga4_property_id: "{ga4_property_id}"
gsc_site_url: "{gsc_site_url}"
credentials_file: "{credentials_file}"

# Branding
primary_color: "#2D5016"
secondary_color: "#F4C430"

# Timezone
timezone: "America/New_York"

# Homepage paths to track
homepage_paths:
  - "/"
  - "/home"

# Paths to exclude
exclude_paths:
  - "/admin"
  - "/wp-admin"
"""
    
    # Write config file
    config_path = CLIENTS_DIR / f"{client_name}.yaml"
    
    if config_path.exists():
        if not click.confirm(f"Config file {config_path} already exists. Overwrite?"):
            console.print("[yellow]Aborted.[/yellow]")
            return
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    console.print(f"\n[green]✓ Created config file: {config_path}[/green]")
    console.print(f"\n[yellow]Next steps:[/yellow]")
    console.print(f"1. Place your service account JSON key at: credentials/{credentials_file}")
    console.print(f"2. Add the service account email to GA4 property access")
    console.print(f"3. Add the service account email to Search Console users")
    console.print(f"4. Run: python main.py generate Q4 2024 --client {client_name}")


@cli.command('test-connection')
@click.option('--client', '-c', required=True, help='Client configuration name')
def test_connection(client: str):
    """Test API connections for a client."""
    console.print(f"\n[bold]Testing connections for: {client}[/bold]\n")
    
    try:
        settings = get_settings()
        client_config = settings.load_client(client)
        
        # Test GA4
        console.print("Testing GA4 connection...", end=" ")
        try:
            from src.clients.ga4_client import GA4Client
            ga4 = GA4Client(client_config)
            # Try a simple query
            result = ga4.get_traffic_overview("2024-01-01", "2024-01-07")
            if result:
                console.print("[green]✓ Connected[/green]")
            else:
                console.print("[yellow]⚠ Connected but no data[/yellow]")
        except Exception as e:
            console.print(f"[red]✗ Failed: {e}[/red]")
        
        # Test GSC
        console.print("Testing Search Console connection...", end=" ")
        try:
            from src.clients.gsc_client import SearchConsoleClient
            gsc = SearchConsoleClient(client_config)
            result = gsc.get_search_overview("2024-01-01", "2024-01-07")
            if result:
                console.print("[green]✓ Connected[/green]")
            else:
                console.print("[yellow]⚠ Connected but no data[/yellow]")
        except Exception as e:
            console.print(f"[red]✗ Failed: {e}[/red]")
        
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")


if __name__ == '__main__':
    cli()

