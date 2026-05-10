# NexShift
AI-based Employee Shift Scheduling Optimization System using Python, Linear Programming, and PuLP.



  
## Overview
  

  
NexShift is an intelligent workforce optimization platform designed to automate employee shift scheduling using Artificial Intelligence and Mathematical Optimization techniques.
  

  
The system dynamically allocates employees to Morning, Evening, and Night shifts while considering organizational constraints such as workload balancing, overtime reduction, employee availability, and fair shift distribution.
  

  
Using Mixed-Integer Linear Programming (MILP) with the PuLP optimization library, NexShift generates optimized schedules that improve workforce efficiency and operational management.
  

  
---
  

  
## Features
  

  
- AI-Based Employee Shift Scheduling
  
- Automatic Morning, Evening, and Night Shift Allocation
  
- Work/Off Dynamic Scheduling System
  
- Constraint-Based Workforce Optimization
  
- Overtime and Undertime Monitoring
  
- Fair Workload Distribution
  
- Interactive Analytics Dashboard
  
- Shift Distribution Visualization
  
- Real-Time Schedule Generation
  
- Employee Login and Logout Timings
  
- Excel Dataset Upload Support
  
- Optimized Schedule Export to Excel
  
- Responsive Dark-Themed User Interface
  

  
---
  

  
## Shift Timings
  

  
| Shift Type | Login Time | Logout Time |
  
|------------|------------|-------------|
  
| Morning Shift | 6:00 AM | 2:00 PM |
  
| Evening Shift | 2:00 PM | 10:00 PM |
  
| Night Shift | 10:00 PM | 6:00 AM |
  
| Off Day | — | — |
  

  
---
  

  
## Optimization Constraints
  

  
The scheduling engine considers:
  

  
- Maximum 8 working hours per day
  
- Maximum 40 working hours per week
  
- One shift per employee per day
  
- Fair workload balancing
  
- Overtime minimization
  
- Minimum staffing requirement per shift
  
- Employee availability constraints
  
- No consecutive night shifts
  

  
---
  

  
## Technologies Used
  

  
### Backend
  
- Python
  
- Flask
  
- PuLP
  
- Pandas
  

  
### Frontend
  
- HTML
  
- CSS
  
- JavaScript
  
- Chart.js
  

  
---
  

  
## Project Structure
  

  
```text
  
NexShift/
  
│
  
├── app.py
  
├── optimization.py
  
├── requirements.txt
  
├── README.md
  
│
  
├── data/
  
├── uploads/
  
├── templates/
  
│     └── index.html
  
│
  
├── static/
  
│
  
└── screenshots/


---

Installation

Clone the repository:

git clone https://github.com/gourysurendran/NexShift.git

Navigate to the project directory:

cd NexShift

Install dependencies:

pip install -r requirements.txt


---

Run the Application

python app.py

The application will run locally at:

http://127.0.0.1:5000


---

System Workflow

1. Upload Employee Dataset


2. Generate Optimized Schedule


3. Apply Scheduling Constraints


4. Allocate Employee Shifts Automatically


5. Display Workforce Analytics


6. Export Optimized Schedule




---

Output

The system generates:

Optimized Employee Shift Schedules

Workforce Analytics Reports

Shift Distribution Insights

Overtime and Undertime Reports

Downloadable Excel Schedules



---

NexShift – Intelligent Workforce Optimization