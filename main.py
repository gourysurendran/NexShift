import pandas as pd

# Load dataset
file_path = "data/Employees_dataset.xlsx"

# Read Excel file
df = pd.read_excel(file_path)

# Display first 5 rows
print("Dataset Preview:\n")
print(df.head())

# Display dataset information
print("\nDataset Information:\n")
print(df.info())

df_demand = pd.read_excel(file_path, sheet_name='Demand', header=1)

import pulp

# Data Preprocessing
days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
groups = df['Group code'].unique()

# Initialize the problem
prob = pulp.LpProblem("Shift_Scheduling", pulp.LpMinimize)

# Decision Variables
# x[i, d] = 1 if employee i works on day d, 0 otherwise
x = pulp.LpVariable.dicts("shift",
                          [(i, d) for i in df.index for d in days],
                          cat='Binary')

# Overtime and Undertime variables
ot = pulp.LpVariable.dicts("OT", df.index, lowBound=0, cat='Continuous')
ut = pulp.LpVariable.dicts("UT", df.index, lowBound=0, cat='Continuous')

# Objective: Minimize total overtime and undertime
prob += pulp.lpSum([ot[i] + ut[i] for i in df.index])

# Constraints
for d in days:
    for g in groups:
        # Group members
        g_members = df[df['Group code'] == g].index
        
        # 1. Demand Constraint
        demand_row = df_demand[df_demand['Weekday'] == d]
        demand = int(demand_row.iloc[0][g]) if not demand_row.empty and g in demand_row.columns else 0
        prob += pulp.lpSum([x[(i, d)] for i in g_members]) == demand
        
        # 2. Special Skills Constraint
        n_special = df[(df['Group code'] == g) & (df['Special Skill'] == 1)].shape[0]
        if n_special > 0 and demand > 0:
            special_members = df[(df['Group code'] == g) & (df['Special Skill'] == 1)].index
            required_special = min(demand, n_special - 1)
            prob += pulp.lpSum([x[(i, d)] for i in special_members]) >= required_special

# 3. Availability Constraints
for i in df.index:
    for d in days:
        if pd.notna(df.loc[i, d]) and str(df.loc[i, d]).strip().upper() == 'NW':
            prob += x[(i, d)] == 0  # Employee not working on this day

# 4. Min/Max Hours Constraints
SHIFT_HOURS = 8
for i in df.index:
    total_hours = pulp.lpSum([x[(i, d)] * SHIFT_HOURS for d in days])
    min_h = df.loc[i, 'Min_Hours']
    max_h = df.loc[i, 'Max_Hours']
    
    prob += total_hours - ot[i] <= max_h
    prob += total_hours + ut[i] >= min_h

# Solve the problem
prob.solve(pulp.PULP_CBC_CMD(msg=0))

print("Status:", pulp.LpStatus[prob.status])
print("Total Overtime + Undertime (slack):", pulp.value(prob.objective))

# Create schedule output
schedule = []
for i in df.index:
    emp_name = df.loc[i, 'Name']
    group = df.loc[i, 'Group code']
    row = {'Name': emp_name, 'Group code': group}
    total_shifts = 0
    for d in days:
        is_working = pulp.value(x[(i, d)])
        row[d] = 'Working' if is_working == 1 else 'Off'
        total_shifts += is_working if is_working == 1 else 0
    row['Total Hours'] = total_shifts * SHIFT_HOURS
    row['Min_Hours'] = df.loc[i, 'Min_Hours']
    row['Max_Hours'] = df.loc[i, 'Max_Hours']
    row['OT'] = pulp.value(ot[i])
    row['UT'] = pulp.value(ut[i])
    schedule.append(row)

df_schedule = pd.DataFrame(schedule)
print("\nGenerated Schedule Preview:")
print(df_schedule.head())

# Save to Excel
output_file = "Optimized_Schedule.xlsx"
df_schedule.to_excel(output_file, index=False)
print(f"\nSchedule saved to {output_file}")

# Workforce Analytics and Insights
print("\n--- Workforce Analytics & Workload Distribution Insights ---")
total_shifts = sum([1 for i in df.index for d in days if pulp.value(x[(i, d)]) == 1])
print(f"Total Shifts Scheduled: {total_shifts}")
print(f"Total Hours Scheduled: {total_shifts * SHIFT_HOURS}")

print("\nWorkload by Group (Hours):")
group_hours = df_schedule.groupby('Group code')['Total Hours'].sum()
print(group_hours)

print("\nEfficiency Improvements (Slack Hours):")
print(f"Total Overtime (Hours): {df_schedule['OT'].sum()}")
print(f"Total Undertime (Hours): {df_schedule['UT'].sum()}")

print("\nOptimization Complete.")