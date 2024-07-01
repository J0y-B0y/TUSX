import redis # Redis client for connecting to the Redis database
import json # JSON library for handling JSON data
import yfinance as yf # Yahoo Finance API for fetching stock data
import plotly.graph_objects as go # Plotly for creating interactive charts
import matplotlib as mpl # Matplotlib configuration for customizing plots
from tabulate import tabulate # Tabulate library for formatting tables
from termcolor import colored # Termcolor library for adding color to terminal output
from concurrent.futures import ThreadPoolExecutor, as_completed # ThreadPoolExecutor for concurrent execution
import time # Time library for managing sleep intervals
import talib as ta # Technical Analysis Library in Python for financial data analysis
import pandas as pd # Powerful data manipulation and analysis library, especially for time-series data
import requests # Library for making HTTP requests to fetch data from web APIs
import plotly.subplots as sp # Subplots module from Plotly for creating complex, multi-plot visualizations

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Define Aura style
aura_style = {
    "axes.facecolor": "#15141b",
    "axes.edgecolor": "#6d6d6d",
    "axes.labelcolor": "#edecee",
    "figure.facecolor": "#15141b",
    "grid.color": "#6d6d6d",
    "text.color": "#edecee",
    "xtick.color": "#edecee",
    "ytick.color": "#edecee",
    "axes.prop_cycle": mpl.cycler(color=["#82e2ff", "#ffca85", "#61ffca", "#ff6767", "#a277ff", "#f694ff", "#6d6d6d"])
}

# Apply Aura style
mpl.rcParams.update(aura_style)

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

def view_stock(stock_id):
    # Load portfolio and find the specific stock
    portfolio = load_portfolio()
    stock = next((stock for stock in portfolio if stock['id'] == stock_id), None)
    
    if stock:
        # Get stock information
        symbol = stock['symbol']
        tsx_symbol = get_tsx_symbol(symbol)
        stock_info = yf.Ticker(tsx_symbol).info
        hist = yf.Ticker(tsx_symbol).history(period="1d")
        latest_data = hist.iloc[-1]

        # Prepare main table data
        purchase_price = stock['purchase_price']
        current_price = get_current_stock_price(symbol) or purchase_price
        change = ((current_price - purchase_price) / purchase_price) * 100
        change_color = 'green' if change >= 0 else 'red'
        change_formatted = colored(f"{change:.3f}%", change_color)

        main_table = [
            [stock['id'], symbol, stock['shares'], f"{purchase_price:.3f}", f"{current_price:.3f}", change_formatted, stock['threshold']]
        ]
        main_headers = ["ID", "Symbol", "Shares", "Purchase Price", "Current Price", "Change (%)", "Threshold (%)"]
        alignment = ["center", "center", "center", "center", "center", "center", "center"]

        # Prepare sub-table data
        sub_headers = [
            "Previous Close", "Open", "Bid", "Ask",
            "Day's Range", "52 Week Range", "Volume", "Avg Volume",
            "Market Cap", "Beta", "P/E Ratio (TTM)", "EPS (TTM)",
            "Earnings Date", "Forward Dividend & Yield", "Ex-Dividend Date", "1y Target Est",
            "Enterprise Value", "Forward P/E", "PEG Ratio", "Price/Sales",
            "Price/Book", "Enterprise Value/Revenue", "Enterprise Value/EBITDA", "Profit Margin",
            "Return on Assets (ttm)", "Return on Equity (ttm)", "Revenue (ttm)", "Net Income (ttm)",
            "Total Cash (mrq)", "Total Debt/Equity (mrq)", "Levered Free Cash Flow (ttm)", "50-Day Moving Average",
            "200-Day Moving Average", "Shares Outstanding", "Float", "Held by Insiders",
            "Held by Institutions", "Shares Short", "Short Ratio", "Short % of Float",
            "Short % of Shares Outstanding", "Forward Annual Dividend Rate", "Forward Annual Dividend Yield", "Trailing Annual Dividend Rate",
            "Trailing Annual Dividend Yield", "5 Year Average Dividend Yield", "Payout Ratio", "Dividend Date",
            "Last Split Factor", "Last Split Date", "Sector", "Industry",
            "Last Trade", "Last Trade Size", "Consolidated Volume", "NBBO Bid/Ask Price",
            "Bid/Ask Size", "VWAP", "VWAP Volume"
        ]

        sub_headers_colored = [colored(header.center(35), 'magenta') for header in sub_headers]

        sub_values = [
            stock_info.get('previousClose', 'N/A'), stock_info.get('open', 'N/A'), stock_info.get('bid', 'N/A'), stock_info.get('ask', 'N/A'),
            stock_info.get('dayRange', 'N/A'), stock_info.get('fiftyTwoWeekRange', 'N/A'), stock_info.get('volume', 'N/A'), stock_info.get('averageVolume', 'N/A'),
            stock_info.get('marketCap', 'N/A'), stock_info.get('beta', 'N/A'), stock_info.get('trailingPE', 'N/A'), stock_info.get('trailingEps', 'N/A'),
            stock_info.get('earningsDate', 'N/A'), f"{stock_info.get('forwardAnnualDividendRate', 'N/A')} ({stock_info.get('forwardAnnualDividendYield', 'N/A')})",
            stock_info.get('exDividendDate', 'N/A'), stock_info.get('oneYearTargetEstimate', 'N/A'), stock_info.get('enterpriseValue', 'N/A'),
            stock_info.get('forwardPE', 'N/A'), stock_info.get('pegRatio', 'N/A'), stock_info.get('priceToSalesTrailing12Months', 'N/A'),
            stock_info.get('priceToBook', 'N/A'), stock_info.get('enterpriseToRevenue', 'N/A'), stock_info.get('enterpriseToEbitda', 'N/A'),
            stock_info.get('profitMargins', 'N/A'), stock_info.get('returnOnAssets', 'N/A'), stock_info.get('returnOnEquity', 'N/A'),
            stock_info.get('revenue', 'N/A'), stock_info.get('netIncomeToCommon', 'N/A'), stock_info.get('totalCash', 'N/A'),
            stock_info.get('debtToEquity', 'N/A'), stock_info.get('leveredFreeCashFlow', 'N/A'), stock_info.get('fiftyDayAverage', 'N/A'),
            stock_info.get('twoHundredDayAverage', 'N/A'), stock_info.get('sharesOutstanding', 'N/A'), stock_info.get('floatShares', 'N/A'),
            stock_info.get('heldPercentInsiders', 'N/A'), stock_info.get('heldPercentInstitutions', 'N/A'), stock_info.get('sharesShort', 'N/A'),
            stock_info.get('shortRatio', 'N/A'), stock_info.get('shortPercentOfFloat', 'N/A'), stock_info.get('sharesShortPriorMonth', 'N/A'),
            stock_info.get('dividendRate', 'N/A'), stock_info.get('dividendYield', 'N/A'), stock_info.get('trailingAnnualDividendRate', 'N/A'),
            stock_info.get('trailingAnnualDividendYield', 'N/A'), stock_info.get('fiveYearAvgDividendYield', 'N/A'), stock_info.get('payoutRatio', 'N/A'),
            stock_info.get('dividendDate', 'N/A'), stock_info.get('lastSplitFactor', 'N/A'), stock_info.get('lastSplitDate', 'N/A'),
            stock_info.get('sector', 'N/A'), stock_info.get('industry', 'N/A'), latest_data.name.strftime('%b %d, %Y, %I:%M %p ET'),
            stock_info.get('lastTradeSize', 'N/A'), stock_info.get('consolidatedVolume', 'N/A'), f"{stock_info.get('bid', 'N/A')}/{stock_info.get('ask', 'N/A')}",
            f"{stock_info.get('bidSize', 'N/A')}/{stock_info.get('askSize', 'N/A')}", stock_info.get('vwap', 'N/A'), stock_info.get('vwapVolume', 'N/A')
        ]

        # Create the formatted sub-table
        column_width = 35
        def format_row(data):
            return '|'.join([str(item).center(column_width) for item in data])
        
        sub_table = "+".join(['=' * column_width for _ in range(4)]) + "\n"
        for i in range(0, len(sub_headers_colored), 4):
            headers_row = sub_headers_colored[i:i+4]
            values_row = sub_values[i:i+4]
            sub_table += f"|{format_row(headers_row)}|\n"
            sub_table += "+".join(['-' * column_width for _ in range(4)]) + "\n"
            sub_table += f"|{format_row(values_row)}|\n"
            sub_table += "+".join(['=' * column_width for _ in range(4)]) + "\n"

        # Print the main table and sub-table
        print(tabulate(main_table, headers=main_headers, tablefmt="grid", colalign=alignment))
        print(sub_table)

        # Add company description
        print("\n" + colored("Company Description:", 'magenta'))
        print(stock_info.get('longBusinessSummary', 'N/A'))

        print("\nChoose chart type:")
        print("1. Candlestick Chart")
        print("2. Line Chart")
        print("3. Bar Chart")
        chart_choice = input("Enter choice: ").strip()

        print("\nChoose period:")
        periods = [
            ('1m', '1d'), ('5m', '1d'), ('15m', '1d'), ('30m', '1d'), 
            ('60m', '1mo'), ('1d', '1mo'), ('1wk', '3mo'), 
            ('1mo', '6mo'), ('3mo', '1y')
        ]
        period_labels = [
            '1 day (1 minute intervals)', '1 day (5 minute intervals)', '1 day (15 minute intervals)', 
            '1 day (30 minute intervals)', '1 month (60 minute intervals)', '1 month (1 day intervals)', 
            '3 months (1 week intervals)', '6 months (1 month intervals)', '1 year (3 month intervals)'
        ]
        for idx, label in enumerate(period_labels, 1):
            print(f"{idx}. {label}")
        period_choice = input("Enter period choice: ").strip()

        try:
            interval, period = periods[int(period_choice) - 1]
            print(f"Selected interval: {interval}, Selected period: {period}")  # Debug statement
        except (ValueError, IndexError):
            print("Invalid choice. Displaying 1 day data by default.")
            interval, period = '1d', '1d'

        if chart_choice == '1':
            plot_candlestick_chart(stock['symbol'], interval, period)
        elif chart_choice == '2':
            plot_line_chart(stock['symbol'], interval, period)
        elif chart_choice == '3':
            plot_bar_chart(stock['symbol'], interval, period)
        else:
            print("Invalid choice. Displaying candlestick chart by default.")
            plot_candlestick_chart(stock['symbol'], interval, period)
    else:
        print("Stock not found.")

                
# Plot a candlestick chart for a given TSX stock symbol using Plotly
def plot_candlestick_chart(symbol, interval, period):
    """Plot an interactive candlestick chart for the given TSX stock symbol and highlight candlestick patterns."""
    tsx_symbol = get_tsx_symbol(symbol)
    stock = yf.Ticker(tsx_symbol)
    hist = stock.history(period=period, interval=interval)

    # Define candlestick patterns with unique colors and priority
    patterns = {
        "Hammer": (ta.CDLHAMMER(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'blue', 'circle', 1),
        "Piercing Pattern": (ta.CDLPIERCING(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'cyan', 'diamond', 2),
        "Bullish Engulfing": (ta.CDLENGULFING(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'green', 'star', 3),
        "Morning Star": (ta.CDLMORNINGSTAR(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'purple', 'x', 4),
        "Three White Soldiers": (ta.CDL3WHITESOLDIERS(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'magenta', 'cross', 5),
        "White Marubozu": (ta.CDLMARUBOZU(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'orange', 'triangle-up', 6),
        "Three Inside Up": (ta.CDL3INSIDE(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'yellow', 'triangle-down', 7),
        "Bullish Harami": (ta.CDLHARAMI(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'pink', 'pentagon', 8),
        "Inverted Hammer": (ta.CDLINVERTEDHAMMER(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'lime', 'hexagon', 9),
        "Three Outside Up": (ta.CDL3OUTSIDE(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'teal', 'octagon', 10),
        "On-Neck Pattern": (ta.CDLONNECK(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'indigo', 'triangle-right', 11),
        "Bullish Counterattack": (ta.CDLCOUNTERATTACK(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'navy', 'triangle-left', 12),
        "Hanging Man": (ta.CDLHANGINGMAN(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'brown', 'star-diamond', 13),
        "Dark Cloud Cover": (ta.CDLDARKCLOUDCOVER(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'maroon', 'hourglass', 14),
        "Bearish Engulfing": (ta.CDLENGULFING(hist['Open'], hist['High'], hist['Low'], hist['Close']) * -1, 'red', 'square', 15),
        "Evening Star": (ta.CDLEVENINGSTAR(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'darkred', 'circle-open', 16),
        "Three Black Crows": (ta.CDL3BLACKCROWS(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'black', 'diamond-open', 17),
        "Black Marubozu": (ta.CDLMARUBOZU(hist['Open'], hist['High'], hist['Low'], hist['Close']) * -1, 'gray', 'cross-open', 18),
        "Three Inside Down": (ta.CDL3INSIDE(hist['Open'], hist['High'], hist['Low'], hist['Close']) * -1, 'darkorange', 'triangle-up-open', 19),
        "Bearish Harami": (ta.CDLHARAMI(hist['Open'], hist['High'], hist['Low'], hist['Close']) * -1, 'darkblue', 'triangle-down-open', 20),
        "Shooting Star": (ta.CDLSHOOTINGSTAR(hist['Open'], hist['High'], hist['Low'], hist['Close']), 'darkgreen', 'hexagon-open', 21),
        "Tweezer Top": (ta.CDLHARAMI(hist['Open'], hist['High'], hist['Low'], hist['Close']) * -1, 'darkgoldenrod', 'pentagon-open', 22),  # No specific TA-Lib function for Tweezer Top
        "Three Outside Down": (ta.CDL3OUTSIDE(hist['Open'], hist['High'], hist['Low'], hist['Close']) * -1, 'darkslategray', 'octagon-open', 23),
        "Bearish Counterattack": (ta.CDLCOUNTERATTACK(hist['Open'], hist['High'], hist['Low'], hist['Close']) * -1, 'darkviolet', 'star-open', 24),
    }

    fig = go.Figure(data=[go.Candlestick(
        x=hist.index,
        open=hist['Open'],
        high=hist['High'],
        low=hist['Low'],
        close=hist['Close'],
        increasing_line_color='lightgreen',
        decreasing_line_color='darkred'
    )])

    # Create a mask to mark which candles already have a pattern plotted
    pattern_mask = pd.Series([False] * len(hist), index=hist.index)

    # Sort patterns by priority
    sorted_patterns = sorted(patterns.items(), key=lambda x: x[1][3])

    # Add traces for each pattern using different markers and offsets
    for pattern, (values, color, marker, priority) in sorted_patterns:
        pattern_indices = values[values != 0].index
        for idx in pattern_indices:
            if not pattern_mask.loc[idx]:  # Only plot if no pattern has been plotted on this candlestick
                fig.add_trace(go.Scatter(
                    x=[idx],
                    y=[hist.loc[idx, 'Close']],
                    mode='markers',
                    marker=dict(color=color, size=10, symbol=marker),
                    name=pattern,
                    hovertemplate=f"{pattern}<extra></extra>"
                ))
                pattern_mask.loc[idx] = True

    fig.update_layout(
        title=f'{symbol} Performance ({period})',
        yaxis_title='Price',
        xaxis_title='Date',
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        hoverlabel=dict(
            font_size=16,
            font_family="Times New Roman"
        ),
        hovermode="x unified",
        showlegend=True
    )

    fig.show()


# Plot a line chart for a given TSX stock symbol using Plotly
def plot_line_chart(symbol, interval='1m', period='1d'):
    """Plot an interactive line chart with area under the line for the given TSX stock symbol."""
    tsx_symbol = get_tsx_symbol(symbol)
    stock = yf.Ticker(tsx_symbol)
    hist = stock.history(period=period, interval=interval)

    last_close = hist['Close'].iloc[-1]
    first_close = hist['Close'].iloc[0]
    color = 'purple' if last_close >= first_close else 'maroon'
    fill_color = 'rgba(128, 0, 128, 0.2)' if last_close >= first_close else 'rgba(128, 0, 0, 0.2)'

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=hist.index, 
        y=hist['Close'], 
        mode='lines', 
        name='Close Price',
        line=dict(color=color),
        fill='tozeroy',
        fillcolor=fill_color,
        hovertemplate = '<b>Open:</b> %{customdata[0]:.3f}<br><b>High:</b> %{customdata[1]:.3f}<br><b>Low:</b> %{customdata[2]:.3f}<br><b>Close:</b> %{y:.3f}',
        customdata=hist[['Open', 'High', 'Low']].values
    ))

    fig.update_layout(
        title=f'{symbol} Performance ({period})',
        yaxis_title='Price',
        xaxis_title='Date',
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        hoverlabel=dict(
            font_size=16,
            font_family="Times New Roman"
        ),
        hovermode="x unified"
    )

    fig.show()

# Plot a bar chart for a given TSX stock symbol using Plotly
def plot_bar_chart(symbol, interval, period):
    """Plot an interactive bar chart for the given TSX stock symbol."""
    tsx_symbol = get_tsx_symbol(symbol)
    stock = yf.Ticker(tsx_symbol)
    hist = stock.history(period=period, interval=interval)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=hist.index, 
        y=hist['Close'], 
        name='Close Price',
        hovertemplate = '<b>Open:</b> %{customdata[0]:.3f}<br><b>High:</b> %{customdata[1]:.3f}<br><b>Low:</b> %{customdata[2]:.3f}<br><b>Close:</b> %{y:.3f}',
        customdata=hist[['Open', 'High', 'Low']].values
    ))

    fig.update_layout(
        title=f'{symbol} Performance ({period})',
        yaxis_title='Price',
        xaxis_title='Date',
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        hoverlabel=dict(
            font_size=16,
            font_family="Times New Roman"
        ),
        hovermode="x unified"
    )

    fig.show()

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
        tsx_symbol = get_tsx_symbol(symbol)
        stock_info = yf.Ticker(tsx_symbol).info
        hist = yf.Ticker(tsx_symbol).history(period="1d")
        latest_data = hist.iloc[-1]

        current_price = get_current_stock_price(symbol)
        if current_price is not None:
            table = [
                [symbol, current_price]
            ]
            headers = ["Symbol", "Current Price"]
            alignment = ["left", "center"]
            print(tabulate(table, headers, tablefmt="grid", colalign=alignment))

            sub_headers = [
                colored("Open", 'cyan'), 
                colored("Volume", 'cyan'), 
                colored("52W High", 'cyan'), 
                colored("Yield", 'cyan'), 
                colored("High", 'cyan'), 
                colored("P/E", 'cyan'), 
                colored("52W Low", 'cyan'), 
                colored("Beta", 'cyan'), 
                colored("Low", 'cyan'), 
                colored("Market Cap", 'cyan'), 
                colored("Avg Volume", 'cyan'), 
                colored("EPS", 'cyan'),
                colored("Sector", 'cyan'),
                colored("Industry", 'cyan'),
                colored("Last Trade", 'cyan'),
                colored("Last Trade Size", 'cyan'),
                colored("Consolidated Volume", 'cyan'),
                colored("NBBO Bid/Ask Price", 'cyan'),
                colored("Bid/Ask Size", 'cyan'),
                colored("VWAP", 'cyan'),
                colored("VWAP Volume", 'cyan')
            ]
            sub_values = [
                stock_info.get('open', 'N/A'), stock_info.get('volume', 'N/A'), stock_info.get('fiftyTwoWeekHigh', 'N/A'), stock_info.get('yield', 'N/A'),
                stock_info.get('dayHigh', 'N/A'), stock_info.get('trailingPE', 'N/A'), stock_info.get('fiftyTwoWeekLow', 'N/A'), stock_info.get('beta', 'N/A'),
                stock_info.get('dayLow', 'N/A'), stock_info.get('marketCap', 'N/A'), stock_info.get('averageVolume', 'N/A'), stock_info.get('trailingEps', 'N/A'),
                stock_info.get('sector', 'N/A'), stock_info.get('industry', 'N/A'), latest_data.name.strftime('%b %d, %Y, %I:%M %p ET'),
                stock_info.get('lastTradeSize', 'N/A'), stock_info.get('consolidatedVolume', 'N/A'), f"{stock_info.get('bid', 'N/A')}/{stock_info.get('ask', 'N/A')}",
                f"{stock_info.get('bidSize', 'N/A')}/{stock_info.get('askSize', 'N/A')}", stock_info.get('vwap', 'N/A'), stock_info.get('vwapVolume', 'N/A')
            ]

            # Format sub-values to 3 decimal places if they are numeric
            sub_values = [f"{value:.3f}" if isinstance(value, (int, float)) else value for value in sub_values]

            # Pad sub_values to make the length a multiple of 4
            while len(sub_values) % 4 != 0:
                sub_values.append('N/A')

            sub_rows = [[str(sub_values[i]).center(12), str(sub_values[i + 1]).center(12), str(sub_values[i + 2]).center(12), str(sub_values[i + 3]).center(12)] for i in range(0, len(sub_values), 4)]

            sub_table = [
                sub_headers[0:4],
                sub_rows[0],
                sub_headers[4:8],
                sub_rows[1],
                sub_headers[8:12],
                sub_rows[2],
                sub_headers[12:16],
                sub_rows[3],
                sub_headers[16:20],
                sub_rows[4],
            ]

            print(tabulate(sub_table, tablefmt="grid", colalign=["center", "center", "center", "center"]))

            # Add company description
            print("\n" + colored("Company Description:", 'magenta'))
            print(stock_info.get('longBusinessSummary', 'N/A'))

            print("\nChoose chart type:")
            print("1. Candlestick Chart")
            print("2. Line Chart")
            print("3. Bar Chart")
            chart_choice = input("Enter choice: ").strip()

            print("\nChoose period:")
            periods = [
                ('1m', '1d'), ('5m', '1d'), ('15m', '1d'), ('30m', '1d'), 
                ('60m', '1mo'), ('1d', '1mo'), ('1wk', '3mo'), 
                ('1mo', '6mo'), ('3mo', '1y')
            ]
            period_labels = [
                '1 day (1 minute intervals)', '1 day (5 minute intervals)', '1 day (15 minute intervals)', 
                '1 day (30 minute intervals)', '1 month (60 minute intervals)', '1 month (1 day intervals)', 
                '3 months (1 week intervals)', '6 months (1 month intervals)', '1 year (3 month intervals)'
            ]
            for idx, label in enumerate(period_labels, 1):
                print(f"{idx}. {label}")
            period_choice = input("Enter period choice: ").strip()

            try:
                interval, period = periods[int(period_choice) - 1]
                print(f"Selected interval: {interval}, Selected period: {period}")  # Debug statement
            except (ValueError, IndexError):
                print("Invalid choice. Displaying 1 day data by default.")
                interval, period = '1d', '1d'

            if chart_choice == '1':
                plot_candlestick_chart(symbol, interval, period)
            elif chart_choice == '2':
                plot_line_chart(symbol, interval, period)
            elif chart_choice == '3':
                plot_bar_chart(symbol, interval, period)
            else:
                print("Invalid choice. Displaying candlestick chart by default.")
                plot_candlestick_chart(symbol, interval, period)
        else:
            print("Unable to fetch current price for the symbol.")
    else:
        print("Symbol validation failed. Please try again.")

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
                    print(subject)
                    print(body)
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
