"""Source Ledger role/source catalog. These are data-object mappings, not API endpoints.
All example workbook values are illustrative and fictional, per The Source Ledger.
"""
from copy import deepcopy

MODULES = [
    {
        "key": "cfo", "role": "Chief Financial Officer", "workbook": "01-cfo-sample-extract.xlsx",
        "description": "Asset accounting, capital allocation, financial strategy and risk oversight.", "source_ledger_pages": [3],
        "sheets": [
            {"name": "ANLA", "object": "SAP FI-AA ANLA", "header_row": 5, "primary_key": ["MANDT", "BUKRS", "ANLN1", "ANLN2"], "join_keys": ["MANDT", "BUKRS", "ANLN1", "ANLN2"], "columns": ["MANDT", "BUKRS", "ANLN1", "ANLN2", "ANLKL", "AKTIV", "DEAKT"]},
            {"name": "ANLZ", "object": "SAP FI-AA ANLZ", "header_row": 5, "primary_key": ["MANDT", "BUKRS", "ANLN1", "ANLN2", "BDATU"], "join_keys": ["MANDT", "BUKRS", "ANLN1", "ANLN2"], "columns": ["MANDT", "BUKRS", "ANLN1", "ANLN2", "KOSTL", "BDATU"]},
            {"name": "ANLC", "object": "SAP FI-AA ANLC", "header_row": 5, "primary_key": ["MANDT", "BUKRS", "ANLN1", "ANLN2", "GJAHR"], "join_keys": ["MANDT", "BUKRS", "ANLN1", "ANLN2"], "columns": ["MANDT", "BUKRS", "ANLN1", "ANLN2", "GJAHR", "KANSW", "NAFAG"]},
        ],
    },
    {
        "key": "corporate-controller", "role": "Corporate Controller", "workbook": "02-corporate-controller-sample-extract.xlsx",
        "description": "General ledger, journal documents, financial close and internal controls.", "source_ledger_pages": [4],
        "sheets": [
            {"name": "BKPF", "object": "SAP BKPF document header", "header_row": 5, "primary_key": ["MANDT", "BUKRS", "BELNR", "GJAHR"], "join_keys": ["MANDT", "BUKRS", "BELNR", "GJAHR"], "columns": ["MANDT", "BUKRS", "BELNR", "GJAHR", "BLART", "BUDAT", "BLDAT", "WAERS"]},
            {"name": "BSEG", "object": "SAP BSEG document line items", "header_row": 5, "primary_key": ["MANDT", "BUKRS", "BELNR", "GJAHR", "BUZEI"], "join_keys": ["MANDT", "BUKRS", "BELNR", "GJAHR"], "columns": ["MANDT", "BUKRS", "BELNR", "GJAHR", "BUZEI", "HKONT", "DMBTR", "SHKZG"]},
        ],
    },
    {
        "key": "plant-controller", "role": "Plant / BU Controller", "workbook": "03-plant-controller-sample-extract.xlsx",
        "description": "Plant cost line items, inventory valuation, goods movements, BOM accuracy and capex.", "source_ledger_pages": [5],
        "sheets": [{"name": "MBEW", "object": "SAP MBEW material valuation", "header_row": 5, "primary_key": ["MANDT", "MATNR", "BWKEY", "BWTAR"], "join_keys": ["MANDT", "MATNR", "BWKEY"], "columns": ["MANDT", "MATNR", "BWKEY", "BWTAR", "BKLAS", "VPRSV", "VERPR", "STPRS", "PEINH", "LBKUM", "SALK3", "SALKV", "LFGJA", "LFMON"]}],
        "related_objects": ["SAP COEP", "SAP COSS/COSP", "SAP MSEG/MKPF", "SAP STKO/STPO", "Oracle BOM_COMPONENTS_B"],
    },
    {
        "key": "cost-accounting", "role": "Cost Accounting Manager", "workbook": "04-cost-accounting-sample-extract.xlsx",
        "description": "Standard costing, BOM costing, production-order variance and scrap variance.", "source_ledger_pages": [6],
        "sheets": [{"name": "WIP_PERIOD_BALANCES", "object": "Oracle WIP_PERIOD_BALANCES", "header_row": 5, "primary_key": ["ORGANIZATION_ID", "WIP_ENTITY_ID", "ACCT_PERIOD_ID", "CLASS_TYPE"], "join_keys": ["ORGANIZATION_ID", "WIP_ENTITY_ID", "ACCT_PERIOD_ID"], "columns": ["ORGANIZATION_ID", "WIP_ENTITY_ID", "ACCT_PERIOD_ID", "CLASS_TYPE", "TL_MATERIAL_VAR", "TL_MATERIAL_OVERHEAD_VAR", "TL_RESOURCE_VAR", "TL_OVERHEAD_VAR", "TL_OUTSIDE_PROCESSING_VAR", "TL_SCRAP_VAR"]}],
        "related_objects": ["SAP KEKO", "Oracle CST_ITEM_COSTS", "SAP PLPO", "SAP STKO/STPO", "SAP AFKO/AFPO"],
    },
    {
        "key": "fpa", "role": "FP&A Manager", "workbook": "05-fpa-sample-extract.xlsx",
        "description": "Financial modeling, actual-versus-plan/forecast analysis and scenario planning.", "source_ledger_pages": [7, 8],
        "sheets": [{"name": "COEP", "object": "SAP COEP controlling line items", "header_row": 5, "primary_key": ["KOKRS", "BELNR", "BUZEI", "GJAHR", "PERIO"], "join_keys": ["OBJNR", "GJAHR", "PERIO", "KSTAR"], "columns": ["KOKRS", "BELNR", "BUZEI", "GJAHR", "PERIO", "OBJNR", "KSTAR", "WRTTP", "VERSN", "WTGBTR", "WKGBTR", "TWAER", "SGTXT"]}],
    },
    {
        "key": "treasury", "role": "Treasury Manager", "workbook": "06-treasury-sample-extract.xlsx",
        "description": "Cash positioning, bank statements, liquidity and FX/commodity risk.", "source_ledger_pages": [8],
        "sheets": [
            {"name": "CE_STATEMENT_HEADERS", "object": "Oracle CE_STATEMENT_HEADERS", "header_row": 5, "primary_key": ["STATEMENT_HEADER_ID"], "join_keys": ["STATEMENT_HEADER_ID"], "columns": ["STATEMENT_HEADER_ID", "BANK_ACCOUNT_ID", "STATEMENT_NUMBER", "STATEMENT_DATE", "STMT_FROM_DATE", "STMT_TO_DATE", "CURRENCY_CODE", "RECON_STATUS_CODE", "BALANCE_CHECK"]},
            {"name": "CE_STATEMENT_LINES", "object": "Oracle CE_STATEMENT_LINES", "header_row": 5, "primary_key": ["STATEMENT_LINE_ID"], "join_keys": ["STATEMENT_HEADER_ID"], "columns": ["STATEMENT_LINE_ID", "STATEMENT_HEADER_ID", "LINE_NUMBER", "TRX_CODE_ID", "FLOW_INDICATOR", "AMOUNT", "TRX_CURR_CODE", "BOOKING_DATE", "VALUE_DATE", "RECON_STATUS", "TRANSACTION_ID"]},
        ],
    },
    {
        "key": "tax", "role": "Tax Manager", "workbook": "07-tax-sample-extract.xlsx",
        "description": "Direct/indirect tax, tax determination and cross-border/customs-related data.", "source_ledger_pages": [9],
        "sheets": [{"name": "ZX_LINES", "object": "Oracle Fusion ZX_LINES", "header_row": 5, "primary_key": ["TAX_LINE_ID"], "join_keys": ["TRX_NUMBER", "LEGAL_ENTITY_ID"], "columns": ["TAX_LINE_ID", "TRX_NUMBER", "LEGAL_ENTITY_ID", "TAX_REGIME_CODE", "TAX_STATUS_CODE", "TAX_RATE_CODE", "TAX_JURISDICTION_CODE", "TAXABLE_AMT", "TAX_AMT", "TAX_AMT_FUNCL_CURR", "TRX_CURRENCY_CODE"]}],
    },
    {
        "key": "internal-audit", "role": "Internal Audit Manager", "workbook": "08-internal-audit-sample-extract.xlsx",
        "description": "Journal-entry testing, risk-based audit planning and internal-controls testing.", "source_ledger_pages": [10],
        "sheets": [
            {"name": "GL_JE_HEADERS", "object": "Oracle GL_JE_HEADERS", "header_row": 5, "primary_key": ["JE_HEADER_ID"], "join_keys": ["JE_HEADER_ID"], "columns": ["JE_HEADER_ID", "JE_BATCH_ID", "JE_CATEGORY", "JE_SOURCE", "PERIOD_NAME", "STATUS", "POSTED_DATE"]},
            {"name": "GL_JE_LINES", "object": "Oracle GL_JE_LINES", "header_row": 5, "primary_key": ["JE_HEADER_ID", "JE_LINE_NUM"], "join_keys": ["JE_HEADER_ID"], "columns": ["JE_HEADER_ID", "JE_LINE_NUM", "CODE_COMBINATION_ID", "ENTERED_DR", "ENTERED_CR", "ACCOUNTED_DR", "ACCOUNTED_CR"]},
        ],
    },
    {
        "key": "risk-management", "role": "Risk Management Lead", "workbook": "09-risk-management-sample-extract.xlsx",
        "description": "Enterprise risk identification, commodity/FX exposures and hedge disclosure.", "source_ledger_pages": [11],
        "sheets": [{"name": "ASC815_Hedge_Disclosure", "object": "ASC 815-10-50 disclosure structure", "header_row": 5, "primary_key": ["Derivative category", "Hedge designation"], "join_keys": ["Derivative category", "Hedge designation"], "columns": ["Derivative category", "Hedge designation", "Notional amount", "Fair value — Assets", "Fair value — Liabilities", "Balance-sheet location"]}],
        "note": "Workbook structure is based on disclosure format; figures are illustrative and not sourced from Honeywell or another real company.",
    },
    {
        "key": "investor-relations", "role": "Investor Relations Manager", "workbook": "10-investor-relations-sample-extract.xlsx",
        "description": "Public-filing, earnings, shareholder and analyst-consensus data.", "source_ledger_pages": [11],
        "sheets": [{"name": "Form13F_InfoTable", "object": "SEC Form 13F Information Table compiled view", "header_row": 5, "primary_key": ["Filing Manager", "CUSIP", "Investment Discretion"], "join_keys": ["Name of Issuer", "CUSIP"], "columns": ["Filing Manager", "Name of Issuer", "Title of Class", "CUSIP", "Value ($000s)", "Shares/Principal Amount", "SH/PRN Type", "Investment Discretion", "Voting Auth—Sole", "Voting Auth—Shared", "Voting Auth—None"]}],
    },
    {
        "key": "accounts-payable", "role": "Accounts Payable Manager", "workbook": "11-accounts-payable-sample-extract.xlsx",
        "description": "Vendor open items, invoice matching and payment processing.", "source_ledger_pages": [12],
        "sheets": [{"name": "BSIK", "object": "SAP BSIK vendor open-items index", "header_row": 5, "primary_key": ["MANDT", "BUKRS", "LIFNR", "GJAHR", "BELNR", "BUZEI"], "join_keys": ["MANDT", "BUKRS", "LIFNR", "BELNR", "GJAHR"], "columns": ["MANDT", "BUKRS", "LIFNR", "GJAHR", "BELNR", "BUZEI", "WRBTR", "DMBTR", "WAERS", "ZFBDT", "ZTERM", "BUDAT", "AUGDT", "XBLNR"]}],
        "related_objects": ["SAP EKKO/EKPO/EKBE", "SAP LFA1/LFB1/LFBK", "SAP REGUH/REGUP", "Oracle AP_INVOICES_ALL/AP_INVOICE_DISTRIBUTIONS_ALL"],
    },
    {
        "key": "ar-credit", "role": "AR & Credit Manager", "workbook": "12-ar-credit-sample-extract.xlsx",
        "description": "Customer open items, receivables aging, collections and credit exposure.", "source_ledger_pages": [13],
        "sheets": [{"name": "BSID", "object": "SAP BSID customer open-items index", "header_row": 5, "primary_key": ["MANDT", "BUKRS", "KUNNR", "BELNR", "GJAHR", "BUZEI"], "join_keys": ["MANDT", "BUKRS", "KUNNR", "BELNR", "GJAHR"], "columns": ["MANDT", "BUKRS", "KUNNR", "BELNR", "GJAHR", "BUZEI", "WRBTR", "DMBTR", "SKFBT", "BUDAT", "ZFBDT", "ZTERM", "ZBD1T", "ZBD1P", "AUGDT", "AUGBL", "SHKZG", "WAERS"]}],
        "related_objects": ["Oracle RA_CUSTOMER_TRX_ALL", "Oracle Advanced Collections (IEX)", "SAP KNKK/UKM_BP"],
    },
]

MODULE_MAP = {m["key"]: m for m in MODULES}

def public_modules():
    return deepcopy(MODULES)

def get_module(key: str):
    item = MODULE_MAP.get(key)
    return deepcopy(item) if item else None
