import tkinter as tk
root = tk.Tk()
root.title('Test Window')
root.geometry('200x200')
root.after(3000, root.destroy)
root.mainloop()

