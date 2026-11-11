import os
import platform
import shutil
import time

HOME = os.path.expanduser("~")


def get_user():
    return os.getenv("USER") or os.getenv("USERNAME") or "неизвестный_кто-то"


def is_root_or_admin():
    system = platform.system()
    if system in ("Linux", "Darwin"):
        uid = os.getuid()
        return uid == 0, f"UID = {uid}"
    if system == "Windows":
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin()), "проверка через Windows API"
        except Exception:
            return False, "не удалось проверить"
    return False, f"неизвестная система: {system}"


def get_groups():
    system = platform.system()
    if system in ("Linux", "Darwin"):
        try:
            import grp, pwd
            user = pwd.getpwuid(os.getuid()).pw_name
            groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]
            main = grp.getgrgid(pwd.getpwuid(os.getuid()).pw_gid).gr_name
            return sorted(set(groups + [main]))
        except Exception:
            return []
    if system == "Windows":
        domain = os.getenv("USERDOMAIN", "")
        return [domain] if domain else []
    return []


def writable_report():
    if platform.system() == "Windows":
        targets = {
            "Свой дом": HOME,
            "Текущая папка": os.getcwd(),
            "Системная (Windows)": r"C:\Windows\System32",
        }
    else:
        targets = {
            "Свой дом": HOME,
            "Текущая папка": os.getcwd(),
            "Системная (/etc)": "/etc",
            "Системная (/usr/bin)": "/usr/bin",
        }
    return {name: os.access(path, os.W_OK)
            for name, path in targets.items() if path and os.path.exists(path)}


def computer_status():
    """Что происходит на компьютере: память, диск, время работы."""
    lines = []
    # Память (Linux читаем из /proc/meminfo, Windows — через ctypes, иначе пропускаем)
    system = platform.system()
    if system == "Linux":
        try:
            info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        info[parts[0]] = int(parts[1].strip().split()[0])  # в КБ
            total_gb = info.get("MemTotal", 0) / (1024 * 1024)
            avail_gb = info.get("MemAvailable", 0) / (1024 * 1024)
            used_gb = total_gb - avail_gb
            lines.append(f"Память: занято {used_gb:.1f} ГБ из {total_gb:.1f} ГБ "
                         f"(свободно {avail_gb:.1f} ГБ)")
        except Exception:
            pass
    elif system == "Windows":
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong),
                            ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong),
                            ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong),
                            ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            total_gb = stat.ullTotalPhys / (1024 ** 3)
            avail_gb = stat.ullAvailPhys / (1024 ** 3)
            lines.append(f"Память: занято {total_gb - avail_gb:.1f} ГБ из {total_gb:.1f} ГБ "
                         f"(свободно {avail_gb:.1f} ГБ), загрузка {stat.dwMemoryLoad}%")
        except Exception:
            pass

    # Диск: тот, где лежит дом пользователя
    try:
        usage = shutil.disk_usage(HOME)
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        lines.append(f"Диск (где твой дом): свободно {free_gb:.1f} ГБ из {total_gb:.1f} ГБ")
    except Exception:
        pass

    # Время работы (Linux)
    if system == "Linux":
        try:
            with open("/proc/uptime") as f:
                up = float(f.read().split()[0])
            hours = int(up // 3600)
            minutes = int((up % 3600) // 60)
            lines.append(f"Компьютер работает: {hours} ч {minutes} мин")
        except Exception:
            pass

    # Время сейчас
    lines.append(f"Сейчас: {time.strftime('%d.%m.%Y %H:%M:%S')}")
    return lines


def build_report():
    user = get_user()
    admin, how = is_root_or_admin()
    groups = get_groups()

    lines = []
    lines.append("СИСТЕМНЫЙ ТЕСТЕР: КТО ТЫ ТАКОЙ И ЛОХ ЛИ?")
    lines.append("")
    lines.append(f"Пользователь: {user}")
    lines.append(f"Система:      {platform.system()} {platform.release()}")
    lines.append(f"Компьютер:    {platform.node()}")
    lines.append(f"Дом:          {HOME}")
    lines.append("")

    if admin:
        label = "АДМИН" if platform.system() == "Windows" else "ROOT"
        lines.append(f"ВЕРДИКТ: ты {label} — всемогущий!")
        lines.append("Но осторожно: rm в таких руках опасен.")
    else:
        lines.append("ВЕРДИКТ: обычный пользователь — права нормальные, не лох!")
    lines.append(f"(проверено так: {how})")
    lines.append("")

    if groups:
        lines.append(f"Группы: {', '.join(groups)}")
        if "sudo" in groups:
            lines.append("sudo: есть — админские полномочия по запросу.")
    lines.append("")

    lines.append("Куда можно писать:")
    for name, ok in writable_report().items():
        lines.append(f"  {name}: {'ДА' if ok else 'НЕТ'}")
    lines.append("")

    lines.append("Что происходит на компьютере:")
    lines.extend("  " + s for s in computer_status())

    return "\n".join(lines)


def show():
    report = build_report()
    print(report)  # дублируем в терминал на всякий случай
    try:
        import tkinter as tk
        from tkinter import scrolledtext

        root = tk.Tk()
        root.title("Тестер системы")
        root.geometry("560x480")

        text = scrolledtext.ScrolledText(root, font=("Courier", 10), wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.insert("1.0", report)
        text.configure(state="disabled")

        def close():
            root.destroy()

        btn = tk.Button(root, text="OK", width=12, command=close)
        btn.pack(pady=8)

        root.mainloop()
    except Exception as e:
        print(f"(Окно не показалось: {e} — смотри вывод в терминале)")


if __name__ == "__main__":
    show()

