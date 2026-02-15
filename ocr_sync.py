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
        self.root.title("OCR 同步助手 V2.0 (精度优化版)")
        self.root.geometry("850x650")
        
        self.srt_path = ""
        self.subs = []
        self.is_running = False
        self.captured_texts = []
        
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
        
        # OCR快捷键
        tk.Label(frame_config, text="OCR 快捷键:").grid(row=0, column=0, sticky="w")
        self.ent_hotkey = tk.Entry(frame_config, width=15)
        self.ent_hotkey.insert(0, "ctrl,alt,z")
        self.ent_hotkey.grid(row=0, column=1, padx=5, sticky="w")
        tk.Label(frame_config, text="(用逗号分隔按键)", fg="gray", font=("Arial", 8)).grid(row=0, column=2, sticky="w")

        # 毫秒偏移
        tk.Label(frame_config, text="触发偏移 (ms):").grid(row=1, column=0, pady=10, sticky="w")
        self.ent_offset = tk.Entry(frame_config, width=10)
        self.ent_offset.insert(0, "0")
        self.ent_offset.grid(row=1, column=1, sticky="w")
        tk.Label(frame_config, text="1000ms = 1秒。正数延迟触发，负数提前触发", fg="gray", font=("Arial", 8)).grid(row=1, column=2, sticky="w")

        # 启动延迟
        tk.Label(frame_config, text="准备时间 (秒):").grid(row=2, column=0, sticky="w")
        self.ent_prep = tk.Entry(frame_config, width=10)
        self.ent_prep.insert(0, "5")
        self.ent_prep.grid(row=2, column=1, sticky="w")
        tk.Label(frame_config, text="点击开始后，给你多少秒时间切换到视频窗口", fg="gray", font=("Arial", 8)).grid(row=2, column=2, sticky="w")

        # 控制按钮
        frame_btn = tk.Frame(self.root, pady=15)
        frame_btn.pack()
        
        self.btn_start = tk.Button(frame_btn, text="🚀 开始同步 (空格起跑)", command=self.start_task, 
                                  bg="#ddffdd", width=20, font=("Arial", 12, "bold"))
        self.btn_start.pack(side=tk.LEFT, padx=10)
        
        self.btn_stop = tk.Button(frame_btn, text="🛑 停止", command=self.stop_task, 
                                 bg="#ffdddd", width=10, font=("Arial", 12, "bold"), state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=10)
        
        tk.Button(frame_btn, text="💾 导出结果", command=self.export_txt).pack(side=tk.LEFT, padx=10)

        # 日志预览
        tk.Label(self.root, text="识别日志 (按时间轴排序):").pack(anchor="w", padx=10)
        self.txt_log = tk.Text(self.root, bg="#f8f8f8", font=("Consolas", 10))
        self.txt_log.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.lbl_status = tk.Label(self.root, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

    def load_srt(self):
        path = filedialog.askopenfilename(filetypes=[("SRT files", "*.srt")])
        if path:
            try:
                self.srt_path = path
                with open(path, 'r', encoding='utf-8') as f:
                    self.subs = list(srt.parse(f.read()))
                self.lbl_file.config(text=f"已加载: {os.path.basename(path)}", fg="blue")
                self.log(f"--- 成功加载字幕，共 {len(self.subs)} 条 ---")
            except Exception as e:
                messagebox.showerror("加载失败", f"SRT格式错误: {e}")

    def log(self, msg):
        self.txt_log.insert(tk.END, msg + "\n")
        self.txt_log.see(tk.END)

    def stop_task(self):
        self.is_running = False
        self.log("!!! 用户手动停止 !!!")
        self.btn_stop.config(state=tk.DISABLED)

    def start_task(self):
        if not self.subs:
            messagebox.showwarning("错误", "请先加载 SRT 文件！")
            return
        if self.is_running: return
        
        self.is_running = True
        self.captured_texts = []
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        
        threading.Thread(target=self.core_loop, daemon=True).start()

    def core_loop(self):
        try:
            # 读取配置
            hotkeys = [k.strip() for k in self.ent_hotkey.get().split(",")]
            offset_sec = float(self.ent_offset.get()) / 1000.0 # 毫秒转秒
            prep_time = int(self.ent_prep.get())
            
            # 1. 倒计时准备
            for i in range(prep_time, 0, -1):
                if not self.is_running: return
                self.lbl_status.config(text=f"倒计时 {i}... 请切换到视频窗口！")
                time.sleep(1)
            
            # 2. 空格起跑
            self.lbl_status.config(text="🔥 正在按下空格并启动计时...")
            pyautogui.press('space')
            
            # 【关键】按下空格的一瞬间，使用高精度计时器
            start_time_real = time.perf_counter()
            self.log(f"--- 计时开始：{datetime.datetime.now().strftime('%H:%M:%S')} ---")
            
            for sub in self.subs:
                if not self.is_running: break
                
                # 计算目标时刻
                target_point = sub.end.total_seconds() + offset_sec
                
                # 等待直到目标时刻
                while True:
                    if not self.is_running: return
                    elapsed = time.perf_counter() - start_time_real
                    if elapsed >= target_point:
                        break
                    # 短暂休眠防止CPU占用过高，但保持高频检查
                    time.sleep(0.001) 
                
                # 3. 触发 OCR
                pyautogui.hotkey(*hotkeys)
                
                # 预留给 OCR 软件处理的时间（可根据网速/机器性能调）
                # 如果你的OCR很快，可以调小
                time.sleep(0.5) 
                
                # 4. 读取剪贴板
                content = pyperclip.paste().strip()
                # 过滤掉重复项或空项（可选）
                self.captured_texts.append(content)
                
                # 更新 UI
                timestamp = str(sub.end).split('.')[0] # 格式化时间显示
                self.root.after(0, lambda c=content, t=timestamp: self.log(f"[{t}] {c}"))

            if self.is_running:
                self.root.after(0, lambda: messagebox.showinfo("完成", "所有时间轴已处理完毕！"))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"运行中出错: {e}"))
        finally:
            self.is_running = False
            self.root.after(0, lambda: self.btn_start.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.btn_stop.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.lbl_status.config(text="就绪"))

    def export_txt(self):
        if not self.captured_texts:
            messagebox.showwarning("提示", "当前没有捕获到任何文本")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.captured_texts))
            messagebox.showinfo("成功", "文本已保存。")

if __name__ == "__main__":
    root = tk.Tk()
    app = OCRSyncApp(root)
    root.mainloop()
