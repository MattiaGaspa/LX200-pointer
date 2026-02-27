import time
import re
import serial
import serial.tools.list_ports
from tkinter import *
from tkinter import ttk
from tkinter import messagebox

# Costanti predefinite
BAUD_RATE = 9600
TIMEOUT = 0.5
SLEEP_TIME = 0.05

commands = {
    "north":    [b":RG#", b":Mn#"],
    "south":    [b":RG#", b":Ms#"],
    "east":     [b":RG#", b":Me#"],
    "west":     [b":RG#", b":Mw#"],
    "stop":     [b":Q#"],
}

def get_ports():
    ports = [port for port in serial.tools.list_ports.comports() if port[2] != 'n/a']
    return sorted(ports)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Telescope pointer")
        try:
            self.root.iconbitmap("telescope.ico")
        except Exception as e:
            try:
                from tkinter import PhotoImage
                icon = PhotoImage(file="telescope.png")
                self.root.iconphoto(False, icon)
            except Exception:
                messagebox.showwarning("Warning", "Could not set window icon (telescope.ico).")
        self.root.resizable(False, False)
        self.conn = None
        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(column=0, row=0, sticky=(N, W, E, S))

        conn_frame = ttk.LabelFrame(main_frame, text=" Configuration ", padding="10")
        conn_frame.grid(column=0, row=0, columnspan=3, pady=10, sticky="ew")

        ttk.Label(conn_frame, text="Serial Port:").grid(column=0, row=0, padx=5)
        self.port_selection = ttk.Combobox(conn_frame, values=get_ports(), width=15)
        self.port_selection.grid(column=1, row=0, padx=5)

        self.btn_connect = ttk.Button(conn_frame, text="Connect", command=self.connect)
        self.btn_connect.grid(column=2, row=0, padx=5)

        track_frame = ttk.LabelFrame(main_frame, text=" Tracking Speed (Hz) ", padding="10")
        track_frame.grid(column=0, row=1, columnspan=3, pady=10, sticky="ew")

        ttk.Label(track_frame, text="Value (NNN.N):").grid(column=0, row=0, padx=5)
        self.tracking_var = StringVar(value="123.4")
        self.entry_tracking = ttk.Entry(track_frame, textvariable=self.tracking_var, width=10)
        self.entry_tracking.grid(column=1, row=0, padx=5)

        ctrl_frame = ttk.LabelFrame(main_frame, text=" Movement ", padding="10")
        ctrl_frame.grid(column=0, row=2, columnspan=3, pady=10)

        ttk.Button(ctrl_frame, text="▲", command=lambda: self.send_direction("north")).grid(column=1, row=0, pady=2)
        ttk.Button(ctrl_frame, text="◀", command=lambda: self.send_direction("east")).grid(column=0, row=1, padx=2)
        ttk.Button(ctrl_frame, text="STOP", command=lambda: self.send_direction("stop")).grid(column=1, row=1, padx=2)
        ttk.Button(ctrl_frame, text="▶", command=lambda: self.send_direction("west")).grid(column=2, row=1, padx=2)
        ttk.Button(ctrl_frame, text="▼", command=lambda: self.send_direction("south")).grid(column=1, row=2, pady=2)

        ttk.Button(main_frame, text="Exit", command=self.quit_app).grid(column=0, row=3, columnspan=3, pady=10)

    def validate_tracking(self, val):
        pattern = r"^\d{1,3}\.\d{1}$"
        return re.match(pattern, val)

    def connect(self):
        selected_port = self.port_selection.get()
        tracking_val = self.tracking_var.get()

        if not selected_port:
            messagebox.showwarning("Warning", "select a serial port.")
            return

        if not self.validate_tracking(tracking_val):
            messagebox.showerror("Error", "Tracking speed must be formatted as NNN.N (e.g. 123.4)")
            return

        try:
            self.conn = serial.Serial(selected_port, BAUD_RATE, timeout=TIMEOUT)

            self.conn.write(f":S{tracking_val}#".encode())
            time.sleep(SLEEP_TIME)
            if self.conn.read(1) == b"1":
                messagebox.showinfo("Success", f"Succesfully connected to {selected_port} and set tracking speed to {tracking_val}Hz")
                self.btn_connect.configure(state="disabled")
            else:
                messagebox.showerror("Error", f"Couldn't set tracking speed to {tracking_val}Hz'")

        except Exception as e:
            messagebox.showerror("Errore", f"Failed to connect: {str(e)}")

    def send_direction(self, direction):
        if self.conn and self.conn.is_open:
            try:
                for command in commands[direction]:
                    self.conn.write(command)
                    time.sleep(SLEEP_TIME)
                return self.conn.read(self.conn.in_waiting)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send {direction} to {self.conn}: {str(e)}\n")
                return ""
        else:
            messagebox.showwarning("Warning", "No connection established.")

    def quit_app(self):
        if self.conn and self.conn.is_open:
            self.conn.close()
        self.root.destroy()

if __name__ == "__main__":
    root = Tk()
    app = App(root)
    root.mainloop()
