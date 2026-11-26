from table_lookup_service import TableLookupService

service = TableLookupService()

# Test 1: 5-column classic table
text_5col = """
Product life cycle dates
| Type Model | Announced | Available | Marketing Withdrawn | Service Discontinued |
|---|---|---|---|---|
| 9080-M9S | 2018-08-07 | 2018-09-21 | 2022-10-31 | - |
"""

print("=== Test 1: 5-col E980 Withdrawn ===")
res1 = service._parse_lifecycle_table(text_5col, "E980", "withdrawn", "9080-M9S")
print(res1)

print("\n=== Test 2: 5-col E980 Support / Discontinued ===")
res2 = service._parse_lifecycle_table(text_5col, "E980", "end_of_support", "9080-M9S")
print(res2)

# Test 3: 6-column table from real scraped E980 (9080-03.json) where 6th column is empty
text_6col_empty_discontinued = """
Product life cycle dates
| Type Model | Announced | Available | Marketing Withdrawn | Support level changed | Service discontinued |
|---|---|---|---|---|---|
| 9080-M9S | 2018-08-07 | 2018-09-21 | 2022-10-31 | 2027-12-31 |  |
"""

print("\n=== Test 3: Real E980 6-col (Support Level Changed=2027-12-31, Service Discontinued=empty) - All Dates ===")
res3 = service._parse_lifecycle_table(text_6col_empty_discontinued, "E980", None, "9080-M9S")
print(res3)

print("\n=== Test 4: Real E980 6-col - End of Support query ===")
res4 = service._parse_lifecycle_table(text_6col_empty_discontinued, "E980", "end_of_support", "9080-M9S")
print(res4)

print("\n=== Test 5: Real E980 6-col - Service Discontinued specific query ===")
res5 = service._parse_lifecycle_table(text_6col_empty_discontinued, "E980", "discontinued", "9080-M9S")
print(res5)

print("\n=== Test 6: Real E980 6-col - Support Level Changed specific query ===")
res6 = service._parse_lifecycle_table(text_6col_empty_discontinued, "E980", "support_level_changed", "9080-M9S")
print(res6)

# Test 7: 6-column modern table with Support level changed and hyphen (e.g. S924 9009-42A)
text_6col_s924 = """
Product life cycle dates
| Type Model | Announced | Available | Marketing Withdrawn | Support level changed | Service Discontinued |
|---|---|---|---|---|---|
| 9009-42A | 2018-02-13 | 2018-03-20 | 2021-01-29 | 31 January 2026 | - |
"""

print("\n=== Test 7: 6-col S924 End of Support query ===")
res7 = service._parse_lifecycle_table(text_6col_s924, "S924", "end_of_support", "9009-42A")
print(res7)

# Test 8: Multi-MTM family table (e.g. S1112)
text_multi_mtm = """
Product life cycle dates
| Type Model | Announced | Available | Marketing Withdrawn | Service Discontinued |
|---|---|---|---|---|
| 9242-21B | 2026-07-14 | 2026-07-24 | - | - |
| 9242-21T | 2026-07-14 | 2026-07-24 | - | - |
"""

print("\n=== Test 8: S1112 Multi-MTM summary (no specific MTM) ===")
res8 = service._parse_lifecycle_table(text_multi_mtm, "S1112", None, None)
print(res8)

print("\n=== Test 9: S1112 Multi-MTM with specific field (announced) ===")
res9 = service._parse_lifecycle_table(text_multi_mtm, "S1112", "announced", None)
print(res9)
