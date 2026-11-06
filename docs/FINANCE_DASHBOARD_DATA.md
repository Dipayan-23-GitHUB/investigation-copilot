# Connecting the Controller Finance Dashboard

## Why the cards were empty

The dashboard's earlier version read only the exception/action registers. Those records are not a P&L, cash-flow statement, budget or trial balance. The current finance API reads a dedicated normalized reporting pack instead of guessing account classifications from raw GL lines.

## Upload path

1. Download `sample_data/Finance_Dashboard_Upload_Template.xlsx`.
2. Populate all four sheets from approved, posted finance reports after your normal finance/ERP reconciliation.
3. In Investigation Copilot, choose **Upload extract** and select module key `finance-reporting`.
4. Choose the workbook and upload. Refresh the Finance Dashboard.

All sheets use the header row at row 5. The period format is `YYYY-MM`; entity names and three-letter currencies must be consistent across sheets. The dashboard treats the most recently uploaded finance workbook as the active full-period snapshot, so upload a complete replacement pack when refreshing the reporting history (not only a delta file).

## Sheet contracts

### `PNL_ACTUALS`

Required columns: `PERIOD`, `ENTITY`, `CURRENCY`, `ACCOUNT_CODE`, `ACCOUNT_NAME`, `STATEMENT_LINE`, `CATEGORY`, `AMOUNT`.

`STATEMENT_LINE` must be one of `REVENUE`, `COGS`, `OPERATING_EXPENSE`, `OTHER_INCOME`, `OTHER_EXPENSE`, or `TAX`. Amounts are positive for the named line type; credit notes/reversals may be negative. The service calculates gross profit as revenue less COGS, operating profit as gross profit less operating expenses, and net profit as operating profit plus other income less other expenses and tax. To show net profit and net margin, include all six statement-line classes for the selected period/currency; enter an explicit zero row when a class has no postings rather than omitting it.

### `BUDGET`

Required columns: `PERIOD`, `ENTITY`, `CURRENCY`, `ACCOUNT_CODE`, `ACCOUNT_NAME`, `STATEMENT_LINE`, `CATEGORY`, `BUDGET_AMOUNT`. Use the same account/category and statement-line conventions as `PNL_ACTUALS`. Costs are positive budget amounts. Actual-versus-budget comparisons match period, currency and category.

### `CASH_FLOW`

Required columns: `PERIOD`, `ENTITY`, `CURRENCY`, `CASH_FLOW_CLASS`, `CATEGORY`, `AMOUNT`. `CASH_FLOW_CLASS` must be `OPERATING`, `INVESTING`, or `FINANCING`. Amounts are signed: positive inflow and negative outflow. Only an approved/classified cash-flow statement should be used here; an unclassified bank movement is not automatically operating cash flow.

### `TRIAL_BALANCE`

Required columns: `PERIOD`, `ENTITY`, `CURRENCY`, `BALANCE_CLASS`, `ACCOUNT_CODE`, `ACCOUNT_NAME`, `CLOSING_BALANCE`. `BALANCE_CLASS` must be `CASH`, `ACCOUNTS_RECEIVABLE`, `ACCOUNTS_PAYABLE`, `INVENTORY`, or `OTHER`. Provide posted closing balances from a reconciled trial balance. For presentation, enter each class's displayed closing balance as a positive amount.

## Calculation and safety rules

- No FX conversion: values from different currencies are never summed together. Choose a currency filter before comparing bars if more than one currency is present.
- Entity filtering uses the exact `ENTITY` values present in the workbook. The dropdown is populated from uploaded data.
- Period filtering uses `PERIOD` in `YYYY-MM` form.
- Missing sheets, malformed rows and unsupported statement classifications are reported as warnings and excluded from calculations.
- No figures are generated from the exception register or fictional sample workbooks.
- Do not upload confidential customer/employee data unless the environment, access controls and data-processing approval are appropriate for it.

## Important source mapping note

The Source Ledger's twelve sample workbooks describe source-system objects such as SAP `BKPF/BSEG`, `COEP`, and Oracle bank statement lines. They do not include a full chart-of-accounts statement-line mapping or a cash-flow transaction-code mapping. Those must be provided/validated by Finance before a normalized pack can be produced. The included sample source workbook figures are fictional illustrations and must not be presented as a real company's financial results.
