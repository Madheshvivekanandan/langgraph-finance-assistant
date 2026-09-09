"""Keyword rules that categorize common merchants without calling a model."""

from app.domain.transaction_category import TransactionCategory

# Ordered most-specific first: the first keyword found in the description wins.
# "AURAGOLD" must precede "AUTOPAY" so a gold-savings mandate is not filed as a
# subscription, and "CASH WDL" must precede "WDL" for the same reason.
_RULES: tuple[tuple[str, TransactionCategory], ...] = (
    # Investments (before AUTOPAY/subscription keywords)
    ("AURAGOLD", TransactionCategory.INVESTMENTS),
    ("MUTUAL FUND", TransactionCategory.INVESTMENTS),
    ("SMALLCASE", TransactionCategory.INVESTMENTS),
    ("ZERODHA", TransactionCategory.INVESTMENTS),
    ("GROWW", TransactionCategory.INVESTMENTS),
    ("UPSTOX", TransactionCategory.INVESTMENTS),
    ("SIP", TransactionCategory.INVESTMENTS),
    ("ELSS", TransactionCategory.INVESTMENTS),
    ("NPS", TransactionCategory.INVESTMENTS),
    ("PPF", TransactionCategory.INVESTMENTS),
    # Groceries
    ("BIGBASKET", TransactionCategory.GROCERIES),
    ("BLINKIT", TransactionCategory.GROCERIES),
    ("ZEPTO", TransactionCategory.GROCERIES),
    ("INSTAMART", TransactionCategory.GROCERIES),
    ("DMART", TransactionCategory.GROCERIES),
    ("D MART", TransactionCategory.GROCERIES),
    ("RELIANCE FRESH", TransactionCategory.GROCERIES),
    ("SPENCER", TransactionCategory.GROCERIES),
    ("GROCERY", TransactionCategory.GROCERIES),
    ("SUPERMARKET", TransactionCategory.GROCERIES),
    # Dining
    ("SWIGGY", TransactionCategory.DINING),
    ("ZOMATO", TransactionCategory.DINING),
    ("DOMINO", TransactionCategory.DINING),
    ("MCDONALD", TransactionCategory.DINING),
    ("STARBUCKS", TransactionCategory.DINING),
    ("CHAI POINT", TransactionCategory.DINING),
    ("BIRYANI", TransactionCategory.DINING),
    ("RESTAURANT", TransactionCategory.DINING),
    ("BAKERY", TransactionCategory.DINING),
    ("CAFE", TransactionCategory.DINING),
    # Transport
    ("UBER", TransactionCategory.TRANSPORT),
    ("OLA ", TransactionCategory.TRANSPORT),
    ("RAPIDO", TransactionCategory.TRANSPORT),
    ("IRCTC", TransactionCategory.TRANSPORT),
    ("REDBUS", TransactionCategory.TRANSPORT),
    ("INDIGO", TransactionCategory.TRANSPORT),
    ("SPICEJET", TransactionCategory.TRANSPORT),
    ("FASTAG", TransactionCategory.TRANSPORT),
    ("PETROL", TransactionCategory.TRANSPORT),
    ("DIESEL", TransactionCategory.TRANSPORT),
    ("FUEL", TransactionCategory.TRANSPORT),
    ("PARKING", TransactionCategory.TRANSPORT),
    ("TOLL", TransactionCategory.TRANSPORT),
    # Housing
    ("RENT", TransactionCategory.HOUSING),
    ("LANDLORD", TransactionCategory.HOUSING),
    ("MAINTENANCE", TransactionCategory.HOUSING),
    # Utilities
    ("ELECTRICITY", TransactionCategory.UTILITIES),
    ("TNEB", TransactionCategory.UTILITIES),
    ("BESCOM", TransactionCategory.UTILITIES),
    ("BROADBAND", TransactionCategory.UTILITIES),
    ("FIBERNET", TransactionCategory.UTILITIES),
    ("INDANE", TransactionCategory.UTILITIES),
    ("BHARATGAS", TransactionCategory.UTILITIES),
    ("WATER BILL", TransactionCategory.UTILITIES),
    ("RECHARGE", TransactionCategory.UTILITIES),
    ("TATA PLAY", TransactionCategory.UTILITIES),
    # Subscriptions
    ("NETFLIX", TransactionCategory.SUBSCRIPTIONS),
    ("SPOTIFY", TransactionCategory.SUBSCRIPTIONS),
    ("HOTSTAR", TransactionCategory.SUBSCRIPTIONS),
    ("PRIME VIDEO", TransactionCategory.SUBSCRIPTIONS),
    ("ADOBE", TransactionCategory.SUBSCRIPTIONS),
    ("ICLOUD", TransactionCategory.SUBSCRIPTIONS),
    ("SUBSCRIPTION", TransactionCategory.SUBSCRIPTIONS),
    # Shopping
    ("AMAZON", TransactionCategory.SHOPPING),
    ("FLIPKART", TransactionCategory.SHOPPING),
    ("MYNTRA", TransactionCategory.SHOPPING),
    ("AJIO", TransactionCategory.SHOPPING),
    ("MEESHO", TransactionCategory.SHOPPING),
    ("NYKAA", TransactionCategory.SHOPPING),
    ("DECATHLON", TransactionCategory.SHOPPING),
    ("CROMA", TransactionCategory.SHOPPING),
    ("LIFESTYLE", TransactionCategory.SHOPPING),
    # Entertainment
    ("BOOKMYSHOW", TransactionCategory.ENTERTAINMENT),
    ("PVR", TransactionCategory.ENTERTAINMENT),
    ("INOX", TransactionCategory.ENTERTAINMENT),
    ("CINEMA", TransactionCategory.ENTERTAINMENT),
    # Health
    ("PHARMEASY", TransactionCategory.HEALTH),
    ("MEDPLUS", TransactionCategory.HEALTH),
    ("APOLLO", TransactionCategory.HEALTH),
    ("PHARMACY", TransactionCategory.HEALTH),
    ("HOSPITAL", TransactionCategory.HEALTH),
    ("DIAGNOSTIC", TransactionCategory.HEALTH),
    ("CLINIC", TransactionCategory.HEALTH),
    ("DENTAL", TransactionCategory.HEALTH),
    # Education
    ("COURSERA", TransactionCategory.EDUCATION),
    ("UDEMY", TransactionCategory.EDUCATION),
    ("TUITION", TransactionCategory.EDUCATION),
    ("COLLEGE", TransactionCategory.EDUCATION),
    ("SCHOOL", TransactionCategory.EDUCATION),
    # Cash
    ("CASH WDL", TransactionCategory.CASH),
    ("ATM", TransactionCategory.CASH),
    ("CASH WITHDRAWAL", TransactionCategory.CASH),
    # Fees
    ("SMS CHARGES", TransactionCategory.FEES),
    ("AMB CHARGES", TransactionCategory.FEES),
    ("ANNUAL FEE", TransactionCategory.FEES),
    ("PENALTY", TransactionCategory.FEES),
    ("GST", TransactionCategory.FEES),
    # Income
    ("SALARY", TransactionCategory.INCOME),
    ("INTEREST", TransactionCategory.INCOME),
    ("DIVIDEND", TransactionCategory.INCOME),
    ("CASHBACK", TransactionCategory.INCOME),
    ("REFUND", TransactionCategory.INCOME),
    # Transfers (last: these keywords appear inside more specific descriptions)
    ("NEFT", TransactionCategory.TRANSFERS),
    ("IMPS", TransactionCategory.TRANSFERS),
    ("RTGS", TransactionCategory.TRANSFERS),
)


class CategoryRules:
    """Matches a transaction description against known merchant keywords.

    Deterministic, free, and instant - so it runs before any model is asked.
    Whatever it cannot place is what the LLM node is given.
    """

    @staticmethod
    def match(description: str) -> TransactionCategory | None:
        """Return the category for this description, or None if no rule applies.

        Args:
            description: The transaction narration, in any case.
        """
        haystack = description.upper()
        for keyword, category in _RULES:
            if keyword in haystack:
                return category
        return None

    @staticmethod
    def rule_count() -> int:
        """How many keyword rules are configured; used in tests and logs."""
        return len(_RULES)
