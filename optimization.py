import pandas as pd
import pulp

def run_optimization(file_path):
    df = pd.read_excel(file_path)
    df_demand = pd.read_excel(file_path, sheet_name='Demand', header=1)

    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    groups = df['Group code'].unique()
    shifts = ['Morning', 'Evening', 'Night']
    
    # Shift timings mapping
    shift_details = {
        'Morning': {'Login': '6:00 AM', 'Logout': '2:00 PM'},
        'Evening': {'Login': '2:00 PM', 'Logout': '10:00 PM'},
        'Night': {'Login': '10:00 PM', 'Logout': '6:00 AM'}
    }

    # ---------------------------------------------------------
    # ACADEMIC PRESENTATION: OPTIMIZATION MODEL OVERVIEW
    # ---------------------------------------------------------
    # This optimization model is formulated as a Mixed-Integer 
    # Linear Programming (MILP) problem. The objective is to
    # schedule employees efficiently while minimizing overtime
    # and undertime, ensuring optimal workload distribution.
    
    prob = pulp.LpProblem("Shift_Scheduling", pulp.LpMinimize)

    # 1. DECISION VARIABLES
    # x[i, d, s] is a Binary variable (0 or 1).
    # 1 if employee 'i' works shift 's' on day 'd', else 0.
    x = pulp.LpVariable.dicts("shift",
                              [(i, d, s) for i in df.index for d in days for s in shifts],
                              cat='Binary')

    # Continuous variables for measuring deviations from ideal hours
    # ot: Overtime hours (hours worked above the employee's maximum threshold)
    # ut: Undertime hours (hours worked below the employee's minimum threshold)
    ot = pulp.LpVariable.dicts("OT", df.index, lowBound=0, cat='Continuous')
    ut = pulp.LpVariable.dicts("UT", df.index, lowBound=0, cat='Continuous')

    # 2. OBJECTIVE FUNCTION
    # Objective: Minimize the sum of all overtime and undertime.
    # This naturally leads to a "Fair Workload Distribution" as the
    # solver avoids assigning too many or too few hours to individuals.
    prob += pulp.lpSum([ot[i] + ut[i] for i in df.index])

    # 3. DEMAND AND COVERAGE CONSTRAINTS
    for d in days:
        for g in groups:
            g_members = df[df['Group code'] == g].index
            demand_row = df_demand[df_demand['Weekday'] == d]
            demand = int(demand_row.iloc[0][g]) if not demand_row.empty and g in demand_row.columns else 0
            
            # Constraint 3a: Meet daily demand across all shifts for the group
            # Ensure enough employees from the group are scheduled to meet the total daily requirement.
            prob += pulp.lpSum([x[(i, d, s)] for i in g_members for s in shifts]) >= demand

    # 4. EMPLOYEE-SPECIFIC CONSTRAINTS
    for i in df.index:
        for d in days:
            # Constraint 4a: One shift per employee per day
            # An employee cannot work multiple shifts (e.g., Morning and Night) on the same day.
            prob += pulp.lpSum([x[(i, d, s)] for s in shifts]) <= 1
            
            # Constraint 4b: Non-working days preference (NW)
            # Hard constraint to respect approved time-off or unavailable days.
            if pd.notna(df.loc[i, d]) and str(df.loc[i, d]).strip().upper() == 'NW':
                for s in shifts:
                    prob += x[(i, d, s)] == 0

        # Constraint 4c: No consecutive night shifts
        # Prevents an employee from working a Night shift on day D and another Night shift on day D+1.
        for d_idx in range(len(days) - 1):
            prob += x[(i, days[d_idx], 'Night')] + x[(i, days[d_idx+1], 'Night')] <= 1

    SHIFT_HOURS = 8
    # 5. REGULATORY & WORKLOAD LIMIT CONSTRAINTS
    for i in df.index:
        total_hours = pulp.lpSum([x[(i, d, s)] * SHIFT_HOURS for d in days for s in shifts])
        min_h = df.loc[i, 'Min_Hours']
        max_h = df.loc[i, 'Max_Hours']
        
        # Max 8 hours per day is inherently handled since max 1 shift per day per employee.
        # We do not strictly cap at 40 to prevent infeasibility during high demand, 
        # but overtime will be heavily penalized.
        
        # Constraint 5a: Overtime Calculation
        # The deviation variable ot[i] absorbs any hours exceeding the employee's Max_Hours.
        prob += total_hours - ot[i] <= max_h
        
        # Constraint 5b: Undertime Calculation
        # The deviation variable ut[i] absorbs any deficit below the employee's Min_Hours.
        prob += total_hours + ut[i] >= min_h

    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    status = pulp.LpStatus[prob.status]

    schedule = []
    extra_workers = []
    available_workers = []
    
    # Store assigned shifts
    shift_assignments = {}

    for i in df.index:
        emp_name = df.loc[i, 'Name']
        group = df.loc[i, 'Group code']
        row = {'Name': emp_name, 'Group_code': group}
        total_shifts = 0
        
        for d in days:
            assigned_shift = None
            for s in shifts:
                if pulp.value(x[(i, d, s)]) == 1:
                    assigned_shift = s
                    break
            
            if assigned_shift:
                row[d] = assigned_shift
                shift_assignments[f"{emp_name}_{d}"] = {
                    "Type": f"{assigned_shift} Shift",
                    "Login": shift_details[assigned_shift]['Login'],
                    "Logout": shift_details[assigned_shift]['Logout']
                }
                total_shifts += 1
            else:
                row[d] = 'Off'
                shift_assignments[f"{emp_name}_{d}"] = None
                
        total_h = total_shifts * SHIFT_HOURS
        max_h = float(df.loc[i, 'Max_Hours'])
        min_h = float(df.loc[i, 'Min_Hours'])
        overtime = float(pulp.value(ot[i]))
        
        row['Total_Hours'] = total_h
        row['Min_Hours'] = min_h
        row['Max_Hours'] = max_h
        row['OT'] = overtime
        row['UT'] = float(pulp.value(ut[i]))
        schedule.append(row)
        
        if overtime > 0:
            extra_workers.append({"Name": emp_name, "OT": overtime, "Group": group})
            
        slack = max_h - total_h
        if slack > 0:
            available_workers.append({"Name": emp_name, "Available": slack, "Group": group})

    df_schedule = pd.DataFrame(schedule)
    output_file = "Optimized_Schedule.xlsx"
    df_schedule.to_excel(output_file, index=False)
    
    total_assigned_shifts = sum([1 for i in df.index for d in days for s in shifts if pulp.value(x[(i, d, s)]) == 1])
    group_hours = df_schedule.groupby('Group_code')['Total_Hours'].sum().to_dict()

    # Shift distribution for analytics
    shift_counts = {'Morning': 0, 'Evening': 0, 'Night': 0}
    for i in df.index:
        for d in days:
            for s in shifts:
                if pulp.value(x[(i, d, s)]) == 1:
                    shift_counts[s] += 1

    return {
        "status": status,
        "slack": pulp.value(prob.objective),
        "total_shifts": total_assigned_shifts,
        "total_hours": total_assigned_shifts * SHIFT_HOURS,
        "group_hours": group_hours,
        "shift_counts": shift_counts,
        "total_ot": float(df_schedule['OT'].sum()),
        "total_ut": float(df_schedule['UT'].sum()),
        "schedule": schedule,
        "shift_assignments": shift_assignments,
        "extra_workers": extra_workers,
        "available_workers": available_workers
    }
