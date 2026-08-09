class StockAIError(Exception):
    """Base exception for the project."""


class InvalidStockCodeError(StockAIError):
    """Raised when a stock code is outside the MVP scope."""


class DataSourceError(StockAIError):
    """Raised when a remote data provider returns an error."""


class MissingDependencyError(StockAIError):
    """Raised when an optional data-source package is not installed."""


class AIAnalysisError(StockAIError):
    """Raised when AI analysis cannot be generated or parsed."""
