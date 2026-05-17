import pandas as pd
import numpy as np
import pulp
import logging

# Configure logging for the optimization module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_optimization(file_path, absences=None, locked_assignments=None, branch="All", rl_history=None):
    """
    Analyzes workforce data and generates an optimized schedule.
    Supports real-time rescheduling, Skill-based allocation, RL adaptive weights, and Payroll calculation.
    """
    if absences is None: absences = []
    if locked_assignments is None: locked_assignments = {}
    if rl_history is None: rl_history = {"total_ot": 0, "total_ut": 0, "iterations": 0}

    try:
        excel_file = pd.ExcelFile(file_path)
    except Exception as e:
        raise ValueError(f"Invalid Excel file format: {str(e)}")
        
    sheet_names = excel_file.sheet_names
    if not sheet_names:
        raise ValueError("The uploaded Excel file has no sheets.")
        
    # --- 1. PARSE EMPLOYEE AVAILABILITY (Main Sheet) ---
    # We assume the first sheet or a sheet named 'Availability' contains employee data
    avail_sheet_name = next((s for s in sheet_names if 'avail' in s.lower()), sheet_names[0])
    df = excel_file.parse(avail_sheet_name)
    
    # Clean column names
    df.columns = [str(c).strip().replace('_', ' ').replace('-', ' ').lower() for c in df.columns]
    
    # Map required columns
    col_map = {
        'name': 'Name',
        'group code': 'Group',
        'group': 'Group',
        'min hours': 'Min_Hours',
        'max hours': 'Max_Hours',
        'min hour': 'Min_Hours',
        'max hour': 'Max_Hours'
    }
    
    # Days mapping
    days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
    standard_days = [d.capitalize() for d in days]
    
    renamed_cols = {}
    for col in df.columns:
        if col in col_map:
            renamed_cols[col] = col_map[col]
        elif col in days:
            renamed_cols[col] = col.capitalize()
            
    df = df.rename(columns=renamed_cols)
    
    # Check required columns
    if 'Name' not in df.columns:
        # Try to find 'name' in any column
        name_col = next((c for c in df.columns if 'name' in c.lower()), None)
        if name_col: df = df.rename(columns={name_col: 'Name'})
        else: raise ValueError("Missing required column: 'Name' in Availability sheet.")
        
    if 'Group' not in df.columns:
        group_col = next((c for c in df.columns if 'group' in c.lower() or 'dept' in c.lower()), None)
        if group_col: df = df.rename(columns={group_col: 'Group'})
        else: raise ValueError("Missing required column: 'Group Code' in Availability sheet.")

    # Data cleaning
    df = df.dropna(subset=['Name', 'Group'])
    if df.empty:
        raise ValueError("Availability dataset is empty or contains only invalid rows.")
        
    df['Name'] = df['Name'].astype(str).str.strip()
    df['Group'] = df['Group'].astype(str).str.strip()
    
    # Optional columns defaults
    if 'Min_Hours' not in df.columns: df['Min_Hours'] = 0
    if 'Max_Hours' not in df.columns: df['Max_Hours'] = 40
    
    df['Min_Hours'] = pd.to_numeric(df['Min_Hours'], errors='coerce').fillna(0)
    df['Max_Hours'] = pd.to_numeric(df['Max_Hours'], errors='coerce').fillna(40)
    
    # Optional enterprise columns
    if 'Skill' not in df.columns: df['Skill'] = 'General'
    if 'Branch' not in df.columns: df['Branch'] = 'Main'
    if 'Hourly_Rate' not in df.columns: df['Hourly_Rate'] = 500.0
    
    # Filter by Branch if not "All"
    if branch and branch != "All":
        df = df[df['Branch'].astype(str).str.contains(branch, case=False, na=False)]
        if df.empty:
            raise ValueError(f"No employees found for branch '{branch}'.")
    
    # Ensure all days exist
    for d in standard_days:
        if d not in df.columns:
            df[d] = 'Working' # Default to working if not specified
            
    # --- 2. PARSE DEMAND DATA ---
    demand_sheet_name = next((s for s in sheet_names if 'demand' in s.lower()), None)
    if not demand_sheet_name:
        raise ValueError("Missing required sheet: 'Demand'.")
        
    # Read demand sheet - dynamically find the header row
    df_demand_raw = excel_file.parse(demand_sheet_name, header=None)
    header_idx = 0
    for i, row in df_demand_raw.iterrows():
        # Convert row to list of strings for precise matching
        row_values = [str(x).strip().lower() for x in row if pd.notna(x)]
        # Look for the specific 'weekday' header, avoiding title rows like 'People needed per day'
        if 'weekday' in row_values or 'day' in row_values:
            header_idx = i
            break
            
    df_demand = excel_file.parse(demand_sheet_name, header=header_idx)
    # Clean demand columns
    df_demand.columns = [str(c).strip().lower() for c in df_demand.columns]
    
    # Identify Weekday column in demand
    weekday_col = next((c for c in df_demand.columns if 'weekday' in c or 'day' in c), None)
    if not weekday_col:
        raise ValueError("Could not find 'Weekday' column in Demand sheet.")
        
    df_demand = df_demand.rename(columns={weekday_col: 'Weekday'})
    df_demand['Weekday'] = df_demand['Weekday'].astype(str).str.strip().str.capitalize()
    
    # Filter only relevant days
    df_demand = df_demand[df_demand['Weekday'].isin(standard_days)]
    
    # Optional human-centric columns
    if 'Shift_Pref' not in df.columns: df['Shift_Pref'] = 'None'
    if 'Max_Night_Shifts' not in df.columns: df['Max_Night_Shifts'] = 2
    
    df['Max_Night_Shifts'] = pd.to_numeric(df['Max_Night_Shifts'], errors='coerce').fillna(2)

    
    # --- 3. OPTIMIZATION MODEL ---
    groups = df['Group'].unique()
    shifts = ['Morning', 'Evening', 'Night']
    SHIFT_HOURS = 8
    
    shift_details = {
        'Morning': {'Login': '6:00 AM', 'Logout': '2:00 PM'},
        'Evening': {'Login': '2:00 PM', 'Logout': '10:00 PM'},
        'Night': {'Login': '10:00 PM', 'Logout': '6:00 AM'}
    }
    
    prob = pulp.LpProblem("NexShift_Optimization", pulp.LpMinimize)
    
    # Decision Variables
    # x[i, d, s] = 1 if employee i is assigned to day d, shift s
    x = pulp.LpVariable.dicts("assign", 
                               [(i, d, s) for i in df.index for d in standard_days for s in shifts],
                               cat='Binary')
    
    # OT and UT variables for workload balancing
    ot = pulp.LpVariable.dicts("Overtime", df.index, lowBound=0, cat='Continuous')
    ut = pulp.LpVariable.dicts("Undertime", df.index, lowBound=0, cat='Continuous')
    
    # Objective: Minimize total deviation from target hours (Workload Balancing)
    # 6. Reinforcement Learning-Based Adaptive Scheduling
    # Adjust penalties based on historical RL data (e.g. if OT was previously high, penalize OT more)
    ot_weight = 1.0
    ut_weight = 1.0
    if rl_history['iterations'] > 0:
        if rl_history['total_ot'] > rl_history['total_ut']:
            ot_weight = 1.2
            ut_weight = 0.8
        elif rl_history['total_ut'] > rl_history['total_ot']:
            ot_weight = 0.8
            ut_weight = 1.2

    obj_terms = [ot_weight * ot[i] + ut_weight * ut[i] for i in df.index]
    
    # Shift preferences reward
    for i in df.index:
        pref = str(df.loc[i, 'Shift_Pref']).strip().capitalize()
        if pref in shifts:
            for d in standard_days:
                # Reward (negative penalty) for assigning preferred shift
                obj_terms.append(-0.5 * x[(i, d, pref)])
                
    prob += pulp.lpSum(obj_terms)
    
    # Constraints
    for d in standard_days:
        for g in groups:
            g_members = df[df['Group'] == g].index
            
            # Find demand for this group on this day
            demand_row = df_demand[df_demand['Weekday'] == d]
            demand_val = 0
            if not demand_row.empty:
                # Match group name in demand columns (case-insensitive)
                match_col = next((c for c in demand_row.columns if str(c).lower() == g.lower()), None)
                if match_col:
                    val = demand_row.iloc[0][match_col]
                    try:
                        demand_val = int(float(val)) if pd.notna(val) else 0
                    except:
                        demand_val = 0
            
            # 1. Satisfy Demand: Sum of all shifts for this group >= demand
            prob += pulp.lpSum([x[(i, d, s)] for i in g_members for s in shifts]) >= demand_val
            
            # 2. Shift Balancing: Try to distribute people across shifts
            # If demand is D, aim for ~D/3 per shift
            if demand_val > 0:
                target_per_shift = demand_val / 3.0
                for s in shifts:
                    # We allow some flexibility but try to keep it balanced
                    # (This is a soft constraint in spirit, but here we just ensure at least 1 person per shift if demand is high)
                    if demand_val >= 3:
                        prob += pulp.lpSum([x[(i, d, s)] for i in g_members]) >= int(target_per_shift)
    
    for i in df.index:
        # 3. Max one shift per day
        for d in standard_days:
            prob += pulp.lpSum([x[(i, d, s)] for s in shifts]) <= 1
            
            # 4. Respect 'NW' (Not Working) and absences
            avail_val = str(df.loc[i, d]).strip().upper()
            emp_name = str(df.loc[i, 'Name'])
            
            # Check absences (case-insensitive)
            is_absent = any(str(a).strip().lower() == emp_name.lower() for a in absences)
            
            # Check locked assignments
            locked_shift = locked_assignments.get(f"{emp_name}_{d}")
            
            if avail_val == 'NW' or avail_val == 'OFF' or avail_val == '0' or is_absent:
                for s in shifts:
                    prob += x[(i, d, s)] == 0
            elif locked_shift in shifts:
                for s in shifts:
                    if s == locked_shift:
                        prob += x[(i, d, s)] == 1
                    else:
                        prob += x[(i, d, s)] == 0
                    
        # 5. Burnout Prevention & Sustainable Scheduling
        # 5a. Max night shifts per week
        prob += pulp.lpSum([x[(i, d, 'Night')] for d in standard_days]) <= df.loc[i, 'Max_Night_Shifts']
        
        # 5b. Avoid consecutive night shifts
        for day_idx in range(len(standard_days) - 1):
            prob += x[(i, standard_days[day_idx], 'Night')] + x[(i, standard_days[day_idx+1], 'Night')] <= 1
            
        # 5c. Minimum Rest Hours (12 hours between shifts across consecutive days)
        # Morning: 6-14, Evening: 14-22, Night: 22-6
        # Evening -> Morning: 8 hrs rest (Invalid)
        # Night -> Morning: 0 hrs rest (Invalid)
        # Night -> Evening: 8 hrs rest (Invalid)
        for day_idx in range(len(standard_days) - 1):
            d1 = standard_days[day_idx]
            d2 = standard_days[day_idx+1]
            prob += x[(i, d1, 'Evening')] + x[(i, d2, 'Morning')] <= 1
            prob += x[(i, d1, 'Night')] + x[(i, d2, 'Morning')] <= 1
            prob += x[(i, d1, 'Night')] + x[(i, d2, 'Evening')] <= 1
            
        # 5d. Fair Weekend Rotation (Max 1 weekend shift per employee)
        weekend_days = [d for d in ['Saturday', 'Sunday'] if d in standard_days]
        if weekend_days:
            prob += pulp.lpSum([x[(i, d, s)] for d in weekend_days for s in shifts]) <= 1
            
        # 6. Total Hours Constraints
        total_hours = pulp.lpSum([x[(i, d, s)] * SHIFT_HOURS for d in standard_days for s in shifts])
        min_h = df.loc[i, 'Min_Hours']
        max_h = df.loc[i, 'Max_Hours']
        
        # 7. Workload Balancing & Predictive Overtime Control
        # Heavy penalty on OT handled in objective (ot variable)
        prob += total_hours - ot[i] <= max_h
        prob += total_hours + ut[i] >= min_h

    # Solve
    try:
        solver = pulp.PULP_CBC_CMD(msg=0)
        prob.solve(solver)
    except Exception as e:
        logger.error(f"Solver error: {e}")
        raise ValueError("The optimization solver failed. Please check if your demand constraints are realistic.")
    
    status = pulp.LpStatus[prob.status]
    if status != 'Optimal':
        logger.warning(f"Optimization Status: {status}")
        
    # --- 4. GENERATE RESULTS ---
    schedule = []
    shift_assignments = {}
    shift_counts = {s: 0 for s in shifts}
    group_hours = {str(g): 0 for g in groups}
    extra_workers = []
    available_workers = []
    preferences_met = 0
    
    for i in df.index:
        emp_name = str(df.loc[i, 'Name'])
        group = str(df.loc[i, 'Group'])
        row = {'Name': emp_name, 'Group': group}
        
        emp_total_hours = 0
        for d in standard_days:
            assigned = None
            for s in shifts:
                try:
                    if pulp.value(x[(i, d, s)]) == 1:
                        assigned = s
                        break
                except:
                    continue
            
            if assigned:
                row[d] = assigned
                shift_counts[assigned] += 1
                emp_total_hours += SHIFT_HOURS
                shift_assignments[f"{emp_name}_{d}"] = {
                    "Type": f"{assigned} Shift",
                    "Login": shift_details[assigned]['Login'],
                    "Logout": shift_details[assigned]['Logout']
                }
                
                # Check if preferred shift was granted
                pref = str(df.loc[i, 'Shift_Pref']).strip().capitalize()
                if assigned == pref:
                    preferences_met += 1
            else:
                row[d] = 'Off'
                shift_assignments[f"{emp_name}_{d}"] = None
                
        row['Total_Hours'] = float(emp_total_hours)
        row['OT'] = float(pulp.value(ot[i]) or 0)
        row['UT'] = float(pulp.value(ut[i]) or 0)
        
        # 3. Payroll Integration
        hourly_rate = float(df.loc[i, 'Hourly_Rate'])
        base_pay = row['Total_Hours'] * hourly_rate
        ot_pay = row['OT'] * (hourly_rate * 1.5)
        row['Base_Pay'] = base_pay
        row['OT_Pay'] = ot_pay
        row['Total_Pay'] = base_pay + ot_pay
        
        schedule.append(row)
        
        if group in group_hours:
            group_hours[group] += emp_total_hours
        
        if row['OT'] > 0:
            extra_workers.append({"Name": emp_name, "OT": row['OT'], "Group": group})
            
        slack = float(df.loc[i, 'Max_Hours']) - emp_total_hours
        if slack > 0:
            available_workers.append({"Name": emp_name, "Available": slack, "Group": group})
            
    df_schedule = pd.DataFrame(schedule)
    
    # Robust file saving
    output_file = "Optimized_Schedule.xlsx"
    try:
        df_schedule.to_excel(output_file, index=False)
    except PermissionError:
        logger.warning(f"Could not save to {output_file}. File may be open in another program.")
        # Fallback to a unique filename if the default is locked
        output_file = f"Optimized_Schedule_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df_schedule.to_excel(output_file, index=False)
    
    # Ensure all return values are JSON serializable (no NaN)
    return {
        "status": str(status),
        "total_shifts": int(sum(shift_counts.values())),
        "total_hours": float(sum(shift_counts.values()) * SHIFT_HOURS),
        "group_hours": {k: float(v) for k, v in group_hours.items()},
        "shift_counts": {k: int(v) for k, v in shift_counts.items()},
        "total_ot": float(df_schedule['OT'].sum() or 0),
        "total_ut": float(df_schedule['UT'].sum() or 0),
        "schedule": schedule,
        "shift_assignments": shift_assignments,
        "extra_workers": extra_workers,
        "available_workers": available_workers,
        "preferences_met": preferences_met,
        "total_payroll": sum(r['Total_Pay'] for r in schedule)
    }

