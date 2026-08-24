import tkinter as tk
root = tk.Tk()
root.title('Test')
root.update()
root.after(1000, root.destroy)
root.mainloop()
