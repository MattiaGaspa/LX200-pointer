import time
import re
import serial
import serial.tools.list_ports
from tkinter import *
from tkinter import ttk
from tkinter import messagebox

BAUD_RATE = 9600
TIMEOUT = 0.5
SLEEP_TIME = 0.05

movements = {
    "north":    [b":Mn#"],
    "south":    [b":Ms#"],
    "east":     [b":Me#"],
    "west":     [b":Mw#"],
    "stop":     [b":Q#"],
}
speeds = {
    "slowest":  [b":RG#"],
    "slow":     [b":RC#"],
    "fast":     [b":RM#"],
    "fastest":  [b":RS#"],
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
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.conn = None
        self.speed = StringVar(value="fast")
        self.setup_ui()
        self.setup_bindings()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(column=0, row=0, sticky=(N, W, E, S))

        conn_frame = ttk.Frame(main_frame)
        conn_frame.grid(column=0, row=0, columnspan=3, pady=2, sticky="ew")
        conn_frame.columnconfigure(1, weight=1)
        ttk.Label(conn_frame, text="Port:").grid(column=0, row=0, padx=5)
        self.port_selection = ttk.Combobox(conn_frame, postcommand=self.update_ports, state="readonly")
        self.port_selection.grid(column=1, row=0, padx=5, sticky="ew")
        available_ports = get_ports()
        if available_ports:
            self.port_selection['values'] = available_ports
            self.port_selection.current(0)
        button_container = ttk.Frame(conn_frame)
        button_container.grid(column=0, row=1, columnspan=2, pady=2)
        self.btn_connect = ttk.Button(button_container, text="Connect", command=self.connect)
        self.btn_connect.pack(side=LEFT, padx=5)
        self.btn_disconnect = ttk.Button(button_container, text="Disconnect", command=self.disconnect)
        self.btn_disconnect.pack(side=LEFT, padx=5)
        self.btn_disconnect.configure(state="disabled")

        speed_frame = ttk.Frame(main_frame)
        speed_frame.grid(column=0, row=1, columnspan=3, pady=2, sticky="ew")
        for i, speed_name in enumerate(speeds.keys()):
            ttk.Radiobutton(
                speed_frame,
                text=speed_name,
                variable=self.speed,
                value=speed_name,
            ).grid(column=i, row=0, padx=10)

        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.grid(column=0, row=2, columnspan=3, pady=2, sticky="ew")
        joy_container = ttk.Frame(ctrl_frame)
        joy_container.pack(expand=True)
        ttk.Button(joy_container, text="▲", command=lambda: self.send_direction("north")).grid(column=1, row=0, pady=2)
        ttk.Button(joy_container, text="◀", command=lambda: self.send_direction("east")).grid(column=0, row=1, padx=2)
        ttk.Button(joy_container, text="STOP", command=lambda: self.send_direction("stop")).grid(column=1, row=1, padx=2)
        ttk.Button(joy_container, text="▶", command=lambda: self.send_direction("west")).grid(column=2, row=1, padx=2)
        ttk.Button(joy_container, text="▼", command=lambda: self.send_direction("south")).grid(column=1, row=2, pady=2)

    def setup_bindings(self):
        self.root.bind("<Up>", lambda e: self.send_direction("north"))
        self.root.bind("<Down>", lambda e: self.send_direction("south"))
        self.root.bind("<Left>", lambda e: self.send_direction("east"))
        self.root.bind("<Right>", lambda e: self.send_direction("west"))
        self.root.bind("<space>", lambda e: self.send_direction("stop"))
        self.root.bind("<Escape>", lambda e: self.send_direction("stop"))

    def connect(self):
        selected_port = self.port_selection.get().split(' - ')[0]
        if not selected_port:
            messagebox.showwarning("Warning", "Select a serial port.")
            return

        try:
            self.conn = serial.Serial(selected_port, BAUD_RATE, timeout=TIMEOUT)
            self.btn_connect.configure(state="disabled")
            self.btn_disconnect.configure(state="enabled")
        except Exception as e:
            messagebox.showerror("Errore", f"Failed to connect: {str(e)}")

    def disconnect(self):
        try:
            self.conn.close()
            self.btn_connect.configure(state="enabled")
            self.btn_disconnect.configure(state="disabled")
        except Exception as e:
            messagebox.showerror("Errore", f"Failed to disconnect: {str(e)}")

    def send_direction(self, direction):
        if self.conn and self.conn.is_open:
            try:
                selected_speed = self.speed.get()
                if direction != "stop":
                    for command in speeds[selected_speed]:
                        self.conn.write(command)
                        time.sleep(SLEEP_TIME)
                for command in movements[direction]:
                    self.conn.write(command)
                    time.sleep(SLEEP_TIME)
                return self.conn.read(self.conn.in_waiting)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send {direction} to {self.conn}: {str(e)}\n")
                return ""
        else:
            messagebox.showwarning("Warning", "No connection established.")

    def update_ports(self):
        self.port_selection['values'] = get_ports()

    def quit_app(self):
        if self.conn and self.conn.is_open:
            self.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = Tk()
    app = App(root)
    root.mainloop()
