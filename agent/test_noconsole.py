import tkinter as tk
try:
 root = tk.Tk()
 root.title('Test')
 root.after(100, root.destroy)
 root.mainloop()
 with open('test_ok.txt', 'w') as f: f.write('OK')
except Exception as e:
 with open('test_err.txt', 'w') as f: f.write(str(e))

