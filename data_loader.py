import pandas as pd
import numpy as np
from datetime import datetime

# ── Mill assignment ───────────────────────────────────────
SM_SECTIONS = {'50X50','55X55','60X60','65X65','70X70','75X75'}
LM_SECTIONS = {'80X80','90X90','100X100','110X110','120X120','130X130'}

PLAN_START_DAY = 1   # Jan 1
PLAN_END_DAY   = 31  # Jan 31


def parse_bucket_date(val):
    """
    Returns day-of-month (1–31) for planning.
    - Valid Jan 2026 date  → use that day
    - Date before Jan 2026 → PLAN_START_DAY (1)
    - time(0,0) / NaN / 0  → PLAN_END_DAY (31)
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return PLAN_END_DAY

    # Excel midnight stored as time(0,0)
    if hasattr(val, 'hour') and not hasattr(val, 'year'):
        return PLAN_END_DAY

    if isinstance(val, datetime):
        if val.year == 2026 and val.month == 1:
            return val.day
        elif val < datetime(2026, 1, 1):
            return PLAN_START_DAY
        else:
            return PLAN_END_DAY

    return PLAN_END_DAY


def parse_section(section_raw):
    """
    '70X70X5' → section='70X70', thickness=5
    '60X60X10' → section='60X60', thickness=10
    """
    s = str(section_raw).strip()
    parts = s.split('X')
    if len(parts) >= 3:
        section   = parts[0] + 'X' + parts[1]
        try:
            thickness = int(parts[2])
        except ValueError:
            thickness = 6
    elif len(parts) == 2:
        section   = s
        thickness = 6
    else:
        section   = s
        thickness = 6
    return section, thickness


def assign_mill(section):
    if section in SM_SECTIONS:
        return 'SM'
    elif section in LM_SECTIONS:
        return 'LM'
    else:
        return None   # unknown section — will be dropped


def load_loi(path):
    """
    Loads LOI sheet, parses section/thickness/mill/bucket,
    returns clean DataFrame of individual LOI rows.
    """
    df = pd.read_excel(path, sheet_name='LOI')
    df.columns = df.columns.str.strip()

    # Rename the leading-space column
    if ' SECTIONS' in df.columns:
        df.rename(columns={' SECTIONS': 'SECTIONS'}, inplace=True)

    df['SECTIONS'] = df['SECTIONS'].astype(str).str.strip()
    df['qty']      = pd.to_numeric(df['PO Qty'], errors='coerce').fillna(0)

    # Parse section and thickness
    parsed         = df['SECTIONS'].apply(parse_section)
    df['section']  = parsed.apply(lambda x: x[0])
    df['thickness']= parsed.apply(lambda x: x[1])

    # Assign mill
    df['mill']     = df['section'].apply(assign_mill)

    # Parse bucket date → planning day
    df['due_day']  = df['LOI_Bucket'].apply(parse_bucket_date)

    # Drop zero qty and unknown mill rows
    df = df[(df['qty'] > 0) & (df['mill'].notna())].copy()

    return df.reset_index(drop=True)


MILL_CAPACITY = {'SM': 150.0, 'LM': 250.0}

def build_campaigns(loi_df, mill):
    sub = loi_df[loi_df['mill'] == mill].copy()
    cap = MILL_CAPACITY[mill]

    # Step 1 — group by section + thickness + due_day
    grouped = sub.groupby(
        ['section', 'thickness', 'due_day'], as_index=False
    ).agg(qty=('qty', 'sum'))

    # Step 2 — split each group into shift-capacity chunks
    rows = []
    for _, row in grouped.iterrows():
        remaining = row['qty']
        while remaining > 0:
            chunk = min(remaining, cap)
            rows.append({
                'section'  : row['section'],
                'thickness': row['thickness'],
                'qty'      : chunk,
                'due'      : row['due_day'],
                'mill'     : mill
            })
            remaining -= chunk

    camps = pd.DataFrame(rows).reset_index(drop=True)
    return camps

def load_changeover(path):
    xl = pd.ExcelFile(path)
    co = {}

    # ── Section changeover TIME ───────────────────────────
    if 'Section Roll Changeover Time' in xl.sheet_names:
        raw = pd.read_excel(path,
                            sheet_name='Section Roll Changeover Time',
                            header=0,
                            index_col=0)
        # row 0 = header (section names), col 0 = index (section names)

        def to_hours(val):
            if pd.isna(val):
                return np.nan
            s = str(val).strip().lower()
            if s == 'x':
                return np.nan
            if '8-12' in s or '8 -12' in s:
                return 10.0
            if '6-8' in s or '6 -8' in s:
                return 7.0
            try:
                return float(val)
            except:
                return np.nan

        hours_data = np.vectorize(to_hours)(raw.values)
        sec_time   = pd.DataFrame(
            hours_data,
            index  =[str(i).strip() for i in raw.index],
            columns=[str(c).strip() for c in raw.columns]
        )
        co['sec_time'] = sec_time

    # ── Section changeover COST (fixed) ──────────────────
    co['sec_cost'] = 24100.0

    # ── Thickness changeover COST ─────────────────────────
    for mill_tag in ['SM', 'LM']:
        sheet = f'Thickness Changeover Cost_{mill_tag}'
        if sheet in xl.sheet_names:
            raw = pd.read_excel(path,
                                sheet_name=sheet,
                                header=0,
                                index_col=0)
            # row 0 = header (thickness numbers), col 0 = index (thickness numbers)

            def to_cost(val):
                if pd.isna(val):
                    return np.nan
                s = str(val).strip()
                if s == 'X':
                    return 0.0
                try:
                    v = float(val)
                    return v if v > 0 else np.nan
                except:
                    return np.nan

            cost_data = np.vectorize(to_cost)(raw.values)
            thk_cost  = pd.DataFrame(
                cost_data,
                index  =pd.to_numeric(raw.index,   errors='coerce'),
                columns=pd.to_numeric(raw.columns, errors='coerce')
            )
            # Drop NaN index or columns
            thk_cost = thk_cost.loc[
                [i for i in thk_cost.index   if not pd.isna(i)],
                [c for c in thk_cost.columns if not pd.isna(c)]
            ]
            co[f'thk_cost_{mill_tag}'] = thk_cost

    return co


def load_actual_plan(path, mill):
    """
    Loads actual historical rolling plan from Excel.
    Row 0 = header, row 1 = blank — skip row 1.
    Returns DataFrame sorted by start_date (actual rolling sequence).
    """
    df = pd.read_excel(path, header=0, skiprows=[1])
    df.columns = [
        'start_date', 'end_date', 'mill_code', 'loi', 'loi_dt',
        'location', 'bucket', 'pg_npg', 'grade', 'series',
        'gr', 'sections', 'qty', 'project',
        'billet_status', 'billet_order_status', 'remarks'
    ]
    df = df.dropna(subset=['sections', 'qty'])
    df['qty']       = pd.to_numeric(df['qty'], errors='coerce').fillna(0)
    df              = df[df['qty'] > 0].copy()

    parsed          = df['sections'].apply(parse_section)
    df['section']   = parsed.apply(lambda x: x[0])
    df['thickness'] = parsed.apply(lambda x: x[1])
    df['mill']      = df['section'].apply(assign_mill)
    df['due_day']   = df['bucket'].apply(parse_bucket_date)
    df['due']       = df['due_day']

    df = df[df['mill'] == mill].copy()
    return df.reset_index(drop=True)


def build_actual_permutation(actual_df, camps):
    """
    Maps actual rolling sequence (LOI rows ordered by start_date)
    to a permutation of campaign indices.

    Each unique (section, thickness, due) combination in actual_df
    is matched to a campaign in camps. First appearance order defines
    the sequence. Campaigns not in actual plan are appended at end.

    Returns (perm, n_missing) where n_missing = count of campaigns
    in actual plan not found in camps (due to date bucket differences).
    """
    seen  = {}
    order = []
    for _, row in actual_df.iterrows():
        key = (row['section'], row['thickness'], row['due'])
        if key not in seen:
            seen[key] = len(seen)
            order.append(key)

    camp_lookup = {}
    for i, row in camps.iterrows():
        key = (row['section'], row['thickness'], row['due'])
        camp_lookup[key] = i

    perm    = []
    missing = 0
    for key in order:
        if key in camp_lookup:
            perm.append(camp_lookup[key])
        else:
            missing += 1

    # Append campaigns not covered by actual plan
    used = set(perm)
    for i in range(len(camps)):
        if i not in used:
            perm.append(i)

    return np.array(perm, dtype=int), missing