"""
PostgreSQL database initialization and schema management.
SINGLE SOURCE OF TRUTH FOR ALL STRUCTURED FINANCE DATA
"""

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Numeric,
    DateTime,
    Text,
    Index,
    UniqueConstraint,
    CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import logging
from datetime import datetime

from config.settings import get_settings

logger = logging.getLogger(__name__)
Base = declarative_base()


class Company(Base):
    """Company master table."""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    cik = Column(String(10), unique=True, nullable=False, index=True)
    sic_code = Column(String(10))
    industry = Column(String(255))
    sector = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_company_ticker", "ticker"),
        Index("idx_company_cik", "cik"),
    )


class SECFiling(Base):
    """SEC filing metadata."""
    __tablename__ = "sec_filings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    filing_type = Column(String(10), nullable=False)  # 10-K, 10-Q
    fiscal_year = Column(Integer, nullable=False)
    fiscal_period = Column(String(10), nullable=False)  # Q1, Q2, Q3, Q4, FY
    filing_date = Column(DateTime, nullable=False)
    accession_number = Column(String(30), unique=True, nullable=False)
    document_url = Column(Text)
    processed = Column(Integer, default=0)  # 0=not processed, 1=processed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("ticker", "fiscal_year", "fiscal_period", name="uq_filing"),
        Index("idx_filing_ticker_year", "ticker", "fiscal_year"),
        Index("idx_filing_date", "filing_date"),
    )


class FinancialStatement(Base):
    """Financial statement data."""
    __tablename__ = "financial_statements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    fiscal_year = Column(Integer, nullable=False)
    fiscal_period = Column(String(10), nullable=False)
    filing_date = Column(DateTime, nullable=False)
    
    # Balance Sheet
    total_assets = Column(Numeric(20, 2))
    current_assets = Column(Numeric(20, 2))
    total_liabilities = Column(Numeric(20, 2))
    current_liabilities = Column(Numeric(20, 2))
    shareholders_equity = Column(Numeric(20, 2))
    retained_earnings = Column(Numeric(20, 2))
    working_capital = Column(Numeric(20, 2))
    
    # Income Statement
    revenue = Column(Numeric(20, 2))
    gross_profit = Column(Numeric(20, 2))
    operating_income = Column(Numeric(20, 2))
    ebit = Column(Numeric(20, 2))
    net_income = Column(Numeric(20, 2))
    
    # Cash Flow
    operating_cash_flow = Column(Numeric(20, 2))
    free_cash_flow = Column(Numeric(20, 2))
    
    # Debt
    total_debt = Column(Numeric(20, 2))
    short_term_debt = Column(Numeric(20, 2))
    long_term_debt = Column(Numeric(20, 2))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("ticker", "fiscal_year", "fiscal_period", name="uq_statement"),
        Index("idx_statement_ticker_year", "ticker", "fiscal_year"),
        CheckConstraint("fiscal_year >= 1900 AND fiscal_year <= 2100", name="chk_year"),
    )


class FinancialRatio(Base):
    """Calculated financial ratios."""
    __tablename__ = "financial_ratios"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    fiscal_year = Column(Integer, nullable=False)
    calculation_date = Column(DateTime, default=datetime.utcnow)
    
    # Liquidity
    current_ratio = Column(Numeric(10, 4))
    quick_ratio = Column(Numeric(10, 4))
    cash_ratio = Column(Numeric(10, 4))
    
    # Leverage
    debt_to_equity = Column(Numeric(10, 4))
    debt_to_assets = Column(Numeric(10, 4))
    interest_coverage = Column(Numeric(10, 4))
    
    # Profitability
    gross_margin = Column(Numeric(10, 4))
    operating_margin = Column(Numeric(10, 4))
    net_margin = Column(Numeric(10, 4))
    roa = Column(Numeric(10, 4))
    roe = Column(Numeric(10, 4))
    
    # Credit Metrics
    altman_z_score = Column(Numeric(10, 4))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_ratio_ticker_year", "ticker", "fiscal_year"),
    )


class CreditAssessmentRecord(Base):
    """Credit assessment history."""
    __tablename__ = "credit_assessments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False, index=True)
    assessment_date = Column(DateTime, default=datetime.utcnow)
    
    liquidity_score = Column(Integer)
    leverage_score = Column(Integer)
    profitability_score = Column(Integer)
    overall_credit_score = Column(Integer)
    credit_rating = Column(String(10))
    recommendation = Column(String(50))
    
    risk_summary = Column(Text)
    analyst_notes = Column(Text)
    compliance_check_passed = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_assessment_ticker_date", "ticker", "assessment_date"),
        CheckConstraint("liquidity_score >= 1 AND liquidity_score <= 10", name="chk_liquidity"),
        CheckConstraint("overall_credit_score >= 1 AND overall_credit_score <= 100", name="chk_credit"),
    )


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.SessionLocal = None
        self._initialize()
    
    def _initialize(self):
        """Initialize database engine and session factory."""
        try:
            self.engine = create_engine(
                self.settings.database.connection_string,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # Verify connections before using
                echo=False,
                future=True
            )
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            logger.info("Database connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def create_tables(self):
        """Create all tables if they don't exist."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all tables. USE WITH CAUTION!"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.warning("All database tables dropped")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        Automatically handles commit/rollback and cleanup.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Singleton instance
_db_manager: DatabaseManager = None


def get_db_manager() -> DatabaseManager:
    """Get database manager singleton."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager