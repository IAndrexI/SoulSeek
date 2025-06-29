import customtkinter as ctk
import subprocess
import threading
import os
import json
import webbrowser
from tkinter import filedialog
import requests
import base64
import time
import re
import csv

# --- Configuration & Constants ---
CONFIG_FILE = "config.json"
SLDL_EXECUTABLE = "sldl.exe" # Make sure sldl.exe is in the same directory or in your PATH
ABOUT_URL = "https://github.com/fiso64/slsk-batchdl"
SLSK_URL = "https://www.slsknet.org/"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"
OBSCURIFY_RECOMMENDATIONS_URL = "https://obscurifymusic.com/recommendations"
DEFAULT_DOWNLOAD_PATH = os.path.join(os.path.expanduser("~"), "Downloads", "slsk-batchdl")

# --- UI Class ---

class App(ctk.CTk):
    """
    A GUI application to download songs using slsk-batchdl.
    """
    def __init__(self):
        super().__init__()

        self.title("Soulseek Batch Downloader")
        self.geometry("800x880") # Increased height to accommodate new field
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Apply dark mode theme
        ctk.set_appearance_mode("dark")  # Set default to dark mode

        # --- Frames ---
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)

        self.main_frame = ctk.CTkScrollableFrame(self)
        self.main_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.footer_frame = ctk.CTkFrame(self)
        self.footer_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.footer_frame.grid_columnconfigure(0, weight=1)
        self.footer_frame.grid_columnconfigure(1, weight=1)

        # --- Header Widgets ---
        self.logo_label = ctk.CTkLabel(self.header_frame, text="Soulseek Downloader", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        
        self.dark_mode_switch_var = ctk.StringVar(value="on")
        self.dark_mode_switch = ctk.CTkSwitch(
            self.header_frame,
            text="Dark Mode",
            command=self.toggle_dark_mode,
            variable=self.dark_mode_switch_var,
            onvalue="on",
            offvalue="off"
        )
        self.dark_mode_switch.grid(row=0, column=2, padx=20, pady=10, sticky="e")
        
        self.about_button = ctk.CTkButton(self.header_frame, text="About slsk-batchdl", command=self.open_about)
        self.about_button.grid(row=0, column=3, padx=10, pady=10, sticky="e")
        
        self.slsk_button = ctk.CTkButton(self.header_frame, text="Get Soulseek", command=self.open_slsk)
        self.slsk_button.grid(row=0, column=4, padx=20, pady=10, sticky="e")

        # --- Main Widgets (Input & Options) ---
        self.create_input_section()
        self.create_credentials_section()
        self.create_download_options_section()
        self.create_search_options_section()
        self.create_spotify_options_section()
        self.create_output_frame()

        # --- Footer Widgets ---
        self.download_button = ctk.CTkButton(self.footer_frame, text="Start Download", command=self.start_download, height=50, font=ctk.CTkFont(size=20, weight="bold"))
        self.download_button.grid(row=0, column=0, padx=20, pady=20, sticky="ew")

        self.status_label = ctk.CTkLabel(self.footer_frame, text="Status: Ready", font=ctk.CTkFont(size=14))
        self.status_label.grid(row=1, column=0, columnspan=2, padx=20, pady=5, sticky="w")
        
        self.load_credentials()
        
        # --- New: Lists to store download status ---
        self.all_queries = []
        self.downloaded_queries = set()
        self.failed_downloads = []

    def create_input_section(self):
        """Creates the section for the input URL/path."""
        input_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        input_frame.grid(row=0, column=0, sticky="ew", padx=1.5, pady=10)
        input_frame.grid_columnconfigure(1, weight=1)

        input_label = ctk.CTkLabel(input_frame, text="Input (URL or Path):")
        input_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.input_entry = ctk.CTkEntry(input_frame, placeholder_text="e.g., https://open.spotify.com/playlist/... or C:/obscurify_listening.csv")
        self.input_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        input_type_label = ctk.CTkLabel(input_frame, text="Input Type:")
        input_type_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.input_type_optionmenu = ctk.CTkOptionMenu(
            input_frame,
            values=["auto", "csv", "youtube", "spotify", "bandcamp", "string", "list"]
        )
        self.input_type_optionmenu.set("auto")
        self.input_type_optionmenu.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

    def create_credentials_section(self):
        """Creates the section for Soulseek credentials."""
        credentials_frame = ctk.CTkFrame(self.main_frame)
        credentials_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        credentials_frame.grid_columnconfigure(1, weight=1)

        credentials_label = ctk.CTkLabel(credentials_frame, text="Soulseek Credentials", font=ctk.CTkFont(size=16, weight="bold"))
        credentials_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        username_label = ctk.CTkLabel(credentials_frame, text="Username:")
        username_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.username_entry = ctk.CTkEntry(credentials_frame)
        self.username_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        password_label = ctk.CTkLabel(credentials_frame, text="Password:")
        password_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.password_entry = ctk.CTkEntry(credentials_frame, show="*")
        self.password_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
    def create_download_options_section(self):
        """Creates the section for general download options."""
        options_frame = ctk.CTkFrame(self.main_frame)
        options_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        options_frame.grid_columnconfigure(1, weight=1)
        options_frame.grid_columnconfigure(3, weight=1)

        options_label = ctk.CTkLabel(options_frame, text="Download Options", font=ctk.CTkFont(size=16, weight="bold"))
        options_label.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="w")

        path_label = ctk.CTkLabel(options_frame, text="Download Path:")
        path_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.path_entry = ctk.CTkEntry(options_frame, placeholder_text=f"e.g., {DEFAULT_DOWNLOAD_PATH}")
        self.path_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        
        # New Browse button
        browse_button = ctk.CTkButton(options_frame, text="Browse", width=80, command=self.browse_download_path)
        browse_button.grid(row=1, column=3, padx=10, pady=5, sticky="e")
        
        # Row 2
        number_label = ctk.CTkLabel(options_frame, text="Max Tracks:")
        number_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.number_entry = ctk.CTkEntry(options_frame, placeholder_text="all")
        self.number_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        offset_label = ctk.CTkLabel(options_frame, text="Offset:")
        offset_label.grid(row=2, column=2, padx=10, pady=5, sticky="w")
        self.offset_entry = ctk.CTkEntry(options_frame, placeholder_text="0")
        self.offset_entry.grid(row=2, column=3, padx=10, pady=5, sticky="ew")
        
        # Row 3
        self.reverse_checkbox = ctk.CTkCheckBox(options_frame, text="Reverse Order")
        self.reverse_checkbox.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        
        self.write_playlist_checkbox = ctk.CTkCheckBox(options_frame, text="Write M3U Playlist")
        self.write_playlist_checkbox.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        self.no_skip_existing_checkbox = ctk.CTkCheckBox(options_frame, text="No Skip Existing")
        self.no_skip_existing_checkbox.grid(row=3, column=2, padx=10, pady=5, sticky="w")
        
        # Row 4 (New)
        listen_port_label = ctk.CTkLabel(options_frame, text="Listen Port:")
        listen_port_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.listen_port_entry = ctk.CTkEntry(options_frame, placeholder_text="49998 (default)")
        self.listen_port_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

    def create_search_options_section(self):
        """Creates the section for search-related options."""
        search_frame = ctk.CTkFrame(self.main_frame)
        search_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        search_frame.grid_columnconfigure(1, weight=1)
        search_frame.grid_columnconfigure(3, weight=1)

        search_label = ctk.CTkLabel(search_frame, text="Search & File Conditions", font=ctk.CTkFont(size=16, weight="bold"))
        search_label.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="w")
        
        # Row 1 (New search format options)
        search_format_label = ctk.CTkLabel(search_frame, text="Search Query Format:")
        search_format_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        # Updated placeholder to a simpler format
        self.search_format_entry = ctk.CTkEntry(search_frame, placeholder_text="{artist} {title}")
        self.search_format_entry.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="ew")
        
        # Helper checkbox for vague search
        self.vague_search_checkbox = ctk.CTkCheckBox(search_frame, text="Simple query (artist keywords)", command=self.set_vague_search_format)
        self.vague_search_checkbox.grid(row=1, column=3, padx=10, pady=5, sticky="w")
        
        # Row 2
        self.fast_search_checkbox = ctk.CTkCheckBox(search_frame, text="Fast Search")
        self.fast_search_checkbox.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.desperate_checkbox = ctk.CTkCheckBox(search_frame, text="Desperate Search")
        self.desperate_checkbox.grid(row=2, column=1, padx=10, pady=5, sticky="w")
        
        self.yt_dlp_checkbox = ctk.CTkCheckBox(search_frame, text="Use yt-dlp as fallback")
        self.yt_dlp_checkbox.grid(row=2, column=2, padx=10, pady=5, sticky="w")
        
        # Row 3 (Bitrate)
        min_bitrate_label = ctk.CTkLabel(search_frame, text="Min Bitrate:")
        min_bitrate_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.min_bitrate_entry = ctk.CTkEntry(search_frame, placeholder_text="200")
        self.min_bitrate_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        max_bitrate_label = ctk.CTkLabel(search_frame, text="Max Bitrate:")
        max_bitrate_label.grid(row=3, column=2, padx=10, pady=5, sticky="w")
        self.max_bitrate_entry = ctk.CTkEntry(search_frame, placeholder_text="2500")
        self.max_bitrate_entry.grid(row=3, column=3, padx=10, pady=5, sticky="ew")
        
        # Row 4 (Formats)
        pref_format_label = ctk.CTkLabel(search_frame, text="Preferred Formats:")
        pref_format_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.pref_format_entry = ctk.CTkEntry(search_frame, placeholder_text="flac")
        self.pref_format_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        
        format_label = ctk.CTkLabel(search_frame, text="Accepted Formats:")
        format_label.grid(row=4, column=2, padx=10, pady=5, sticky="w")
        self.format_entry = ctk.CTkEntry(search_frame, placeholder_text="flac,mp3")
        self.format_entry.grid(row=4, column=3, padx=10, pady=5, sticky="ew")

    def set_vague_search_format(self):
        """Sets a vague search format if the checkbox is selected."""
        if self.vague_search_checkbox.get() == 1:
            self.search_format_entry.delete(0, ctk.END)
            self.search_format_entry.insert(0, "{artist} {title}")
            self.update_status("Search query format set to '{artist} {title}'", "blue")
        else:
            self.search_format_entry.delete(0, ctk.END)
            self.update_status("Search query format reset.", "blue")

    def create_spotify_options_section(self):
        """Creates the section for Spotify credentials."""
        spotify_frame = ctk.CTkFrame(self.main_frame)
        spotify_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=10)
        spotify_frame.grid_columnconfigure(1, weight=1)
        spotify_frame.grid_columnconfigure(3, weight=1)

        spotify_label = ctk.CTkLabel(spotify_frame, text="Spotify Credentials & Options", font=ctk.CTkFont(size=16, weight="bold"))
        spotify_label.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="w")
        
        # Row 1
        id_label = ctk.CTkLabel(spotify_frame, text="Client ID:")
        id_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.spotify_id_entry = ctk.CTkEntry(spotify_frame)
        self.spotify_id_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        secret_label = ctk.CTkLabel(spotify_frame, text="Client Secret:")
        secret_label.grid(row=1, column=2, padx=10, pady=5, sticky="w")
        self.spotify_secret_entry = ctk.CTkEntry(spotify_frame, show="*")
        self.spotify_secret_entry.grid(row=1, column=3, padx=10, pady=5, sticky="ew")
        
        # Row 2 (Optional for refresh token flow)
        refresh_label = ctk.CTkLabel(spotify_frame, text="Refresh Token:")
        refresh_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.spotify_refresh_entry = ctk.CTkEntry(spotify_frame)
        self.spotify_refresh_entry.grid(row=2, column=1, columnspan=3, padx=10, pady=5, sticky="ew")
        
        # Save button for credentials in this frame
        save_credentials_button = ctk.CTkButton(spotify_frame, text="Save All Credentials", command=self.save_credentials)
        save_credentials_button.grid(row=3, column=3, padx=10, pady=10, sticky="e")
        
        # Row 4 (Obscurify & other options)
        self.remove_from_source_checkbox = ctk.CTkCheckBox(spotify_frame, text="Remove downloaded tracks from playlist")
        self.remove_from_source_checkbox.grid(row=4, column=0, columnspan=4, padx=10, pady=5, sticky="w")
        
        obscurify_label = ctk.CTkLabel(spotify_frame, text="Obscurify Daily Download", font=ctk.CTkFont(size=14, weight="bold"))
        obscurify_label.grid(row=5, column=0, padx=10, pady=10, sticky="w")
        
        # --- CORRECTED INSTRUCTIONS ---
        obscurify_info_label = ctk.CTkLabel(spotify_frame, text="1. Click the button to open your recommendations page.\n2. On the website, click 'Create a playlist on Spotify'.\n3. Copy the URL of the new Spotify playlist and paste it into the input field above.\n4. Select 'spotify' as the input type to download the songs.", wraplength=550, justify="left")
        obscurify_info_label.grid(row=6, column=0, columnspan=3, padx=10, pady=5, sticky="w")

        # --- Obscurify Recommendations button ---
        self.obscurify_button = ctk.CTkButton(spotify_frame, text="Open Obscurify Recommendations", command=self.open_obscurify_recommendations)
        self.obscurify_button.grid(row=6, column=3, padx=10, pady=5, sticky="e")


    def create_output_frame(self):
        """Creates the frame for the console output."""
        output_frame = ctk.CTkFrame(self.main_frame)
        output_frame.grid(row=5, column=0, sticky="nsew", padx=10, pady=10)
        output_frame.grid_columnconfigure(0, weight=1)
        output_frame.grid_rowconfigure(0, weight=1)

        output_label = ctk.CTkLabel(output_frame, text="Log Output", font=ctk.CTkFont(size=16, weight="bold"))
        output_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.output_text = ctk.CTkTextbox(output_frame, height=200)
        self.output_text.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.output_text.configure(state="disabled") # Make it read-only
        
        output_frame.grid_rowconfigure(1, weight=1)

    def toggle_dark_mode(self):
        """Toggles between dark and light mode."""
        if self.dark_mode_switch_var.get() == "on":
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")

    def browse_download_path(self):
        """Opens a file dialog to select the download folder and updates the entry field."""
        folder_selected = filedialog.askdirectory()
        if folder_selected: # If a folder was selected (not cancelled)
            self.path_entry.delete(0, ctk.END) # Clear the current entry
            self.path_entry.insert(0, folder_selected) # Insert the selected path
            self.update_status(f"Download path set to: {folder_selected}", "blue")

    def save_credentials(self):
        """Saves Soulseek and Spotify credentials to a JSON file."""
        config_data = {
            "soulseek_username": self.username_entry.get(),
            "soulseek_password": self.password_entry.get(),
            "spotify_id": self.spotify_id_entry.get(),
            "spotify_secret": self.spotify_secret_entry.get(),
            "spotify_refresh": self.spotify_refresh_entry.get(),
            "download_path": self.path_entry.get(),
            "listen_port": self.listen_port_entry.get(),
            "preferred_format": self.pref_format_entry.get(),
            "accepted_format": self.format_entry.get(),
            "search_format": self.search_format_entry.get()
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config_data, f, indent=4)
            self.update_status("Credentials and settings saved successfully!", "green")
        except Exception as e:
            self.update_status(f"Error saving credentials: {e}", "red")

    def load_credentials(self):
        """Loads credentials from the JSON file if it exists."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config_data = json.load(f)
                    self.username_entry.insert(0, config_data.get("soulseek_username", ""))
                    self.password_entry.insert(0, config_data.get("soulseek_password", ""))
                    self.spotify_id_entry.insert(0, config_data.get("spotify_id", ""))
                    self.spotify_secret_entry.insert(0, config_data.get("spotify_secret", ""))
                    self.spotify_refresh_entry.insert(0, config_data.get("spotify_refresh", ""))
                    self.path_entry.insert(0, config_data.get("download_path", ""))
                    self.pref_format_entry.insert(0, config_data.get("preferred_format", "flac")) 
                    self.format_entry.insert(0, config_data.get("accepted_format", "flac,mp3"))
                    self.listen_port_entry.insert(0, config_data.get("listen_port", ""))
                    self.search_format_entry.insert(0, config_data.get("search_format", ""))
                self.update_status("Credentials loaded from config file.", "blue")
            except Exception as e:
                self.update_status(f"Error loading credentials: {e}", "red")

    def open_obscurify_recommendations(self):
        """Opens the Obscurify recommendations page in the user's browser."""
        self.update_status("Opening Obscurify recommendations page... Please create a Spotify playlist from there.", "blue")
        webbrowser.open(OBSCURIFY_RECOMMENDATIONS_URL)

    def get_spotify_access_token(self):
        """
        Retrieves a Spotify access token using Refresh Token Flow or Client Credentials Flow.
        """
        client_id = self.spotify_id_entry.get()
        client_secret = self.spotify_secret_entry.get()
        refresh_token = self.spotify_refresh_entry.get()

        if not client_id or not client_secret:
            self.print_to_output("Error: Spotify Client ID and Secret are required for Spotify input.", "red")
            return None
            
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # First, try to use the Refresh Token
        if refresh_token:
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token
            }
            auth_string = f"{client_id}:{client_secret}"
            auth_bytes = auth_string.encode("utf-8")
            auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")
            headers["Authorization"] = f"Basic {auth_base64}"

            self.print_to_output("Attempting to get Spotify token using Refresh Token...", "blue")
            try:
                response = requests.post(SPOTIFY_TOKEN_URL, data=payload, headers=headers)
                response.raise_for_status() # This will raise an HTTPError for bad responses
                token_info = response.json()
                return token_info.get("access_token")
            except requests.exceptions.RequestException as e:
                self.print_to_output(f"Failed to get token with Refresh Token: {e}", "red")
                if hasattr(e, 'response') and e.response is not None:
                    self.print_to_output(f"Spotify API Response: {e.response.text}", "red")
                self.print_to_output("Falling back to Client Credentials Flow...", "yellow")
        
        # If no refresh token or the refresh token failed, use Client Credentials flow
        payload = {
            "grant_type": "client_credentials"
        }
        auth_string = f"{client_id}:{client_secret}"
        auth_bytes = auth_string.encode("utf-8")
        auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")
        headers["Authorization"] = f"Basic {auth_base64}"

        self.print_to_output("Attempting to get Spotify token using Client Credentials...", "blue")
        try:
            response = requests.post(SPOTIFY_TOKEN_URL, data=payload, headers=headers)
            response.raise_for_status()
            token_info = response.json()
            return token_info.get("access_token")
        except requests.exceptions.RequestException as e:
            self.print_to_output(f"Failed to get token with Client Credentials: {e}", "red")
            if hasattr(e, 'response') and e.response is not None:
                self.print_to_output(f"Spotify API Response: {e.response.text}", "red")
            return None

    def get_spotify_playlist_details(self, playlist_id, access_token):
        """
        Fetches details (like name) for a Spotify playlist.
        """
        url = f"{SPOTIFY_API_URL}/playlists/{playlist_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("name")
        except requests.exceptions.RequestException as e:
            self.print_to_output(f"Error fetching Spotify playlist details: {e}", "red")
            return None

    def get_spotify_playlist_tracks(self, playlist_id, access_token):
        """
        Fetches tracks from a Spotify playlist.
        """
        tracks = []
        next_url = f"{SPOTIFY_API_URL}/playlists/{playlist_id}/tracks"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        while next_url:
            self.print_to_output(f"Fetching tracks from: {next_url}...", "blue")
            try:
                response = requests.get(next_url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                for item in data['items']:
                    track = item['track']
                    if track and track['artists']:
                        artist_names = [artist['name'] for artist in track['artists']]
                        tracks.append({
                            'title': track['name'],
                            'artist': ", ".join(artist_names),
                            'album': track['album']['name']
                        })
                
                next_url = data['next']
            except requests.exceptions.RequestException as e:
                self.print_to_output(f"Error fetching Spotify playlist tracks: {e}", "red")
                if hasattr(e, 'response') and e.response is not None:
                    self.print_to_output(f"Spotify API Response: {e.response.text}", "red")
                return None
        return tracks

    def process_obscurify_csv(self, file_path):
        """
        Reads a CSV from Obscurify and extracts artist and track information.
        """
        tracks = []
        try:
            with open(file_path, mode='r', encoding='utf-8') as f:
                # Use DictReader which is more robust if column order changes
                reader = csv.DictReader(f)
                
                # Check for expected headers (case-insensitive)
                headers = [header.lower() for header in reader.fieldnames]
                if 'track name' not in headers or 'artist name(s)' not in headers:
                    self.print_to_output("Error: CSV must contain 'Track Name' and 'Artist Name(s)' columns.", "red")
                    return None
                    
                # Map headers to the correct case from the file
                track_name_key = next((h for h in reader.fieldnames if h.lower() == 'track name'), None)
                artist_name_key = next((h for h in reader.fieldnames if h.lower() == 'artist name(s)'), None)
                
                for row in reader:
                    tracks.append({
                        'title': row.get(track_name_key, ''),
                        'artist': row.get(artist_name_key, ''),
                        'album': '' # Obscurify CSV doesn't have album info
                    })
            self.print_to_output(f"Successfully loaded {len(tracks)} tracks from the CSV.", "green")
            return tracks
        except FileNotFoundError:
            self.print_to_output(f"Error: CSV file not found at '{file_path}'.", "red")
            return None
        except Exception as e:
            self.print_to_output(f"Error processing CSV file: {e}", "red")
            return None

    def sanitize_filename(self, name):
        """
        Removes invalid characters from a string to make it a valid filename/folder name.
        """
        # Replace characters that are not letters, numbers, spaces, hyphens, or underscores with an empty string
        sanitized = re.sub(r'[\\/:*?"<>|]', '', name)
        # Trim leading/trailing whitespace
        sanitized = sanitized.strip()
        return sanitized
        
    def start_download(self):
        """
        Starts the download process in a separate thread to prevent the GUI from freezing.
        Handles Spotify URLs by pre-processing them.
        """
        input_value = self.input_entry.get()
        if not input_value:
            self.update_status("Please provide a Spotify URL or file path.", "red")
            return
        
        # --- New: Reset download status lists before a new download ---
        self.all_queries = []
        self.downloaded_queries = set()
        self.failed_downloads = []

        self.output_text.delete("1.0", ctk.END) # Clear the log
        self.update_status("Starting download...", "yellow")
        self.download_button.configure(state="disabled", text="Downloading...")
        
        # Create a thread to handle both pre-processing and the subprocess
        download_thread = threading.Thread(target=self.prepare_and_run_download, args=(input_value,))
        download_thread.start()

    def prepare_and_run_download(self, input_value):
        """
        Determines the input type and prepares the input for sldl.exe.
        """
        temp_file_path = None
        
        # Get the base download path, use default if empty
        base_download_path = self.path_entry.get() if self.path_entry.get() else DEFAULT_DOWNLOAD_PATH
        
        # Determine the input type based on the user's selection and input value
        selected_input_type = self.input_type_optionmenu.get()
        
        if selected_input_type == "auto":
            if "open.spotify.com" in input_value:
                final_input_type = "spotify"
            elif input_value.lower().endswith(('.csv')):
                final_input_type = "csv"
            elif input_value.lower().endswith(('.txt')):
                final_input_type = "list"
            elif "youtube.com" in input_value or "youtu.be" in input_value:
                final_input_type = "youtube"
            else:
                # Let sldl.exe figure out a direct string search
                final_input_type = "string"
                
            self.print_to_output(f"Input type 'auto' resolved to '{final_input_type}'.", "blue")
        else:
            final_input_type = selected_input_type

        try:
            # --- New logic for dynamic playlist/source folder name ---
            dynamic_download_path = base_download_path
            
            if final_input_type == "spotify":
                self.print_to_output("Detected Spotify URL. Fetching tracks...", "blue")
                
                # Extract playlist ID from the URL
                parts = input_value.split('/')
                playlist_id = parts[-1].split('?')[0]
                
                # Get Access Token
                access_token = self.get_spotify_access_token()
                if not access_token:
                    self.update_status("Failed to get Spotify token. Check credentials.", "red")
                    return
                
                # --- NEW: Get playlist name to create a folder ---
                playlist_name = self.get_spotify_playlist_details(playlist_id, access_token)
                if playlist_name:
                    sanitized_name = self.sanitize_filename(playlist_name)
                    dynamic_download_path = os.path.join(base_download_path, sanitized_name)
                    self.print_to_output(f"Creating download folder: {dynamic_download_path}", "blue")

                # Fetch tracks from Spotify
                tracks = self.get_spotify_playlist_tracks(playlist_id, access_token)
                if not tracks:
                    self.update_status("Failed to fetch tracks from the Spotify playlist.", "red")
                    return
                
                # If a custom search format is specified, create a temp file
                if self.search_format_entry.get():
                    temp_file_path = self.generate_query_file(tracks, self.search_format_entry.get())
                    final_input = temp_file_path
                    final_input_type = "list"
                else:
                    final_input = input_value # Pass the URL directly to sldl.exe
            
            # --- NEW: Logic for Obscurify CSV input ---
            elif final_input_type == "csv":
                self.print_to_output("Detected Obscurify CSV file. Processing...", "blue")
                # Get a list of tracks from the CSV
                tracks = self.process_obscurify_csv(input_value)
                if not tracks:
                    self.update_status("Failed to process the CSV file.", "red")
                    return
                
                # Create a temp file with formatted queries from the CSV data
                search_format = self.search_format_entry.get() if self.search_format_entry.get() else "{artist} {title}"
                temp_file_path = self.generate_query_file(tracks, search_format)
                final_input = temp_file_path
                final_input_type = "list"
                
                # --- NEW: Use CSV filename for folder name ---
                csv_name = os.path.splitext(os.path.basename(input_value))[0]
                sanitized_name = self.sanitize_filename(csv_name)
                dynamic_download_path = os.path.join(base_download_path, sanitized_name)
                self.print_to_output(f"Creating download folder: {dynamic_download_path}", "blue")

            else:
                # If not Spotify or CSV, use the original input
                final_input = input_value
                dynamic_download_path = base_download_path # Use the base path
                
                # If it's a direct search string or single input, store it.
                if final_input_type in ["string", "bandcamp", "youtube"]:
                    self.all_queries.append(final_input)

            # Now, run the download command with the prepared input and dynamic path
            self.run_download_command(final_input, final_input_type, dynamic_download_path)

        except Exception as e:
            self.update_status(f"An error occurred during pre-processing: {e}", "red")
        finally:
            # Clean up the temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    self.print_to_output(f"Cleaned up temporary file: {temp_file_path}", "blue")
                except OSError as e:
                    self.print_to_output(f"Error cleaning up temporary file: {e}", "red")
            
            # --- New: Display a summary of missing songs after the download finishes ---
            self.display_download_summary()

    def generate_query_file(self, tracks, search_format):
        """
        Generates a temporary file with formatted search queries.
        """
        temp_file_path = "temp_queries.txt"
        with open(temp_file_path, "w", encoding="utf-8") as f:
            for track in tracks:
                query = search_format.format(artist=track['artist'], title=track['title'], album=track['album'])
                
                # Store the original query to track it later
                self.all_queries.append(query)
                
                # Remove any double quotes from the query string to prevent parsing issues
                cleaned_query = query.replace('"', '')
                
                # Wrap the cleaned query in double quotes
                quoted_query = f'"{cleaned_query}"'
                
                self.print_to_output(f"Generated query: {quoted_query}", "grey")
                f.write(quoted_query + "\n")
        return temp_file_path

    def run_download_command(self, input_value, input_type, download_path):
        """
        Builds and executes the sldl.exe command in a subprocess.
        """
        try:
            command = [SLDL_EXECUTABLE]
            
            # --- Build the command based on user inputs ---
            command.extend(["--input", input_value])
            
            # Only add the input type if it's not 'auto'
            if input_type != "auto":
                command.extend(["--input-type", input_type])
            
            user = self.username_entry.get()
            if user:
                command.extend(["--user", user])
            
            password = self.password_entry.get()
            if password:
                command.extend(["--pass", password])
            
            # --- Use the dynamically determined download path ---
            if download_path:
                command.extend(["--path", download_path])
            
            if self.number_entry.get():
                command.extend(["--number", self.number_entry.get()])
                
            if self.offset_entry.get():
                command.extend(["--offset", self.offset_entry.get()])

            if self.reverse_checkbox.get() == 1:
                command.append("--reverse")
            
            if self.write_playlist_checkbox.get() == 1:
                command.append("--write-playlist")
                
            if self.no_skip_existing_checkbox.get() == 1:
                command.append("--no-skip-existing")
            
            # Search options
            if self.fast_search_checkbox.get() == 1:
                command.append("--fast-search")
            
            if self.desperate_checkbox.get() == 1:
                command.append("--desperate")
            
            if self.yt_dlp_checkbox.get() == 1:
                command.append("--yt-dlp")
            
            if self.min_bitrate_entry.get():
                command.extend(["--min-bitrate", self.min_bitrate_entry.get()])
            
            if self.max_bitrate_entry.get():
                command.extend(["--max-bitrate", self.max_bitrate_entry.get()])
                
            # Add preferred and accepted formats
            if self.pref_format_entry.get():
                command.extend(["--pref-format", self.pref_format_entry.get()])
                
            if self.format_entry.get():
                command.extend(["--format", self.format_entry.get()])
            
            listen_port = self.listen_port_entry.get()
            if listen_port and listen_port.isdigit():
                command.extend(["--listen-port", listen_port])

            # Spotify options are now handled by the GUI to fetch the data
            # so we don't need to pass them to slsk-batchdl unless it's a direct Spotify input
            if input_type == "spotify":
                if self.spotify_id_entry.get():
                    command.extend(["--spotify-id", self.spotify_id_entry.get()])
                if self.spotify_secret_entry.get():
                    command.extend(["--spotify-secret", self.spotify_secret_entry.get()])
                
                if self.remove_from_source_checkbox.get() == 1:
                    command.append("--remove-from-source")
            
            self.print_to_output(f"Executing command: {' '.join(command)}\n", "blue")
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # --- Process output line by line to track downloads ---
            for line in process.stdout:
                # Check for successful download patterns
                line_stripped = line.strip()
                if line_stripped.startswith("Downloaded:") or line_stripped.startswith("Skipped existing:"):
                    # Extract the filename and try to match it to a query
                    parts = line_stripped.split(':')
                    if len(parts) > 1:
                        filename_with_ext = parts[1].strip()
                        cleaned_filename = os.path.splitext(filename_with_ext)[0]
                        
                        # Find the corresponding query in our list (case-insensitive)
                        for original_query in self.all_queries:
                            if cleaned_filename.lower() in original_query.lower():
                                self.downloaded_queries.add(original_query)
                                break
                elif "No files found for" in line_stripped:
                    try:
                        query_start = line_stripped.find("'") + 1
                        query_end = line_stripped.rfind("'")
                        failed_query = line_stripped[query_start:query_end]
                        # Only add to failed_downloads if it hasn't been downloaded/skipped
                        if failed_query not in self.downloaded_queries:
                            self.failed_downloads.append((failed_query, "No files found"))
                    except IndexError:
                        pass
                
                self.after(0, self.print_to_output, line)
                
            process.wait()
            
            if process.returncode == 0:
                self.update_status("Download finished successfully!", "green")
            else:
                self.update_status(f"Download failed with exit code {process.returncode}.", "red")

        except FileNotFoundError:
            self.update_status(f"Error: Could not find '{SLDL_EXECUTABLE}'. Make sure it's in the same directory or in your system's PATH.", "red")
        except Exception as e:
            self.update_status(f"An error occurred: {e}", "red")
        finally:
            self.download_button.configure(state="normal", text="Start Download")

    def display_download_summary(self):
        """
        Displays a summary of downloaded vs. non-downloaded songs.
        """
        self.print_to_output("\n" + "="*50, "white")
        self.print_to_output("DOWNLOAD SUMMARY", "white")
        self.print_to_output("="*50 + "\n", "white")

        # Use a set difference for efficient comparison
        all_queries_set = set(self.all_queries)
        not_downloaded_set = all_queries_set - self.downloaded_queries

        if not_downloaded_set:
            self.print_to_output(f"Failed to find or download {len(not_downloaded_set)} out of {len(self.all_queries)} songs:", "red")
            
            # Create a dictionary to map failed queries to reasons
            failed_queries_with_reasons = {query: reason for query, reason in self.failed_downloads}
            
            for query in sorted(list(not_downloaded_set)):
                reason = failed_queries_with_reasons.get(query, "Unknown reason (e.g., download failed, file too small, etc.).")
                self.print_to_output(f"  - {query} (Reason: {reason})", "red")
                
        else:
            self.print_to_output(f"All {len(self.all_queries)} songs were successfully downloaded or skipped!", "green")

        self.print_to_output("\n" + "="*50 + "\n", "white")

    def print_to_output(self, text, color=None):
        """
        Appends text to the output textbox.
        """
        self.output_text.configure(state="normal")
        self.output_text.insert(ctk.END, text)
        self.output_text.see(ctk.END)
        self.output_text.configure(state="disabled")

    def update_status(self, message, color="white"):
        """
        Updates the status label in the footer.
        """
        self.status_label.configure(text=f"Status: {message}", text_color=color)
        
    def open_about(self):
        """Opens the slsk-batchdl GitHub page in a web browser."""
        webbrowser.open(ABOUT_URL)
        
    def open_slsk(self):
        """Opens the Soulseek website in a web browser."""
        webbrowser.open(SLSK_URL)

if __name__ == "__main__":
    app = App()
    app.mainloop()