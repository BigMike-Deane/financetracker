"""
Transaction Auto-Categorization Engine

Categorizes transactions based on:
1. Provider category information (SimpleFIN, etc.)
2. Merchant name pattern matching
3. User-defined rules (learned from manual categorizations)
"""

import re
from typing import Optional
from database import TransactionCategory

# Mapping from provider categories to our categories
CATEGORY_MAP = {
    # Income
    "INCOME_DIVIDENDS": TransactionCategory.INCOME_INVESTMENT,
    "INCOME_INTEREST_EARNED": TransactionCategory.INCOME_INVESTMENT,
    "INCOME_WAGES": TransactionCategory.INCOME_SALARY,
    "INCOME_OTHER_INCOME": TransactionCategory.INCOME_OTHER,
    "TRANSFER_IN_DEPOSIT": TransactionCategory.INCOME_TRANSFER,

    # Food & Dining
    "FOOD_AND_DRINK_GROCERIES": TransactionCategory.FOOD_GROCERIES,
    "FOOD_AND_DRINK_RESTAURANT": TransactionCategory.FOOD_RESTAURANTS,
    "FOOD_AND_DRINK_COFFEE": TransactionCategory.FOOD_COFFEE,
    "FOOD_AND_DRINK_FAST_FOOD": TransactionCategory.FOOD_RESTAURANTS,
    "FOOD_AND_DRINK_DELIVERY": TransactionCategory.FOOD_RESTAURANTS,

    # Transportation
    "TRANSPORTATION_GAS": TransactionCategory.TRANSPORT_GAS,
    "TRANSPORTATION_PARKING": TransactionCategory.TRANSPORT_PARKING,
    "TRANSPORTATION_PUBLIC_TRANSIT": TransactionCategory.TRANSPORT_PUBLIC,
    "TRANSPORTATION_TAXIS_AND_RIDE_SHARES": TransactionCategory.TRANSPORT_RIDESHARE,
    "TRANSPORTATION_CAR_SERVICE": TransactionCategory.TRANSPORT_MAINTENANCE,

    # Shopping
    "SHOPS_CLOTHING_AND_ACCESSORIES": TransactionCategory.SHOPPING_CLOTHING,
    "SHOPS_ELECTRONICS": TransactionCategory.SHOPPING_ELECTRONICS,
    "SHOPS_SUPERMARKETS_AND_GROCERIES": TransactionCategory.FOOD_GROCERIES,
    "SHOPS_GENERAL_MERCHANDISE": TransactionCategory.SHOPPING_GENERAL,
    "SHOPS_HOUSEHOLD": TransactionCategory.SHOPPING_HOUSEHOLD,

    # Entertainment
    "ENTERTAINMENT_MUSIC_AND_AUDIO": TransactionCategory.ENTERTAINMENT_STREAMING,
    "ENTERTAINMENT_MOVIES_AND_DVDS": TransactionCategory.ENTERTAINMENT_STREAMING,
    "ENTERTAINMENT_TV_AND_MOVIES": TransactionCategory.ENTERTAINMENT_STREAMING,
    "ENTERTAINMENT_GAMES": TransactionCategory.ENTERTAINMENT_GAMES,
    "ENTERTAINMENT_SPORTING_EVENTS": TransactionCategory.ENTERTAINMENT_EVENTS,

    # Health
    "HEALTHCARE_MEDICAL_SERVICES": TransactionCategory.HEALTH_MEDICAL,
    "HEALTHCARE_PHARMACIES_AND_SUPPLEMENTS": TransactionCategory.HEALTH_PHARMACY,
    "HEALTHCARE_MEDICAL_EQUIPMENT": TransactionCategory.HEALTH_MEDICAL,
    "PERSONAL_CARE_GYMS_AND_FITNESS_CENTERS": TransactionCategory.HEALTH_FITNESS,

    # Housing
    "RENT_AND_UTILITIES_RENT": TransactionCategory.HOUSING_RENT,
    "RENT_AND_UTILITIES_GAS_AND_ELECTRICITY": TransactionCategory.HOUSING_UTILITIES,
    "RENT_AND_UTILITIES_WATER": TransactionCategory.HOUSING_UTILITIES,
    "RENT_AND_UTILITIES_INTERNET_AND_CABLE": TransactionCategory.HOUSING_UTILITIES,
    "RENT_AND_UTILITIES_TELEPHONE": TransactionCategory.HOUSING_UTILITIES,
    "HOME_IMPROVEMENT_REPAIR_AND_MAINTENANCE": TransactionCategory.HOUSING_MAINTENANCE,

    # Financial
    "BANK_FEES_ATM_FEES": TransactionCategory.FINANCIAL_FEES,
    "BANK_FEES_OVERDRAFT": TransactionCategory.FINANCIAL_FEES,
    "BANK_FEES_FOREIGN_TRANSACTION": TransactionCategory.FINANCIAL_FEES,
    "BANK_FEES_INTEREST_CHARGE": TransactionCategory.FINANCIAL_INTEREST,
    "TRANSFER_OUT_INVESTMENT": TransactionCategory.FINANCIAL_INVESTMENT,
    "TRANSFER_INTERNAL_ACCOUNT_TRANSFER": TransactionCategory.FINANCIAL_TRANSFER,

    # Travel
    "TRAVEL_FLIGHTS": TransactionCategory.TRAVEL,
    "TRAVEL_LODGING": TransactionCategory.TRAVEL,
    "TRAVEL_CAR_RENTAL": TransactionCategory.TRAVEL,

    # Other
    "GOVERNMENT_AND_NON_PROFIT_TAX_PAYMENT": TransactionCategory.TAXES,
    "GOVERNMENT_AND_NON_PROFIT_DONATIONS": TransactionCategory.CHARITY,
    "GENERAL_MERCHANDISE_GIFT_SHOPS": TransactionCategory.GIFTS,
    "LOAN_PAYMENTS_CAR_PAYMENT": TransactionCategory.FINANCIAL_TRANSFER,
    "LOAN_PAYMENTS_MORTGAGE_PAYMENT": TransactionCategory.HOUSING_MORTGAGE,
}

# Teller uses simpler category strings
TELLER_CATEGORY_MAP = {
    # Transportation
    "accommodation": TransactionCategory.TRAVEL,
    "advertising": TransactionCategory.UNCATEGORIZED,
    "bar": TransactionCategory.FOOD_RESTAURANTS,
    "charity": TransactionCategory.CHARITY,
    "clothing": TransactionCategory.SHOPPING_CLOTHING,
    "dining": TransactionCategory.FOOD_RESTAURANTS,
    "education": TransactionCategory.EDUCATION,
    "electronics": TransactionCategory.SHOPPING_ELECTRONICS,
    "entertainment": TransactionCategory.ENTERTAINMENT_OTHER,
    "fuel": TransactionCategory.TRANSPORT_GAS,
    # "general" removed - let it fall through to merchant pattern matching
    "groceries": TransactionCategory.FOOD_GROCERIES,
    "health": TransactionCategory.HEALTH_MEDICAL,
    "home": TransactionCategory.HOUSING_MAINTENANCE,
    "income": TransactionCategory.INCOME_OTHER,
    "insurance": TransactionCategory.INSURANCE,
    "investment": TransactionCategory.FINANCIAL_INVESTMENT,
    "loan": TransactionCategory.FINANCIAL_TRANSFER,
    "office": TransactionCategory.SHOPPING_GENERAL,
    "phone": TransactionCategory.HOUSING_UTILITIES,
    # "service" removed - let it fall through to merchant pattern matching
    "shopping": TransactionCategory.SHOPPING_GENERAL,
    "software": TransactionCategory.SUBSCRIPTION_MEMBERSHIP,
    "sport": TransactionCategory.HEALTH_FITNESS,
    "tax": TransactionCategory.TAXES,
    "transport": TransactionCategory.TRANSPORT_PUBLIC,
    "transportation": TransactionCategory.TRANSPORT_PUBLIC,
    "travel": TransactionCategory.TRAVEL,
    "utilities": TransactionCategory.HOUSING_UTILITIES,
    "gas": TransactionCategory.TRANSPORT_GAS,  # Teller sometimes sends this
}

# Merchant name patterns for categorization
MERCHANT_PATTERNS = {
    # Groceries
    TransactionCategory.FOOD_GROCERIES: [
        r"walmart", r"target", r"kroger", r"safeway", r"whole foods",
        r"trader joe", r"aldi", r"costco", r"sam's club", r"publix",
        r"h-e-b", r"heb ", r"albertsons", r"wegmans", r"sprouts", r"grocery",
        r"randalls", r"fiesta mart", r"food lion", r"giant", r"stop.?shop",
        r"shipt", r"fresh market", r"market basket", r"instacart"
    ],

    # Restaurants (includes food delivery)
    TransactionCategory.FOOD_RESTAURANTS: [
        r"mcdonald", r"burger king", r"wendy", r"taco bell", r"chipotle",
        r"panera", r"subway", r"chick-fil-a", r"starbucks", r"dunkin",
        r"pizza hut", r"domino", r"papa john", r"kfc", r"popeye",
        r"olive garden", r"applebee", r"chili's", r"outback", r"red lobster",
        r"restaurant", r"grill", r"cafe", r"diner", r"bistro",
        r"tst\*", r"sq \*", r"stadium.?conc", r"concession",
        r"buffalo wild", r"wingstop", r"five guys", r"shake shack",
        r"panda express", r"sonic ", r"whataburger", r"in-n-out",
        r"cava", r"sweetgreen", r"cane's", r"zaxby", r"wawa food",
        r"the burnt", r"bar ", r" bar$", r"tavern", r"pub ", r"brewery",
        r"longhorn", r"texas roadhouse", r"cracker barrel", r"ihop", r"denny",
        r"waffle house", r"huddle house", r"golden corral", r"luby",
        r"pizza", r"pizzeria", r"taqueria", r"tacos", r"burrito",
        r"sushi", r"ramen", r"pho ", r"thai ", r"chinese",
        r"mias ", r"franks", r"joe's", r"tony's", r"luigi",
        r"7-eleven", r"7 eleven", r"circle k", r"quiktrip", r"qt ",
        r"stripes", r"buc-ee", r"loves travel", r"pilot flying",
        # Food delivery services
        r"doordash", r"dd \*doordash", r"dd\*doordash", r"dd \*",
        r"uber eats", r"ubereats", r"grubhub", r"postmates",
        r"seamless", r"gopuff", r"caviar", r"favor"
    ],

    # Coffee
    TransactionCategory.FOOD_COFFEE: [
        r"starbucks", r"dunkin", r"peet's coffee", r"coffee bean",
        r"dutch bros", r"caribou coffee", r"tim horton"
    ],

    # Gas
    TransactionCategory.TRANSPORT_GAS: [
        r"shell", r"chevron", r"exxon", r"\bmobil\b", r"bp ", r"texaco",
        r"76 ", r"arco", r"speedway", r"wawa", r"sheetz", r"racetrac",
        r"gas station", r"fuel", r"petroleum"
    ],

    # Rideshare
    TransactionCategory.TRANSPORT_RIDESHARE: [
        r"uber", r"lyft", r"via "
    ],


    # Games
    TransactionCategory.ENTERTAINMENT_GAMES: [
        r"steam", r"blizzard", r"battle\.net", r"xbox", r"playstation",
        r"nintendo", r"epic games", r"riot games", r"farlight", r"jagex",
        r"runescape", r"roblox", r"mojang", r"minecraft", r"ea\.com",
        r"ubisoft", r"activision", r"bungie"
    ],

    # Subscriptions (software, memberships, streaming, etc.)
    TransactionCategory.SUBSCRIPTION_MEMBERSHIP: [
        r"adobe", r"microsoft", r"google storage", r"icloud", r"dropbox",
        r"notion", r"slack", r"zoom", r"github", r"aws ", r"heroku",
        r"digital ocean", r"openai", r"anthropic", r"linkedin",
        r"chatgpt", r"google one", r"google play", r"claude\.ai",
        r"membership fee", r"annual fee", r"monthly fee",
        r"amazon prime", r"costco member", r"sam's club member",
        # Streaming services
        r"netflix", r"hulu", r"disney\+", r"disney plus", r"hbo max",
        r"spotify", r"apple music", r"youtube", r"youtu\.be",
        r"paramount\+", r"peacock", r"apple tv", r"audible", r"pandora",
        r"tidal", r"deezer", r"crunchyroll", r"max\.com", r"twitch"
    ],

    # Fitness
    TransactionCategory.HEALTH_FITNESS: [
        r"planet fitness", r"la fitness", r"gold's gym", r"24 hour fitness",
        r"anytime fitness", r"equinox", r"crossfit", r"orangetheory",
        r"peloton", r"classpass", r"ymca", r"gym"
    ],

    # Utilities
    TransactionCategory.HOUSING_UTILITIES: [
        r"electric", r"gas company", r"water bill", r"at&t", r"verizon",
        r"t-mobile", r"comcast", r"xfinity", r"spectrum", r"cox ",
        r"internet", r"utility", r"fiber", r"broadband", r"centerpoint",
        r"reliant", r"txu ", r"direct energy", r"green mountain",
        r"champion energy", r"energy servic"
    ],

    # Amazon and general shopping
    TransactionCategory.SHOPPING_GENERAL: [
        r"amazon", r"amzn", r"amazon marketplace", r"amazon retail",
        r"usps", r"ups store", r"fedex", r"postal", r"us postal",
        r"etsy", r"ebay", r"wish\.com", r"shein", r"temu", r"tiktok shop",
        r"williams.?sonoma", r"pottery barn", r"crate.?barrel",
        r"bed bath", r"wayfair", r"overstock", r"ikea",
        r"dollar tree", r"dollar general", r"five below",
        r"academy", r"dicks sporting", r"rei ", r"bass pro",
        r"bookstore", r"kinokuniya", r"barnes.*noble", r"half price books",
        r"chatbooks", r"sberries",
        r"office depot", r"office max", r"staples",
        r"hobby lobby", r"michaels", r"joann", r"craft",
        r"dsw", r"shoe", r"payless",
        r"dry clean", r"cleaners", r"laundry", r"tailor", r"alterations",
        r"minted", r"the knot", r"zola", r"shutterfly", r"snapfish",
        r"blueland", r"grove collaborative", r"method home",
        r"teachers pay", r"teacherspay", r"tpt ", r"education",
        r"vending", r"payrange", r"canteen"
    ],

    # Electronics
    TransactionCategory.SHOPPING_ELECTRONICS: [
        r"best buy", r"apple store", r"apple\.com", r"b&h photo",
        r"micro center", r"newegg"
    ],

    # Clothing
    TransactionCategory.SHOPPING_CLOTHING: [
        r"nordstrom", r"macy's", r"gap ", r"old navy", r"h&m",
        r"zara", r"uniqlo", r"nike", r"adidas", r"lululemon",
        r"tj maxx", r"ross ", r"marshalls",
        r"men's wearhouse", r"mens wearhouse", r"jos\.? a\.? bank",
        r"altar.?d state", r"anthropologie", r"free people", r"urban outfitters",
        r"banana republic", r"express ", r"forever ?21", r"aeropostale",
        r"american eagle", r"abercrombie", r"hollister", r"patagonia",
        r"aveda", r"sephora", r"ulta"
    ],

    # Pharmacy
    TransactionCategory.HEALTH_PHARMACY: [
        r"cvs", r"walgreens", r"rite aid", r"pharmacy"
    ],

    # Medical (doctors, dentists, hospitals, clinics)
    TransactionCategory.HEALTH_MEDICAL: [
        r"dental", r"dentist", r"orthodont", r"doctor", r"dr\.",
        r"medical", r"hospital", r"clinic", r"urgent care",
        r"physician", r"healthcare", r"health center",
        r"optometr", r"eye care", r"vision center",
        r"dermatolog", r"pediatr", r"obgyn", r"cardio",
        r"therapy", r"therapist", r"chiropr", r"physical therapy",
        r"labcorp", r"quest diag", r"radiology", r"imaging",
        r"memorial hermann", r"med\*", r"methodist", r"baptist",
        r"st\.? luke", r"md anderson", r"kaiser", r"cigna",
        r"aetna", r"united health", r"bluecross", r"humana"
    ],

    # Insurance
    TransactionCategory.INSURANCE: [
        r"geico", r"state farm", r"allstate", r"progressive",
        r"liberty mutual", r"usaa", r"insurance"
    ],

    # Transfers/Payments (only actual transfers, not purchases via payment services)
    TransactionCategory.FINANCIAL_TRANSFER: [
        r"^venmo\s", r"zelle", r"cash app", r"transfer",
        r"wire ", r"credit crd.*epay", r"mobile pmt",
        r"payment from", r"payment to", r"online banking",
        r"onetimepayment", r"one time payment", r"card payment",
        r"online deposit", r"remote.*deposit", r"statement credit",
        # Credit card payments
        r"capital one.*pymt", r"capital one.*payment", r"capital one.*mobile",
        r"capital one\s+des:mobile", r"capital one\s+des:.*pmt",
        r"chase.*payment", r"chase credit crd", r"chase credit card",
        r"payment thank you", r"autopay payment", r"automatic payment",
        r"epayment", r"online payment", r"web payment",
        r"citi.*payment", r"amex.*payment", r"discover.*payment",
        r"bank of america.*payment", r"wells fargo.*payment",
        r"credit card payment", r"cc payment",
        # Store card payments
        r"amazon corp.*syf paymnt", r"amazon.*syf.*paym", r"synchrony",
        r"des:epay", r"des:.*paymnt", r"des:.*payment"
    ],

    # Financial/Investment Services
    TransactionCategory.FINANCIAL_INVESTMENT: [
        r"pershing", r"fidelity", r"schwab", r"vanguard", r"td ameritrade",
        r"e\*trade", r"robinhood", r"wealthfront", r"betterment"
    ],

    # Home Improvement
    TransactionCategory.HOUSING_MAINTENANCE: [
        r"lowes", r"home depot", r"menards", r"ace hardware",
        r"true value", r"sherwin.?williams", r"benjamin moore",
        r"harbor freight", r"northern tool"
    ],

    # Travel (flights, hotels, car rental, tolls, travel insurance)
    TransactionCategory.TRAVEL: [
        r"united air", r"american air", r"delta air", r"southwest",
        r"jetblue", r"spirit air", r"frontier air", r"alaska air",
        r"marriott", r"hilton", r"hyatt", r"holiday inn", r"best western",
        r"hampton inn", r"homewood suites", r"embassy suites", r"sheraton",
        r"airbnb", r"vrbo", r"booking\.com", r"expedia", r"hotels\.com",
        r"hertz", r"enterprise", r"avis", r"budget rent", r"national car",
        r"toll", r"tollway", r"toll road", r"ezpass", r"pikepass",
        r"harris county toll", r"txtag", r"sunpass",
        r"travel guard", r"travel insurance", r"allianz travel", r"travelex"
    ],

    # Parking
    TransactionCategory.TRANSPORT_PARKING: [
        r"parking", r"propark", r"spothero", r"parkwhiz", r"parkme",
        r"lazpark", r"ace parking", r"icon parking", r"sp\+ parking"
    ],

    # Charity/Religious
    TransactionCategory.CHARITY: [
        r"church", r"catholic", r"baptist", r"methodist", r"lutheran",
        r"episcopal", r"presbyterian", r"temple", r"synagogue", r"mosque",
        r"epiphany", r"parish", r"diocese", r"salvation army", r"red cross",
        r"united way", r"goodwill", r"habitat for human", r"unicef",
        r"world vision", r"st\.? jude", r"make.?a.?wish", r"charity",
        r"donate", r"donation", r"tithe", r"focus"
    ],

    # Pet (supplies, stores, vet)
    TransactionCategory.PET: [
        r"pet.*smart", r"petco", r"chewy", r"hollywood feed", r"blue buffalo",
        r"pet supplies", r"pet store", r"petsense", r"pet valu",
        r"animal clini", r"veterinar", r"vet ", r"pet hospital"
    ],

}


def extract_paypal_merchant(name: str) -> Optional[str]:
    """Extract merchant name from PayPal transactions like 'PAYPAL *CHEWY' or 'PP*GOOGLE'"""
    if not name:
        return None
    name_upper = name.upper()
    # Match patterns like "PAYPAL *MERCHANT" or "PP*MERCHANT"
    if name_upper.startswith("PAYPAL *") or name_upper.startswith("PAYPAL*"):
        return name[8:].strip()
    if name_upper.startswith("PP*") or name_upper.startswith("PP *"):
        return name[3:].strip() if name_upper.startswith("PP*") else name[4:].strip()
    return None


def is_investment_transaction(name: str) -> bool:
    """
    Detect brokerage/investment account transactions.
    These should be categorized as investment activity, not matched against merchants.
    """
    if not name:
        return False
    name_upper = name.upper()

    investment_patterns = [
        # Stock/ETF trades
        "YOU BOUGHT", "YOU SOLD",
        # Mutual fund transactions
        "REDEMPTION FROM", "PURCHASE INTO",
        # Dividends and distributions
        "DIVIDEND", "DISTRIBUTION", "REINVESTMENT",
        # Options
        "ASSIGNED", "EXERCISED", "EXPIRED",
        "CALL (", "PUT (", "CALL)", "PUT)",
        # Internal brokerage movements
        "JOURNALED", "JNL VS A/C",
        # Core/sweep account
        "CORE ACCOUNT", "MONEY MARKET", "SPAXX", "FDRXX", "VMFXX",
        # Contributions
        "CONTRIBUTION", "ROLLOVER",
        # Interest on brokerage cash
        "INTEREST ON CASH",
        # Fee patterns
        "MARGIN INTEREST", "ADVISORY FEE",
        # Transfer patterns specific to brokerages
        "ELECTRONIC FUNDS TRANSFER", "EFT FROM", "EFT TO",
        # Common brokerage identifiers in transaction names
        "(MARGIN)", "(CASH)", "(SHS)",
    ]

    return any(pattern in name_upper for pattern in investment_patterns)


def categorize_transaction(
    name: str,
    merchant_name: Optional[str],
    original_category: Optional[list],
    original_category_id: Optional[str],
    amount: float,
    user_rules=None
) -> TransactionCategory:
    """
    Categorize a transaction using multiple signals.

    Priority:
    1. User-defined rules (highest priority)
    2. Investment transaction detection (brokerage activity)
    3. Provider category mapping (if available)
    4. Merchant name pattern matching
    5. Transaction name pattern matching
    6. Default to UNCATEGORIZED
    """

    # FIRST: Check user-defined rules (highest priority)
    user_category = apply_user_rules(name, merchant_name, user_rules)
    if user_category:
        return user_category

    # Check for investment/brokerage transactions
    # This must come before merchant matching to avoid false positives
    # (e.g., "YOU BOUGHT CAVA GROUP INC" should not match "cava" restaurant)
    if is_investment_transaction(name):
        return TransactionCategory.FINANCIAL_INVESTMENT

    # Check if this is income (positive amount = income)
    if amount > 0:
        # Check for common income patterns
        name_lower = (name or "").lower()
        if any(word in name_lower for word in ["payroll", "direct dep", "salary", "wage", "payrollcorp", "calpine", "employee", "deposit check"]):
            return TransactionCategory.INCOME_SALARY
        if any(word in name_lower for word in ["dividend", "interest"]):
            return TransactionCategory.INCOME_INVESTMENT
        # Zelle payments FROM others are income (must check before generic transfer check)
        if "zelle" in name_lower and "payment from" in name_lower:
            return TransactionCategory.INCOME_OTHER
        if any(word in name_lower for word in ["transfer", "xfer"]):
            return TransactionCategory.INCOME_TRANSFER
        # Mobile check deposits (e.g., "BKOFAMERICA MOBILE ... DEPOSIT")
        if "mobile" in name_lower and "deposit" in name_lower:
            return TransactionCategory.INCOME_OTHER
        # Remote/online deposits (e.g., "REMOTE ONLINE DEPOSIT # 1")
        if "deposit" in name_lower and ("remote" in name_lower or "online" in name_lower):
            return TransactionCategory.INCOME_OTHER

    # Try provider category first
    if original_category_id:
        category_key = original_category_id.upper()
        if category_key in CATEGORY_MAP:
            return CATEGORY_MAP[category_key]

    # Try building category from category list
    if original_category and len(original_category) >= 2:
        category_key = "_".join(original_category[:2]).upper().replace(" ", "_")
        if category_key in CATEGORY_MAP:
            return CATEGORY_MAP[category_key]

    # Try Teller simple category (single string like "gas", "dining", etc.)
    if original_category and len(original_category) == 1:
        teller_cat = original_category[0].lower() if original_category[0] else None
        if teller_cat and teller_cat in TELLER_CATEGORY_MAP:
            return TELLER_CATEGORY_MAP[teller_cat]

    # Extract PayPal merchant if applicable
    paypal_merchant = extract_paypal_merchant(name)

    # Try merchant name patterns (include PayPal merchant in search)
    search_text = f"{merchant_name or ''} {name or ''} {paypal_merchant or ''}".lower()

    for category, patterns in MERCHANT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, search_text, re.IGNORECASE):
                return category

    return TransactionCategory.UNCATEGORIZED


def get_category_display_name(category: TransactionCategory) -> str:
    """Get human-readable category name"""
    display_names = {
        TransactionCategory.INCOME_SALARY: "Salary",
        TransactionCategory.INCOME_INVESTMENT: "Investment Income",
        TransactionCategory.INCOME_TRANSFER: "Transfer In",
        TransactionCategory.INCOME_OTHER: "Other Income",

        TransactionCategory.HOUSING_RENT: "Rent",
        TransactionCategory.HOUSING_MORTGAGE: "Mortgage",
        TransactionCategory.HOUSING_UTILITIES: "Utilities",
        TransactionCategory.HOUSING_MAINTENANCE: "Home Maintenance",

        TransactionCategory.TRANSPORT_GAS: "Gas",
        TransactionCategory.TRANSPORT_PARKING: "Parking",
        TransactionCategory.TRANSPORT_PUBLIC: "Public Transit",
        TransactionCategory.TRANSPORT_RIDESHARE: "Rideshare",
        TransactionCategory.TRANSPORT_MAINTENANCE: "Car Maintenance",

        TransactionCategory.FOOD_GROCERIES: "Groceries",
        TransactionCategory.FOOD_RESTAURANTS: "Restaurants",
        TransactionCategory.FOOD_COFFEE: "Coffee",

        TransactionCategory.SHOPPING_CLOTHING: "Clothing",
        TransactionCategory.SHOPPING_ELECTRONICS: "Electronics",
        TransactionCategory.SHOPPING_HOUSEHOLD: "Household",
        TransactionCategory.SHOPPING_GENERAL: "Shopping",

        TransactionCategory.ENTERTAINMENT_STREAMING: "Streaming",
        TransactionCategory.ENTERTAINMENT_GAMES: "Games",
        TransactionCategory.ENTERTAINMENT_EVENTS: "Events",
        TransactionCategory.ENTERTAINMENT_OTHER: "Entertainment",

        TransactionCategory.HEALTH_MEDICAL: "Medical",
        TransactionCategory.HEALTH_PHARMACY: "Pharmacy",
        TransactionCategory.HEALTH_FITNESS: "Fitness",
        TransactionCategory.HEALTH_INSURANCE: "Health Insurance",

        TransactionCategory.FINANCIAL_FEES: "Bank Fees",
        TransactionCategory.FINANCIAL_INTEREST: "Interest",
        TransactionCategory.FINANCIAL_INVESTMENT: "Investments",
        TransactionCategory.FINANCIAL_TRANSFER: "Transfers",

        TransactionCategory.SUBSCRIPTION_SOFTWARE: "Subscriptions",
        TransactionCategory.SUBSCRIPTION_MEMBERSHIP: "Subscriptions",
        TransactionCategory.SUBSCRIPTION_OTHER: "Subscriptions",

        TransactionCategory.TRAVEL: "Travel",
        TransactionCategory.EDUCATION: "Education",
        TransactionCategory.GIFTS: "Gifts",
        TransactionCategory.CHARITY: "Charity",
        TransactionCategory.TAXES: "Taxes",
        TransactionCategory.INSURANCE: "Insurance",
        TransactionCategory.PET: "Pet",
        TransactionCategory.UNCATEGORIZED: "Uncategorized",
    }
    return display_names.get(category, category.value)


def get_category_emoji(category: TransactionCategory) -> str:
    """Get emoji for category"""
    emojis = {
        TransactionCategory.INCOME_SALARY: "💰",
        TransactionCategory.INCOME_INVESTMENT: "📈",
        TransactionCategory.INCOME_TRANSFER: "↩️",
        TransactionCategory.INCOME_OTHER: "💵",

        TransactionCategory.HOUSING_RENT: "🏠",
        TransactionCategory.HOUSING_MORTGAGE: "🏡",
        TransactionCategory.HOUSING_UTILITIES: "⚡",
        TransactionCategory.HOUSING_MAINTENANCE: "🔧",

        TransactionCategory.TRANSPORT_GAS: "⛽",
        TransactionCategory.TRANSPORT_PARKING: "🅿️",
        TransactionCategory.TRANSPORT_PUBLIC: "🚇",
        TransactionCategory.TRANSPORT_RIDESHARE: "🚗",
        TransactionCategory.TRANSPORT_MAINTENANCE: "🔧",

        TransactionCategory.FOOD_GROCERIES: "🛒",
        TransactionCategory.FOOD_RESTAURANTS: "🍽️",
        TransactionCategory.FOOD_COFFEE: "☕",

        TransactionCategory.SHOPPING_CLOTHING: "👕",
        TransactionCategory.SHOPPING_ELECTRONICS: "📱",
        TransactionCategory.SHOPPING_HOUSEHOLD: "🏠",
        TransactionCategory.SHOPPING_GENERAL: "🛍️",

        TransactionCategory.ENTERTAINMENT_STREAMING: "📺",
        TransactionCategory.ENTERTAINMENT_GAMES: "🎮",
        TransactionCategory.ENTERTAINMENT_EVENTS: "🎫",
        TransactionCategory.ENTERTAINMENT_OTHER: "🎭",

        TransactionCategory.HEALTH_MEDICAL: "🏥",
        TransactionCategory.HEALTH_PHARMACY: "💊",
        TransactionCategory.HEALTH_FITNESS: "🏋️",
        TransactionCategory.HEALTH_INSURANCE: "🏥",

        TransactionCategory.FINANCIAL_FEES: "💳",
        TransactionCategory.FINANCIAL_INTEREST: "📊",
        TransactionCategory.FINANCIAL_INVESTMENT: "📈",
        TransactionCategory.FINANCIAL_TRANSFER: "↔️",

        TransactionCategory.SUBSCRIPTION_SOFTWARE: "🔄",
        TransactionCategory.SUBSCRIPTION_MEMBERSHIP: "🔄",
        TransactionCategory.SUBSCRIPTION_OTHER: "🔄",

        TransactionCategory.TRAVEL: "✈️",
        TransactionCategory.EDUCATION: "📚",
        TransactionCategory.GIFTS: "🎁",
        TransactionCategory.CHARITY: "❤️",
        TransactionCategory.TAXES: "🏛️",
        TransactionCategory.INSURANCE: "🛡️",
        TransactionCategory.PET: "🐾",
        TransactionCategory.UNCATEGORIZED: "❓",
    }
    return emojis.get(category, "❓")


def get_parent_category(category: TransactionCategory) -> str:
    """Get parent category for grouping"""
    category_value = category.value

    if category_value.startswith("income_"):
        return "Income"
    elif category_value.startswith("housing_"):
        return "Housing"
    elif category_value.startswith("transport_"):
        return "Transportation"
    elif category_value.startswith("food_"):
        return "Food & Dining"
    elif category_value.startswith("shopping_"):
        return "Shopping"
    elif category_value.startswith("entertainment_"):
        return "Entertainment"
    elif category_value.startswith("health_"):
        return "Health"
    elif category_value.startswith("financial_"):
        return "Financial"
    elif category_value.startswith("subscription_"):
        return "Subscriptions"
    else:
        return "Other"


# ============== User-Defined Rules Engine ==============

def apply_single_rule_params(
    match_field: str,
    match_type: str,
    match_value: str,
    case_sensitive: bool,
    txn_name: str,
    txn_merchant: Optional[str]
) -> bool:
    """
    Check if a transaction matches a rule's pattern.
    Used for testing rules before saving.
    """
    # Determine which text to match against
    if match_field == 'name':
        texts = [txn_name or '']
    elif match_field == 'merchant_name':
        texts = [txn_merchant or '']
    else:  # 'any'
        texts = [txn_name or '', txn_merchant or '']

    # Prepare for case sensitivity
    if not case_sensitive:
        match_value = match_value.lower()
        texts = [t.lower() for t in texts]

    # Check each text against the pattern
    for text in texts:
        if match_type == 'contains':
            if match_value in text:
                return True
        elif match_type == 'starts_with':
            if text.startswith(match_value):
                return True
        elif match_type == 'ends_with':
            if text.endswith(match_value):
                return True
        elif match_type == 'exact':
            if text == match_value:
                return True

    return False


def apply_single_rule(rule, txn_name: str, txn_merchant: Optional[str]) -> bool:
    """
    Check if a transaction matches a rule object.
    Used when applying rules to transactions.
    """
    return apply_single_rule_params(
        rule.match_field,
        rule.match_type,
        rule.match_value,
        rule.case_sensitive,
        txn_name,
        txn_merchant
    )


def get_user_rules():
    """
    Load active user rules from database.
    Cached for performance during batch categorization.
    """
    from database import SessionLocal, TransactionRule

    db = SessionLocal()
    try:
        rules = db.query(TransactionRule).filter(
            TransactionRule.is_active == True
        ).order_by(TransactionRule.priority.desc()).all()
        return rules
    finally:
        db.close()


def apply_user_rules(name: str, merchant_name: Optional[str], rules=None) -> Optional[TransactionCategory]:
    """
    Apply user-defined rules to categorize a transaction.
    Returns the category if a rule matches, None otherwise.
    """
    if rules is None:
        rules = get_user_rules()

    for rule in rules:
        if apply_single_rule(rule, name, merchant_name):
            return rule.assign_category

    return None
