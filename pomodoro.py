import time
import os
import json
import datetime
import threading
import sys

try:
    import customtkinter as ctk
except ImportError:
    print("customtkinter not installed.")
    print("Run: pip install customtkinter")
    sys.exit(1)

# ============================================================
# PATHS
# ============================================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FOLDER = os.path.join(BASE_DIR, "data")
LOG_FILE = os.path.join(DATA_FOLDER, "pomodoro_log.json")
SETTINGS_FILE = os.path.join(DATA_FOLDER, "pomodoro_settings.json")
os.makedirs(DATA_FOLDER, exist_ok=True)


def resource_path(relative_path):
    """
    Resolve a path to a bundled resource (like the .ico) so it works both
    when running as a plain .py script AND when frozen into a PyInstaller
    .exe (--onefile builds unpack bundled data into a temp _MEIPASS folder
    at runtime, which is NOT the same folder as the .exe itself).
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(BASE_DIR, relative_path)


# ============================================================
# DEFAULTS
# ============================================================
SESSIONS_BEFORE_LONG_BREAK = 4
DEFAULT_WORK = 25
DEFAULT_SHORT_BREAK = 5
DEFAULT_LONG_BREAK = 15

timer_running = False
timer_paused = False
timer_seconds = 0
total_seconds = 0
current_session = 1
current_label = ""
current_task = ""


# ============================================================
# DATA FUNCTIONS
# ============================================================
def save_session(task, minutes, status="completed"):
    entry = {
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.datetime.now().strftime("%I:%M %p"),
        "task": task,
        "minutes": minutes,
        "status": status
    }
    sessions = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            sessions = json.load(f)
    sessions.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(sessions, f, indent=2)


def get_daily_stats():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(LOG_FILE):
        return {"completed": 0, "cancelled": 0, "total_min": 0}
    with open(LOG_FILE, "r") as f:
        sessions = json.load(f)
    today_sessions = [s for s in sessions if s["date"] == today]
    completed = [s for s in today_sessions if s["status"] == "completed"]
    cancelled = [s for s in today_sessions if s["status"] == "cancelled"]
    return {
        "completed": len(completed),
        "cancelled": len(cancelled),
        "total_min": sum(s["minutes"] for s in today_sessions)
    }


def get_all_sessions(limit=50):
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        sessions = json.load(f)
    return sessions[-limit:][::-1]


def clear_all_history():
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)


def save_settings(work, short_break, long_break):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"work_min": work, "short_break_min": short_break, "long_break_min": long_break}, f)


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return DEFAULT_WORK, DEFAULT_SHORT_BREAK, DEFAULT_LONG_BREAK
    with open(SETTINGS_FILE, "r") as f:
        s = json.load(f)
    return (s.get("work_min", DEFAULT_WORK), s.get("short_break_min", DEFAULT_SHORT_BREAK), s.get("long_break_min", DEFAULT_LONG_BREAK))


# ============================================================
# TIMER LOGIC
# ============================================================
def format_time(seconds):
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def update_timer():
    global timer_running, timer_paused, timer_seconds
    if timer_running and not timer_paused:
        if timer_seconds > 0:
            timer_seconds -= 1
            timer_label.configure(text=format_time(timer_seconds))
            progress_bar.set((total_seconds - timer_seconds) / total_seconds)
            root.after(1000, update_timer)
        else:
            timer_running = False
            timer_label.configure(text="DONE!")
            progress_bar.set(1.0)
            beep()
            if "WORK" in current_label:
                save_session(current_task, total_seconds // 60, "completed")
            update_stats_display()
            show_done_screen()


def beep():
    for _ in range(3):
        print('\a', end='', flush=True)
        time.sleep(0.2)


def start_work_session():
    global timer_running, timer_paused, timer_seconds, total_seconds, current_label, current_task

    timer_running = False
    timer_paused = False

    task = task_entry.get().strip() or "Focus Session"
    current_task = task

    try:
        wm = int(work_entry.get())
    except ValueError:
        wm = DEFAULT_WORK
    wm = max(1, min(120, wm))

    timer_seconds = wm * 60
    total_seconds = timer_seconds
    current_label = f"WORK ({current_session})"

    status_label.configure(text=current_label, text_color="#e94560")
    timer_label.configure(text=format_time(timer_seconds))
    progress_bar.set(0)

    timer_running = True
    pause_btn.configure(state="normal", text="Pause")
    stop_btn.configure(state="normal")
    start_frame.pack_forget()
    control_frame.pack(pady=20)
    update_timer()


def start_break(break_type):
    global timer_running, timer_paused, timer_seconds, total_seconds, current_label

    timer_running = False
    timer_paused = False

    if break_type == "short":
        try:
            minutes = int(short_break_entry.get())
        except ValueError:
            minutes = DEFAULT_SHORT_BREAK
        label = "SHORT BREAK"
        color = "#4ecca3"
    else:
        try:
            minutes = int(long_break_entry.get())
        except ValueError:
            minutes = DEFAULT_LONG_BREAK
        label = "LONG BREAK"
        color = "#4ecca3"

    minutes = max(1, min(60, minutes))
    timer_seconds = minutes * 60
    total_seconds = timer_seconds
    current_label = label

    status_label.configure(text=label, text_color=color)
    timer_label.configure(text=format_time(timer_seconds))
    progress_bar.set(0)

    timer_running = True
    pause_btn.configure(state="normal", text="Pause")
    stop_btn.configure(state="normal")
    break_frame.pack_forget()
    control_frame.pack(pady=20)
    update_timer()


def toggle_pause():
    global timer_paused
    timer_paused = not timer_paused
    pause_btn.configure(text="Resume" if timer_paused else "Pause")
    status_label.configure(text="PAUSED" if timer_paused else current_label,
                          text_color="#f0c040" if timer_paused else "#e94560")


def stop_timer():
    global timer_running
    timer_running = False
    elapsed = total_seconds - timer_seconds
    actual_min = max(1, round(elapsed / 60))
    if "WORK" in current_label and actual_min >= 1:
        save_session(current_task, actual_min, "cancelled")
    update_stats_display()
    go_to_main()


def show_done_screen():
    control_frame.pack_forget()
    if "WORK" in current_label:
        done_frame.pack(pady=20)
        session_label.configure(text=f"Session {current_session} complete!")
    else:
        go_to_break_choice()


def go_to_break_choice():
    if current_session % SESSIONS_BEFORE_LONG_BREAK == 0:
        break_choice_label.configure(text="Long break time!")
        short_break_btn.pack_forget()
        long_break_btn.pack(pady=5)
    else:
        break_choice_label.configure(text="Break time!")
        long_break_btn.pack_forget()
        short_break_btn.pack(pady=5)
    done_frame.pack_forget()
    break_frame.pack(pady=20)


def next_session():
    global current_session
    current_session += 1
    go_to_main()


def go_to_main():
    for frame in [done_frame, break_frame, control_frame, settings_frame, history_frame]:
        frame.pack_forget()

    w, _, _ = load_settings()
    timer_label.configure(text=f"{w:02d}:00")
    progress_bar.set(0)
    status_label.configure(text="Ready", text_color="#888")

    start_frame.pack(pady=20)
    update_stats_display()


def update_stats_display():
    stats = get_daily_stats()
    hrs = round(stats["total_min"] / 60, 1)
    stats_label.configure(
        text=f"Completed: {stats['completed']}  |  Cancelled: {stats['cancelled']}  |  Total: {stats['total_min']} min ({hrs} hrs)"
    )


def open_settings():
    for frame in [start_frame, done_frame, break_frame, control_frame, history_frame]:
        frame.pack_forget()
    w, s, l = load_settings()
    work_entry.delete(0, "end")
    work_entry.insert(0, str(w))
    short_break_entry.delete(0, "end")
    short_break_entry.insert(0, str(s))
    long_break_entry.delete(0, "end")
    long_break_entry.insert(0, str(l))
    settings_frame.pack(pady=20)


def close_settings():
    global current_session
    try:
        w = int(work_entry.get())
        s = int(short_break_entry.get())
        l = int(long_break_entry.get())
    except ValueError:
        w, s, l = DEFAULT_WORK, DEFAULT_SHORT_BREAK, DEFAULT_LONG_BREAK
    w = max(1, min(120, w))
    s = max(1, min(60, s))
    l = max(1, min(60, l))
    save_settings(w, s, l)
    current_session = 1
    go_to_main()


def confirm_clear_history():
    dialog = ctk.CTkToplevel(root)
    dialog.title("Clear History")
    dialog.geometry("300x150")
    dialog.resizable(False, False)
    dialog.grab_set()

    ctk.CTkLabel(dialog, text="Clear all session history?",
                 font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(20, 5))
    ctk.CTkLabel(dialog, text="This cannot be undone.",
                 font=ctk.CTkFont(size=12), text_color="#888").pack()

    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    ctk.CTkButton(btn_frame, text="Cancel", width=100,
                  fg_color="transparent", border_width=1,
                  command=dialog.destroy).pack(side="left", padx=5)
    ctk.CTkButton(btn_frame, text="Clear", width=100,
                  fg_color="#e94560", hover_color="#c73e54",
                  command=lambda: [clear_all_history(), dialog.destroy(), open_history()]).pack(side="left", padx=5)
    btn_frame.pack(pady=20)


def open_history():
    for frame in [start_frame, done_frame, break_frame, control_frame, settings_frame]:
        frame.pack_forget()

    history_text.configure(state="normal")
    history_text.delete("0.0", "end")

    sessions = get_all_sessions(50)

    if not sessions:
        history_text.insert("end", "\n\n")
        history_text.insert("end", "     No sessions recorded yet.\n")
        history_text.insert("end", "     Start a pomodoro session to see it here!\n")
    else:
        total_done = sum(1 for s in sessions if s["status"] == "completed")
        total_canc = sum(1 for s in sessions if s["status"] == "cancelled")
        total_min = sum(s["minutes"] for s in sessions)

        history_text.insert("end", "\n")
        history_text.insert("end", f"     [DONE] {total_done} sessions  |  [CANC] {total_canc} sessions\n")
        history_text.insert("end", f"     Total: {total_min} min ({round(total_min/60, 1)} hrs) tracked\n")
        history_text.insert("end", "     " + "=" * 42 + "\n\n")

        current_date = None
        session_num = len(sessions)
        w, _, _ = load_settings()

        for s in sessions:
            date_str = s["date"]

            if date_str != current_date:
                current_date = date_str
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

                if date_str == today:
                    label = "TODAY"
                elif date_str == yesterday:
                    label = "YESTERDAY"
                else:
                    label = date_str

                history_text.insert("end", f"  ---- {label} ----\n\n")

            icon = "[DONE]" if s["status"] == "completed" else "[CANC]"
            time_str = s["time"]
            task_str = s["task"][:35] if len(s["task"]) > 35 else s["task"]
            mins = s["minutes"]

            bar_width = 10
            filled = min(bar_width, int((mins / w) * bar_width)) if w > 0 else bar_width
            bar = "|" * filled + "." * (bar_width - filled)

            line = f"  #{session_num} {icon} {time_str}\n"
            line += f"     {task_str}\n"
            line += f"     [{bar}] {mins} min\n\n"

            history_text.insert("end", line)
            session_num -= 1

    history_text.configure(state="disabled")
    history_frame.pack(pady=20)


def close_history():
    history_frame.pack_forget()
    go_to_main()


# ============================================================
# GUI SETUP
# ============================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()

root.title("Pomodoro Timer")
root.geometry("440x620")
root.resizable(False, False)

# Give the app its own identity in Windows so the taskbar shows OUR icon
# instead of grouping under the generic Python icon. Must run before the
# icon/window are shown, and only matters on Windows.
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Pomodoro.Timer.App")
except Exception:
    pass

# Window icon (title bar + taskbar). Use resource_path() rather than
# BASE_DIR directly: in a --onefile .exe, bundled data is unpacked to a
# temp _MEIPASS folder at runtime, which is NOT next to the .exe. Checking
# both locations means the icon shows whether it was bundled via
# --add-data or simply dropped in the same folder as the .exe.
icon_path = resource_path("Pomodoro_timer.ico")
if not os.path.exists(icon_path):
    icon_path = os.path.join(BASE_DIR, "Pomodoro_timer.ico")

if os.path.exists(icon_path):
    try:
        root.iconbitmap(default=icon_path)
    except Exception:
        pass

# Stats
stats = get_daily_stats()
hrs = round(stats["total_min"] / 60, 1)
stats_label = ctk.CTkLabel(root, text=f"Completed: {stats['completed']}  |  Cancelled: {stats['cancelled']}  |  Total: {stats['total_min']} min ({hrs} hrs)",
                           font=ctk.CTkFont(size=12), text_color="#888")
stats_label.pack(pady=(0, 10))

# Timer
w_init, _, _ = load_settings()
timer_label = ctk.CTkLabel(root, text=f"{w_init:02d}:00", font=ctk.CTkFont(size=56, weight="bold"))
timer_label.pack(pady=(10, 5))

# Progress
progress_bar = ctk.CTkProgressBar(root, width=320)
progress_bar.set(0)
progress_bar.pack(pady=(0, 5))

# Status
status_label = ctk.CTkLabel(root, text="Ready", font=ctk.CTkFont(size=14), text_color="#888")
status_label.pack(pady=(0, 20))

# --- START FRAME ---
start_frame = ctk.CTkFrame(root, fg_color="transparent")

ctk.CTkLabel(start_frame, text="What are you working on?", font=ctk.CTkFont(size=13)).pack()

task_entry = ctk.CTkEntry(start_frame, width=280, placeholder_text="Task name (optional)")
task_entry.pack(pady=(5, 10))
task_entry.bind("<Return>", lambda e: start_work_session())

w, _, _ = load_settings()
ctk.CTkLabel(start_frame, text=f"Work time: {w} min  |  Enter = start",
             font=ctk.CTkFont(size=11), text_color="#888").pack(pady=(0, 5))

ctk.CTkButton(start_frame, text="Start", width=200, height=40,
              fg_color="#e94560", hover_color="#c73e54",
              command=start_work_session).pack(pady=(0, 10))

btn_row = ctk.CTkFrame(start_frame, fg_color="transparent")
ctk.CTkButton(btn_row, text="History", width=90, height=30,
              fg_color="transparent", border_width=1,
              command=open_history).pack(side="left", padx=5)
ctk.CTkButton(btn_row, text="Settings", width=90, height=30,
              fg_color="transparent", border_width=1,
              command=open_settings).pack(side="left", padx=5)
btn_row.pack()

start_frame.pack(pady=20)

# --- CONTROL FRAME ---
control_frame = ctk.CTkFrame(root, fg_color="transparent")
pause_btn = ctk.CTkButton(control_frame, text="Pause", width=120, height=35,
                          fg_color="#f0c040", hover_color="#d4a830",
                          command=toggle_pause)
pause_btn.pack(side="left", padx=10)
stop_btn = ctk.CTkButton(control_frame, text="Stop", width=120, height=35,
                         fg_color="#555", hover_color="#444",
                         command=stop_timer)
stop_btn.pack(side="left", padx=10)

# --- DONE FRAME ---
done_frame = ctk.CTkFrame(root, fg_color="transparent")
session_label = ctk.CTkLabel(done_frame, text="", font=ctk.CTkFont(size=16, weight="bold"))
session_label.pack(pady=(0, 15))
ctk.CTkButton(done_frame, text="Next Session", width=180, height=35,
              fg_color="#4ecca3", hover_color="#3da882",
              command=next_session).pack(pady=5)
ctk.CTkButton(done_frame, text="Main Menu", width=180, height=35,
              fg_color="transparent", border_width=1,
              command=go_to_main).pack(pady=5)

# --- BREAK FRAME ---
break_frame = ctk.CTkFrame(root, fg_color="transparent")
break_choice_label = ctk.CTkLabel(break_frame, text="", font=ctk.CTkFont(size=16, weight="bold"))
break_choice_label.pack(pady=(0, 15))
short_break_btn = ctk.CTkButton(break_frame, text="Start Short Break", width=180, height=35,
                                fg_color="#4ecca3", hover_color="#3da882",
                                command=lambda: start_break("short"))
long_break_btn = ctk.CTkButton(break_frame, text="Start Long Break", width=180, height=35,
                               fg_color="#4ecca3", hover_color="#3da882",
                               command=lambda: start_break("long"))
ctk.CTkButton(break_frame, text="Skip Break", width=180, height=35,
              fg_color="transparent", border_width=1,
              command=next_session).pack(pady=5)

# --- SETTINGS FRAME ---
settings_frame = ctk.CTkFrame(root, fg_color="transparent")

ctk.CTkLabel(settings_frame, text="SETTINGS", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(0, 15))

ctk.CTkLabel(settings_frame, text="Work (minutes)", font=ctk.CTkFont(size=12)).pack()
work_entry = ctk.CTkEntry(settings_frame, width=80, justify="center")
work_entry.pack(pady=(5, 10))
w, _, _ = load_settings()
work_entry.insert(0, str(w))

ctk.CTkLabel(settings_frame, text="Short Break (minutes)", font=ctk.CTkFont(size=12)).pack()
short_break_entry = ctk.CTkEntry(settings_frame, width=80, justify="center")
short_break_entry.pack(pady=(5, 10))
_, s, _ = load_settings()
short_break_entry.insert(0, str(s))

ctk.CTkLabel(settings_frame, text="Long Break (minutes)", font=ctk.CTkFont(size=12)).pack()
long_break_entry = ctk.CTkEntry(settings_frame, width=80, justify="center")
long_break_entry.pack(pady=(5, 15))
_, _, l = load_settings()
long_break_entry.insert(0, str(l))

ctk.CTkButton(settings_frame, text="Save & Back", width=150, height=35,
              fg_color="#4ecca3", hover_color="#3da882",
              command=close_settings).pack()

# --- HISTORY FRAME ---
history_frame = ctk.CTkFrame(root, fg_color="transparent")

ctk.CTkLabel(history_frame, text="SESSION HISTORY", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 10))

history_text = ctk.CTkTextbox(history_frame, width=380, height=200,
                              font=ctk.CTkFont(size=12), wrap="word",
                              state="disabled",
                              fg_color="#1a1a2e",
                              text_color="#d0d0d0",
                              border_width=1,
                              border_color="#2a2a4a",
                              corner_radius=8)
history_text.pack(pady=(0, 10))

history_btn_row = ctk.CTkFrame(history_frame, fg_color="transparent")
ctk.CTkButton(history_btn_row, text="Back", width=100, height=30,
              fg_color="transparent", border_width=1,
              command=close_history).pack(side="left", padx=5)
ctk.CTkButton(history_btn_row, text="Clear All", width=100, height=30,
              fg_color="#e94560", hover_color="#c73e54",
              command=confirm_clear_history).pack(side="left", padx=5)
history_btn_row.pack()


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    root.mainloop()