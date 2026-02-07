Finance Database Schema – Overview

This folder contains the database schema and database management code for a finance application.

The database is designed to store structured financial data in a clean and organised manner.
It acts as the single source of truth for company information, filings, financial statements, ratios, and credit assessments.

The system uses:

PostgreSQL as the database

SQLAlchemy ORM for database interaction

What is ORM (Simple Explanation)

ORM stands for Object Relational Mapping.

ORM allows us to work with the database using Python classes instead of writing SQL queries manually.

Example

Without ORM (SQL):

INSERT INTO companies (ticker, name)
VALUES ('AAPL', 'Apple Inc.');


With ORM (Python):

company = Company(ticker="AAPL", name="Apple Inc.")
session.add(company)
session.commit()


ORM automatically converts Python code into SQL internally.

What is Base and Why Every Class Inherits It
Base = declarative_base()


Base is the foundation class provided by SQLAlchemy.

When a class inherits from Base:

SQLAlchemy treats it as a database table

Python variables become database columns

Tables can be created automatically

Database Tables (Detailed Explanation)
1. Company Table (companies)

This table stores basic company master data.
Every other table depends on this table.

Column meanings

id
Internal auto-generated number.
Used only by the database as a primary key.

ticker
Stock market symbol of the company.
Example: AAPL, TSLA.

name
Full registered name of the company.
Example: Apple Inc.

cik
Unique company ID given by the SEC.
Used to fetch official filings.
This value never changes.

sic_code
Industry classification code.
Helps group similar companies.

industry
Human-readable industry name.
Example: Consumer Electronics.

sector
Broad business category.
Example: Technology.

created_at
Date and time when the record was created.

updated_at
Date and time when the record was last updated.

2. SEC Filings Table (sec_filings)

This table stores information about SEC filings, not the financial numbers.

Column meanings

id
Internal primary key.

ticker
Company stock ticker.

filing_type
Type of SEC filing.
Example: 10-K (annual), 10-Q (quarterly).

fiscal_year
Financial year of the filing.
Example: 2023.

fiscal_period
Quarter or year of filing.
Values: Q1, Q2, Q3, Q4, FY.

filing_date
Date when the filing was submitted to the SEC.

accession_number
Unique ID given by the SEC to each filing.
Used to identify the exact document.

document_url
Link to the filing document.

processed
Indicates whether the filing has been processed.
0 = Not processed
1 = Processed

created_at
Record creation timestamp.

3. Financial Statements Table (financial_statements)

This table stores actual financial values extracted from filings.

Common columns

ticker
Company stock ticker.

fiscal_year
Financial year of the data.

fiscal_period
Quarter or full year (Q1, FY, etc.).

filing_date
Date of the filing from which data is taken.

Balance Sheet columns

total_assets
Total assets owned by the company.

current_assets
Assets that can be converted to cash within 1 year.

total_liabilities
Total amount the company owes.

current_liabilities
Liabilities due within 1 year.

shareholders_equity
Net value belonging to shareholders.

retained_earnings
Profits reinvested in the business.

working_capital
Current assets minus current liabilities.

Income Statement columns

revenue
Total sales or income.

gross_profit
Revenue minus cost of goods sold.

operating_income
Profit from core business operations.

ebit
Earnings before interest and tax.

net_income
Final profit after all expenses.

Cash Flow columns

operating_cash_flow
Cash generated from daily operations.

free_cash_flow
Cash left after capital expenses.

Debt columns

total_debt
Total borrowed money.

short_term_debt
Debt due within 1 year.

long_term_debt
Debt due after 1 year.

4. Financial Ratios Table (financial_ratios)

This table stores calculated ratios based on financial statements.

Column meanings

ticker
Company stock ticker.

fiscal_year
Financial year of the ratios.

calculation_date
Date when ratios were calculated.

Liquidity ratios

current_ratio
Ability to pay short-term obligations.

quick_ratio
Liquidity without inventory.

cash_ratio
Ability to pay liabilities using cash only.

Leverage ratios

debt_to_equity
Debt compared to shareholder equity.

debt_to_assets
Debt compared to total assets.

interest_coverage
Ability to pay interest expenses.

Profitability ratios

gross_margin
Gross profit as a percentage of revenue.

operating_margin
Operating profit as a percentage of revenue.

net_margin
Net profit as a percentage of revenue.

roa
Return generated from assets.

roe
Return generated for shareholders.

Credit metric

altman_z_score
Score used to estimate bankruptcy risk.

5. Credit Assessment Table (credit_assessments)

This table stores credit evaluation results.

Column meanings

ticker
Company stock ticker.

assessment_date
Date when assessment was done.

liquidity_score
Score (1–10) for liquidity health.

leverage_score
Score representing debt risk.

profitability_score
Score for profit strength.

overall_credit_score
Final score (1–100).

credit_rating
Rating like AAA, AA, BBB.

recommendation
Decision such as Approve or Reject.

risk_summary
Text summary of key risks.

analyst_notes
Manual comments by analyst.

compliance_check_passed
Whether compliance checks passed.

created_at
Record creation timestamp.

Database Manager

The DatabaseManager handles all database operations.

Responsibilities

Creates database connection

Manages sessions

Creates and drops tables

Performs health checks

Example usage
with db_manager.get_session() as session:
    session.add(company)

Summary

This database design:

Clearly separates different types of financial data

Is easy to understand and maintain

Follows good ORM practices

Suitable for real-world finance systems

If you want next:

Even simpler version for non-tech people

ER diagram explanation in plain English

Interview explanation (2–3 minute answer)

Review and improvements suggestion

How All These Tables Work Together (Big Picture)

Think of this system like a company financial file that grows step by step.

You cannot jump directly to credit decision or ratios.
You must go in this order:

Company → Filings → Financial Numbers → Ratios → Credit Decision

Let’s walk through this slowly.

Step 1: Company Table – “Who is the company?”

This is the starting point.

Before doing anything in finance, you must know:

Which company?

What business does it do?

Which sector and industry?

That is why the Company table exists.

Example
Company: Apple Inc.
Ticker: AAPL
Sector: Technology
Industry: Consumer Electronics


Without this:

You don’t know whom the data belongs to

You cannot group or compare companies

👉 Everything else depends on this table

Step 2: SEC Filings – “What did the company officially submit?”

Companies don’t directly give you clean numbers.

They first submit reports to the government (SEC) like:

Annual reports (10-K)

Quarterly reports (10-Q)

The SEC Filings table answers:

Which report?

For which year?

Has it been processed or not?

Example
AAPL | 10-K | FY | 2023 | Filed on 29-Oct-2023


Why this is needed:

One company files many reports

You must track which report you are using

Avoid duplicate or missing data

👉 This table is like a register of documents

Step 3: Financial Statements – “What are the actual numbers?”

Filings contain raw financial data.

From those filings, you extract:

Revenue

Profit

Assets

Debt

Cash

All these go into the Financial Statements table.

Example
Revenue: 383,000 Cr
Net Income: 95,000 Cr
Total Assets: 352,000 Cr


Why this is needed:

This is the core financial data

All analysis depends on these numbers

This is what companies are judged on

👉 Think of this as the marksheet of the company

Step 4: Financial Ratios – “What do these numbers actually mean?”

Raw numbers alone are confusing.

Example:

Revenue is high – but is debt also high?

Profit is good – but is cash flow weak?

That’s why Financial Ratios are needed.

Ratios answer questions like:

Can the company pay its bills?

Is the company over-borrowed?

Is the company profitable compared to size?

Example
Current Ratio: 1.5
Debt to Equity: 0.8
ROE: 24%


Why this is needed:

Ratios make companies comparable

Easier to judge health

Used by banks, investors, and analysts

👉 Ratios are interpreted scores, not raw data

Step 5: Credit Assessment – “Should we trust this company?”

This is the final decision layer.

Using:

Financial statements

Financial ratios

Business understanding

A credit decision is made:

Can we lend money?

Is risk high or low?

Approve or reject?

The Credit Assessment table stores this decision.

Example
Overall Credit Score: 82
Rating: AA
Recommendation: Approve


Why this is needed:

Decisions must be recorded

Required for audits and compliance

Allows comparison over time

👉 This is the final outcome of all analysis

How Everything Connects (Simple Flow)
Company
   ↓
SEC Filings
   ↓
Financial Statements
   ↓
Financial Ratios
   ↓
Credit Assessment


Each step depends on the previous step.