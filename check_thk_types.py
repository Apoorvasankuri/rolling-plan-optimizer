from data_loader import load_loi, load_changeover, build_campaigns

loi_df = load_loi('LOI_Jan_2026.xlsx')
co     = load_changeover('changeover_data.json')
camps  = build_campaigns(loi_df, 'SM')

# Check what type thickness is in campaigns
print("Campaign thickness types:")
print(camps['thickness'].dtype)
print(camps['thickness'].head())

# Check what type the thk_cost index is
thk = co['thk_cost_SM']
print(f"\nThk cost matrix index type: {thk.index.dtype}")
print(f"Thk cost matrix index: {list(thk.index)}")

# Test a lookup
from evaluator import get_thk_cost
t1 = camps.iloc[0]['thickness']
t2 = camps.iloc[1]['thickness']
print(f"\nLooking up: {t1} (type={type(t1)}) -> {t2} (type={type(t2)})")
result = get_thk_cost(co, t1, t2, 'SM')
print(f"Result: {result}")

# Test different thickness lookup
t1 = 4
t2 = 5
print(f"\nLooking up: {t1} (int) -> {t2} (int)")
result = get_thk_cost(co, t1, t2, 'SM')
print(f"Result: {result}")

# Try direct DataFrame lookup
try:
    val = co['thk_cost_SM'].loc[4, 5]
    print(f"Direct loc[4, 5]: {val}")
except KeyError as e:
    print(f"Direct loc[4, 5] FAILED: {e}")

try:
    val = co['thk_cost_SM'].loc['4', '5']
    print(f"Direct loc['4', '5']: {val}")
except KeyError as e:
    print(f"Direct loc['4', '5'] FAILED: {e}")