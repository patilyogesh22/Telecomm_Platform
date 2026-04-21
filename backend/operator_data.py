"""
operator_data.py
Complete Indian telecom operator plans database.
Used by: payment routes, plan detection, AI tutor context.
"""

# ── Operator detection by mobile number prefix ─────────────────
OPERATOR_PREFIXES = {
    # Jio
    "6": "Jio", "7": "Jio",  # broad fallback — refined below
    # Specific prefix ranges
    "70": "Jio",  "71": "Jio",  "72": "Jio",  "73": "Jio",  "74": "Jio",
    "75": "Jio",  "76": "Jio",  "77": "Jio",  "78": "Jio",  "79": "Jio",
    "62": "Jio",  "63": "Jio",  "64": "Jio",  "65": "Jio",
    # Airtel
    "98": "Airtel","99": "Airtel","97": "Airtel","96": "Airtel",
    "80": "Airtel","81": "Airtel","82": "Airtel","83": "Airtel","84": "Airtel",
    "85": "Airtel","86": "Airtel","87": "Airtel","88": "Airtel","89": "Airtel",
    # Vi (Vodafone-Idea)
    "94": "Vi",   "95": "Vi",   "93": "Vi",   "92": "Vi",
    "90": "Vi",   "91": "Vi",
    # BSNL
    "94": "BSNL",  # overlap — simplified
    "99": "BSNL",
}

# Refined 4-digit prefix lookup (more accurate)
OPERATOR_4DIG = {
    # Jio
    "6000":"Jio","6001":"Jio","6002":"Jio","6003":"Jio","6004":"Jio","6005":"Jio",
    "7000":"Jio","7001":"Jio","7002":"Jio","7003":"Jio","7004":"Jio","7005":"Jio",
    "7006":"Jio","7007":"Jio","7008":"Jio","7009":"Jio","7010":"Jio","7011":"Jio",
    "7012":"Jio","7013":"Jio","7014":"Jio","7015":"Jio","7016":"Jio","7017":"Jio",
    "7018":"Jio","7019":"Jio","7020":"Jio","7021":"Jio","7022":"Jio","7023":"Jio",
    "7024":"Jio","7025":"Jio","7026":"Jio","7027":"Jio","7028":"Jio","7029":"Jio",
    "7030":"Jio","7031":"Jio","7032":"Jio","7033":"Jio","7034":"Jio","7035":"Jio",
    # Airtel
    "9800":"Airtel","9801":"Airtel","9810":"Airtel","9811":"Airtel","9818":"Airtel",
    "9899":"Airtel","9871":"Airtel","9958":"Airtel","9999":"Airtel","9911":"Airtel",
    "8800":"Airtel","8801":"Airtel","8802":"Airtel","8803":"Airtel","8810":"Airtel",
    "8826":"Airtel","8860":"Airtel","8447":"Airtel","9717":"Airtel","9716":"Airtel",
    # Vi
    "9212":"Vi","9213":"Vi","9214":"Vi","9215":"Vi","9811":"Vi","9312":"Vi",
    "9810":"Vi","9319":"Vi","9810":"Vi","9899":"Vi","9711":"Vi","9891":"Vi",
    "9650":"Vi","9654":"Vi","9999":"Vi",
    # BSNL
    "9436":"BSNL","9414":"BSNL","9415":"BSNL","9450":"BSNL","9455":"BSNL",
    "9452":"BSNL","9453":"BSNL","9454":"BSNL","9456":"BSNL","9457":"BSNL",
}


def detect_operator(mobile: str) -> str:
    """Detect operator from mobile number. Returns operator name or 'Unknown'."""
    digits = "".join(filter(str.isdigit, mobile))
    if len(digits) < 10:
        return "Unknown"
    digits = digits[-10:]  # last 10 digits

    # Try 4-digit prefix first (more accurate)
    op = OPERATOR_4DIG.get(digits[:4])
    if op:
        return op

    # Fall back to 2-digit prefix
    prefix2 = digits[:2]
    if prefix2 in ("62","63","64","65","66","67","68","69"):
        return "Jio"
    if prefix2 in ("70","71","72","73","74","75","76","77","78","79"):
        return "Jio"
    if prefix2 in ("80","81","82","83","84","85","86","87","88","89"):
        return "Airtel"
    if prefix2 in ("90","91","92","93"):
        return "Vi"
    if prefix2 in ("94","95","96","97","98","99"):
        # More granular
        p3 = digits[:3]
        if p3 in ("944","945","946","941","942"):
            return "BSNL"
        if p3 in ("987","988","989","991","992","993","994","995","996","997","998","999","800","801"):
            return "Airtel"
        if p3 in ("900","901","902","903","904","905","906","907","908","909",
                  "910","911","912","913","914","915","916","917","918","919","920","921","922","923"):
            return "Vi"
        return "Airtel"  # default

    return "Unknown"


# ════════════════════════════════════════════════════════════════
#  PLANS DATABASE
# ════════════════════════════════════════════════════════════════

OPERATOR_PLANS = {

    "Jio": {
        "logo":  "🟦",
        "color": "#0070BA",
        "prepaid": [
            {"id":"jio_1","name":"Jio Basic",     "price":155,  "validity":"24 days", "data":"1.5GB/day",  "calls":"Unlimited","sms":"100/day","extras":["JioTV","JioCinema"],"category":"popular"},
            {"id":"jio_2","name":"Jio Daily 2GB",  "price":209,  "validity":"28 days", "data":"2GB/day",   "calls":"Unlimited","sms":"100/day","extras":["JioTV","JioCinema","JioCloud"],"category":"popular"},
            {"id":"jio_3","name":"Jio 3GB/day",    "price":299,  "validity":"28 days", "data":"3GB/day",   "calls":"Unlimited","sms":"100/day","extras":["JioTV","JioCinema","Netflix Mobile"],"category":"popular"},
            {"id":"jio_4","name":"Jio 2GB 84d",    "price":533,  "validity":"84 days", "data":"2GB/day",   "calls":"Unlimited","sms":"100/day","extras":["JioTV","JioCinema"],"category":"long"},
            {"id":"jio_5","name":"Jio Annual",     "price":2999, "validity":"365 days","data":"2.5GB/day", "calls":"Unlimited","sms":"100/day","extras":["JioTV","JioCinema","JioCloud 100GB"],"category":"annual"},
            {"id":"jio_6","name":"Jio 5G Boost",   "price":349,  "validity":"28 days", "data":"Unlimited 5G","calls":"Unlimited","sms":"100/day","extras":["JioTV","JioCinema","JioCloud","5G Unlimited"],"category":"5g"},
            {"id":"jio_7","name":"Jio 1GB/day",    "price":119,  "validity":"28 days", "data":"1GB/day",   "calls":"Unlimited","sms":"100/day","extras":["JioTV","JioCinema"],"category":"budget"},
            {"id":"jio_8","name":"Jio Dhan Dhana", "price":601,  "validity":"84 days", "data":"3GB/day",   "calls":"Unlimited","sms":"100/day","extras":["JioTV","JioCinema","NetFlix Mobile"],"category":"long"},
        ],
        "postpaid": [
            {"id":"jio_p1","name":"JioPostpaid Plus 399","price":399,"validity":"30 days","data":"75GB","calls":"Unlimited","sms":"100/day","extras":["JioTV","JioCinema","Netflix Mobile","Amazon Prime"],"category":"postpaid"},
            {"id":"jio_p2","name":"JioPostpaid Plus 599","price":599,"validity":"30 days","data":"125GB","calls":"Unlimited","sms":"100/day","extras":["JioTV","JioCinema","Netflix Basic","Amazon Prime","Disney+Hotstar"],"category":"postpaid"},
            {"id":"jio_p3","name":"JioPostpaid Plus 999","price":999,"validity":"30 days","data":"Unlimited","calls":"Unlimited","sms":"100/day","extras":["JioTV","JioCinema","Netflix Standard","Amazon Prime","Disney+Hotstar"],"category":"postpaid"},
        ]
    },

    "Airtel": {
        "logo":  "🔴",
        "color": "#ED1C24",
        "prepaid": [
            {"id":"air_1","name":"Airtel Smart",      "price":179,  "validity":"28 days", "data":"1.5GB/day",  "calls":"Unlimited","sms":"100/day","extras":["Wynk Music","Airtel Thanks"],"category":"popular"},
            {"id":"air_2","name":"Airtel 2GB/day",    "price":239,  "validity":"28 days", "data":"2GB/day",    "calls":"Unlimited","sms":"100/day","extras":["Wynk Music","Apollo 24|7","Airtel Thanks"],"category":"popular"},
            {"id":"air_3","name":"Airtel 3GB/day",    "price":329,  "validity":"28 days", "data":"3GB/day",    "calls":"Unlimited","sms":"100/day","extras":["Wynk Music","Amazon Prime 30d","Airtel Thanks"],"category":"popular"},
            {"id":"air_4","name":"Airtel 2GB 84d",    "price":569,  "validity":"84 days", "data":"2GB/day",    "calls":"Unlimited","sms":"100/day","extras":["Wynk Music","Airtel Thanks"],"category":"long"},
            {"id":"air_5","name":"Airtel Annual",     "price":3359, "validity":"365 days","data":"2.5GB/day",  "calls":"Unlimited","sms":"100/day","extras":["Wynk Music","Airtel Thanks","Amazon Prime"],"category":"annual"},
            {"id":"air_6","name":"Airtel 5G Ultra",   "price":409,  "validity":"28 days", "data":"Unlimited 5G","calls":"Unlimited","sms":"100/day","extras":["Wynk Music","Amazon Prime","5G Unlimited","Airtel XStream"],"category":"5g"},
            {"id":"air_7","name":"Airtel Budget",     "price":99,   "validity":"28 days", "data":"1GB",        "calls":"100 min",  "sms":"300","extras":["Wynk Music"],"category":"budget"},
            {"id":"air_8","name":"Airtel 2GB 56d",    "price":479,  "validity":"56 days", "data":"1.5GB/day",  "calls":"Unlimited","sms":"100/day","extras":["Wynk Music","Airtel Thanks"],"category":"long"},
        ],
        "postpaid": [
            {"id":"air_p1","name":"Airtel Postpaid 399","price":399,"validity":"30 days","data":"75GB","calls":"Unlimited","sms":"100/day","extras":["Amazon Prime","Wynk","Disney+Hotstar Mobile"],"category":"postpaid"},
            {"id":"air_p2","name":"Airtel Postpaid 499","price":499,"validity":"30 days","data":"Unlimited","calls":"Unlimited","sms":"100/day","extras":["Amazon Prime","Netflix Mobile","Disney+Hotstar","Wynk"],"category":"postpaid"},
            {"id":"air_p3","name":"Airtel Postpaid 999","price":999,"validity":"30 days","data":"Unlimited","calls":"Unlimited+Intl","sms":"100/day","extras":["Netflix Basic","Amazon Prime","Disney+Hotstar","Wynk","International Roaming"],"category":"postpaid"},
        ]
    },

    "Vi": {
        "logo":  "🟣",
        "color": "#721D6B",
        "prepaid": [
            {"id":"vi_1","name":"Vi Hero Unlimited",  "price":179,  "validity":"28 days", "data":"1.5GB/day",  "calls":"Unlimited","sms":"100/day","extras":["Vi Movies & TV","Weekend Data Rollover"],"category":"popular"},
            {"id":"vi_2","name":"Vi 2GB/day",         "price":239,  "validity":"28 days", "data":"2GB/day",    "calls":"Unlimited","sms":"100/day","extras":["Vi Movies & TV","Binge All Night","Weekend Rollover"],"category":"popular"},
            {"id":"vi_3","name":"Vi Hero 3GB",        "price":299,  "validity":"28 days", "data":"3GB/day",    "calls":"Unlimited","sms":"100/day","extras":["Vi Movies & TV","Binge All Night","Disney+Hotstar Mobile 30d"],"category":"popular"},
            {"id":"vi_4","name":"Vi 84 Day",          "price":553,  "validity":"84 days", "data":"1.5GB/day",  "calls":"Unlimited","sms":"100/day","extras":["Vi Movies & TV","Weekend Rollover"],"category":"long"},
            {"id":"vi_5","name":"Vi Annual",          "price":2899, "validity":"365 days","data":"1.5GB/day",  "calls":"Unlimited","sms":"100/day","extras":["Vi Movies & TV","Binge All Night"],"category":"annual"},
            {"id":"vi_6","name":"Vi 5G Ready",        "price":359,  "validity":"28 days", "data":"2.5GB/day",  "calls":"Unlimited","sms":"100/day","extras":["Vi Movies & TV","5G Ready","Binge All Night"],"category":"5g"},
            {"id":"vi_7","name":"Vi Budget",          "price":99,   "validity":"28 days", "data":"1GB",        "calls":"100 min",  "sms":"300","extras":["Vi Movies & TV"],"category":"budget"},
        ],
        "postpaid": [
            {"id":"vi_p1","name":"Vi Red 399","price":399,"validity":"30 days","data":"75GB","calls":"Unlimited","sms":"100/day","extras":["Vi Movies & TV","Amazon Prime"],"category":"postpaid"},
            {"id":"vi_p2","name":"Vi Red 499","price":499,"validity":"30 days","data":"100GB","calls":"Unlimited","sms":"100/day","extras":["Vi Movies & TV","Amazon Prime","Netflix Mobile"],"category":"postpaid"},
            {"id":"vi_p3","name":"Vi Red 699","price":699,"validity":"30 days","data":"Unlimited","calls":"Unlimited","sms":"100/day","extras":["Vi Movies & TV","Amazon Prime","Netflix Basic","Disney+Hotstar"],"category":"postpaid"},
        ]
    },

    "BSNL": {
        "logo":  "🟡",
        "color": "#F7A600",
        "prepaid": [
            {"id":"bsnl_1","name":"BSNL STV 94",   "price":94,   "validity":"28 days", "data":"2GB/day",   "calls":"Unlimited","sms":"100/day","extras":["Zing Music"],"category":"budget"},
            {"id":"bsnl_2","name":"BSNL STV 197",  "price":197,  "validity":"54 days", "data":"2GB/day",   "calls":"Unlimited","sms":"100/day","extras":["Zing Music"],"category":"popular"},
            {"id":"bsnl_3","name":"BSNL STV 247",  "price":247,  "validity":"30 days", "data":"3GB/day",   "calls":"Unlimited","sms":"100/day","extras":["Zing Music"],"category":"popular"},
            {"id":"bsnl_4","name":"BSNL 365 Day",  "price":1515, "validity":"365 days","data":"2GB/day",   "calls":"Unlimited","sms":"100/day","extras":["Zing Music"],"category":"annual"},
            {"id":"bsnl_5","name":"BSNL Bulkdata",  "price":398,  "validity":"81 days", "data":"3GB/day",   "calls":"Unlimited","sms":"100/day","extras":["Zing Music"],"category":"long"},
        ],
        "postpaid": [
            {"id":"bsnl_p1","name":"BSNL Plan 99","price":99,"validity":"30 days","data":"2GB","calls":"250 min","sms":"100","extras":[],"category":"postpaid"},
            {"id":"bsnl_p2","name":"BSNL Plan 349","price":349,"validity":"30 days","data":"Unlimited","calls":"Unlimited","sms":"100/day","extras":["Zing Music"],"category":"postpaid"},
        ]
    }
}


# ── DTH Operators ─────────────────────────────────────────────
DTH_OPERATORS = [
    {"id":"tataplay",  "name":"Tata Play",   "logo":"📺"},
    {"id":"airtel_dth","name":"Airtel DTH",  "logo":"📺"},
    {"id":"dishtv",    "name":"Dish TV",     "logo":"📺"},
    {"id":"sundirect", "name":"Sun Direct",  "logo":"📺"},
    {"id":"d2h",       "name":"D2H",         "logo":"📺"},
    {"id":"videocon",  "name":"Videocon D2H","logo":"📺"},
]

DTH_PLANS = {
    "tataplay": [
        {"id":"tp_1","name":"Basic SD",    "price":153, "channels":"280+","validity":"30 days","category":"basic"},
        {"id":"tp_2","name":"Basic HD",    "price":199, "channels":"350+","validity":"30 days","category":"basic"},
        {"id":"tp_3","name":"Maxi HD",     "price":249, "channels":"430+","validity":"30 days","category":"popular"},
        {"id":"tp_4","name":"Binge HD",    "price":399, "channels":"500+","validity":"30 days","extras":["Netflix Mobile","Tata Play Binge"],"category":"premium"},
    ],
    "airtel_dth": [
        {"id":"ad_1","name":"Basic SD",    "price":99,  "channels":"200+","validity":"30 days","category":"basic"},
        {"id":"ad_2","name":"HD Entertainment","price":199,"channels":"350+","validity":"30 days","category":"popular"},
        {"id":"ad_3","name":"Super HD",    "price":299, "channels":"450+","validity":"30 days","extras":["Airtel Xstream"],"category":"premium"},
    ],
    "dishtv": [
        {"id":"dt_1","name":"Basic",       "price":99,  "channels":"200+","validity":"30 days","category":"basic"},
        {"id":"dt_2","name":"Super Family","price":199, "channels":"350+","validity":"30 days","category":"popular"},
        {"id":"dt_3","name":"Super Plus",  "price":299, "channels":"450+","validity":"30 days","category":"premium"},
    ],
}


# ── Broadband Operators ───────────────────────────────────────
BROADBAND_OPERATORS = [
    {"id":"jio_fiber",     "name":"Jio Fiber",       "logo":"🌐"},
    {"id":"airtel_xstream","name":"Airtel Xstream",   "logo":"🌐"},
    {"id":"bsnl_fiber",    "name":"BSNL Fiber",       "logo":"🌐"},
    {"id":"act_fibernet",  "name":"ACT Fibernet",     "logo":"🌐"},
    {"id":"hathway",       "name":"Hathway",          "logo":"🌐"},
]

BROADBAND_PLANS = {
    "jio_fiber": [
        {"id":"jf_1","name":"JioFiber Bronze","price":399,"speed":"30 Mbps","data":"3300GB","validity":"30 days","category":"basic"},
        {"id":"jf_2","name":"JioFiber Silver","price":699,"speed":"100 Mbps","data":"Unlimited","validity":"30 days","extras":["OTT: JioTV, JioCinema"],"category":"popular"},
        {"id":"jf_3","name":"JioFiber Gold",  "price":999,"speed":"200 Mbps","data":"Unlimited","validity":"30 days","extras":["Netflix Mobile","Amazon Prime","Disney+Hotstar"],"category":"popular"},
        {"id":"jf_4","name":"JioFiber Platinum","price":1499,"speed":"500 Mbps","data":"Unlimited","validity":"30 days","extras":["Netflix Standard","Amazon Prime","Disney+Hotstar","ZEE5"],"category":"premium"},
        {"id":"jf_5","name":"JioFiber Diamond","price":2499,"speed":"1 Gbps","data":"Unlimited","validity":"30 days","extras":["Netflix HD","Amazon Prime","All OTT"],"category":"premium"},
    ],
    "airtel_xstream": [
        {"id":"ax_1","name":"Basic 40Mbps",  "price":499, "speed":"40 Mbps", "data":"Unlimited","validity":"30 days","category":"basic"},
        {"id":"ax_2","name":"Standard 100Mbps","price":799,"speed":"100 Mbps","data":"Unlimited","validity":"30 days","extras":["Amazon Prime","Airtel Xstream"],"category":"popular"},
        {"id":"ax_3","name":"Premium 200Mbps","price":999,"speed":"200 Mbps","data":"Unlimited","validity":"30 days","extras":["Amazon Prime","Netflix Mobile","Disney+Hotstar"],"category":"premium"},
        {"id":"ax_4","name":"Ultra 1Gbps",   "price":1999,"speed":"1 Gbps",  "data":"Unlimited","validity":"30 days","extras":["Netflix Basic","Amazon Prime","All OTT"],"category":"premium"},
    ],
}


# ── Electricity Boards ────────────────────────────────────────
ELECTRICITY_BOARDS = [
    {"id":"bses_rajdhani",  "name":"BSES Rajdhani",  "state":"Delhi"},
    {"id":"bses_yamuna",    "name":"BSES Yamuna",    "state":"Delhi"},
    {"id":"tpddl",          "name":"TPDDL",          "state":"Delhi"},
    {"id":"msedcl",         "name":"MSEDCL",         "state":"Maharashtra"},
    {"id":"bescom",         "name":"BESCOM",         "state":"Karnataka"},
    {"id":"tneb",           "name":"TNEB",           "state":"Tamil Nadu"},
    {"id":"wbsedcl",        "name":"WBSEDCL",        "state":"West Bengal"},
    {"id":"uppcl",          "name":"UPPCL",          "state":"Uttar Pradesh"},
    {"id":"pspcl",          "name":"PSPCL",          "state":"Punjab"},
    {"id":"jvvnl",          "name":"JVVNL",          "state":"Rajasthan"},
    {"id":"kseb",           "name":"KSEB",           "state":"Kerala"},
    {"id":"apcpdcl",        "name":"APCPDCL",        "state":"Andhra Pradesh"},
    {"id":"tsspdcl",        "name":"TSSPDCL",        "state":"Telangana"},
    {"id":"cesc",           "name":"CESC",           "state":"West Bengal"},
    {"id":"dgvcl",          "name":"DGVCL",          "state":"Gujarat"},
]


# ── Gas Providers ─────────────────────────────────────────────
GAS_PROVIDERS = [
    {"id":"indraprastha","name":"Indraprastha Gas",  "state":"Delhi/NCR"},
    {"id":"mahanagar",   "name":"Mahanagar Gas",     "state":"Mumbai"},
    {"id":"gujarat_gas", "name":"Gujarat Gas",       "state":"Gujarat"},
    {"id":"adani_gas",   "name":"Adani Gas",         "state":"Multiple"},
    {"id":"torrent_gas", "name":"Torrent Gas",       "state":"Multiple"},
    {"id":"igl",         "name":"IGL",               "state":"Multiple"},
]


# ── Water Boards ──────────────────────────────────────────────
WATER_BOARDS = [
    {"id":"djb",     "name":"Delhi Jal Board",      "state":"Delhi"},
    {"id":"mcgm",    "name":"MCGM",                 "state":"Mumbai"},
    {"id":"bwssb",   "name":"BWSSB",                "state":"Bengaluru"},
    {"id":"cmwssb",  "name":"CMWSSB",               "state":"Chennai"},
    {"id":"hmwssb",  "name":"HMWSSB",               "state":"Hyderabad"},
]


# ── Landline Providers ────────────────────────────────────────
LANDLINE_PROVIDERS = [
    {"id":"bsnl_ll",    "name":"BSNL Landline",     "logo":"📞"},
    {"id":"mtnl_ll",    "name":"MTNL Landline",     "logo":"📞"},
    {"id":"airtel_ll",  "name":"Airtel Landline",   "logo":"📞"},
    {"id":"jio_ll",     "name":"JioFiber Landline", "logo":"📞"},
    {"id":"act_ll",     "name":"ACT Landline",      "logo":"📞"},
]


# ── Helper functions ──────────────────────────────────────────

def get_operator_plans(operator: str, plan_type: str = "prepaid") -> list:
    """Get plans for a specific operator and type."""
    op_data = OPERATOR_PLANS.get(operator, {})
    return op_data.get(plan_type, [])


def get_all_operators() -> list:
    """List all mobile operators."""
    return [
        {"id": k, "name": k, "logo": v["logo"], "color": v["color"]}
        for k, v in OPERATOR_PLANS.items()
    ]


def get_plan_by_id(plan_id: str) -> dict:
    """Find a plan by its ID across all operators."""
    for op_data in OPERATOR_PLANS.values():
        for plans in [op_data.get("prepaid", []), op_data.get("postpaid", [])]:
            for p in plans:
                if p["id"] == plan_id:
                    return p
    return {}


def format_plans_for_ai(operator: str = None) -> str:
    """Format plans as text for AI tutor context."""
    lines = []
    operators = [operator] if operator else list(OPERATOR_PLANS.keys())
    for op in operators:
        op_data = OPERATOR_PLANS.get(op)
        if not op_data:
            continue
        lines.append(f"\n=== {op} PREPAID PLANS ===")
        for p in op_data.get("prepaid", []):
            extras = ", ".join(p.get("extras", []))
            lines.append(
                f"• {p['name']} — ₹{p['price']} | {p['validity']} | {p['data']} | "
                f"{p['calls']} calls | {p['sms']} SMS"
                + (f" | Extras: {extras}" if extras else "")
            )
        lines.append(f"\n--- {op} POSTPAID PLANS ---")
        for p in op_data.get("postpaid", []):
            extras = ", ".join(p.get("extras", []))
            lines.append(
                f"• {p['name']} — ₹{p['price']}/month | Unlimited data {p['data']} | "
                f"{p['calls']} calls"
                + (f" | Extras: {extras}" if extras else "")
            )
    return "\n".join(lines)


def get_ai_plans_context() -> str:
    """Full plans context string for AI tutor."""
    return format_plans_for_ai()