import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import datetime
import requests
import configparser
from pathlib import Path

class MusicDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Soulseek Music Downloader")
        self.root.geometry("1000x800")
        
        # Force dark mode
        self.dark_mode = True
        
        # Initialize configuration
        self.config = configparser.ConfigParser()
        self.config_file = Path.home() / ".musicdownloader.ini"
        self._ensure_config_exists()
        self.load_config()

        self.style = ttk.Style()
        self.set_theme()

        self.create_widgets()
        self.animate_status()

    def _ensure_config_exists(self):
        """Create config file with all required keys if it doesn't exist"""
        if not self.config_file.exists():
            self.config['DEFAULT'] = {
                'spotify_client_id': '',
                'spotify_client_secret': '',
                'soulseek_username': '',
                'soulseek_password': '',
                'download_folder': str(Path.home() / 'Music'),
                'sldl_path': '',
                'obscurity_threshold': '30',
                'max_obscure_tracks': '30'
            }
            with open(self.config_file, 'w') as f:
                self.config.write(f)

    def load_config(self):
        """Load configuration from file"""
        self.config.read(self.config_file)

    def set_theme(self):
        # Dark theme colors
        bg_color = "#121212"  # Main background
        fg_color = "#FFFFFF"  # Text color
        entry_bg = "#1e1e1e"  # Entry fields
        btn_bg = "#1c1c1c"    # Buttons
        hover_bg = "#333333"  # Button hover
        accent_color = "#44ff44"  # Status animation
        tab_bg = "#1e1e1e"    # Tab background
        selected_tab_bg = "#121212"  # Selected tab

        # Configure root window
        self.root.configure(bg=bg_color)
        
        # Style configuration
        self.style.theme_use('clam')
        
        # Main styles
        self.style.configure(".", background=bg_color, foreground=fg_color, font=("Segoe UI", 10))
        self.style.configure("TLabel", background=bg_color, foreground=fg_color)
        self.style.configure("TButton", background=btn_bg, foreground=fg_color, relief="flat")
        self.style.map("TButton", background=[("active", hover_bg)], foreground=[("active", fg_color)])
        self.style.configure("TEntry", fieldbackground=entry_bg, foreground=fg_color, insertbackground=fg_color)
        self.style.configure("TRadiobutton", background=bg_color, foreground=fg_color)
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("TLabelframe", background=bg_color, foreground=fg_color)
        self.style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color)
        self.style.configure("TNotebook", background=tab_bg)
        self.style.configure("TNotebook.Tab", background=tab_bg, foreground=fg_color, padding=[10, 5])
        self.style.map("TNotebook.Tab", background=[("selected", selected_tab_bg)])
        
        # Listbox style
        self.style.element_create("Custom.Listbox.field", "from", "clam")
        self.style.layout("Custom.Listbox", [
            ('Custom.Listbox.field', {'sticky': 'nswe', 'children': [
                ('Listbox', {'sticky': 'nswe'})
            ]})
        ])
        self.style.configure("Custom.Listbox", background=entry_bg, foreground=fg_color)

    def create_widgets(self):
        # Create main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill="both", expand=True)

        # Create tabs
        self.create_download_tab()
        self.create_obscurify_tab()
        self.create_settings_tab()

        # Status box at bottom
        self.status_box = tk.Text(self.main_frame, height=10, wrap="word", relief="flat", 
                                font=("Consolas", 10), bg="#1e1e1e", fg="#FFFFFF",
                                insertbackground="#FFFFFF")
        self.status_box.pack(fill="x", padx=20, pady=(0, 20))

    def create_download_tab(self):
        """Create the main download tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Download")

        # Mode selection
        mode_frame = ttk.LabelFrame(tab, text="Download Mode", padding=10)
        mode_frame.pack(fill="x", padx=5, pady=5)

        self.mode = tk.StringVar(value="spotify")
        modes = [
            ("Spotify Playlist", "spotify"),
            ("YouTube URL", "youtube"),
            ("CSV File", "csv"),
            ("Last.fm Recommended", "lastfm"),
            ("Spotify Weekly", "weekly"),
            ("Obscure (Spotify)", "obscurify")
        ]

        for idx, (text, value) in enumerate(modes):
            rb = ttk.Radiobutton(mode_frame, text=text, variable=self.mode, value=value)
            rb.grid(row=idx, column=0, sticky="w", pady=2)

        # Input section
        input_frame = ttk.LabelFrame(tab, text="Input", padding=10)
        input_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(input_frame, text="Input (Playlist ID/URL/CSV etc):").grid(row=0, column=0, sticky="w")
        self.input_entry = ttk.Entry(input_frame, width=60)
        self.input_entry.grid(row=1, column=0, columnspan=2, sticky="we", pady=5)

        # Action buttons
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", padx=5, pady=10)

        self.download_button = ttk.Button(btn_frame, text="▶ Download Songs", command=self.threaded_download)
        self.download_button.pack(side="left", padx=5)

    def create_obscurify_tab(self):
        """Create the Obscurify-specific tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Obscurify")

        # Settings frame
        settings_frame = ttk.LabelFrame(tab, text="Obscurify Settings", padding=10)
        settings_frame.pack(fill="x", padx=5, pady=5)

        # Obscurity threshold
        ttk.Label(settings_frame, text="Obscurity Threshold (0-100, lower is more obscure):").grid(row=0, column=0, sticky="w")
        self.obscurity_threshold = tk.StringVar(value=self.config['DEFAULT'].get('obscurity_threshold', '30'))
        threshold_entry = ttk.Entry(settings_frame, textvariable=self.obscurity_threshold, width=5)
        threshold_entry.grid(row=0, column=1, sticky="w", padx=5)

        # Max tracks to fetch
        ttk.Label(settings_frame, text="Maximum tracks to fetch:").grid(row=1, column=0, sticky="w")
        self.max_obscure_tracks = tk.StringVar(value=self.config['DEFAULT'].get('max_obscure_tracks', '30'))
        max_tracks_entry = ttk.Entry(settings_frame, textvariable=self.max_obscure_tracks, width=5)
        max_tracks_entry.grid(row=1, column=1, sticky="w", padx=5)

        # Preview button
        preview_frame = ttk.Frame(settings_frame)
        preview_frame.grid(row=2, column=0, columnspan=2, pady=10)
        self.preview_button = ttk.Button(preview_frame, text="Preview Obscure Tracks", command=self.preview_obscure_tracks)
        self.preview_button.pack(side="left", padx=5)

        # Preview list
        list_frame = ttk.LabelFrame(tab, text="Preview", padding=10)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.preview_list = tk.Listbox(list_frame, height=15, bg="#1e1e1e", fg="white")
        self.preview_list.pack(fill="both", expand=True)

        # Download button
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", padx=5, pady=10)
        self.obscurify_download_button = ttk.Button(btn_frame, text="Download Obscure Tracks", 
                                                  command=self.download_obscure_tracks)
        self.obscurify_download_button.pack()

    def create_settings_tab(self):
        """Create the settings tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Settings")

        # Path settings
        path_frame = ttk.LabelFrame(tab, text="Paths", padding=10)
        path_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(path_frame, text="Download Folder:").grid(row=0, column=0, sticky="w")
        self.music_dir_entry = ttk.Entry(path_frame, width=60)
        self.music_dir_entry.insert(0, self.config['DEFAULT'].get('download_folder', ''))
        self.music_dir_entry.grid(row=1, column=0, columnspan=2, sticky="we", pady=5)
        browse_music_btn = ttk.Button(path_frame, text="Browse", command=self.browse_music_folder, width=10)
        browse_music_btn.grid(row=1, column=2, padx=5)

        ttk.Label(path_frame, text="sldl.exe Path:").grid(row=2, column=0, sticky="w")
        self.slsk_path_entry = ttk.Entry(path_frame, width=60)
        self.slsk_path_entry.insert(0, self.config['DEFAULT'].get('sldl_path', ''))
        self.slsk_path_entry.grid(row=3, column=0, columnspan=2, sticky="we", pady=5)
        browse_sldl_btn = ttk.Button(path_frame, text="Browse", command=self.browse_sldl, width=10)
        browse_sldl_btn.grid(row=3, column=2, padx=5)

        # Credentials frame
        cred_frame = ttk.LabelFrame(tab, text="Credentials", padding=10)
        cred_frame.pack(fill="x", padx=5, pady=5)

        # Spotify credentials
        ttk.Label(cred_frame, text="Spotify Client ID:").grid(row=0, column=0, sticky="w")
        self.spotify_id_entry = ttk.Entry(cred_frame, width=30)
        self.spotify_id_entry.insert(0, self.config['DEFAULT'].get('spotify_client_id', ''))
        self.spotify_id_entry.grid(row=1, column=0, sticky="w", pady=5)

        ttk.Label(cred_frame, text="Spotify Client Secret:").grid(row=2, column=0, sticky="w")
        self.spotify_secret_frame = ttk.Frame(cred_frame)
        self.spotify_secret_frame.grid(row=3, column=0, sticky="w", pady=5)
        self.spotify_secret_entry = ttk.Entry(self.spotify_secret_frame, width=25, show="*")
        self.spotify_secret_entry.pack(side="left")
        self.spotify_secret_toggle = ttk.Button(
            self.spotify_secret_frame, 
            text="👁", 
            width=3,
            command=lambda: self.toggle_password_visibility(self.spotify_secret_entry, self.spotify_secret_toggle)
        )
        self.spotify_secret_toggle.pack(side="left", padx=5)
        self.spotify_secret_entry.insert(0, self.config['DEFAULT'].get('spotify_client_secret', ''))

        # Soulseek credentials
        ttk.Label(cred_frame, text="Soulseek Username:").grid(row=0, column=1, sticky="w", padx=(20, 0))
        self.slsk_user_entry = ttk.Entry(cred_frame, width=30)
        self.slsk_user_entry.insert(0, self.config['DEFAULT'].get('soulseek_username', ''))
        self.slsk_user_entry.grid(row=1, column=1, sticky="w", padx=(20, 0), pady=5)

        ttk.Label(cred_frame, text="Soulseek Password:").grid(row=2, column=1, sticky="w", padx=(20, 0))
        self.slsk_pass_frame = ttk.Frame(cred_frame)
        self.slsk_pass_frame.grid(row=3, column=1, sticky="w", padx=(20, 0), pady=5)
        self.slsk_pass_entry = ttk.Entry(self.slsk_pass_frame, width=25, show="*")
        self.slsk_pass_entry.pack(side="left")
        self.slsk_pass_toggle = ttk.Button(
            self.slsk_pass_frame, 
            text="👁", 
            width=3,
            command=lambda: self.toggle_password_visibility(self.slsk_pass_entry, self.slsk_pass_toggle)
        )
        self.slsk_pass_toggle.pack(side="left", padx=5)
        self.slsk_pass_entry.insert(0, self.config['DEFAULT'].get('soulseek_password', ''))

        # Save button
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", padx=5, pady=10)
        self.save_button = ttk.Button(btn_frame, text="💾 Save Settings", command=self.save_settings)
        self.save_button.pack()

    def toggle_password_visibility(self, entry, toggle_button):
        """Toggle password visibility between hidden and visible"""
        if entry['show'] == "*":
            entry.config(show="")
            toggle_button.config(text="🙈")
        else:
            entry.config(show="*")
            toggle_button.config(text="👁")

    def save_settings(self):
        """Save all settings to config file"""
        self.config['DEFAULT']['spotify_client_id'] = self.spotify_id_entry.get()
        self.config['DEFAULT']['spotify_client_secret'] = self.spotify_secret_entry.get()
        self.config['DEFAULT']['soulseek_username'] = self.slsk_user_entry.get()
        self.config['DEFAULT']['soulseek_password'] = self.slsk_pass_entry.get()
        self.config['DEFAULT']['download_folder'] = self.music_dir_entry.get()
        self.config['DEFAULT']['sldl_path'] = self.slsk_path_entry.get()
        self.config['DEFAULT']['obscurity_threshold'] = self.obscurity_threshold.get()
        self.config['DEFAULT']['max_obscure_tracks'] = self.max_obscure_tracks.get()
        with open(self.config_file, 'w') as f:
            self.config.write(f)
        self.log("[INFO] Settings saved successfully.")

    def animate_status(self):
        self.status_box.tag_configure("animate", foreground="#44ff44")
        self.status_box.after(500, self._animate_cursor)

    def _animate_cursor(self):
        self.status_box.insert(tk.END, ".", "animate")
        self.status_box.see(tk.END)
        self.status_box.after(1000, self._animate_cursor)

    def browse_music_folder(self):
        folder_selected = filedialog.askdirectory(title="Select Music Download Folder")
        if folder_selected:
            self.music_dir_entry.delete(0, tk.END)
            self.music_dir_entry.insert(0, folder_selected)

    def browse_sldl(self):
        file_selected = filedialog.askopenfilename(title="Select sldl.exe", filetypes=[("Executable Files", "*.exe")])
        if file_selected:
            self.slsk_path_entry.delete(0, tk.END)
            self.slsk_path_entry.insert(0, file_selected)

    def threaded_download(self):
        threading.Thread(target=self.download_songs, daemon=True).start()

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
        self.status_box.insert(tk.END, timestamp + message + "\n")
        self.status_box.see(tk.END)

    def fetch_obscure_spotify_tracks(self):
        self.log("[INFO] Fetching obscure Spotify tracks...")
        token = self.get_spotify_token()
        if not token:
            self.log("[ERROR] Failed to get Spotify token.")
            return []
        
        try:
            threshold = int(self.obscurity_threshold.get())
            max_tracks = int(self.max_obscure_tracks.get())
            
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get("https://api.spotify.com/v1/me/top/tracks?limit=50", headers=headers)
            response.raise_for_status()
            tracks = response.json().get("items", [])
            obscure = [
                f"{t['artists'][0]['name']} - {t['name']}" 
                for t in tracks 
                if t['popularity'] <= threshold
            ]
            return obscure[:max_tracks]
        except Exception as e:
            self.log(f"[ERROR] Failed to fetch obscure tracks: {str(e)}")
            return []

    def preview_obscure_tracks(self):
        """Fetch and display obscure tracks in the preview list"""
        self.preview_list.delete(0, tk.END)
        tracks = self.fetch_obscure_spotify_tracks()
        if not tracks:
            self.log("[ERROR] No obscure tracks found or failed to fetch.")
            return
        
        for track in tracks:
            self.preview_list.insert(tk.END, track)
        self.log(f"[INFO] Found {len(tracks)} obscure tracks")

    def download_obscure_tracks(self):
        """Download the tracks shown in the preview list"""
        tracks = [self.preview_list.get(i) for i in range(self.preview_list.size())]
        if not tracks:
            self.log("[ERROR] No tracks to download. Please preview first.")
            return
        
        input_value = ", ".join(tracks)
        self.download_songs(mode="obscurify", input_value=input_value)

    def get_spotify_token(self):
        client_id = self.spotify_id_entry.get().strip()
        client_secret = self.spotify_secret_entry.get().strip()
        
        if not client_id or not client_secret:
            self.log("[ERROR] Spotify credentials not configured")
            return None

        try:
            data = {
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }
            r = requests.post('https://accounts.spotify.com/api/token', data=data)
            r.raise_for_status()
            return r.json().get('access_token')
        except Exception as e:
            self.log(f"[ERROR] Spotify auth error: {str(e)}")
            return None

    def download_songs(self, mode=None, input_value=None):
        if mode is None:
            mode = self.mode.get()
        if input_value is None:
            input_value = self.input_entry.get().strip()
        
        music_dir = self.music_dir_entry.get().strip()
        slsk_path = self.slsk_path_entry.get().strip()
        slsk_user = self.slsk_user_entry.get().strip()
        slsk_pass = self.slsk_pass_entry.get().strip()

        # Validate inputs
        if not slsk_path or not os.path.isfile(slsk_path):
            self.log("ERROR: sldl.exe not found or not specified.")
            return
        if not music_dir or not os.path.isdir(music_dir):
            self.log("ERROR: Download folder not found or not specified.")
            return
        if not slsk_user or not slsk_pass:
            self.log("ERROR: Soulseek credentials not specified.")
            return

        if mode == "spotify" and "playlist/" in input_value:
            input_value = input_value.split("playlist/")[-1].split("?")[0]
        elif mode == "obscurify":
            if not input_value:
                song_list = self.fetch_obscure_spotify_tracks()
                if not song_list:
                    self.log("ERROR: No obscure tracks found or failed to fetch.")
                    return
                input_value = ", ".join(song_list)

        # Create log directory if it doesn't exist
        log_dir = Path.home() / "musicdownloader_logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"download_log_{datetime.date.today()}.txt"

        command = [
            slsk_path,
            input_value,
            "--user", slsk_user,
            "--pass", slsk_pass,
            "--path", music_dir,
            "--pref-format", "flac,mp3",
            "--name-format", "{artist}/{album}/{title}.{ext}",
            "--write-playlist",
            "--log-file", str(log_file)
        ]

        self.log("Starting download process...")
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Stream output in real-time
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    self.log(output.strip())
            
            stderr = process.stderr.read()
            if stderr:
                self.log(f"[ERROR] {stderr.strip()}")

            if process.returncode == 0:
                self.log("Download completed successfully.")
            else:
                self.log(f"Download failed with return code {process.returncode}")

        except Exception as e:
            self.log(f"Exception occurred: {str(e)}")
        finally:
            self.log(f"Download process completed. Files saved to: {music_dir}")
            self.log(f"Log file saved to: {log_file}")

if __name__ == "__main__":
    root = tk.Tk()
    try:
        app = MusicDownloaderGUI(root)
        root.mainloop()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start application: {str(e)}")