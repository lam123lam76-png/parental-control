try:
 import tkinter as tk
except Exception as e:
 with open('test_err.txt', 'w') as f: f.write(str(e))

