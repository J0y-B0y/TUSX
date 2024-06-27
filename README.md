# TUSX: TSX Portfolio Management System
**Author:** Divjot Singh

## Problem Statement:

Efficient portfolio management is crucial for investors, particularly those who are new to the market. The lack of a fast, streamlined platform for tracking and managing investments can hinder growth and decision-making. TUSX aims to provide a truly fast and efficient mini portfolio management system tailored for the Toronto Stock Exchange (TSX), empowering investors, especially those who are blooming, with the tools they need to succeed.

TUSX enhances portfolio management by offering real-time tracking, detailed financial charts, automated email alerts, and secure storage using Redis. This comprehensive solution promotes an organized workflow, fostering productivity and informed decision-making.

## Pre-Requisites:

- Python 3.x
- Redis Server
- Email account for sending notifications (e.g., Gmail)

## Structure:

The project comprises a single Python file (`main.py`) and a `requirements.txt` file.

- **Main File (`main.py`):**
  This file encapsulates all functionalities, including adding, updating, deleting, and viewing stocks, fetching stock details, monitoring the portfolio for threshold breaches, and sending email notifications.

- **Configuration File (`requirements.txt`):**
  This file enumerates all the dependencies required to run the project, ensuring that users can set up the necessary environment without compatibility issues.

## Features:

- **Add Stock:** Add new stocks to the portfolio with purchase details and loss thresholds.
- **Update Stock:** Modify existing stock details in the portfolio.
- **Delete Stock:** Remove stocks from the portfolio.
- **View Stock Details:** Access detailed information for a specific stock, including a candlestick chart.
- **List Stocks:** Display all stocks in the portfolio with their current status.
- **Portfolio Summary:** Provide a comprehensive summary of the portfolio.
- **Search and View Stock:** Search for a stock and view its current details.
- **Automated Alerts:** Monitor the portfolio and send email notifications if the stock price drops below the threshold.

## Configuration Variables:
These variables need to be configured before running the program:

- **Email Configuration:**
  - `from_email`: Sender's email address.
  - `from_password`: Sender's email password.

- **Redis Configuration:**
  - `r`: Redis connection details (host, port, db).

## Dependencies:
Please check requirements.txt file. This program is to be run in a virtual environment with requirements.txt dependencies installed.
