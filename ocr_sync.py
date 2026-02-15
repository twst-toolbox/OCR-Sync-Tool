import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import srt
import pyautogui
import pyperclip
import time
import threading
import datetime
import os

class OCRSyncApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OCR 同步助手 V2.1 (带时间戳导出版)")
        self.root.geometry("850x650")
        
        self.srt_path = ""
        self.subs = []
        self.is_running = False
        self.captured_records = [] # 存储格式: {"time": "00:00:00", "text": "内容"}
        
        self._init_ui()
        
    def _init_ui(self):
        # 文件选择
        frame_file = tk.Frame(self.root, pady=10)
        frame_file.pack(fill=tk.X)
        tk.Button(frame_file, text="📂 加载 SRT 文件", command=self.load_srt).pack(side=tk.LEFT, padx=10)
        self.lbl_file = tk.Label(frame_file, text="请加载字幕文件...", fg="gray")
        self.lbl_file.pack(side=tk.LEFT)

        # 设置区
        frame_config = tk.LabelFrame(self.root, text="同步配置", padx=10, pady=10)
        frame_config.pack(fill=tk.X, padx=10)
        
        tk.Label(frame_config, text="OCR 快捷键:").grid(row=0, column=0, sticky="w")
        self.ent_hotkey = tk.Entry(frame_config, width=15)
        self.ent_hotkey.insert(0, "ctrl,alt,z")
        self.ent_hotkey.grid(row=0, column=1, padx=5, sticky="w")
        tk.Label(frame_config, text="(用逗号分隔按键)", fg="gray", font=("Arial", 8)).grid(row=0, column=2, sticky="w")

        tk.Label(frame_config, text="触发偏移 (ms):").grid(row=1, column=0, pady=10, sticky="w")
        self.ent_offset = tk.Entry(frame_config, width=10)
        self.ent_offset.insert(0, "-100") # 默认给个-100ms，补偿OCR响应延迟
        self.ent_offset.grid(row=1, column=1, sticky="w")

        tk.Label(frame_config, text="准备时间 (秒):").grid(row=2, column=0, sticky="w")
        self.ent_prep = tk.Entry(frame_config, width=10)
        self.ent_prep.insert(0, "5")
        self.ent_prep.grid(row=2, column=1, sticky="w")

        # 控制按钮
        frame_btn = tk.Frame(self.root, pady=15)
        frame_btn.pack()
        self.btn_start = tk.Button(frame_btn, text="🚀 开始同步 (空格起跑)", command=self.start_task, 
                                  bg="#ddffdd", width=20, font=("Arial", 12, "bold"))
        self.btn_start.pack(side=tk.LEFT, padx=10)
        self.btn_stop = tk.Button(frame_btn, text="🛑 停止", command=self.stop_task, 
                                 bg="#ffdddd", width=10, font=("Arial", 12, "bold"), state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=10)
        tk.Button(frame_btn, text="💾 导出带时间戳的TXT", command=self.export_txt).pack(side=tk.LEFT, padx=10)

        # 日志预览
        tk.Label(self.root, text="识别日志:").pack(anchor="w", padx=10)
        self.txt_log = tk.Text(self.root, bg="#f8f8f8", font=("Microsoft YaHei", 10))
        self.txt_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.lbl_status = tk.Label(self.root, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

    def format_time(self, td):
        """格式化时间为 [00:00:00]"""
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"

    def load_srt(self):
        path = filedialog.askopenfilename(filetypes=[("SRT files", "*.srt")])
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.subs = list(srt.parse(f.read()))
                self.lbl_file.config(text=f"已加载: {os.path.basename(path)}", fg="blue")
                self.log(f"--- 字幕加载成功 ({len(self.subs)}条) ---")
            except Exception as e:
                messagebox.showerror("错误", f"SRT解析失败: {e}")

    def log(self, msg):
        self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)

    def stop_task(self):
        self.is_running = False
        self.log("!!! 停止运行 !!!")

    def start_task(self):
        if not self.subs:
            messagebox.showwarning("错误", "请先加载 SRT 文件")
            return
        self.is_running = True
        self.captured_records = []
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        threading.Thread(target=self.core_loop, daemon=True).start()

    def core_loop(self):
        try:
            hotkeys = [k.strip() for k in self.ent_hotkey.get().split(",")]
            offset_sec = float(self.ent_offset.get()) / 1000.0
            prep_time = int(self.ent_prep.get())
            
            for i in range(prep_time, 0, -1):
                if not self.is_running: return
                self.lbl_status.config(text=f"准备起跑: {i}...")
                time.sleep(1)
            
            pyautogui.press('space')
            start_time_real = time.perf_counter()
            self.log("--- 计时启动 ---")
            
            for sub in self.subs:
                if not self.is_running: break
                
                target_point = sub.end.total_seconds() + offset_sec
                while time.perf_counter() - start_time_real < target_point:
                    if not self.is_running: return
                    time.sleep(0.001)
                
                # 触发 OCR
                pyautogui.hotkey(*hotkeys)
                
                # 等待 OCR 响应（如果文本多，建议设为 0.6 或 0.7）
                time.sleep(0.6)
                
                # 抓取并记录
                content = pyperclip.paste().strip()
                ts_str = self.format_time(sub.end)
                
                # 存储数据
                self.captured_records.append({"time": ts_str, "text": content})
                
                # UI 显示
                self.root.after(0, lambda t=ts_str, c=content: self.log(f"{t} {c}"))

            if self.is_running:
                self.root.after(0, lambda: messagebox.showinfo("完成", "时间轴提取完毕"))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.btn_start.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_stop.config(state=tk.DISABLED))

    def export_txt(self):
        if not self.captured_records:
            messagebox.showwarning("提示", "没有捕获到内容")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                for rec in self.captured_records:
                    # 格式: [00:02:22] 识别到的内容
                    f.write(f"{rec['time']} {rec['text']}\n")
            messagebox.showinfo("成功", "保存成功！")

if __name__ == "__main__":
    root = tk.Tk()
    app = OCRSyncApp(root)
    root.mainloop()
