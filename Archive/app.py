import tkinter as tk

fenster = tk.Tk()

fenster.title("Stickeralbum 😄")

fenster.geometry("400x300")

text = tk.Label(
    fenster,
    text="Meine erste App 🚀",
    font=("Helvetica", 20)
)

text.pack(pady=100)

fenster.mainloop()