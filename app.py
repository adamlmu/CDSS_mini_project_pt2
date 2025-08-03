# app.py
import tkinter as tk
from tkinter import ttk
from frames import add_patient, add_observation  # More can be added later

class CDSSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Clinical Decision Support System")
        self.geometry("800x600")

        # Sidebar
        self.sidebar = tk.Frame(self, width=200, bg="#f0f0f0")
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        # Main content area
        self.content = tk.Frame(self, bg="white")
        self.content.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        self.init_sidebar()

    def init_sidebar(self):
        actions = [
        ("Add Patient", self.load_add_patient),
        ("Add Observation", self.load_add_observation),
        ("Show History", self.load_show_history),
        ("Patient Status", self.load_patient_status),
        ("Retroactive Edit", self.load_retroactive_editor),
        ("Hemoglobin Intervals", self.load_hemo_intervals),
        ("Treatment Recommendation", self.load_treatment_view),
    ]

        for label, command in actions:
            b = tk.Button(self.sidebar, text=label, command=command)
            b.pack(padx=10, pady=5, fill=tk.X)

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def load_add_patient(self):
        self.clear_content()
        add_patient.render(self.content)

    def load_add_observation(self):
        self.clear_content()
        add_observation.render(self.content)
    

    def load_show_history(self):
        self.clear_content()
        from frames import show_history
        show_history.render(self.content)

    def load_patient_status(self):
        self.clear_content()
        from frames import patient_status
        patient_status.render(self.content)

    def load_retroactive_editor(self):
        self.clear_content()
        from frames import retroactive_editor
        retroactive_editor.render(self.content)

    def load_hemo_intervals(self):
        self.clear_content()
        from frames import hemo_interval
        hemo_interval.render(self.content)

    def load_treatment_view(self):
        self.clear_content()
        from frames import treatment_recommendation
        treatment_recommendation.render(self.content)


if __name__ == "__main__":
    app = CDSSApp()
    app.mainloop()
