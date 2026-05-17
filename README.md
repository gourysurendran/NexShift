# NexShift 🚀
*Intelligent AI-Powered Workforce Optimization System*

NexShift is an enterprise-grade workforce management and shift-scheduling platform. It leverages **Mixed-Integer Linear Programming (MILP)** and **Reinforcement Learning** to generate highly optimized, cost-efficient, and human-centric employee schedules dynamically.

## 🌟 Key Features

### 🧠 Core Optimization Engine
- **AI Schedule Generation**: Uses Python's `PuLP` library to solve complex shift-assignment constraints (Morning, Evening, Night) against required workload demands.
- **Burnout Prevention**: Enforces a strict 12-hour minimum rest period between shifts, caps maximum weekly working hours, and prevents back-to-back night shifts.
- **Adaptive Reinforcement Learning**: The system tracks historical Overtime (OT) vs. Undertime (UT) and dynamically adjusts penalty weights in the objective function to balance workforce budgets over time.

### 🏢 Enterprise Workforce Management
- **Skill-Based Allocation**: Automatically tags and factors in employee skill sets (e.g., Security, Support, Management) when assigning shifts.
- **Multi-Branch Support**: Easily partition datasets and optimize schedules for localized branches (e.g., Main Branch, North Branch).
- **Payroll Integration**: Automatically calculates Base Pay and Overtime Pay (at 1.5x) using localized currency formatting (₹ INR).
- **Real-Time Sudden Absences**: Emergency shift-replacement allows managers to type in an absent employee's name and instantly recalculate the schedule to cover their missing shifts.

### 👥 HR & Employee Portals
- **Leave Management System**: Built-in approval workflow for submitting and approving PTO/Vacation. Approved leaves are automatically injected as hard absences into the AI scheduler.
- **Biometric Integration Sandbox**: Simulate employee ID check-ins and check-outs for automated attendance tracking.
- **AI Chatbot Assistant**: A floating, interactive widget that handles common HR queries, shift questions, and payroll concerns directly on the dashboard.

### 📅 Advanced Analytics & Export
- **Dynamic ICS Calendar Sync**: Instantly convert an optimized schedule into a downloadable `.ics` Calendar file that employees can add to their Google, Apple, or Outlook calendars.
- **Demand Forecasting**: Predictive analytics sandbox for forecasting future weekend workload spikes.
- **Excel Export**: Download the finalized AI schedule into a clean, formatted Excel file for external use.

---

## 🛠️ Technology Stack
* **Backend:** Python, Flask, Pandas, PuLP (MILP Solver)
* **Frontend:** HTML5, Vanilla JavaScript, CSS3 (Glassmorphism UI)
* **Visualizations:** Chart.js

---

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/NexShift.git
   cd NexShift
   ```

2. **Install the required dependencies:**
   Make sure you have Python installed, then run:
   ```bash
   pip install flask pandas pulp openpyxl
   ```

3. **Run the Application:**
   ```bash
   python app.py
   ```

4. **Access the Dashboard:**
   Open your browser and navigate to: `http://127.0.0.1:5000`

---

## 📂 Data Input Format (Excel)
NexShift requires an Excel file (`.xlsx`) with two primary sheets:
1. **Availability**: Contains `Name`, `Group`, `Skill`, `Branch`, `Hourly_Rate`, `Max_Hours`, and columns for each day of the week containing availability data.
2. **Demand**: Contains `Weekday` and columns for each group to dictate how many staff members are required per day.

*(A default dataset is provided in the application for immediate testing).*

---

## 📜 License
This project is licensed under the MIT License - see the LICENSE file for details.
