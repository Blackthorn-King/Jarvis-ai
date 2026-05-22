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
import base64
from io import BytesIO

# --- Optional: pyautogui for computer control & vision ---
try:
    import pyautogui
    from PIL import Image
    pyautogui.FAILSAFE = True
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# --- Optional: speech recognition via sounddevice (no pyaudio/C++ needed) ---
try:
    import speech_recognition as sr
    import sounddevice as sd
    import numpy as np
    VOICE_INPUT_AVAILABLE = True
except ImportError:
    VOICE_INPUT_AVAILABLE = False

# --- Optional: voice output ---
try:
    import pyttsx3
    _tts = pyttsx3.init()
    _tts.setProperty("rate", 180)
    VOICE_OUTPUT_AVAILABLE = True
except ImportError:
    VOICE_OUTPUT_AVAILABLE = False

# =========================================================
# CONFIGURATION — update this with your ngrok URL
# =========================================================
CONFIG_FILE = os.path.join(os.path.dirname(__file__), ".jarvis_url")

def load_url():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return f.read().strip()
    return "https://replace-with-your-ngrok-url.ngrok-free.dev"

def save_url(url):
    with open(CONFIG_FILE, "w") as f:
        f.write(url)

COLAB_SERVER_URL = load_url()

class JarvisUltraHUD:
    def __init__(self, root):
        self.root = root
        self.root.title("STARK INDUSTRIES - J.A.R.V.I.S. OS")
        self.root.attributes("-fullscreen", True)
        self.root.configure(bg="#00050a")

        self.angle_cw = 0
        self.angle_ccw = 0
        self.pulse = 0
        self.is_thinking = False
        self.voice_mode = False
        self.cpu_history = [0] * 20
        self.ram_history = [0] * 20

        self.init_static_data()

        self.canvas = tk.Canvas(root, bg="#000307", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.setup_chat_ui()
        self.setup_input_ui()

        self.root.bind("<Escape>", lambda e: self.root.attributes("-fullscreen", False))
        self.root.bind("<F11>", lambda e: self.root.attributes("-fullscreen", True))

        self.add_message("SYSTEM INITIALIZATION COMPLETED. CORE TELEMETRY CHANNELS SECURED.", "jarvis")
        if not VOICE_INPUT_AVAILABLE:
            self.add_message("VOICE MODULE OFFLINE — run: pip install sounddevice numpy SpeechRecognition", "jarvis")
        self.animate()

    def init_static_data(self):
        self.grid_nodes = [(random.randint(50, 1870), random.randint(50, 800)) for _ in range(35)]
        self.matrix_streams = [{'x': random.randint(400, 1500), 'y': random.randint(80, 650),
                                 'speed': random.randint(1, 3),
                                 'val': random.choice(["0x7F", "SYS_ON", "ARC_V", "LOC_LOK"])} for _ in range(16)]

    def setup_chat_ui(self):
        self.chat_outer = tk.Frame(self.root, bg="#00a2ff", bd=1)
        self.chat_outer.place(relx=0.5, rely=0.82, anchor="center", width=1000, height=180)

        self.chat_frame = tk.Frame(self.chat_outer, bg="#000913")
        self.chat_frame.pack(fill="both", expand=True, padx=1, pady=1)

        self.chat_canvas = tk.Canvas(self.chat_frame, bg="#000913", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.chat_frame, orient="vertical", command=self.chat_canvas.yview)
        self.messages_frame = tk.Frame(self.chat_canvas, bg="#000913")

        self.messages_frame.bind("<Configure>", lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))
        self.chat_canvas.create_window((0, 0), window=self.messages_frame, anchor="nw", width=960)
        self.chat_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.chat_canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.scrollbar.pack(side="right", fill="y")

    def setup_input_ui(self):
        self.input_outer = tk.Frame(self.root, bg="#00a2ff", bd=1)
        self.input_outer.place(relx=0.5, rely=0.94, anchor="center", width=1000, height=40)

        self.input_inner = tk.Frame(self.input_outer, bg="#00050d")
        self.input_inner.pack(fill="both", expand=True, padx=1, pady=1)

        self.entry = tk.Entry(self.input_inner, font=("Consolas", 14), bg="#00050d", fg="#7dd3fc",
                              insertbackground="#00a2ff", bd=0)
        self.entry.pack(side="left", fill="both", expand=True, padx=10)
        self.entry.bind("<Return>", self.handle_query)

        self.voice_btn = tk.Button(self.input_inner, text="🎤", font=("Consolas", 14),
                                   bg="#00050d", fg="#005588", bd=0, command=self.toggle_voice)
        self.voice_btn.pack(side="right", padx=10)

    # =========================================================
    # VISION
    # =========================================================
    def capture_screen_b64(self):
        if not GUI_AVAILABLE:
            return None
        try:
            screenshot = pyautogui.screenshot()
            screenshot.thumbnail((1280, 720))
            buffered = BytesIO()
            screenshot.save(buffered, format="JPEG", quality=70)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Vision Error: {e}")
            return None

    # =========================================================
    # VOICE (uses sounddevice — no pyaudio/C++ needed)
    # =========================================================
    def toggle_voice(self):
        if not VOICE_INPUT_AVAILABLE:
            self.add_message("VOICE MODULE OFFLINE — pip install sounddevice numpy SpeechRecognition", "jarvis")
            return
        self.voice_mode = not self.voice_mode
        self.voice_btn.config(fg="#00d2ff" if self.voice_mode else "#005588")
        if self.voice_mode:
            self.add_message("VOICE INPUT ACTIVATED. LISTENING...", "jarvis")
            threading.Thread(target=self.listen_loop, daemon=True).start()
        else:
            self.add_message("VOICE INPUT DEACTIVATED.", "jarvis")

    def listen_loop(self):
        recognizer = sr.Recognizer()
        samplerate = 16000
        chunk_duration = 5

        while self.voice_mode:
            try:
                recording = sd.rec(
                    int(chunk_duration * samplerate),
                    samplerate=samplerate,
                    channels=1,
                    dtype='int16'
                )
                sd.wait()
                audio_data = sr.AudioData(recording.tobytes(), samplerate, 2)
                text = recognizer.recognize_google(audio_data)
                if text.strip():
                    self.root.after(0, self.process_query, text)
            except sr.UnknownValueError:
                continue
            except Exception:
                continue

    # =========================================================
    # BRAIN (AI + COMMANDS)
    # =========================================================
    def handle_query(self, event=None):
        query = self.entry.get().strip()
        if query:
            self.entry.delete(0, tk.END)
            self.process_query(query)

    def process_query(self, query):
        self.add_message(query, "user")
        self.is_thinking = True

        local_resp = self.handle_local_commands(query)
        if local_resp:
            self.show_answer(local_resp)
            return

        threading.Thread(target=self.fetch_ai, args=(query,), daemon=True).start()

    def fetch_ai(self, query):
        try:
            payload = {"query": query}
            vision_keywords = ["see", "look", "analyze", "screen", "screenshot", "vision"]
            if any(word in query.lower() for word in vision_keywords):
                img_b64 = self.capture_screen_b64()
                if img_b64:
                    payload["image"] = img_b64

            r = requests.post(f"{COLAB_SERVER_URL}/ask", json=payload, timeout=60)
            data = r.json()
            answer = data.get("answer", "No response from core.")

            action = data.get("action")
            if action:
                self.root.after(0, self.execute_motor_action, action)

            self.root.after(0, self.show_answer, answer)
        except Exception as e:
            self.root.after(0, self.show_answer, f"CORE LINK ERROR: {e}")

    def show_answer(self, answer):
        self.is_thinking = False
        self.add_message(f"J.A.R.V.I.S.: {answer}", "jarvis")
        if VOICE_OUTPUT_AVAILABLE and self.voice_mode:
            threading.Thread(target=lambda: (_tts.say(answer), _tts.runAndWait()), daemon=True).start()

    # =========================================================
    # MOTOR FUNCTIONS
    # =========================================================
    def handle_local_commands(self, cmd):
        c = cmd.lower()
        if "set url" in c or "update url" in c:
            parts = cmd.split()
            for p in parts:
                if "ngrok" in p or "http" in p:
                    save_url(p)
                    global COLAB_SERVER_URL
                    COLAB_SERVER_URL = p
                    return f"NGROK URL UPDATED TO: {p}"
        if "open browser" in c:
            webbrowser.open("https://google.com")
            return "OPENING DEFAULT BROWSER."
        if "volume up" in c:
            subprocess.run(["powershell", "-c", "(New-Object -comObject WScript.Shell).SendKeys([char]175)"], capture_output=True)
            return "VOLUME INCREASED."
        if "volume down" in c:
            subprocess.run(["powershell", "-c", "(New-Object -comObject WScript.Shell).SendKeys([char]174)"], capture_output=True)
            return "VOLUME DECREASED."
        if "mute" in c:
            subprocess.run(["powershell", "-c", "(New-Object -comObject WScript.Shell).SendKeys([char]173)"], capture_output=True)
            return "MUTE TOGGLED."
        if "screenshot" in c:
            if not GUI_AVAILABLE:
                return "PYAUTOGUI OFFLINE — pip install pyautogui Pillow"
            fname = f"screenshot_{int(time.time())}.png"
            pyautogui.screenshot(fname)
            return f"SCREENSHOT SAVED: {fname}"
        if "lock screen" in c:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "SCREEN LOCKED."
        if "shutdown" in c:
            return "SHUTDOWN SEQUENCE REQUIRES BIOMETRIC OVERRIDE."
        return None

    def execute_motor_action(self, action):
        atype = action.get("type")
        data = action.get("data", "")
        try:
            if atype == "open":
                subprocess.Popen(data, shell=True)
            elif atype == "type":
                time.sleep(1)
                pyautogui.write(data, interval=0.05)
            elif atype == "click":
                x, y = map(int, data.split(","))
                pyautogui.click(x, y)
            elif atype == "search":
                webbrowser.open(f"https://google.com/search?q={data}")
        except Exception as e:
            self.add_message(f"ACTION ERROR: {e}", "jarvis")

    # =========================================================
    # HUD GRAPHICS
    # =========================================================
    def add_message(self, text, sender="user"):
        color = "#eefaff" if sender == "user" else "#8ae2ff"
        lbl = tk.Label(self.messages_frame, text=f"[{sender.upper()}] {text}",
                       font=("Consolas", 11), bg="#000913", fg=color, wraplength=900, justify="left")
        lbl.pack(anchor="w" if sender != "user" else "e", padx=10, pady=2)
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def draw_hud(self):
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w < 10: return
        cx, cy = w // 2, h // 2 - 100

        c_neon = "#00d2ff"
        c_mid = "#005588"
        c_dark = "#001a33"

        for i in range(0, w, 60):
            self.canvas.create_line(i, 0, i, h, fill="#000a12", width=1)
        for i in range(0, h, 60):
            self.canvas.create_line(0, i, w, i, fill="#000a12", width=1)

        for node in self.grid_nodes:
            self.canvas.create_oval(node[0]-1, node[1]-1, node[0]+1, node[1]+1, fill=c_dark, outline="")

        for stream in self.matrix_streams:
            self.canvas.create_text(stream['x'], stream['y'], text=stream['val'], fill=c_dark, font=("Consolas", 8))

        self.draw_arc_ring(cx, cy, 220, self.angle_cw, 60, c_neon, 2)
        self.draw_arc_ring(cx, cy, 220, self.angle_cw + 180, 60, c_neon, 2)
        self.draw_arc_ring(cx, cy, 200, self.angle_ccw, 90, c_mid, 1)
        self.draw_arc_ring(cx, cy, 240, self.angle_cw * 0.5, 40, c_mid, 1)

        pulse_r = 60 + math.sin(self.pulse * 0.1) * 5
        self.canvas.create_oval(cx - pulse_r, cy - pulse_r, cx + pulse_r, cy + pulse_r, outline=c_neon, width=2)
        self.canvas.create_oval(cx - 40, cy - 40, cx + 40, cy + 40, fill="#000b14", outline=c_mid, width=1)
        self.canvas.create_text(cx, cy, text="J.A.R.V.I.S.", fill="white", font=("Orbitron", 12, "bold"))

        if self.voice_mode:
            self.canvas.create_text(cx, cy + 85, text="◉ VOICE ACTIVE", fill=c_neon, font=("Consolas", 10, "bold"))
        elif self.is_thinking:
            self.canvas.create_text(cx, cy + 85, text="◌ ANALYZING DATASETS...", fill=c_mid, font=("Consolas", 10))

        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.cpu_history.append(cpu); self.cpu_history.pop(0)
        self.ram_history.append(ram); self.ram_history.pop(0)

        self.draw_panel(50, 50, "SYSTEM CORE", [f"CPU: {cpu}%", f"RAM: {ram}%", "ARC REACTOR: STABLE"])
        self.draw_panel(50, 200, "VOICE & VISION", [
            f"VOICE: {'ACTIVE' if self.voice_mode else 'STANDBY'}",
            f"VOICE MODULE: {'ONLINE' if VOICE_INPUT_AVAILABLE else 'OFFLINE'}",
            f"VISION: {'ONLINE' if GUI_AVAILABLE else 'OFFLINE'}"
        ])

        self.canvas.create_text(w - 50, 50, text="STARK INDUSTRIES", fill=c_neon, font=("Orbitron", 14), anchor="e")
        self.canvas.create_text(w - 50, 75, text="MARK LXXXV // J.A.R.V.I.S. OS", fill=c_mid, font=("Consolas", 9), anchor="e")

    def draw_arc_ring(self, cx, cy, r, start, extent, color, width):
        self.canvas.create_arc(cx - r, cy - r, cx + r, cy + r, start=start, extent=extent,
                               outline=color, width=width, style="arc")

    def draw_panel(self, x, y, title, lines):
        self.canvas.create_rectangle(x, y, x + 260, y + 30 + len(lines) * 20 + 20,
                                     outline="#005588", fill="#00050a")
        self.canvas.create_text(x + 10, y + 15, text=title, fill="#00d2ff",
                                font=("Orbitron", 10, "bold"), anchor="w")
        for i, line in enumerate(lines):
            self.canvas.create_text(x + 10, y + 40 + (i * 20), text=line,
                                    fill="#8ae2ff", font=("Consolas", 9), anchor="w")

    def animate(self):
        self.angle_cw = (self.angle_cw + 2) % 360
        self.angle_ccw = (self.angle_ccw - 3) % 360
        self.pulse += 1
        if self.pulse % 4 == 0:
            for stream in self.matrix_streams:
                stream['y'] += stream['speed']
                if stream['y'] > 650:
                    stream['y'] = 80
                    stream['x'] = random.randint(400, 1500)
        self.draw_hud()
        self.root.after(30, self.animate)


if __name__ == "__main__":
    root = tk.Tk()
    app = JarvisUltraHUD(root)
    root.mainloop()
