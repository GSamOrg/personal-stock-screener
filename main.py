import os
from dotenv import load_dotenv

import yfinance as yf
import pandas as pd
import numpy as np
from stqdm import stqdm
import streamlit as st
import requests

from loguru import logger
from utils import DataframeCache


load_dotenv()


def get_nyse_stocks():
    # URL of the Wikipedia page with the list of NYSE-listed companies
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

    # Read the tables on the webpage
    tables = pd.read_html(url)

    # The first table usually contains the list of companies
    nyse_stocks = tables[0]

    # Extract the tickers
    tickers = nyse_stocks["Symbol"].tolist()

    return nyse_stocks, tickers


def check_fields_if_valid(fields: list[str]) -> bool:
    expected_fields = [
        "Current Assets",
        "Current Liabilities",
        "Inventory",
        "Cash Cash Equivalents And Short Term Investments",
        "Total Liabilities Net Minority Interest",
        "Common Stock Equity",
        "Current Capital Lease Obligation",
    ]

    result = [f in fields for f in expected_fields]

    return sum(result) == len(expected_fields)


# Function to fetch financial data
def get_financial_data(ticker):
    stock = yf.Ticker(ticker)

    try:
        # Get balance sheet data
        balance_sheet = stock.quarterly_balancesheet
        nil_pos_col = balance_sheet.columns[0]
        info = stock.info

        if check_fields_if_valid(list(balance_sheet.index)):
            logger.info(f"Adding Ticker {ticker}")
            current_assets = balance_sheet.loc["Current Assets", nil_pos_col]
            current_liabilities = balance_sheet.loc["Current Liabilities", nil_pos_col]
            inventory = balance_sheet.loc["Inventory", nil_pos_col]
            cash_equivalents = balance_sheet.loc[
                "Cash Cash Equivalents And Short Term Investments", nil_pos_col
            ]
            total_liabilities = balance_sheet.loc[
                "Total Liabilities Net Minority Interest", nil_pos_col
            ]
            common_equity = balance_sheet.loc["Common Stock Equity", nil_pos_col]

            # Calculations
            current_ratio = current_assets / current_liabilities
            quick_ratio = (
                current_assets - inventory
            ) / current_liabilities  # If inventory is not available, use cash equivalents
            debt_to_equity = total_liabilities / common_equity
            capital_lease_obligation = balance_sheet.loc[
                "Current Capital Lease Obligation", nil_pos_col
            ]
            free_cash_flow = (
                cash_equivalents - capital_lease_obligation
                if capital_lease_obligation is not None
                else np.nan
            )  # Rough substitute

            # Dividend Yield and Payout Ratio
            pe_ratio = info.get("forwardPE", np.nan)
            dividend_yield = info.get("dividendYield", np.nan)
            payout_ratio = info.get("payoutRatio", np.nan)

            # Store all in a dictionary
            data = {
                "Ticker": ticker,
                "Current Ratio": current_ratio,
                "Quick Ratio": quick_ratio,
                "Debt to Equity": debt_to_equity,
                "P/E Ratio": pe_ratio,
                "Dividend Yield": dividend_yield,
                "Payout Ratio": payout_ratio,
                "Free Cash Flow": free_cash_flow,
            }
            return data
        else:
            return None
    except Exception as e:
        logger.info(f"Ticker failed: {ticker} with {e}")
        return None


def get_fmp_data(ticker: str, api_key: str) -> dict:
    try:
        url = f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}?period=quarter&apikey={api_key}"
        resp = requests.get(url)

        return resp.json()
    except Exception as e:
        print(e)


# Fetch data for all tickers
def filter_data_to_criteria(stock_data: pd.DataFrame, criteria: dict) -> pd.DataFrame:
    df = pd.DataFrame(stock_data)
    # Apply the screening criteria
    filtered_stocks = df[
        (df["Current Ratio"] > criteria["current_ratio"])
        & (df["Debt to Equity"] < criteria["debt_to_equity"])
        & (df["P/E Ratio"] < criteria["pe_ratio"])
        & (df["Dividend Yield"] > criteria["dividend_yield"])
        & (df["Payout Ratio"] < criteria["payout_ratio"])
        & (df["Free Cash Flow"] > 0)  # Ensure positive free cash flow
    ]

    return filtered_stocks


def main() -> None:
    # Streamlit App
    st.title("Stock Screener App")
    cache = DataframeCache()
    # Adjust financial ratios using Streamlit sliders
    st.sidebar.header("Set Financial Ratios")
    current_ratio_min = st.sidebar.slider("Minimum Current Ratio", 0.0, 10.0, 1.5)
    debt_to_equity_max = st.sidebar.slider(
        "Maximum Debt to Equity Ratio", 0.0, 5.0, 0.5
    )
    pe_ratio_max = st.sidebar.slider("Maximum P/E Ratio", 0, 100, 20)
    dividend_yield_min = st.sidebar.slider("Minimum Dividend Yield (%)", 0.0, 10.0, 2.0)
    payout_ratio_max = st.sidebar.slider("Maximum Payout Ratio", 0.0, 1.0, 0.6)

    if st.button("Run Stock Screener"):
        criteria = {
            "current_ratio": current_ratio_min,
            "debt_to_equity": debt_to_equity_max,
            "dividend_yield": dividend_yield_min / 100,  # 2%
            "payout_ratio": payout_ratio_max,
            "pe_ratio": pe_ratio_max,
        }

        stocks, symbols = get_nyse_stocks()
        stocks["Ticker"] = stocks["Symbol"]
        if cache.is_stale():
            stock_fin_list = [get_financial_data(ticker) for ticker in stqdm(symbols)]
            stock_fin_list = [item for item in stock_fin_list if item]
            stock_data = pd.DataFrame(stock_fin_list)
            cache.write_cache(stock_data)
        else:
            stock_data = cache.load_cache()

        filtered_df = filter_data_to_criteria(stock_data=stock_data, criteria=criteria)

        merge_df = pd.merge(filtered_df, stocks, on="Ticker")
        st.write("Filtered Stocks:")
        st.dataframe(
            merge_df.loc[
                :,
                [
                    "Ticker",
                    "GICS Sector",
                    "GICS Sub-Industry",
                    "Current Ratio",
                    "Debt to Equity",
                    "P/E Ratio",
                    "Dividend Yield",
                    "Payout Ratio",
                ],
            ]
        )


if __name__ == "__main__":
    main()
