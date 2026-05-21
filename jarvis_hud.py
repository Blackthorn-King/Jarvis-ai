import tkinter as tk
from tkinter import ttk
import threading
import requests
import math
import random
import psutil
import subprocess
import webbrowser
import time
import os

# --- Optional: pyautogui for mouse/keyboard control ---
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# --- Optional: speech recognition ---
try:
    import speech_recognition as sr
    VOICE_INPUT_AVAILABLE = True
except ImportError:
    VOICE_INPUT_AVAILABLE = False

# --- Optional: pyttsx3 for voice output ---
try:
    import pyttsx3
    _tts = pyttsx3.init()
    _tts.setProperty("rate", 175)
    for v in _tts.getProperty("voices"):
        if any(n in v.name.lower() for n in ["male", "david", "mark"]):
            _tts.setProperty("voice", v.id)
            break
    VOICE_OUTPUT_AVAILABLE = True
except ImportError:
    VOICE_OUTPUT_AVAILABLE = False

# =========================================================
# CONFIG
# =========================================================
COLAB_SERVER_URL = "https://replace-worrier-bullfrog.ngrok-free.dev/"

# =========================================================
# JARVIS ULTRA HUD
# =========================================================
class JarvisUltraHUD:

    def __init__(self, root):
        self.root = root
        self.root.title("STARK INDUSTRIES - J.A.R.V.I.S.")
        self.root.geometry("1920x1080")
        self.root.configure(bg="#00050a")

        self.angle_cw = 0
        self.angle_ccw = 0
        self.pulse = 0
        self.is_thinking = False
        self.voice_mode = False

        self.cpu_history = [0] * 20
        self.ram_history = [0] * 20

        self.init_static_data()

        # =====================================================
        # MAIN HUD CANVAS
        # =====================================================
        self.canvas = tk.Canvas(root, bg="#000307", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # =====================================================
        # OVERLAY CHAT TERMINAL
        # =====================================================
        self.chat_outer = tk.Frame(root, bg="#00a2ff", bd=1)
        self.chat_outer.place(relx=0.5, rely=0.84, anchor="center", width=950, height=160)

        self.chat_frame = tk.Frame(self.chat_outer, bg="#000913")
        self.chat_frame.pack(fill="both", expand=True, padx=1, pady=1)

        self.chat_canvas = tk.Canvas(self.chat_frame, bg="#000913", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.chat_frame, orient="vertical", command=self.chat_canvas.yview)
        self.messages_frame = tk.Frame(self.chat_canvas, bg="#000913")

        self.messages_frame.bind(
            "<Configure>",
            lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))
        )

        self.chat_canvas.create_window((0, 0), window=self.messages_frame, anchor="nw", width=910)
        self.chat_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.chat_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.scrollbar.pack(side="right", fill="y")

        # =====================================================
        # INPUT PROMPT BAR + VOICE BUTTON
        # =====================================================
        self.input_outer = tk.Frame(root, bg="#00a2ff", bd=1)
        self.input_outer.place(relx=0.5, rely=0.935, anchor="center", width=950, height=38)

        self.input_inner = tk.Frame(self.input_outer, bg="#00050d")
        self.input_inner.pack(fill="both", expand=True, padx=1, pady=1)

        self.entry = tk.Entry(self.input_inner, font=("Consolas", 13), bg="#00050d", fg="#7dd3fc",
                              insertbackground="#00a2ff", bd=0)
        self.entry.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.entry.bind("<Return>", self.handle_query)

        self.voice_btn = tk.Button(
            self.input_inner, text="🎤", font=("Consolas", 14),
            bg="#00050d", fg="#005588", activebackground="#001a33",
            activeforeground="#00d2ff", bd=0, cursor="hand2",
            command=self.toggle_voice
        )
        self.voice_btn.pack(side="right", padx=6)

        self.add_message("SYSTEM INITIALIZATION COMPLETED. CORE TELEMETRY CHANNELS SECURED.", "jarvis")
        if not VOICE_INPUT_AVAILABLE:
            self.add_message("VOICE MODULE OFFLINE — pip install SpeechRecognition pyaudio pyttsx3", "jarvis")
        self.animate()

    def init_static_data(self):
        self.grid_nodes = []
        for _ in range(35):
            self.grid_nodes.append((random.randint(50, 1870), random.randint(50, 800)))

        self.matrix_streams = []
        for _ in range(16):
            self.matrix_streams.append({
                'x': random.randint(400, 1500),
                'y': random.randint(80, 650),
                'speed': random.randint(1, 3),
                'val': random.choice(["0x7F", "SYS_ON", "N_ENG", "ARC_V", "99.2", "LOC_LOK"])
            })

    # =========================================================
    # COMPUTER CONTROL
    # =========================================================
    def handle_computer_command(self, cmd):
        cmd_lower = cmd.lower().strip()

        if cmd_lower.startswith("open "):
            app = cmd[5:].strip()
            try:
                subprocess.Popen(app, shell=True)
                return f"OPENING {app.upper()}."
            except Exception as e:
                return f"COULD NOT OPEN {app}: {e}"

        if cmd_lower.startswith("search "):
            query = cmd[7:].strip()
            webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
            return f"SEARCHING: {query}"

        if cmd_lower.startswith("go to ") or cmd_lower.startswith("visit "):
            site = cmd.split(" ", 2)[-1].strip()
            if not site.startswith("http"):
                site = "https://" + site
            webbrowser.open(site)
            return f"NAVIGATING TO {site}"

        if "screenshot" in cmd_lower:
            if not GUI_AVAILABLE:
                return "PYAUTOGUI OFFLINE — pip install pyautogui"
            fname = f"screenshot_{int(time.time())}.png"
            pyautogui.screenshot(fname)
            return f"SCREENSHOT CAPTURED: {fname}"

        if cmd_lower.startswith("type "):
            if not GUI_AVAILABLE:
                return "PYAUTOGUI OFFLINE — pip install pyautogui"
            text = cmd[5:].strip()
            time.sleep(1)
            pyautogui.typewrite(text, interval=0.05)
            return f"TYPED: {text}"

        if cmd_lower.startswith("click"):
            if not GUI_AVAILABLE:
                return "PYAUTOGUI OFFLINE — pip install pyautogui"
            parts = cmd_lower.replace("click", "").strip().split()
            if len(parts) == 2:
                try:
                    pyautogui.click(int(parts[0]), int(parts[1]))
                    return f"CLICKED AT ({parts[0]}, {parts[1]})"
                except ValueError:
                    pass
            pyautogui.click()
            return "CLICK EXECUTED."

        if "scroll up" in cmd_lower:
            if not GUI_AVAILABLE:
                return "PYAUTOGUI OFFLINE — pip install pyautogui"
            pyautogui.scroll(5)
            return "SCROLLED UP."

        if "scroll down" in cmd_lower:
            if not GUI_AVAILABLE:
                return "PYAUTOGUI OFFLINE — pip install pyautogui"
            pyautogui.scroll(-5)
            return "SCROLLED DOWN."

        if "volume up" in cmd_lower:
            subprocess.run(["powershell", "-c",
                "(New-Object -comObject WScript.Shell).SendKeys([char]175)"], capture_output=True)
            return "VOLUME INCREASED."

        if "volume down" in cmd_lower:
            subprocess.run(["powershell", "-c",
                "(New-Object -comObject WScript.Shell).SendKeys([char]174)"], capture_output=True)
            return "VOLUME DECREASED."

        if "mute" in cmd_lower:
            subprocess.run(["powershell", "-c",
                "(New-Object -comObject WScript.Shell).SendKeys([char]173)"], capture_output=True)
            return "MUTE TOGGLED."

        if "lock" in cmd_lower and "screen" in cmd_lower:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "SCREEN LOCKED."

        if cmd_lower == "shutdown":
            subprocess.run(["shutdown", "/s", "/t", "30"])
            return "SHUTDOWN INITIATED. 30 SECONDS. TYPE 'CANCEL SHUTDOWN' TO ABORT."

        if cmd_lower == "cancel shutdown":
            subprocess.run(["shutdown", "/a"])
            return "SHUTDOWN ABORTED."

        if cmd_lower == "restart":
            subprocess.run(["shutdown", "/r", "/t", "30"])
            return "RESTART SEQUENCE INITIATED. 30 SECONDS."

        if cmd_lower in ["help", "commands", "what can you do"]:
            return (
                "AVAILABLE DIRECTIVES: open [app] | search [query] | go to [site] | "
                "screenshot | type [text] | click [x y] | scroll up/down | "
                "volume up/down | mute | lock screen | shutdown | restart"
            )

        return None

    # =========================================================
    # VOICE CONTROL
    # =========================================================
    def toggle_voice(self):
        if not VOICE_INPUT_AVAILABLE:
            self.add_message("VOICE MODULE OFFLINE — pip install SpeechRecognition pyaudio pyttsx3", "jarvis")
            return
        if self.voice_mode:
            self.voice_mode = False
            self.voice_btn.config(fg="#005588")
            self.add_message("VOICE INPUT DEACTIVATED.", "jarvis")
        else:
            self.voice_mode = True
            self.voice_btn.config(fg="#00d2ff")
            self.add_message("VOICE INPUT ACTIVATED. LISTENING...", "jarvis")
            threading.Thread(target=self.listen_loop, daemon=True).start()

    def listen_loop(self):
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 3000
        recognizer.dynamic_energy_threshold = True
        while self.voice_mode:
            try:
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = recognizer.listen(source, timeout=6, phrase_time_limit=15)
                text = recognizer.recognize_google(audio)
                self.root.after(0, self.process_voice_input, text)
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception:
                continue

    def process_voice_input(self, text):
        self.add_message(f"[VOICE] {text}", "user")
        self.is_thinking = True
        threading.Thread(target=self.process_query, args=(text,), daemon=True).start()

    def speak(self, text):
        if VOICE_OUTPUT_AVAILABLE and self.voice_mode:
            threading.Thread(target=lambda: (_tts.say(text), _tts.runAndWait()), daemon=True).start()

    # =========================================================
    # CHAT LOGIC
    # =========================================================
    def add_message(self, text, sender="user"):
        container = tk.Frame(self.messages_frame, bg="#000913")
        container.pack(fill="x", pady=3, padx=5)

        if sender == "user":
            bg_color = "#001a33"
            fg_color = "#eefaff"
            border_color = "#00d2ff"
            align_side = "right"
        else:
            bg_color = "#000f24"
            fg_color = "#8ae2ff"
            border_color = "#005588"
            align_side = "left"

        label = tk.Label(container, text=text, wraplength=650, justify="left",
                         font=("Consolas", 10), bg=bg_color, fg=fg_color,
                         padx=10, pady=6, relief="solid", bd=1,
                         highlightbackground=border_color)
        label.pack(side=align_side, padx=10)

        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def handle_query(self, event=None):
        query = self.entry.get().strip()
        if not query:
            return
        self.entry.delete(0, tk.END)
        self.add_message(query, "user")
        self.is_thinking = True
        threading.Thread(target=self.process_query, args=(query,), daemon=True).start()

    def process_query(self, query):
        # Check computer commands first
        result = self.handle_computer_command(query)
        if result:
            self.root.after(0, self.show_answer, result)
            return
        # Otherwise ask JARVIS AI
        self.fetch_ai(query)

    def fetch_ai(self, query):
        try:
            r = requests.post(f"{COLAB_SERVER_URL}/ask", json={"query": query}, timeout=60)
            answer = r.json().get("answer", "NO LOGICAL RESPONSE MATRIX RETURNED.")
        except Exception as e:
            answer = f"CONNECTION ERROR: UNABLE TO ESTABLISH COMPILER LINK.\n{e}"
        self.root.after(0, self.show_answer, answer)

    def show_answer(self, answer):
        self.is_thinking = False
        self.add_message(f"J.A.R.V.I.S.: {answer}", "jarvis")
        self.speak(answer)

    # =========================================================
    # GRAPHICS PIPELINE
    # =========================================================
    def draw_hud(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10 or h < 10:
            return

        cx = w // 2
        cy = h // 2 - 110

        c_neon = "#00d2ff"
        c_mid = "#005588"
        c_dark = "#00223A"
        c_dim = "#000a12"
        c_white = "#eefaff"

        for i in range(0, w, 60):
            self.canvas.create_line(i, 0, i, h, fill=c_dim, width=1)
        for i in range(0, h, 60):
            self.canvas.create_line(0, i, w, i, fill=c_dim, width=1)

        for node in self.grid_nodes:
            self.canvas.create_line(node[0]-3, node[1], node[0]+3, node[1], fill=c_dark)
            self.canvas.create_line(node[0], node[1]-3, node[0], node[1]+3, fill=c_dark)

        self.canvas.create_text(80, 45, text="CORE SYSTEM STATUS: ACTIVE", fill=c_neon, font=("Consolas", 10, "bold"), anchor="w")
        self.canvas.create_text(80, 62, text="SECURE FEED DIRECT LINK OVERRIDE", fill=c_mid, font=("Consolas", 8), anchor="w")
        self.canvas.create_text(w - 80, 45, text="STARK INDUSTRIES HUD", fill=c_white, font=("Orbitron", 14, "bold"), anchor="e")
        self.canvas.create_text(w - 80, 65, text="MARK LXXXV // MATRIX ENGINE V4.2", fill=c_mid, font=("Consolas", 9), anchor="e")

        # Voice status indicator
        if self.voice_mode:
            self.canvas.create_text(cx, 30, text="◉ VOICE ACTIVE", fill=c_neon, font=("Consolas", 10, "bold"))
        elif self.is_thinking:
            self.canvas.create_text(cx, 30, text="◌ PROCESSING...", fill=c_mid, font=("Consolas", 10))

        self.draw_arc_ring(cx, cy, 290, self.angle_cw, 40, c_mid, width=1)
        self.draw_arc_ring(cx, cy, 290, self.angle_cw + 90, 80, c_neon, width=2)
        self.draw_arc_ring(cx, cy, 290, self.angle_cw + 210, 50, c_dark, width=1)
        self.draw_arc_ring(cx, cy, 260, self.angle_ccw, 140, c_dark, width=4)
        self.draw_arc_ring(cx, cy, 260, self.angle_ccw + 160, 90, c_mid, width=2)

        self.canvas.create_oval(cx-230, cy-230, cx+230, cy+230, outline=c_mid, width=1, dash=(2, 8))
        self.canvas.create_oval(cx-200, cy-200, cx+200, cy+200, outline=c_dark, width=1)

        directions = [("N", 0), ("E", 90), ("S", 180), ("W", 270)]
        for label, d_angle in directions:
            rad_dir = math.radians(d_angle + self.angle_cw * 0.3)
            tx = cx + math.cos(rad_dir) * 215
            ty = cy + math.sin(rad_dir) * 215
            self.canvas.create_text(tx, ty, text=label, fill=c_mid, font=("Orbitron", 8, "bold"))

        pulse_r = 50 + (math.sin(self.pulse * 0.15) * 4)
        self.canvas.create_oval(cx-pulse_r, cy-pulse_r, cx+pulse_r, cy+pulse_r, outline=c_neon, width=2)
        self.canvas.create_oval(cx-35, cy-35, cx+35, cy+35, fill="#000b14", outline=c_mid, width=1)
        self.canvas.create_text(cx, cy, text="J.A.R.V.I.S.", fill=c_white, font=("Orbitron", 9, "bold"))

        for offset in range(0, 360, 45):
            rad = math.radians(offset + (self.angle_cw * 0.5))
            self.canvas.create_line(cx + math.cos(rad) * 70, cy + math.sin(rad) * 70,
                                    cx + math.cos(rad) * 180, cy + math.sin(rad) * 180,
                                    fill=c_mid, width=1, dash=(3, 12))

        for stream in self.matrix_streams:
            self.canvas.create_text(stream['x'], stream['y'], text=stream['val'], fill=c_dark, font=("Consolas", 8))

        cpu_usage = psutil.cpu_percent()
        ram_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')
        self.cpu_history.append(cpu_usage)
        self.cpu_history.pop(0)
        self.ram_history.append(ram_info.percent)
        self.ram_history.pop(0)

        battery = psutil.sensors_battery()
        bat_str = f"{battery.percent}%" if battery else "100% (AC)"
        bat_val = battery.percent if battery else 100

        sys_diagnostics = [
            (f"CPU LOAD // {cpu_usage}%", cpu_usage),
            (f"RAM UTIL // {ram_info.percent}%", ram_info.percent),
            (f"DISK ALLOC // {disk_info.percent}%", disk_info.percent),
            (f"POWER CORING // {bat_str}", bat_val)
        ]

        proc_count = len(psutil.pids())
        net_io = psutil.net_io_counters()
        sent_mb = net_io.bytes_sent / (1024 * 1024)
        recv_mb = net_io.bytes_recv / (1024 * 1024)

        hardware_telemetry = [
            (f"SYSTEM THREADS: {proc_count}", min(proc_count / 6, 100)),
            (f"TX DATAFLOW: {sent_mb:.1f} MB", min(sent_mb / 5, 100)),
            (f"RX DATAFLOW: {recv_mb:.1f} MB", min(recv_mb / 25, 100)),
            ("ARC COUPLING: STEADY", 100.0)
        ]

        voice_status = "ONLINE" if VOICE_INPUT_AVAILABLE else "OFFLINE"
        self.draw_hud_panel(50, 100, 330, 260, "LIVE SYS DIAGNOSTICS", sys_diagnostics, draw_graphs=True)
        self.draw_hud_panel(50, 390, 330, 230, "OS PROCESS METRICS", hardware_telemetry)
        self.draw_hud_panel(w - 380, 100, 330, 260, "NETWORK MATRIX CORES", [
            ("THINKING PIPELINE: RUNNING", 85.0),
            ("SERVER SYNC: ESTABLISHED", 100.0),
            ("ENCRYPTION INTERFACE: AES", 100.0),
            ("AI BACKEND PORT: NGROK LINK", 95.0)
        ])
        self.draw_hud_panel(w - 380, 390, 330, 230, "ENVIRONMENT STAT CORES", [
            (f"VOICE MODULE: {voice_status}", 100.0 if VOICE_INPUT_AVAILABLE else 0.0),
            ("RADAR SECTOR DIST: NOMINAL", 100.0),
            ("INTEGRITY COMPILER: ACTIVE", 100.0),
            ("J.A.R.V.I.S. THREAD: LIVE", 100.0)
        ])

        spacing = w // 10
        for i in range(1, 10):
            bx = i * spacing
            by = h - 55
            self.canvas.create_line(bx - 40, by, bx + 40, by, fill=c_mid, width=1)
            self.canvas.create_line(bx - 40, by - 10, bx - 40, by + 10, fill=c_mid, width=1)
            self.canvas.create_line(bx + 40, by - 10, bx + 40, by + 10, fill=c_mid, width=1)
            self.canvas.create_rectangle(bx - 15, by - 3, bx + 15, by + 3, fill=c_dim, outline=c_neon)
            self.canvas.create_text(bx, by - 20, text=f"STRK_{i:02}", fill=c_mid, font=("Consolas", 8, "bold"))

    def draw_arc_ring(self, cx, cy, radius, start_angle, extent, color, width=1):
        bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
        self.canvas.create_arc(bbox, start=start_angle, extent=extent, outline=color, width=width, style="arc")

    def draw_hud_panel(self, x, y, width, height, title, stat_tuples, draw_graphs=False):
        c_neon = "#00d2ff"
        c_mid = "#005588"

        self.canvas.create_rectangle(x, y, x + width, y + height, fill="#00050c", outline=c_mid, width=1)

        b_len = 12
        for (x1, y1, x2, y2) in [
            (x, y, x+b_len, y), (x, y, x, y+b_len),
            (x+width, y, x+width-b_len, y), (x+width, y, x+width, y+b_len),
            (x, y+height, x+b_len, y+height), (x, y+height, x, y+height-b_len),
            (x+width, y+height, x+width-b_len, y+height), (x+width, y+height, x+width, y+height-b_len)
        ]:
            self.canvas.create_line(x1, y1, x2, y2, fill=c_neon, width=2)

        self.canvas.create_text(x + 15, y + 20, text=title, anchor="w", fill=c_neon, font=("Orbitron", 10, "bold"))
        self.canvas.create_line(x + 15, y + 34, x + width - 15, y + 34, fill=c_mid, width=1)

        for idx, item in enumerate(stat_tuples):
            line_str, percentage = item
            ly = y + 55 + (idx * 26)
            self.canvas.create_rectangle(x + 15, ly - 3, x + 20, ly + 2, fill="", outline=c_neon, width=1)
            self.canvas.create_text(x + 32, ly, text=line_str, anchor="w", fill="#8ae2ff", font=("Consolas", 9))

            if draw_graphs and idx < 2:
                graph_buffer = self.cpu_history if idx == 0 else self.ram_history
                gx_start = x + width - 115
                gy_base = ly + 6
                points = []
                for step, val in enumerate(graph_buffer):
                    points.append((gx_start + (step * 5.5), gy_base - int((val / 100.0) * 16)))
                for p_idx in range(len(points) - 1):
                    self.canvas.create_line(points[p_idx][0], points[p_idx][1],
                                            points[p_idx+1][0], points[p_idx+1][1], fill=c_neon, width=1)
            else:
                bar_x = x + width - 95
                self.canvas.create_rectangle(bar_x, ly - 4, bar_x + 80, ly + 3, fill="#000d1a", outline=c_mid)
                fill_w = max(0, min(80, int((percentage / 100.0) * 80)))
                if fill_w > 0:
                    self.canvas.create_rectangle(bar_x, ly - 4, bar_x + fill_w, ly + 3, fill=c_neon, outline="")

    # =========================================================
    # ANIMATION LOOP
    # =========================================================
    def animate(self):
        self.angle_cw = (self.angle_cw + 1.2) % 360
        self.angle_ccw = (self.angle_ccw - 2.0) % 360
        self.pulse += 1

        if self.pulse % 4 == 0:
            for stream in self.matrix_streams:
                stream['y'] += stream['speed']
                if stream['y'] > 650:
                    stream['y'] = 80
                    stream['x'] = random.randint(400, 1500)

        self.draw_hud()
        self.root.after(33, self.animate)


if __name__ == "__main__":
    root = tk.Tk()
    app = JarvisUltraHUD(root)
    root.mainloop()
