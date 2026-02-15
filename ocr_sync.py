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
        self.root.title("OCR 同步助手 V1.0")
        self.root.geometry("800x600")
        
        self.srt_path = ""
        self.subs = []
        self.is_running = False
        self.captured_texts = []
        
        self._init_ui()
        
    def _init_ui(self):
        # 第一行：文件选择
        frame_file = tk.Frame(self.root, pady=10)
        frame_file.pack(fill=tk.X)
        tk.Button(frame_file, text="📂 选择 SRT 字幕文件", command=self.load_srt).pack(side=tk.LEFT, padx=10)
        self.lbl_file = tk.Label(frame_file, text="未选择文件", fg="gray")
        self.lbl_file.pack(side=tk.LEFT)

        # 第二行：设置区
        frame_config = tk.LabelFrame(self.root, text="设置", padx=10, pady=10)
        frame_config.pack(fill=tk.X, padx=10)
        
        tk.Label(frame_config, text="OCR 快捷键:").grid(row=0, column=0)
        self.ent_hotkey = tk.Entry(frame_config, width=15)
        self.ent_hotkey.insert(0, "ctrl,alt,z") # 默认快捷键，用逗号隔开
        self.ent_hotkey.grid(row=0, column=1, padx=5)
        tk.Label(frame_config, text="(例如: ctrl,alt,a)", fg="gray", font=("Arial", 8)).grid(row=0, column=2)

        tk.Label(frame_config, text="触发偏移 (秒):").grid(row=1, column=0, pady=5)
        self.ent_offset = tk.Entry(frame_config, width=10)
        self.ent_offset.insert(0, "0.0")
        self.ent_offset.grid(row=1, column=1)
        tk.Label(frame_config, text="+代表延迟按键, -代表提前", fg="gray", font=("Arial", 8)).grid(row=1, column=2)

        # 第三行：控制按钮
        frame_btn = tk.Frame(self.root, pady=10)
        frame_btn.pack()
        self.btn_start = tk.Button(frame_btn, text="🚀 开始同步读取", command=self.start_task, bg="#ddffdd", width=20, font=("Arial", 12, "bold"))
        self.btn_start.pack(side=tk.LEFT, padx=5)
        tk.Button(frame_btn, text="💾 导出 TXT", command=self.export_txt).pack(side=tk.LEFT, padx=5)

        # 第四行：实时预览区
        tk.Label(self.root, text="实时抓取结果:").pack(anchor="w", padx=10)
        self.txt_log = tk.Text(self.root, bg="#f0f0f0", padx=5, pady=5)
        self.txt_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.lbl_status = tk.Label(self.root, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

    def load_srt(self):
        path = filedialog.askopenfilename(filetypes=[("SRT files", "*.srt")])
        if path:
            self.srt_path = path
            with open(path, 'r', encoding='utf-8') as f:
                self.subs = list(srt.parse(f.read()))
            self.lbl_file.config(text=os.path.basename(path), fg="black")
            self.log(f"成功加载字幕，共 {len(self.subs)} 条记录。")

    def log(self, msg):
        self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)

    def start_task(self):
        if not self.subs:
            messagebox.showwarning("错误", "请先加载 SRT 文件！")
            return
        if self.is_running: return
        
        self.is_running = True
        self.btn_start.config(state=tk.DISABLED, text="正在运行...")
        threading.Thread(target=self.core_loop, daemon=True).start()

    def core_loop(self):
        try:
            # 1. 准备按键
            hotkeys = [k.strip() for k in self.ent_hotkey.get().split(",")]
            offset = float(self.ent_offset.get())
            
            # 2. 倒计时（给用户时间切换回视频播放器）
            for i in range(5, 0, -1):
                self.lbl_status.config(text=f"请切换到视频并准备播放！倒计时 {i}...")
                time.sleep(1)
            
            self.lbl_status.config(text="🔥 同步中！请点击播放视频！")
            start_time_real = time.time()
            
            for sub in self.subs:
                if not self.is_running: break
                
                # 计算目标时间点（SRT结束时间 + 偏移量）
                target_seconds = sub.end.total_seconds() + offset
                
                # 等待直到到达目标时间
                while True:
                    elapsed = time.time() - start_time_real
                    if elapsed >= target_seconds:
                        break
                    time.sleep(0.01) # 高频率扫描保证精确度
                
                # 执行按键模拟
                pyautogui.hotkey(*hotkeys)
                
                # 等待OCR软件处理并复制（约0.5秒）
                time.sleep(0.6)
                
                # 捕获剪贴板
                new_text = pyperclip.paste().strip()
                self.captured_texts.append(new_text)
                self.root.after(0, lambda t=new_text, i=sub.index: self.log(f"[{i}] {t}"))
                
            self.root.after(0, lambda: messagebox.showinfo("完成", "所有时间点已触发完毕！"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.btn_start.config(state=tk.NORMAL, text="🚀 开始同步读取"))

    def export_txt(self):
        if not self.captured_texts:
            messagebox.showwarning("空", "没有捕获到文字内容")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.captured_texts))
            messagebox.showinfo("成功", "文件已导出。")

if __name__ == "__main__":
    root = tk.Tk()
    app = OCRSyncApp(root)
    root.mainloop()
