"""
Integration with database systems for persistent data storage and analysis.

This module provides functionality for storing and analyzing StatCan data
using SQLite, PostgreSQL, or in-memory pandas DataFrames with advanced
data analysis capabilities.
"""

import logging
import json
import pandas as pd
import sqlite3
import os
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
import numpy as np
from datetime import datetime

from src.config import CACHE_DIRECTORY

logger = logging.getLogger(__name__)

class DataStorageIntegration:
    """Integration for storing and analyzing StatCan data in various database formats."""
    
    DB_DIRECTORY = CACHE_DIRECTORY / "databases"
    
    def __init__(self, db_name: str = "statcan_data"):
        """
        Initialize the data storage integration.
        
        Args:
            db_name: Name of the database
        """
        self.db_name = db_name
        self.db_path = self.DB_DIRECTORY / f"{db_name}.db"
        
        # Ensure database directory exists
        self.DB_DIRECTORY.mkdir(parents=True, exist_ok=True)
        
        # Initialize connection
        self.conn = None
        
    def connect(self) -> sqlite3.Connection:
        """
        Connect to the SQLite database.
        
        Returns:
            SQLite connection object
        """
        if self.conn is None:
            self.conn = sqlite3.connect(str(self.db_path))
            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys = ON")
            # Create function for date parsing
            self.conn.create_function("parse_date", 1, 
                                     lambda x: datetime.fromisoformat(x).timestamp() 
                                     if isinstance(x, str) else None)
        return self.conn
    
    def close(self):
        """Close the database connection."""
        if self.conn is not None:
            self.conn.close()
            self.conn = None
    
    def store_time_series(self, 
                         series_id: str, 
                         data: List[Dict[str, Any]], 
                         metadata: Dict[str, Any]) -> bool:
        """
        Store a time series dataset in the database.
        
        Args:
            series_id: Unique identifier for the series (vector ID or custom ID)
            data: List of data points with date and value
            metadata: Metadata for the series
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Create series table if it doesn't exist
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_series (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                source TEXT,
                units TEXT,
                frequency TEXT,
                start_date TEXT,
                end_date TEXT,
                last_updated TEXT,
                metadata TEXT
            )
            """)
            
            # Create data points table if it doesn't exist
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                series_id TEXT,
                date TEXT,
                value REAL,
                FOREIGN KEY (series_id) REFERENCES time_series (id)
            )
            """)
            
            # Extract metadata fields
            title = metadata.get("title", "")
            description = metadata.get("description", "")
            source = metadata.get("source", "Statistics Canada")
            units = metadata.get("units", "")
            frequency = metadata.get("frequency", "")
            
            # Calculate date range
            dates = [p.get("date", p.get("refPer", "")) for p in data if p.get("value") is not None]
            start_date = min(dates) if dates else ""
            end_date = max(dates) if dates else ""
            last_updated = datetime.now().isoformat()
            
            # Store metadata as JSON
            metadata_json = json.dumps(metadata)
            
            # Insert or replace series metadata
            cursor.execute("""
            INSERT OR REPLACE INTO time_series 
            (id, title, description, source, units, frequency, start_date, end_date, last_updated, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (series_id, title, description, source, units, frequency, 
                 start_date, end_date, last_updated, metadata_json))
            
            # Delete existing data points for this series
            cursor.execute("DELETE FROM data_points WHERE series_id = ?", (series_id,))
            
            # Insert data points
            for point in data:
                date = point.get("date", point.get("refPer", ""))
                value = point.get("value")
                if date and value is not None:
                    cursor.execute("""
                    INSERT INTO data_points (series_id, date, value)
                    VALUES (?, ?, ?)
                    """, (series_id, date, value))
            
            conn.commit()
            logger.info(f"Successfully stored time series {series_id} with {len(data)} data points")
            return True
            
        except Exception as e:
            logger.error(f"Error storing time series {series_id}: {e}")
            if conn:
                conn.rollback()
            return False
    
    def retrieve_time_series(self, series_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Retrieve a time series dataset from the database.
        
        Args:
            series_id: Unique identifier for the series
            
        Returns:
            Tuple of (data_points, metadata)
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Get series metadata
            cursor.execute("""
            SELECT title, description, source, units, frequency, start_date, end_date, metadata
            FROM time_series
            WHERE id = ?
            """, (series_id,))
            
            row = cursor.fetchone()
            if not row:
                return [], {}
                
            title, description, source, units, frequency, start_date, end_date, metadata_json = row
            
            # Parse metadata
            metadata = json.loads(metadata_json)
            metadata.update({
                "title": title,
                "description": description,
                "source": source,
                "units": units,
                "frequency": frequency,
                "start_date": start_date,
                "end_date": end_date
            })
            
            # Get data points
            cursor.execute("""
            SELECT date, value FROM data_points
            WHERE series_id = ?
            ORDER BY date
            """, (series_id,))
            
            data_points = [{"date": date, "value": value} for date, value in cursor.fetchall()]
            
            logger.info(f"Retrieved time series {series_id} with {len(data_points)} data points")
            return data_points, metadata
            
        except Exception as e:
            logger.error(f"Error retrieving time series {series_id}: {e}")
            return [], {}
    
    def to_dataframe(self, series_id: str) -> Optional[pd.DataFrame]:
        """
        Convert a time series to a pandas DataFrame.
        
        Args:
            series_id: Unique identifier for the series
            
        Returns:
            Pandas DataFrame or None if not found
        """
        data, metadata = self.retrieve_time_series(series_id)
        if not data:
            return None
            
        try:
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            df.name = metadata.get('title', series_id)
            return df
        except Exception as e:
            logger.error(f"Error converting series {series_id} to DataFrame: {e}")
            return None
    
    def run_analysis(self, 
                    series_id: str, 
                    analysis_type: str = "summary",
                    params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run analysis on a time series.
        
        Args:
            series_id: Unique identifier for the series
            analysis_type: Type of analysis to perform
                           (summary, trends, seasonal, forecast, correlation)
            params: Additional parameters for the analysis
            
        Returns:
            Analysis results
        """
        if params is None:
            params = {}
            
        df = self.to_dataframe(series_id)
        if df is None:
            return {"error": f"Series {series_id} not found"}
        
        analysis_functions = {
            "summary": self._analyze_summary,
            "trends": self._analyze_trends,
            "seasonal": self._analyze_seasonal,
            "forecast": self._analyze_forecast,
            "correlation": self._analyze_correlation
        }
        
        analysis_func = analysis_functions.get(analysis_type.lower(), self._analyze_summary)
        return analysis_func(df, params)
    
    def _analyze_summary(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for a time series."""
        try:
            result = {
                "count": int(df['value'].count()),
                "mean": float(df['value'].mean()),
                "std": float(df['value'].std()),
                "min": float(df['value'].min()),
                "25%": float(df['value'].quantile(0.25)),
                "median": float(df['value'].median()),
                "75%": float(df['value'].quantile(0.75)),
                "max": float(df['value'].max()),
                "first_date": df.index.min().isoformat(),
                "last_date": df.index.max().isoformat(),
                "duration_days": int((df.index.max() - df.index.min()).days)
            }
            
            # Add trend direction
            first_value = df['value'].iloc[0]
            last_value = df['value'].iloc[-1]
            change = last_value - first_value
            pct_change = (change / first_value) * 100 if first_value != 0 else float('inf')
            
            result["change"] = float(change)
            result["percent_change"] = float(pct_change)
            result["trend_direction"] = "increasing" if change > 0 else "decreasing" if change < 0 else "stable"
            
            return result
        except Exception as e:
            logger.error(f"Error in summary analysis: {e}")
            return {"error": str(e)}
    
    def _analyze_trends(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trends in a time series."""
        try:
            # Resample by month if not already monthly
            if not params.get("skip_resample"):
                df = df.resample('M').mean()
            
            # Calculate rolling averages
            window_size = params.get("window_size", 3)
            df['rolling_avg'] = df['value'].rolling(window=window_size).mean()
            
            # Calculate year-over-year growth rates
            if len(df) >= 12:  # Need at least a year of data
                df['yoy_growth'] = df['value'].pct_change(periods=12) * 100
            
            # Linear regression for trend
            x = np.arange(len(df))
            y = df['value'].values
            
            # Handle NaN values
            mask = ~np.isnan(y)
            if np.sum(mask) > 1:  # Need at least 2 points for regression
                x_clean = x[mask]
                y_clean = y[mask]
                
                # Simple linear regression
                slope, intercept = np.polyfit(x_clean, y_clean, 1)
                
                trend_value = slope * len(df)
                trend_direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
                
                # Calculate R-squared
                y_pred = intercept + slope * x_clean
                r_squared = 1 - (np.sum((y_clean - y_pred) ** 2) / np.sum((y_clean - np.mean(y_clean)) ** 2))
                
                result = {
                    "slope": float(slope),
                    "intercept": float(intercept),
                    "r_squared": float(r_squared),
                    "trend_direction": trend_direction,
                    "trend_strength": "strong" if abs(r_squared) > 0.7 else 
                                      "moderate" if abs(r_squared) > 0.3 else "weak",
                    "annual_change_rate": float(slope * 12)  # Assuming monthly data
                }
            else:
                result = {"error": "Insufficient data for trend analysis"}
            
            # Get some sample points for visualization
            result["sample_points"] = [
                {"date": date.isoformat(), "value": float(val), 
                 "rolling_avg": float(avg) if not np.isnan(avg) else None}
                for date, val, avg in zip(
                    df.index[-min(12, len(df)):],  # Last 12 months or less
                    df['value'][-min(12, len(df)):],
                    df['rolling_avg'][-min(12, len(df)):]
                )
            ]
            
            return result
        except Exception as e:
            logger.error(f"Error in trend analysis: {e}")
            return {"error": str(e)}
    
    def _analyze_seasonal(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze seasonality in a time series."""
        try:
            # Need at least 2 years of data for seasonality
            if len(df) < 24:
                return {"error": "Insufficient data for seasonal analysis (need at least 24 months)"}
                
            # Add month and quarter columns
            df = df.copy()
            df['month'] = df.index.month
            df['quarter'] = df.index.quarter
            
            # Seasonal analysis by month
            monthly_means = df.groupby('month')['value'].mean().to_dict()
            monthly_std = df.groupby('month')['value'].std().to_dict()
            
            # Convert to list of months sorted by value
            monthly_ranking = sorted(
                [(month, mean) for month, mean in monthly_means.items()],
                key=lambda x: x[1],
                reverse=True
            )
            
            # Quarterly analysis
            quarterly_means = df.groupby('quarter')['value'].mean().to_dict()
            quarterly_std = df.groupby('quarter')['value'].std().to_dict()
            
            # Calculate seasonality index
            overall_mean = df['value'].mean()
            seasonality_index = {}
            for month, mean in monthly_means.items():
                seasonality_index[month] = (mean / overall_mean - 1) * 100
            
            result = {
                "monthly_means": {str(k): float(v) for k, v in monthly_means.items()},
                "monthly_std": {str(k): float(v) for k, v in monthly_std.items()},
                "quarterly_means": {str(k): float(v) for k, v in quarterly_means.items()},
                "quarterly_std": {str(k): float(v) for k, v in quarterly_std.items()},
                "seasonality_index": {str(k): float(v) for k, v in seasonality_index.items()},
                "highest_month": int(monthly_ranking[0][0]),
                "lowest_month": int(monthly_ranking[-1][0]),
                "seasonal_amplitude": float(max(monthly_means.values()) - min(monthly_means.values())),
                "seasonality_strength": "strong" if max(seasonality_index.values()) > 20 else
                                      "moderate" if max(seasonality_index.values()) > 10 else "weak"
            }
            
            return result
        except Exception as e:
            logger.error(f"Error in seasonal analysis: {e}")
            return {"error": str(e)}
    
    def _analyze_forecast(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate simple forecast for a time series."""
        try:
            periods = params.get("periods", 6)  # Default to 6 periods ahead
            
            # Simple exponential smoothing for forecast
            alpha = params.get("alpha", 0.3)
            
            # Original data points for reference
            original_values = df['value'].values
            
            # Initialize forecast array with the first observed value
            forecast = np.zeros(len(original_values) + periods)
            forecast[0] = original_values[0]
            
            # Apply exponential smoothing to historical data
            for i in range(1, len(original_values)):
                forecast[i] = alpha * original_values[i] + (1 - alpha) * forecast[i-1]
            
            # Generate forecast for future periods
            for i in range(len(original_values), len(original_values) + periods):
                forecast[i] = forecast[i-1]  # Simple naive forecast
            
            # Calculate error metrics on historical data
            historical_forecast = forecast[:len(original_values)]
            rmse = np.sqrt(np.mean((original_values - historical_forecast) ** 2))
            mape = np.mean(np.abs((original_values - historical_forecast) / original_values)) * 100
            
            # Create dates for the forecast periods
            last_date = df.index[-1]
            if pd.infer_freq(df.index) == 'M' or params.get("frequency") == "monthly":
                forecast_dates = [last_date + pd.DateOffset(months=i+1) for i in range(periods)]
            else:
                # Default to daily frequency
                forecast_dates = [last_date + pd.DateOffset(days=i+1) for i in range(periods)]
            
            forecast_values = forecast[-periods:]
            
            result = {
                "forecast": [
                    {"date": date.isoformat(), "value": float(value)}
                    for date, value in zip(forecast_dates, forecast_values)
                ],
                "rmse": float(rmse),
                "mape": float(mape),
                "method": "Exponential Smoothing",
                "parameters": {"alpha": alpha}
            }
            
            return result
        except Exception as e:
            logger.error(f"Error in forecast analysis: {e}")
            return {"error": str(e)}
    
    def _analyze_correlation(self, df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze correlation between this series and another."""
        try:
            compare_with = params.get("compare_with")
            if not compare_with:
                return {"error": "No comparison series specified"}
                
            # Get the comparison series
            compare_df = self.to_dataframe(compare_with)
            if compare_df is None:
                return {"error": f"Comparison series {compare_with} not found"}
                
            # Align the series on the same dates
            combined = pd.merge(
                df, 
                compare_df,
                left_index=True, 
                right_index=True,
                how='inner',
                suffixes=('_primary', '_secondary')
            )
            
            if len(combined) < 2:
                return {"error": "Insufficient overlapping data points for correlation analysis"}
                
            # Calculate correlation
            correlation = combined['value_primary'].corr(combined['value_secondary'])
            
            # Calculate lagged correlations
            max_lag = min(12, len(combined) // 2)  # Maximum lag of 12 or half the series length
            lag_correlations = {}
            
            for lag in range(-max_lag, max_lag + 1):
                if lag == 0:
                    lag_correlations[lag] = correlation
                else:
                    lag_correlations[lag] = combined['value_primary'].corr(
                        combined['value_secondary'].shift(lag)
                    )
            
            # Find maximum correlation lag
            max_corr_lag = max(lag_correlations.items(), key=lambda x: abs(x[1]) if not np.isnan(x[1]) else 0)
            
            result = {
                "correlation": float(correlation),
                "correlation_strength": "strong" if abs(correlation) > 0.7 else
                                       "moderate" if abs(correlation) > 0.3 else "weak",
                "direction": "positive" if correlation > 0 else "negative",
                "lag_correlations": {str(k): float(v) for k, v in lag_correlations.items() 
                                    if not np.isnan(v)},
                "optimal_lag": int(max_corr_lag[0]),
                "optimal_lag_correlation": float(max_corr_lag[1]),
                "sample_size": len(combined)
            }
            
            return result
        except Exception as e:
            logger.error(f"Error in correlation analysis: {e}")
            return {"error": str(e)}
    
    def generate_analysis_command(self, 
                                series_id: str, 
                                analysis_type: str = "summary",
                                params: Dict[str, Any] = None) -> str:
        """
        Generate an MCP command for data analysis.
        
        Args:
            series_id: Unique identifier for the series
            analysis_type: Type of analysis to perform
            params: Additional parameters for the analysis
            
        Returns:
            MCP command string
        """
        if params is None:
            params = {}
            
        # Create the configuration
        config = {
            "series_id": series_id,
            "analysis_type": analysis_type,
            "params": params
        }
        
        # Create a JSON-formatted string (pretty-printed for readability)
        config_json = json.dumps(config, indent=2)
        
        # Generate the command
        command = (
            f"View result from analyze_stored_data from mcp-statcan-datastorage "
            f"{config_json}"
        )
        
        return command