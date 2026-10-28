from sqlalchemy.orm import Session
from .models import ExceptionRecord, ActionRecord, ControlRecord

DEMO_CASES = {
 "case1": {
  "title": "Material purchase price variance", "summary": "Actual receipt price is $21.75 while the material standard remains $18.40 across 4,000 units.", "material_id": "FRM-VX7-AL", "impact_amount": 13400, "direction": "unfavorable", "priority": "high", "status": "open", "confidence": 0.94, "evidence_count": 4, "root_cause_found": True, "evidence_complete": True,
  "investigation": {"finding":"Stale standard cost after supplier price increase", "finding_text":"The actual receipt price was $21.75 while the material standard remained $18.40. The 4,000-unit receipt creates the full $13,400 unfavorable variance.", "evidence":[
   {"id":"E1","type":"Material master","title":"FRM-VX7-AL","summary":"Standard price $18.40/unit · valuation date 2026-01-04","details":{"standard_price":18.4,"valuation_date":"2026-01-04","plant":"MER-100"}},
   {"id":"E2","type":"Goods receipt","title":"GR-20260819-014","summary":"4,000 units at $21.75 · Alcan Extrusions Ltd.","details":{"quantity":4000,"actual_unit_price":21.75,"posting_date":"2026-08-19","vendor":"Alcan Extrusions Ltd."}},
   {"id":"E3","type":"Variance report","title":"PPV · $13,400 U","summary":"Material purchase price variance is unexplained","details":{"variance_amount":13400,"direction":"unfavorable","status":"unexplained"}},
   {"id":"E4","type":"Journal entry","title":"JE-88231","summary":"$73,600 inventory + $13,400 PPV = $87,000 AP","details":{"inventory_debit":73600,"ppv_debit":13400,"accounts_payable_credit":87000}}
  ], "hypotheses":[
   {"title":"Stale standard cost","status":"primary hypothesis","explanation":"Standard is $18.40 while actual receipt price is $21.75.","evidence_ids":["E1","E2","E3"]},
   {"title":"Quantity or receipt error","status":"not supported by available records","explanation":"Receipt quantity and variance calculation reconcile.","evidence_ids":["E2","E3"]},
   {"title":"Journal imbalance","status":"ruled out by available evidence","explanation":"$73,600 + $13,400 = $87,000.","evidence_ids":["E4"]}
  ], "controls":["Trigger standard-cost review when approved supplier price changes exceed the configured threshold.","Validate supplier price changes against contract effective dates.","Flag receipts that remain outside standard-cost tolerance."], "calculation":{"formula":"(actual_unit_price - standard_unit_price) * quantity","inputs":{"actual_unit_price":21.75,"standard_unit_price":18.4,"quantity":4000},"result":13400}, "demo_only":True}
 },
 "case2": {
  "title":"Inventory book / physical mismatch", "summary":"DR9 book quantity exceeds the physical count by 340 units; movement history points to a likely wrong material code.", "material_id":"DR9 / DR8", "impact_amount":2108, "direction":"exposure", "priority":"medium", "status":"review", "confidence":0.91, "evidence_count":4, "root_cause_found":True, "evidence_complete":True,
  "investigation":{"finding":"Mis-keyed goods issue — not shrinkage","finding_text":"340 DR9 units were issued for Work Order 4471 but the warehouse posting referenced DR8, a phased-out predecessor code. Potential incorrect write-off is 340 × $6.20 = $2,108.","evidence":[
   {"id":"E1","type":"Inventory reconciliation","title":"DR9 · 340 unit gap","summary":"Book 1,850 vs physical 1,510 · gap -340","details":{"book_quantity":1850,"physical_quantity":1510,"gap":-340}},
   {"id":"E2","type":"Goods movements","title":"WO-4471","summary":"DR9 issue -310 · DR8 issue -340","details":{"work_order":"WO-4471","dr9_movement":-310,"dr8_movement":-340,"dr8_status":"phased_out"}},
   {"id":"E3","type":"Material master","title":"DR8 / DR9","summary":"DR8 is phased out; DR9 is active","details":{"active_material":"DR9","phased_out_material":"DR8"}},
   {"id":"E4","type":"Cost impact","title":"$2,108 potential write-off","summary":"340 × $6.20 standard cost","details":{"standard_price":6.2,"quantity":340,"potential_writeoff":2108}}
  ],"hypotheses":[
   {"title":"Mis-keyed material code","status":"primary hypothesis","explanation":"A 340-unit DR8 issue matches the DR9 quantity gap for WO-4471.","evidence_ids":["E1","E2","E3"]},
   {"title":"Shrinkage","status":"less supported","explanation":"Movement records may explain the quantity without treating it as an unexplained loss.","evidence_ids":["E1","E2"]},
   {"title":"Control failure","status":"control issue","explanation":"The phased-out code appears to remain postable.","evidence_ids":["E2","E3"]}
  ],"controls":["Block or warn on goods issues against phased-out material codes.","Validate material eligibility against the work order or routing.","Require review before posting a shrinkage write-off when movements reconcile to the gap."],"calculation":{"formula":"quantity_gap * standard_price","inputs":{"quantity_gap":340,"standard_price":6.2},"result":2108},"demo_only":True}
 },
 "case3": {
  "title":"Favorable standard-cost variance", "summary":"A steel-to-composite BOM change reduced actual cost by $6.80 per unit, while standard cost remained unchanged.", "material_id":"TRHD-3SP", "impact_amount":8160, "direction":"favorable", "priority":"medium", "status":"review", "confidence":0.89, "evidence_count":4, "root_cause_found":True, "evidence_complete":True,
  "investigation":{"finding":"Engineering change not reflected in standard cost","finding_text":"ECN-2261 replaced a steel kickstand bracket with composite, reducing material cost by $6.80 per unit. The standard remained $142 because the standard-cost roll-up was not re-triggered.","evidence":[
   {"id":"E1","type":"Variance report","title":"$8,160 favorable","summary":"$6.80/unit × 1,200 units","details":{"standard_cost":142,"actual_cost":135.2,"quantity":1200,"variance":8160}},
   {"id":"E2","type":"BOM history","title":"ECN-2261","summary":"Steel bracket → composite bracket · effective 2026-06-15","details":{"engineering_change":"ECN-2261","old_component":"KSB-STL-02","new_component":"KSB-CMP-01","cost_impact_per_unit":-6.8,"standard_updated":False}},
   {"id":"E3","type":"Material master","title":"TRHD-3SP","summary":"Standard materials cost remains $142","details":{"standard_cost":142,"valuation_date":"2026-01-04"}},
   {"id":"E4","type":"Journal entry","title":"JE-88450","summary":"$162,240 actual + $8,160 F = $170,400 standard","details":{"actual_cost":162240,"favorable_variance":8160,"standard_cost_total":170400}}
  ],"hypotheses":[
   {"title":"Engineering change impact","status":"primary hypothesis","explanation":"ECN-2261 changed the bracket with a stated $6.80/unit cost impact.","evidence_ids":["E1","E2"]},
   {"title":"Standard cost stale","status":"control issue","explanation":"Standard stayed at $142 after the engineering change.","evidence_ids":["E2","E3"]},
   {"title":"Genuine process efficiency","status":"not established","explanation":"The variance is explained by a component change; a pure efficiency claim needs separate validation.","evidence_ids":["E1","E2"]}
  ],"controls":["Trigger standard-cost review when an approved engineering change has a cost impact.","Review favorable variances with the same discipline as unfavorable variances.","Flag effective-date mismatches between BOM cost and standard cost."],"calculation":{"formula":"(standard_cost - actual_cost) * production_quantity","inputs":{"standard_cost":142,"actual_cost":135.2,"production_quantity":1200},"result":8160},"demo_only":True}
 }
}

OTHER_EXCEPTIONS = [
 {"id":"ex_supplier","title":"Supplier contract drift","summary":"Potential supplier price conditions are not aligned with current standard-cost review.","material_id":"SUP-884","impact_amount":42700,"direction":"unfavorable","priority":"high","status":"queued","confidence":0.78,"evidence_count":2,"root_cause_found":True,"evidence_complete":True},
 {"id":"ex_scrap","title":"Scrap/yield anomaly","summary":"Unusual scrap/yield movement in WLD-LINE-2 requires production and costing review.","material_id":"WLD-LINE-2","impact_amount":16900,"direction":"unfavorable","priority":"medium","status":"queued","confidence":0.76,"evidence_count":2,"root_cause_found":True,"evidence_complete":False},
 {"id":"ex_labor","title":"Labor efficiency deviation","summary":"Labor costs diverge from the illustrative baseline for the period.","material_id":"LAB-PLANT-100","impact_amount":33800,"direction":"unfavorable","priority":"medium","status":"queued","confidence":0.61,"evidence_count":1,"root_cause_found":False,"evidence_complete":False},
 {"id":"ex_overhead","title":"Overhead absorption review","summary":"Overhead absorption differs from the expected production basis.","material_id":"OH-PLANT-100","impact_amount":55200,"direction":"unfavorable","priority":"medium","status":"queued","confidence":0.58,"evidence_count":1,"root_cause_found":False,"evidence_complete":False},
 {"id":"ex_freight","title":"Freight surcharge anomaly","summary":"Freight charges require PO and vendor-condition reconciliation.","material_id":"FRT-2026-08","impact_amount":12032,"direction":"unfavorable","priority":"low","status":"queued","confidence":0.49,"evidence_count":0,"root_cause_found":False,"evidence_complete":False},
]

CONTROLS = [
 {"id":"ctl_ecn_cost","title":"Engineering change triggers standard-cost review","process_area":"Engineering / Cost Accounting","owner":"Cost Accounting + Engineering","description":"Approved changes with a cost impact create a standard-cost review task.","status":"proposed","recurrence_count":3,"exposure_amount":27400},
 {"id":"ctl_supplier_price","title":"Supplier price change triggers standard review","process_area":"Procurement / Cost Accounting","owner":"Procurement + Cost Accounting","description":"Price changes above a customer-configured threshold trigger standard-cost validation.","status":"proposed","recurrence_count":4,"exposure_amount":61200},
 {"id":"ctl_phaseout","title":"Block or warn on phased-out material codes","process_area":"Inventory / Warehouse Systems","owner":"Warehouse Systems","description":"Validate material status and work-order eligibility before goods issue posting.","status":"proposed","recurrence_count":2,"exposure_amount":8600},
 {"id":"ctl_variance_review","title":"Apply review thresholds to favorable and unfavorable variances","process_area":"Procurement / Cost Accounting","owner":"Plant Controller","description":"Route material variance exceptions for evidence review in either direction.","status":"proposed","recurrence_count":5,"exposure_amount":8160},
]

ACTIONS = [
 ("case1", "Review standard cost for FRM-VX7-AL", "Cost Accounting", "open", "corrective"),
 ("case1", "Validate supplier price change against contract", "Procurement", "open", "investigation"),
 ("case1", "Add price-change trigger to control library", "Cost Accounting", "planned", "preventive"),
 ("case2", "Hold potential $2,108 shrinkage write-off pending movement review", "Plant Controller", "open", "corrective"),
 ("case2", "Validate WO-4471 issue and correct material reference if confirmed", "Warehouse", "open", "corrective"),
 ("case3", "Review standard cost after ECN-2261", "Cost Accounting", "planned", "corrective"),
]

def seed_initial_data(db: Session) -> None:
    if db.query(ExceptionRecord).first() is None:
        for case_id, c in DEMO_CASES.items():
            db.add(ExceptionRecord(id=case_id, tenant_id="demo", title=c["title"], summary=c["summary"], material_id=c["material_id"], impact_amount=c["impact_amount"], currency="USD", direction=c["direction"], priority=c["priority"], status=c["status"], confidence=c["confidence"], evidence_count=c["evidence_count"], root_cause_found=c["root_cause_found"], evidence_complete=c["evidence_complete"], investigation=c["investigation"]))
        for c in OTHER_EXCEPTIONS:
            db.add(ExceptionRecord(tenant_id="demo", investigation={}, **c, currency="USD"))
        # Ensure parent exception rows exist before seeding actions with foreign keys.
        db.flush()
    if db.query(ControlRecord).first() is None:
        for c in CONTROLS:
            db.add(ControlRecord(**c))
    if db.query(ActionRecord).first() is None:
        for idx, (exception_id, title, owner, status, action_type) in enumerate(ACTIONS, 1):
            db.add(ActionRecord(id=f"act_{idx:03d}", tenant_id="demo", exception_id=exception_id, title=title, owner=owner, status=status, action_type=action_type))
    db.commit()
