import time
import serial
import serial.tools.list_ports
from tkinter import *
from tkinter import ttk
from tkinter import messagebox

BAUD_RATE = 9600
TIMEOUT = 0.5 # [s]
SLEEP_TIME = 0.05 # [s]
INPUT_DELAY = 50 # [ms]

movements = {
    "north":        [b":Mn#"],
    "south":        [b":Ms#"],
    "east":         [b":Me#"],
    "west":         [b":Mw#"],
    "stop_all":     [b":Q#"],
    "stop_north":   [b":Qn#"],
    "stop_south":   [b":Qs#"],
    "stop_east":    [b":Qe#"],
    "stop_west":    [b":Qw#"],
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

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Telescope pointer")
        try:
            self.root.iconbitmap(resource_path("telescope.ico"))
        except Exception as e:
            try:
                from tkinter import PhotoImage
                icon = PhotoImage(file=resource_path("telescope.ico"))
                self.root.iconphoto(False, icon)
            except Exception:
                messagebox.showwarning("Warning", "Could not set window icon.")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

        self.conn = None
        self.speed = StringVar(value="fast")
        self.curr_mov = {
            "north":    False,
            "south":    False,
            "east":     False,
            "west":     False,
        }
        self.stop_timers = {
            "north": None,
            "south": None,
            "east":  None,
            "west":  None
        }

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
        btn_north = ttk.Button(joy_container, text="▲")
        btn_west  = ttk.Button(joy_container, text="◀")
        btn_east  = ttk.Button(joy_container, text="▶")
        btn_south = ttk.Button(joy_container, text="▼")
        btn_north.grid(column=1, row=0, pady=2)
        btn_west.grid(column=0, row=1, padx=2)
        btn_east.grid(column=2, row=1, padx=2)
        btn_south.grid(column=1, row=2, pady=2)
        btn_north.bind("<ButtonPress-1>", lambda e: self.handle_press("north"))
        btn_north.bind("<ButtonRelease-1>", lambda e: self.handle_release("north"))
        btn_south.bind("<ButtonPress-1>", lambda e: self.handle_press("south"))
        btn_south.bind("<ButtonRelease-1>", lambda e: self.handle_release("south"))
        btn_east.bind("<ButtonPress-1>", lambda e: self.handle_press("east"))
        btn_east.bind("<ButtonRelease-1>", lambda e: self.handle_release("east"))
        btn_west.bind("<ButtonPress-1>", lambda e: self.handle_press("west"))
        btn_west.bind("<ButtonRelease-1>", lambda e: self.handle_release("west"))

    def setup_bindings(self):
        self.root.bind("<KeyPress-Up>", lambda e: self.handle_press("north"))
        self.root.bind("<KeyPress-Down>", lambda e: self.handle_press("south"))
        self.root.bind("<KeyPress-Left>", lambda e: self.handle_press("west"))
        self.root.bind("<KeyPress-Right>", lambda e: self.handle_press("east"))

        self.root.bind("<KeyRelease-Up>", lambda e: self.handle_release("north"))
        self.root.bind("<KeyRelease-Down>", lambda e: self.handle_release("south"))
        self.root.bind("<KeyRelease-Left>", lambda e: self.handle_release("west"))
        self.root.bind("<KeyRelease-Right>", lambda e: self.handle_release("east"))

        self.root.bind("<space>", lambda e: self.send_direction("stop_all"))
        self.root.bind("<Escape>", lambda e: self.send_direction("stop_all"))

    def handle_press(self, direction):
        if self.stop_timers.get(direction):
            self.root.after_cancel(self.stop_timers[direction])
            self.stop_timers[direction] = None

        self.send_direction(direction)

    def handle_release(self, direction):
        self.stop_timers[direction] = self.root.after(INPUT_DELAY, lambda: self.send_direction(f"stop_{direction}"))

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
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")

    def disconnect(self):
        try:
            if self.conn and self.conn.is_open:
                self.send_direction("stop_all")
                self.conn.close()
            self.btn_connect.configure(state="enabled")
            self.btn_disconnect.configure(state="disabled")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to disconnect: {str(e)}")

    def send_direction(self, direction):
        if direction.startswith("stop_"):
            if direction == "stop_all":
                for key in self.curr_mov.keys():
                    self.curr_mov[key] = False
            else:
                base_dir = direction.replace("stop_", "")
                if base_dir in self.curr_mov:
                    self.curr_mov[base_dir] = False

            try:
                self.run_commands(movements[direction])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send stop command: {e}")
            return

        if direction in self.curr_mov:
            if self.curr_mov[direction]:
                return

            self.curr_mov[direction] = True
            try:
                selected_speed = self.speed.get()
                self.run_commands(speeds[selected_speed])
                self.run_commands(movements[direction])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to send movement command: {e}")

    def run_commands(self, commands):
        if self.conn and self.conn.is_open:
            for command in commands:
                self.conn.write(command)
                self.root.update()
                time.sleep(SLEEP_TIME)

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
