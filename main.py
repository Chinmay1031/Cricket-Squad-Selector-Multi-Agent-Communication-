import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.prompt import Prompt
from rich import box
from dotenv import load_dotenv
from debate_loop import run_debate

load_dotenv()
console = Console()

def get_conditions_from_user():
    """Ask the user for match conditions interactively."""
    console.print(Panel.fit(
        "[bold cyan]Fantasy XI Debate[/bold cyan]\n"
        "[dim]GPT-4o-mini picks · Claude critiques · Up to 3 rounds[/dim]",
        border_style="cyan"
    ))

    console.print("\n[bold]Set match conditions:[/bold]\n")

    format_choice = Prompt.ask(
        "  Format",
        choices=["T20", "ODI"],
        default="T20"
    )

    pitch_choice = Prompt.ask(
        "  Pitch",
        choices=["Flat", "Seaming", "Spinning", "Dry", "Hard","Grass"],
        default="Flat"
    )

    weather_choice = Prompt.ask(
        "  Weather",
        choices=["Clear", "Overcast", "Humid"],
        default="Clear"
    )

    venues = [
        "Wankhede Stadium, Mumbai",
        "Eden Gardens, Kolkata",
        "M Chinnaswamy Stadium, Bengaluru",
        "Narendra Modi Stadium, Ahmedabad",
        "MA Chidambaram Stadium, Chennai",
        "Sydney Cricket Ground, Australia",
        "Melbourne Cricket Ground, Australia",
        "Adelaide Cricket Ground, Australia",
        "Perth Cricket Ground, Australia",
        "Lords Cricket Stadium, England",
        "Edgbaston Cricket Stadium, England",
        "Old Traffod Cricket Stadium, England",
        "Dubai Cricket Stadium, UAE",
        "Wanderers Stadium Cricket Stadium, Johannasburg",
        "Newlands Cricket Ground, Capetown",
        "Kingsmead Stadium, Durban",  
    ]
    console.print("\n  Venues:")
    for i, v in enumerate(venues, 1):
        console.print(f"    [cyan]{i}[/cyan]. {v}")

    venue_idx = Prompt.ask(
        "  Choose venue",
        choices=["1", "2", "3", "4", "5"],
        default="1"
    )

    return {
        "format": format_choice,
        "pitch": pitch_choice,
        "weather": weather_choice,
        "venue": venues[int(venue_idx) - 1]
    }

def print_round_header(round_num, agent, action):
    color = "blue" if "GPT" in agent else "green"
    console.print(
        f"\n[bold {color}]{'─'*20} Round {round_num} · {agent} · {action} {'─'*20}[/bold {color}]"
    )

def print_gpt_selection(parsed, round_num):
    print_round_header(round_num, "GPT-4o-mini", "Selecting")

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Field", style="dim")
    table.add_column("Value", style="white")
    table.add_row("Captain", f"[bold yellow]{parsed['captain']}[/bold yellow]")
    table.add_row("Vice-captain", f"[yellow]{parsed['vice_captain']}[/yellow]")
    table.add_row("Team", ", ".join(parsed["team"]))
    table.add_row("Reasoning", f"[dim]{parsed['reasoning']}[/dim]")
    console.print(table)

def print_claude_critique(critique, verdict, round_num):
    print_round_header(round_num, "Claude", "Critiquing")

    verdict_color = "green" if verdict == "ACCEPTABLE" else "red"
    verdict_label = (
        "[bold green]✓ ACCEPTABLE[/bold green]"
        if verdict == "ACCEPTABLE"
        else "[bold red]✗ NEEDS REVISION[/bold red]"
    )

    console.print(Panel(
        critique,
        title=f"Claude's Analysis · {verdict_label}",
        border_style=verdict_color,
        padding=(1, 2)
    ))

def print_final_team(final_team, transcript):
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]FINAL FANTASY XI[/bold cyan]",
        border_style="cyan"
    ))

    # Build the team table
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        border_style="cyan",
        padding=(0, 2)
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Player", min_width=20)
    table.add_column("Role", justify="center")

    for i, player in enumerate(final_team["team"], 1):
        role_tag = ""
        name_style = "white"

        if player == final_team["captain"]:
            role_tag = "[bold yellow]C (2×)[/bold yellow]"
            name_style = "bold yellow"
        elif player == final_team["vice_captain"]:
            role_tag = "[yellow]VC (1.5×)[/yellow]"
            name_style = "yellow"

        table.add_row(str(i), f"[{name_style}]{player}[/{name_style}]", role_tag)

    console.print(table)

    # Summary stats
    rounds_taken = transcript[-1]["round"]
    last_claude = [t for t in transcript if t["agent"] == "Claude"][-1]
    final_verdict = last_claude["verdict"]
    verdict_text = (
        "[green]Approved by Claude[/green]"
        if final_verdict == "ACCEPTABLE"
        else "[red]Max rounds reached[/red]"
    )

    console.print(f"\n  Rounds taken : [cyan]{rounds_taken}[/cyan]")
    console.print(f"  Outcome      : {verdict_text}")

def print_transcript_summary(transcript):
    """Show a compact round-by-round summary."""
    console.print("\n[bold]Debate summary:[/bold]")
    for entry in transcript:
        agent_color = "blue" if entry["agent"] == "GPT-4o-mini" else "green"
        verdict_str = ""
        if entry["agent"] == "Claude":
            v = entry.get("verdict", "")
            verdict_str = (
                " [green]✓ ACCEPTABLE[/green]"
                if v == "ACCEPTABLE"
                else " [red]✗ NEEDS REVISION[/red]"
            )
        console.print(
            f"  Round {entry['round']} · "
            f"[{agent_color}]{entry['agent']}[/{agent_color}] · "
            f"{entry['type'].upper()}{verdict_str}"
        )

def main():
    try:
        conditions = get_conditions_from_user()

        console.print(f"\n[dim]Starting debate for {conditions['format']} "
                      f"at {conditions['venue']}...[/dim]\n")

        # Patch the debate loop to call our Rich printers
        from gpt_selector import load_player_pool, pick_team, parse_team
        from claude_critic import critique_team, parse_verdict

        pool = load_player_pool()
        transcript = []
        critique = None
        final_team = None

        for round_num in range(1, 4):
            # GPT picks
            gpt_response = pick_team(conditions, pool, previous_critique=critique)
            parsed = parse_team(gpt_response)
            final_team = parsed

            transcript.append({
                "round": round_num,
                "agent": "GPT-4o-mini",
                "type": "selection",
                "content": gpt_response
            })
            print_gpt_selection(parsed, round_num)

            # Claude critiques
            critique = critique_team(conditions, gpt_response, round_number=round_num)
            verdict = parse_verdict(critique)

            transcript.append({
                "round": round_num,
                "agent": "Claude",
                "type": "critique",
                "content": critique,
                "verdict": verdict
            })
            print_claude_critique(critique, verdict, round_num)

            if verdict == "ACCEPTABLE":
                console.print("\n[bold green]Claude approved! Debate ends early.[/bold green]")
                break

            if round_num == 3:
                console.print("\n[dim]Maximum rounds reached.[/dim]")

        print_final_team(final_team, transcript)
        print_transcript_summary(transcript)

    except KeyboardInterrupt:
        console.print("\n[dim]Debate cancelled.[/dim]")
        sys.exit(0)

if __name__ == "__main__":
    main()