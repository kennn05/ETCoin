from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()

def buy_et(price_per_coin):
    amount_rm = float(Prompt.ask("[cyan]Enter the amount of RM you want to spend[/]"))
    et_coins = amount_rm / price_per_coin
    console.print(Panel(f"[green]You can buy {et_coins:.2f} ET coins with RM {amount_rm:.2f}[/]", title="💰 Buy ET", style="bold green"))

def sell_et(price_per_coin):
    amount_et = float(Prompt.ask("[cyan]Enter the amount of ET coins you want to sell[/]"))
    rm_received = amount_et * price_per_coin
    console.print(Panel(f"[red]You will receive RM {rm_received:.2f} for selling {amount_et:.2f} ET coins[/]", title="💰 Sell ET", style="bold red"))

def main():
    console.print(Panel("[bold cyan]ET Coin Converter[/]", title="🌟 Welcome", style="cyan"))

    price_per_coin = float(Prompt.ask("[yellow]Enter the price of 1 ET coin in RM[/]"))

    while True:
        console.print("\n[bold magenta]Choose an option:[/]")
        console.print("[1] Buy ET Coins")
        console.print("[2] Sell ET Coins")
        console.print("[3] Exit")

        choice = Prompt.ask("[bold cyan]Enter your choice (1/2/3)[/]")

        if choice == "1":
            buy_et(price_per_coin)
        elif choice == "2":
            sell_et(price_per_coin)
        elif choice == "3":
            console.print("[bold yellow]Exiting...[/]")
            break
        else:
            console.print("[bold red]Invalid choice! Please try again.[/]")

if __name__ == "__main__":
    main()
