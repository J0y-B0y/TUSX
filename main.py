import redis # Redis client for connecting to the Redis database
import json # JSON library for handling JSON data
import yfinance as yf # Yahoo Finance API for fetching stock data
import matplotlib.pyplot as plt # Matplotlib library for plotting graphs
import mplfinance as mpf # Mplfinance library for creating financial charts
import matplotlib as mpl # Matplotlib configuration for customizing plots
from tabulate import tabulate # Tabulate library for formatting tables
from termcolor import colored # Termcolor library for adding color to terminal output
from concurrent.futures import ThreadPoolExecutor, as_completed # ThreadPoolExecutor for concurrent execution
import smtplib # SMTP library for sending emails

# Email libraries for constructing email messages
from email.mime.multipart import MIMEMultipart 
from email.mime.text import MIMEText
import time # Time library for managing sleep intervals

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Set global font properties to monospace
mpl.rcParams['font.family'] = 'monospace'
mpl.rcParams['font.monospace'] = ['Courier New']

# Format stock symbol for the Toronto Stock Exchange (TSX)
def get_tsx_symbol(symbol):
    """Ensure the symbol is formatted for TSX."""
    return f"{symbol}.TO"

# Fetch the company name for a given TSX stock symbol using Yahoo Finance
def get_stock_company_name(symbol):
    """Fetch company name for the given TSX stock symbol using Yahoo Finance."""
    try:
        tsx_symbol = get_tsx_symbol(symbol)
        stock = yf.Ticker(tsx_symbol)
        return stock.info['shortName']
    except Exception as e:
        print(f"Error fetching company name: {e}")
        return None

# Fetch the current stock price for the given TSX symbol using Yahoo Finance
def get_current_stock_price(symbol):
    """Fetch current stock price for the given TSX symbol using Yahoo Finance."""
    try:
        tsx_symbol = get_tsx_symbol(symbol)
        stock = yf.Ticker(tsx_symbol)
        todays_data = stock.history(period='1d')
        return todays_data['Close'].iloc[0]  # Use .iloc[0] to avoid FutureWarning
    except Exception as e:
        print(f"Error fetching stock price: {e}")
        return None

# Add a new stock to the portfolio
def add_stock(symbol, shares, purchase_price, threshold):
    portfolio = load_portfolio()
    new_id = max([stock['id'] for stock in portfolio], default=0) + 1
    portfolio.append({'id': new_id, 'symbol': symbol, 'shares': shares, 'purchase_price': purchase_price, 'threshold': threshold})
    save_portfolio(portfolio)

# Update an existing stock in the portfolio
def update_stock(stock_id, symbol, shares, purchase_price, threshold):
    portfolio = load_portfolio()
    for stock in portfolio:
        if stock['id'] == stock_id:
            stock['symbol'] = symbol
            stock['shares'] = shares
            stock['purchase_price'] = purchase_price
            stock['threshold'] = threshold
            break
    save_portfolio(portfolio)

# Delete a stock from the portfolio
def delete_stock(stock_id):
    portfolio = load_portfolio()
    portfolio = [stock for stock in portfolio if stock['id'] != stock_id]
    for index, stock in enumerate(portfolio):
        stock['id'] = index + 1
    save_portfolio(portfolio)

# Fetch detailed information for a specific stock
def fetch_stock_details(stock):
    symbol = stock['symbol']
    purchase_price = stock['purchase_price']
    current_price = get_current_stock_price(symbol) or purchase_price
    change = ((current_price - purchase_price) / purchase_price) * 100
    change_color = 'green' if change >= 0 else 'red'
    change_formatted = colored(f"{change:.2f}%", change_color)
    return [stock['id'], symbol, stock['shares'], purchase_price, current_price, change_formatted, stock['threshold']]

# List all stocks in the portfolio
def list_stocks():
    portfolio = load_portfolio()
    if not portfolio:
        print("No stocks in portfolio.")
        return

    table = []
    headers = ["ID", "Symbol", "Shares", "Purchase Price", "Current Price", "Change (%)", "Threshold (%)"]
    alignment = ["left", "left", "left", "center", "center", "center", "center"]

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_stock_details, stock) for stock in portfolio]
        for future in as_completed(futures):
            table.append(future.result())

    table.sort(key=lambda x: x[0])  # Sort by ID
    print(tabulate(table, headers, tablefmt="grid", colalign=alignment))

# Load the portfolio data from Redis
def load_portfolio():
    data = r.get('portfolio')
    if data is None:
        return []
    return json.loads(data)

# Save the portfolio data to Redis
def save_portfolio(portfolio):
    r.set('portfolio', json.dumps(portfolio))

# View details for a specific stock by ID
def view_stock(stock_id):
    portfolio = load_portfolio()
    stock = next((stock for stock in portfolio if stock['id'] == stock_id), None)
    if stock:
        symbol = stock['symbol']
        purchase_price = stock['purchase_price']
        current_price = get_current_stock_price(symbol) or purchase_price
        change = ((current_price - purchase_price) / purchase_price) * 100
        change_color = 'green' if change >= 0 else 'red'
        change_formatted = colored(f"{change:.2f}%", change_color)

        table = [
            [stock['id'], symbol, stock['shares'], purchase_price, current_price, change_formatted, stock['threshold']]
        ]
        headers = ["ID", "Symbol", "Shares", "Purchase Price", "Current Price", "Change (%)", "Threshold (%)"]
        alignment = ["left", "left", "left", "center", "center", "center", "center"]

        print(tabulate(table, headers, tablefmt="grid", colalign=alignment))
        plot_candlestick_chart(stock['symbol'])
    else:
        print("Stock not found.")

# Plot a candlestick chart for a given TSX stock symbol
def plot_candlestick_chart(symbol):
    """Plot a candlestick chart for the given TSX stock symbol."""
    tsx_symbol = get_tsx_symbol(symbol)
    stock = yf.Ticker(tsx_symbol)
    hist = stock.history(period='1d', interval='5m')  # Get 24-hour data at 5-minute intervals

    mc = mpf.make_marketcolors(
        up='green', down='red',
        wick={'up': 'green', 'down': 'red'},
        edge={'up': 'green', 'down': 'red'},
        volume={'up': 'green', 'down': 'red'}
    )

    s = mpf.make_mpf_style(marketcolors=mc, base_mpf_style='nightclouds')

    mpf.plot(hist, type='candle', style=s, title=f'{symbol} 24-Hour Performance', ylabel='Price')
    plt.pause(0.001)  # Display the plot for a brief moment to allow interaction
    input("Press Enter to continue...")

# Validate a stock symbol and confirm with the user
def validate_symbol(symbol):
    company_name = get_stock_company_name(symbol)
    if company_name:
        confirmation = input(f"Do you mean {company_name}? (y/n): ").strip().lower()
        if confirmation == 'y':
            return True
    return False

# Display a summary of the entire portfolio
def portfolio_summary():
    portfolio = load_portfolio()
    if not portfolio:
        print("No stocks in portfolio.")
        return

    total_value = 0
    total_purchase_value = 0
    total_dividends = 0
    total_shares = 0
    highest_perf_stock = None
    lowest_perf_stock = None
    table = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_stock_details, stock) for stock in portfolio]
        for future in as_completed(futures):
            stock_details = future.result()
            table.append(stock_details)
            value = stock_details[2] * stock_details[4]
            purchase_value = stock_details[2] * stock_details[3]
            profit_loss = value - purchase_value
            profit_loss_color = 'green' if profit_loss >= 0 else 'red'
            profit_loss_formatted = colored(f"{profit_loss:.2f}", profit_loss_color)
            total_value += value
            total_purchase_value += purchase_value
            total_shares += stock_details[2]

            if highest_perf_stock is None or profit_loss > highest_perf_stock[1]:
                highest_perf_stock = (stock_details[1], profit_loss)
            if lowest_perf_stock is None or profit_loss < lowest_perf_stock[1]:
                lowest_perf_stock = (stock_details[1], profit_loss)

            try:
                tsx_symbol = get_tsx_symbol(stock_details[1])
                stock_info = yf.Ticker(tsx_symbol).info
                dividend_yield = stock_info.get('dividendYield', 0) * 100  # Convert to percentage
                total_dividends += dividend_yield * stock_details[2]
            except Exception as e:
                dividend_yield = 'N/A'

            table[-1].append(dividend_yield)

    headers = ["Symbol", "Shares", "Purchase Price", "Current Price", "Current Value", "Profit/Loss", "Dividend Yield (%)", "Threshold (%)"]
    alignment = ["left", "left", "center", "center", "center", "center", "center", "center"]

    print(tabulate(table, headers, tablefmt="grid", colalign=alignment))
    total_profit_loss = total_value - total_purchase_value
    total_profit_loss_color = 'green' if total_profit_loss >= 0 else 'red'
    total_profit_loss_formatted = colored(f"{total_profit_loss:.2f}", total_profit_loss_color)
    avg_purchase_price = total_purchase_value / total_shares if total_shares > 0 else 0
    avg_current_price = total_value / total_shares if total_shares > 0 else 0
    percentage_profit_loss = (total_profit_loss / total_purchase_value) * 100 if total_purchase_value > 0 else 0

    summary_table = [
        ["Total Portfolio Value", f"{total_value:.2f}"],
        ["Total Investment", f"{total_purchase_value:.2f}"],
        ["Total Profit/Loss", total_profit_loss_formatted],
        ["Percentage Profit/Loss", f"{percentage_profit_loss:.2f}%"],
        ["Average Purchase Price", f"{avg_purchase_price:.2f}"],
        ["Average Current Price", f"{avg_current_price:.2f}"],
        ["Highest Performing Stock", f"{highest_perf_stock[0]} with Profit/Loss of {highest_perf_stock[1]:.2f}" if highest_perf_stock else "N/A"],
        ["Lowest Performing Stock", f"{lowest_perf_stock[0]} with Profit/Loss of {lowest_perf_stock[1]:.2f}" if lowest_perf_stock else "N/A"]
    ]

    print("\nSummary:")
    print(tabulate(summary_table, tablefmt="grid"))

# Search for a stock symbol and display its current details
def search_and_view_stock():
    symbol = input("Enter stock symbol to search: ").strip().upper()
    if validate_symbol(symbol):
        current_price = get_current_stock_price(symbol)
        if current_price is not None:
            table = [
                [symbol, current_price]
            ]
            headers = ["Symbol", "Current Price"]
            alignment = ["left", "center"]
            print(tabulate(table, headers, tablefmt="grid", colalign=alignment))
            plot_candlestick_chart(symbol)
        else:
            print("Unable to fetch current price for the symbol.")
    else:
        print("Symbol validation failed. Please try again.")

# Send an email notification
def send_email_notification(to_email, subject, body):
    from_email = "your_email@example.com"
    from_password = "your_email_password"

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.example.com', 587)
        server.starttls()
        server.login(from_email, from_password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Monitor the portfolio for threshold breaches and send alerts
def monitor_portfolio():
    while True:
        portfolio = load_portfolio()
        for stock in portfolio:
            current_price = get_current_stock_price(stock['symbol'])
            if current_price:
                purchase_price = stock['purchase_price']
                threshold = stock['threshold']
                change = ((current_price - purchase_price) / purchase_price) * 100
                if change <= threshold:
                    subject = f"Stock Alert: {stock['symbol']} has dropped below your threshold"
                    body = f"The stock {stock['symbol']} has dropped to {current_price}, which is below your threshold of {threshold}%. Please review your portfolio."
                    send_email_notification("user_email@example.com", subject, body)
        time.sleep(3600)  # Check every hour

# Display the main menu options
def show_menu():
    print("\n\033[1;36m" + "="*40 + "\033[0m")
    print("\033[1;34m TUSX Stock Portfolio Manager \033[0m".center(40))
    print("\033[1;36m" + "="*40 + "\033[0m")
    print("\033[1;33m1.\033[0m List all stocks")
    print("\033[1;33m2.\033[0m Add a stock")
    print("\033[1;33m3.\033[0m Update a stock")
    print("\033[1;33m4.\033[0m Delete a stock")
    print("\033[1;33m5.\033[0m View stock details")
    print("\033[1;33m6.\033[0m Portfolio summary")
    print("\033[1;33m7.\033[0m Search and view stock details")
    print("\033[1;33m8.\033[0m Show menu")
    print("\033[1;33m9.\033[0m Exit")
    print("\033[1;36m" + "="*40 + "\033[0m")

# Main function to handle user input and execute corresponding functions
def main():
    show_menu()
    while True:
        choice = input("\n> ").strip().lower()

        if choice in ['1', 'l']:
            list_stocks()
        elif choice in ['2', 'a']:
            symbol = input("Enter stock symbol: ").strip().upper()
            if validate_symbol(symbol):
                try:
                    shares = int(input("Enter number of shares: ").strip())
                    purchase_price = float(input("Enter purchase price: ").strip())
                    threshold = float(input("Enter loss threshold percentage: ").strip())
                    add_stock(symbol, shares, purchase_price, threshold)
                except ValueError:
                    print("Invalid input. Please enter numeric values for shares, purchase price, and threshold.")
            else:
                print("Symbol validation failed. Please try again.")
        elif choice in ['3', 'u']:
            try:
                stock_id = int(input("Enter stock ID to update: ").strip())
                symbol = input("Enter new stock symbol: ").strip().upper()
                if validate_symbol(symbol):
                    shares = int(input("Enter new number of shares: ").strip())
                    purchase_price = float(input("Enter new purchase price: ").strip())
                    threshold = float(input("Enter new loss threshold percentage: ").strip())
                    update_stock(stock_id, symbol, shares, purchase_price, threshold)
                else:
                    print("Symbol validation failed. Please try again.")
            except ValueError:
                print("Invalid input. Please enter numeric values for ID, shares, purchase price, and threshold.")
        elif choice in ['4', 'd']:
            try:
                stock_id = int(input("Enter stock ID to delete: ").strip())
                delete_stock(stock_id)
            except ValueError:
                print("Invalid input. Please enter a numeric value for ID.")
        elif choice in ['5', 'v']:
            try:
                stock_id = int(input("Enter stock ID to view: ").strip())
                view_stock(stock_id)
            except ValueError:
                print("Invalid input. Please enter a numeric value for ID.")
        elif choice in ['6', 's']:
            portfolio_summary()
        elif choice in ['7', 'search']:
            search_and_view_stock()
        elif choice in ['8', 'm']:
            show_menu()
        elif choice in ['9', 'e']:
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    from threading import Thread
    Thread(target=monitor_portfolio, daemon=True).start()
    main()