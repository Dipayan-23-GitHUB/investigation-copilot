# Source Ledger mapping and build boundaries

Source basis: *The Source Ledger*, Volume III, especially Schedule L (role → skill → source) and Schedule M (12 attachments), PDF pages 3–13. The guide explicitly says the files contain illustrative Meridian Bicycle Co. numbers, while column structures reflect real-world objects. The workbook tabs generally put the data header on row 5 after three source/illustration lines and a blank spacer row.

The module catalog in `app/catalog.py` is the machine-readable version of this mapping. It includes sheet aliases because workbook tabs may have a descriptive suffix, e.g. `ANLA (Asset Master)`, while the canonical object is `ANLA`.

| Module key | Role | Workbook | Workbook sheet(s) | Canonical source object(s) | Likely integration path |
|---|---|---|---|---|---|
| `cfo` | Chief Financial Officer | `01-cfo-sample-extract.xlsx` | ANLA, ANLZ, ANLC | SAP FI-AA asset master/assignment/values | Authorized SAP extract/API; 3 related tabs share asset keys |
| `corporate-controller` | Corporate Controller | `02-corporate-controller-sample-extract.xlsx` | BKPF, BSEG | SAP accounting document header + line items | Released SAP API/reporting/export; join document keys |
| `plant-controller` | Plant / BU Controller | `03-plant-controller-sample-extract.xlsx` | MBEW | SAP material valuation | SAP material valuation API/report/extract; manufacturing MVP source |
| `cost-accounting` | Cost Accounting Manager | `04-cost-accounting-sample-extract.xlsx` | WIP_PERIOD_BALANCES | Oracle WIP period variance balances | Oracle Fusion service/reporting/export; manufacturing MVP source |
| `fpa` | FP&A Manager | `05-fpa-sample-extract.xlsx` | COEP | SAP controlling actual/plan line items | SAP reporting/API/extract; period/version semantics must be mapped |
| `treasury` | Treasury Manager | `06-treasury-sample-extract.xlsx` | CE_STATEMENT_HEADERS, CE_STATEMENT_LINES | Oracle cash-management bank statement header + lines | Oracle Fusion REST/reporting/export; header-line join |
| `tax` | Tax Manager | `07-tax-sample-extract.xlsx` | ZX_LINES | Oracle Fusion tax determination lines | Oracle Fusion tax/reporting APIs/export |
| `internal-audit` | Internal Audit Manager | `08-internal-audit-sample-extract.xlsx` | GL_JE_HEADERS, GL_JE_LINES | Oracle general-ledger journal headers + lines | Oracle Fusion REST/reporting/export; header-line join |
| `risk-management` | Risk Management Lead | `09-risk-management-sample-extract.xlsx` | ASC815_Hedge_Disclosure | ASC 815-10-50 disclosure-shaped dataset | File/report or relevant treasury/risk source; this workbook is not a direct ERP table |
| `investor-relations` | Investor Relations Manager | `10-investor-relations-sample-extract.xlsx` | Form13F_InfoTable | SEC Form 13F information table | SEC EDGAR/public data API planned; workbook is a compiled illustrative view |
| `accounts-payable` | Accounts Payable Manager | `11-accounts-payable-sample-extract.xlsx` | BSIK | SAP vendor open-items index | Authorized SAP export/API; may join to PO/GR/IR/vendor/payment objects |
| `ar-credit` | AR & Credit Manager | `12-ar-credit-sample-extract.xlsx` | BSID | SAP customer open-items index | Authorized SAP export/API; may join to customer invoice, cleared items and credit data |

## MVP order recommended

**First:** `plant-controller`, `cost-accounting`, `corporate-controller`, `accounts-payable`, `fpa`.

**Second:** `internal-audit`, `ar-credit`, and `cfo` as control/reconciliation adjacencies.

**Later/specialist packs:** treasury, tax, risk management and investor relations.

All 12 modules can be ingested/read via generic APIs now. Module-specific investigation rules and vendor connector implementations are not all built yet.

## Important source-vs-API distinction

A named SAP table such as `MBEW`, `MSEG/MKPF`, `STKO/STPO`, `COEP`, `BKPF/BSEG`, or `BSIK`, and a named Oracle object such as `WIP_PERIOD_BALANCES`, `CST_ITEM_COSTS`, `ZX_LINES`, or `GL_JE_LINES`, is a **source object**—not a promise that the table can be queried directly over a public HTTP API. Each customer integration needs to determine the ERP generation/version, permitted read interface, released APIs/ODATA/CDS views, reports/extracts, role authorization and relevant business keys. Don't connect directly to a production database without explicit customer approval and an approved security architecture.

## Sample data and current UI cases

- The attached Source Ledger workbooks contain fictional illustrative values. E.g., the Plant Controller workbook uses its own sample material such as `FR-CARB-56`; it is not the same row set as the static HTML demo case `FRM-VX7-AL`.
- The seeded HTML-style scenarios `case1`, `case2`, `case3` are API-served demo fixtures. They should not be represented as conclusions calculated from a customer's uploaded workbook.
- The next analytics phase should map source rows into a canonical manufacturing model and emit exception evidence links only when keys, period, quantity, currency and calculation checks reconcile.
