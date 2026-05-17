import sys
import pandas as pd
sys.path.append(r'c:\Users\goury\OneDrive\Desktop\my proj\NexShift')
from optimization import run_optimization
import traceback

try:
    print("Running optimization...")
    # Using the default dataset
    res = run_optimization(r'c:\Users\goury\OneDrive\Desktop\my proj\NexShift\data\Employees_dataset.xlsx')
    print("Status:", res['status'])
    print("Total shifts:", res['total_shifts'])
    print("Success!")
except Exception as e:
    print("Error:", str(e))
    traceback.print_exc()
