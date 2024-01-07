import copy
import ctypes
import json
import math
import os
import sys
import threading
from functools import wraps

import customtkinter as ctk
import psutil
from PIL import Image, ImageTk
from customtkinter import filedialog

from file_handler import FileHandler
# -Custom Classes--
from graphics_manager import GraphicsManager, OverlayGraphicsManager
from image_processor import ImageProcessor
from keybinds import KeyBinds, CanvasKeybinds, OverlayKeyBinds
from outliner import Outliner
from tools import Tools, TextInsertWindow


# Icons used in the app were downloaded from https://icons8.com/.

# ---------------Top Level Windows------------------------#
class FileLoadWindow(ctk.CTkToplevel):
    """
      Toplevel window that handles loading and verifying of Images and Project files.
       """

    def __init__(self, app, *args, **kwargs):
        """

        Args:
            app: main ctk.CTK app
            *args:
            **kwargs:
        """
        super().__init__(*args, **kwargs)
        self.app = app
        self.width = min(720, math.ceil(self.winfo_screenwidth() * 0.335))
        height = self.width - 40

        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.screen_width * 0.5625  # 16:9 ratio

        x = (self.screen_width - self.width) // 2
        y = (self.screen_height - height) // 2

        self.geometry(f"{self.width}x{height}+{x}+{y}")
        self.title("Load Window")
        self.resizable(False, False)
        self.configure(fg_color="#282828")

        if sys.platform.startswith('win'):
            self.after(201, lambda: self.iconbitmap(os.path.join("sources", "images", "logo.ico")))
        else:
            self.after(201, lambda: self.iconbitmap(os.path.join("@sources", "images", "logo.xbm")))

        self.columnconfigure((0, 1), weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=2)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(4, weight=1)

        self.file_list = []
        self.file_names = []
        self.corrupted_file_names = []
        self.file_string = None

        self.project_file_path = None
        self.project_status = None
        self.current_protocol = None

        # for the Dropdown menu
        sequence_search_modes = ["Auto", "Normal (_001, -001, file001)", "Pot Player (_015959.999.jpg)",
                                 "VLC Player (vlcsnap-01_59_59...)"]
        self.sequence_search_mode = "auto"

        title_image = ctk.CTkImage(light_image=Image.open(os.path.join("sources", "images", "rview_title.png")),
                                   size=(self.get_rel_width(.537), self.get_rel_width(.063)))

        image_label = ctk.CTkLabel(self, image=title_image, text="")
        image_label.grid(column=0, row=0, columnspan=2, sticky="we", pady=(10, 10), )

        version_lbl = ctk.CTkLabel(self, text="v 1.0", fg_color="transparent")
        version_lbl.place(in_=image_label, relx=.8, rely=1, anchor="ne")

        self.open_btn = ctk.CTkButton(self, text="Open Images", command=self.browse_images, width=130,
                                      height=35, font=("Arial", 18), text_color="#EFEFEF")

        self.load_project_btn = ctk.CTkButton(self, text="Load Project", command=self.browse_project, width=120,
                                              fg_color="#6C6C6C", height=35, font=("Arial", 17))

        self.clear_btn = ctk.CTkButton(self, text="Clear", command=self.clear_file_list,
                                       state="disabled", width=80, height=30,
                                       font=("Arial", 18), fg_color="#d2190d",
                                       hover_color="#6a0c06")

        self.file_list_box = ctk.CTkTextbox(master=self, width=int(self.width * 0.833),
                                            corner_radius=5, fg_color="#1f1f1f",
                                            font=("Arial", 15), wrap="none",
                                            exportselection=False)
        self.file_list_box.configure(state="disabled")
        self.file_list_box.grid(column=0, row=2, sticky='ns', columnspan=2)

        self.open_btn.place(in_=self.file_list_box, relx=0, rely=0.01, anchor="sw")

        self.clear_btn.place(in_=self.file_list_box, relx=1, rely=.99, anchor="ne", bordermode="outside")

        self.load_project_btn.place(in_=self.file_list_box, relx=1, rely=0.02, anchor="se")

        self.count_lbl = ctk.CTkLabel(self, text=f"Total files: {len(self.file_list)}",
                                      fg_color="transparent", font=("Arial", 18))
        self.count_lbl.place(in_=self.file_list_box, relx=0, rely=1, anchor="nw")

        self.sequence_search_combobox = ctk.CTkComboBox(self, values=sequence_search_modes, dropdown_fg_color="#383838",
                                                        justify="left", state="readonly", dropdown_font=("Arial", 15),
                                                        font=("Arial", 15), width=int(self.get_rel_width(.3)),
                                                        command=self.set_sequence_search_mode)

        self.sequence_search_combobox.place(in_=self.file_list_box, relx=.5, rely=1, anchor="n", bordermode="outside")
        self.sequence_search_combobox.set("Sequence Search (Auto)")

        self.file_load_progressbar = ctk.CTkProgressBar(self, orientation="horizontal", fg_color="#282828",
                                                        progress_color="#227AFF", height=10, corner_radius=0)
        self.file_load_progressbar.set(0)
        self.file_load_progressbar.grid(column=0, row=3, columnspan=2, pady=(20, 0), sticky="s")

        self.main_btn = ctk.CTkButton(self, text="Load", command=self.call_load_files, state="disabled",
                                      width=int(self.get_rel_width(0.288)),
                                      height=int(self.get_rel_width(0.076)), font=("Arial", 25), fg_color="#3651D4",
                                      hover_color="#343F74")
        self.main_btn.grid(column=0, row=4, columnspan=2, sticky="n", pady=(10, 0))

        self.path_override_frame = ctk.CTkFrame(self, fg_color="#1D3159", height=80, width=int(self.width * 0.833))

        self.path_override_frame.columnconfigure((0, 2), weight=1)
        self.path_override_frame.columnconfigure(1, weight=0)
        self.path_override_frame.rowconfigure((0, 1), weight=1)
        self.path_override_frame.grid_propagate(False)

        path_override_label = ctk.CTkLabel(self.path_override_frame, text="Path to the Images:", font=("Arial", 16))
        path_override_label.grid(row=0, column=0, sticky="e")

        self.path_override_entry_var = ctk.StringVar()
        self.path_override_entry = ctk.CTkEntry(self.path_override_frame,
                                                width=int(self.width * 0.43), height=35,
                                                fg_color="#C7C7C7",
                                                placeholder_text_color="#363636",
                                                text_color="Black", exportselection=False,
                                                textvariable=self.path_override_entry_var, font=("Arial", 14))
        self.path_override_entry.grid(row=0, column=1, )
        self.path_override_entry_var.trace_add("write", self.folder_override_entrybox_updated)

        self.pick_override_path_btn = ctk.CTkButton(self.path_override_frame, text="Pick", fg_color="#c43737", width=60,
                                                    hover_color="#632020", command=self.pick_override_path_btn_handler)
        self.pick_override_path_btn.grid(row=0, column=2)

        ignore_images_label = ctk.CTkLabel(self.path_override_frame, text="Ignore Missing Images:", font=("Arial", 16))
        ignore_images_label.grid(row=1, column=0, sticky="e")

        self.ignore_images_checkbox = ctk.CTkCheckBox(self.path_override_frame, text="", width=5, )
        self.ignore_images_checkbox.grid(row=1, column=1, sticky="w", padx=21, )
        self.ignore_images_checkbox.configure(state="disabled")

        ignore_images_toolip = ctk.CTkLabel(self.path_override_frame, text="(Generates blanks in the provided path.)",
                                            font=("Arial", 14))
        ignore_images_toolip.place(in_=self.ignore_images_checkbox, relx=1, rely=0, anchor="nw")

        # Closing the window kills the App.
        self.protocol("WM_DELETE_WINDOW", self.kill_app)

    def pick_override_path_btn_handler(self):
        override_folder_path = filedialog.askdirectory(parent=self, title="Select images folder.")
        if override_folder_path:
            self.path_override_entry_var.set(override_folder_path)

    def get_rel_width(self, times):
        """
        Method that returns a relative width of the window times a value.

        Args:
            times(float): A value that multiplies the window width.

        Returns:
            float: Resulting float value.

        """
        rel_width = self.width * times
        return rel_width

    def set_sequence_search_mode(self, choice: str):
        """
        Called on selecting a search mode from the dropdown menu in the FileLoad window.
        Sets the sequence search mode to the selected mode.

        Args:
            choice:Sequence search mode to extract the sequence pattern from the filenames. Deafault "auto".

        Returns:
                None
        """
        # Normal (_001, -001, file001)= Normal
        self.sequence_search_mode = choice.split()[0].lower()

    def browse_images(self):
        """
        Browse and load Images and sets the current_protocol to "images".

        Returns:
            None
        """
        self.disable_buttons()
        # opened_files = filedialog.askopenfilenames(title="Select Files",
        # filetypes=([("Image Files","*.bmp;*.gif;*.icns;*.ico;*.im;*.jpeg;*.jpg;*.jfif;*.jpeg2000;*.png;*.ppm;*.tga;*.tif;*.tiff;*.webp")]))

        opened_files = filedialog.askopenfilenames(parent=self, title="Select Files",
                                                   filetypes=[("Image Files",
                                                               ".bmp .BMP .gif .GIF .icns .ICNS .ico .ICO .im .IM .jpeg .JPEG .jpg .JPG .jfif .JFIF .jpeg2000 .JPEG2000 .png .PNG .ppm .PPM .tga .TGA .tif .TIF .tiff .TIFF .webp .WEBP"),
                                                              ("All Files", "*.*")])

        if opened_files or self.file_list:
            # If the user used the file load window to load an image, change protocol from project to image.
            if opened_files:
                self.change_protocol("images")
                for file in opened_files:
                    extracted_filename = file.rsplit('/', 2)[-1] + "\n\n"
                    if file not in self.file_list:
                        # validating images.
                        valid_image = FileHandler.validate_image(image=file)
                        if valid_image:
                            self.file_names.append(extracted_filename)
                            self.file_list.append(file)
                        elif extracted_filename not in self.corrupted_file_names:
                            # Storing the corrupted filenames.
                            self.corrupted_file_names.append(extracted_filename)

            file_list_string = ""

            if self.file_list and self.corrupted_file_names:
                file_list_string = "".join(self.file_names) + "\n\nOne or more files failed to load:\n\n" + "".join(
                    self.corrupted_file_names)

            elif self.file_list:
                file_list_string = "".join(self.file_names)

            elif self.corrupted_file_names:
                file_list_string = "One or more files failed to load:\n\n" + "".join(self.corrupted_file_names)
                self.change_protocol("fail")

            self.file_string = file_list_string
            self.update_file_list_box(string=self.file_string, count=len(self.file_list))

        if self.current_protocol == "images" or self.current_protocol == "project":
            self.enable_buttons()

        self.enable_input_buttons()

    def browse_project(self):
        """
        Browse and load a saved project file and sets the current_protocol to "project".

        Returns:
                None
        """

        self.disable_buttons()
        opened_file = filedialog.askopenfilename(parent=self, title="Select File", filetypes=[("RView", "*.rvp")])
        if opened_file:
            # If the user used the file load window to load a project, change protocol from image to project.
            project_file_validated = FileHandler.validate_project_file(opened_file)
            if project_file_validated:
                self.change_protocol("project")
                self.project_status = True
                self.project_file_path = opened_file
                self.update_file_list_box(string="Validating Project file...\n\nProject successfully loaded.",
                                          count=1)
            else:  # project validation failed.
                self.change_protocol("fail")
                self.update_file_list_box(
                    string="Validating Project file...\n\nProject loading failed.\n\nReason: Missing source files or Corrupted save.",
                    count=0)

        if self.current_protocol == "images" or self.current_protocol == "project":
            self.enable_buttons()

        self.enable_input_buttons()

    def call_load_files(self):
        """
        Loads images or project and calls the load_images method on App.

        Returns:
                None
        """

        if self.current_protocol == "images":
            try:
                self.app.load_images()
            except Exception as e:  # Failed to load the image even after full validation.
                error_message = '''The following error occurred:\n\n{}'''.format(e)
                self.clear_file_list()
                # shows the error message on the file_list_box
                self.update_file_list_box(string=error_message, count=0)
                self.file_list_box.see(0.0)
            else:
                self.destroy()

        elif self.current_protocol == "project":
            if self.ignore_images_checkbox.get():
                ignore_missing_images = True
            else:
                ignore_missing_images = False

            try:
                if images_folder_path := self.path_override_entry.get().strip():  # Passing the new folderpath to the images.
                    self.update_file_list_box(string="Retrying....\nFetching images...", count=1)
                    self.app.load_project(project_path=self.project_file_path,
                                          images_folder_override_path=images_folder_path,
                                          ignore_missing_images=ignore_missing_images)

                else:
                    self.app.load_project(project_path=self.project_file_path)

            except FileNotFoundError:
                if self.path_override_entry.get():
                    self.path_override_entry.configure(fg_color="#EEA2A2")  # a red color

                self.update_file_list_box()
                error_message = f"The following error occurred:\n\nOne or more Image files missing.\nProvide a valid path to the images folder."
                self.update_file_list_box(string=error_message, count=0)
                self.file_list_box.see(0.0)
                self.path_override_frame.place(in_=self.file_list_box, relx=0, rely=1, anchor="sw")
                self.enable_buttons()
            #
            except Exception as e:  # Failed to load the project even after full validation.

                error_message = f"The following error occurred:\n\nCorrupted Save.\nTry loading the project again. \nError: {e}"
                self.clear_file_list()
                # shows the error message on the file_list_box
                self.update_file_list_box(string=error_message, count=0)
                self.file_list_box.see(0.0)
            else:
                self.destroy()

    def folder_override_entrybox_updated(self, *args):
        """
        Called when path_override_entry box is updated with a value. If the entry box is empty disable the ignore_missing_image checkbox.

        Args:
            *args:

        Returns:
            None

        """
        entry_value = self.path_override_entry_var.get().strip()
        if entry_value:  # Check if the entry box is not empty
            self.ignore_images_checkbox.configure(state="normal")
        else:
            self.ignore_images_checkbox.deselect()
            self.ignore_images_checkbox.configure(state="disabled")

    def change_protocol(self, new_protocol):
        """
        Change the protocol between "images" , "project" or "fail".

        Args:
            new_protocol (str): Current protocol to use.

        Returns:
            None

        """
        self.path_override_frame.place_forget()
        self.path_override_entry.delete(0, "end")

        if new_protocol == "project":
            self.file_list = []
            self.file_names = []
            self.corrupted_file_names = []
            self.file_string = None
            self.current_protocol = "project"
            self.enable_buttons()

        elif new_protocol == "images":
            self.project_status = None
            self.project_file_path = None
            self.current_protocol = "images"
            self.enable_buttons()

        elif new_protocol == "fail":  # Reset everything on fail.
            self.file_list = []
            self.file_names = []
            self.corrupted_file_names = []
            self.file_string = None
            self.project_status = None
            self.project_file_path = None
            self.current_protocol = "fail"
            self.enable_buttons()
            self.main_btn.configure(state="disabled")

    def update_file_list_box(self, string: str = "", count: int = 0):
        """
        Updates the textbox on the file load window.

        Args:
            string (str): Text to display
            count (int): Count of files loaded.

        Returns:
            None
        """
        self.file_list_box.configure(state="normal")
        self.file_list_box.delete("0.0", "end")
        self.file_list_box.insert("0.0", string)
        self.file_list_box.see("end")
        self.count_lbl.configure(text=f"Total files: {count}")
        self.file_list_box.configure(state="disabled")

    def enable_buttons(self):
        """
        Enables all buttons on the FileLoad window.

        Returns:
            None

        """

        self.main_btn.configure(state="normal")
        self.clear_btn.configure(state="normal", )
        self.load_project_btn.configure(state="normal")
        self.open_btn.configure(state="normal")

    def disable_buttons(self):
        """
         Disables all buttons on the FileLoad window.

        Returns:
            None
        """

        self.main_btn.configure(state="disabled")
        self.clear_btn.configure(state="disabled")
        self.load_project_btn.configure(state="disabled")
        self.open_btn.configure(state="disabled")

    def enable_input_buttons(self):
        """
          Enables all input buttons on the FileLoad window.

         Returns:
             None
         """

        self.load_project_btn.configure(state="normal")
        self.open_btn.configure(state="normal")

    def clear_file_list(self):
        """
        Clears all variables and resets the FileLoad window to initial state.

        Returns:
            None

        """
        self.path_override_frame.place_forget()
        self.path_override_entry.delete(0, "end")
        self.file_list = []
        self.file_names = []
        self.corrupted_file_names = []
        self.file_string = None
        self.project_file_path = None
        self.project_status = None
        self.current_protocol = None
        self.update_file_list_box()
        self.disable_buttons()
        self.enable_input_buttons()

    def update_file_window_progressbar(self, progress: float, progress_color: str = None):
        """
        Updates the file_load_progressbar.

        Args:
            progress (float):A float of range 0 to 1.0 with 1.0 filling the progressbar 100%.
            progress_color (str):A hex color value for the progression color in the progressbar.

        Returns:
            None

        """
        progress = round(progress, 2)
        if progress_color:
            self.file_load_progressbar.configure(progress_color=progress_color)
        self.file_load_progressbar.set(progress)
        self.file_load_progressbar.update_idletasks()

    def kill_app(self):
        """
        Kills the main app.

        Returns:
            None

        """
        self.app.kill_app()


class UserSettingsWindow(ctk.CTkToplevel):
    """
    Toplevel window that handles user settings of the app.
    """

    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app
        width = 250
        height = 200
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.screen_width * 0.5625  # clamps window to 16:9 ratio.
        x = (self.screen_width - width) // 2
        y = (self.screen_height - height) // 2

        MAIN_COLOR = "#28333E"
        self.title("User Settings")
        self.configure(fg_color=MAIN_COLOR)  # Darkish blue
        # 200 ms solves the bug with iconbitmap on toplevel windows.
        if sys.platform.startswith('win'):
            self.after(201, lambda: self.iconbitmap(os.path.join("sources", "images", "logo.ico")))
        else:
            self.after(201, lambda: self.iconbitmap(os.path.join("@sources", "images", "logo.xbm")))

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)

        self.columnconfigure(0, weight=1)
        self.rowconfigure((0, 1, 2), weight=1)

        menu_label = ctk.CTkLabel(self, text="User Settings", font=("Arial Bold", 16))
        menu_label.grid(row=0, column=0, )

        # ========Check Boxes=====================================

        self.reset_user_settings_btn = ctk.CTkButton(self, text="Reset", command=self.reset_user_settings,
                                                     width=50, height=12, font=("Arial", 12),
                                                     fg_color="#931C14", hover_color="#4E1414", text_color="#D2D2D2",
                                                     corner_radius=5)
        self.reset_user_settings_btn.place(x=0, y=0)

        self.dropdown_frame = ctk.CTkFrame(self, fg_color=MAIN_COLOR)
        self.dropdown_frame.columnconfigure((0, 1), weight=1)
        self.dropdown_frame.rowconfigure((0, 1, 2, 3, 4, 5), weight=1)
        self.dropdown_frame.grid(row=1, column=0, sticky="news")

        canvas_color_label = ctk.CTkLabel(self.dropdown_frame, text="Canvas Color:", font=("Arial", 16), width=0)
        canvas_color_label.grid(row=2, column=0, sticky='e')
        self.canvas_color_dropdown = ctk.CTkOptionMenu(self.dropdown_frame,
                                                       values=["Default", "Black", "Grey", "White"],
                                                       width=20, height=25)
        self.canvas_color_dropdown.grid(row=2, column=1, sticky='w', padx=(5, 0))
        self.canvas_color_dropdown.set((self.app.user_settings["canvas_color"]).capitalize())

        selection_color_label = ctk.CTkLabel(self.dropdown_frame, text="Selection Color:", font=("Arial", 16), width=0)
        selection_color_label.grid(row=4, column=0, sticky='e')
        self.selection_color_dropdown = ctk.CTkOptionMenu(self.dropdown_frame,
                                                          values=["Blue", "Pink", "Red", "Green"],
                                                          width=20, height=25)
        self.selection_color_dropdown.grid(row=4, column=1, sticky='w', padx=(5, 0))
        self.selection_color_dropdown.set((self.app.user_settings["selection_color"]).capitalize())

        highlight_opacity_label = ctk.CTkLabel(self.dropdown_frame, text="Highlight Opacity:", font=("Arial", 16),
                                               width=0)
        highlight_opacity_label.grid(row=5, column=0, sticky='e')

        self.highlight_opacity_slider_value_label = ctk.CTkLabel(self,
                                                                 text=self.app.user_settings["highlight_opacity"],
                                                                 font=("Arial", 16), width=0)

        self.highlight_opacity_slider = ctk.CTkSlider(self.dropdown_frame,
                                                      from_=1, to=99, width=int(width * 0.4),
                                                      number_of_steps=98,
                                                      command=lambda
                                                      event: self.highlight_opacity_slider_value_label.configure(
                                                      text=int(event)))

        self.highlight_opacity_slider_value_label.place(in_=self.highlight_opacity_slider, relx=.8, rely=0, anchor="sw")
        self.highlight_opacity_slider.set(self.app.user_settings["highlight_opacity"])
        self.highlight_opacity_slider.grid(row=5, column=1, sticky='w', padx=(5, 0))

        # ================Output ==================================

        self.save_user_settings_btn = ctk.CTkButton(self, text="Save Settings", command=self.save_user_settings,
                                                    width=150, height=35, font=("Arial bold", 17),
                                                    fg_color="#3568B5", hover_color="#213D67", text_color="white")

        self.save_user_settings_btn.grid(column=0, row=3, pady=5)

    def save_user_settings(self):
        """
        Calls the save_user_settings on main app and Kills the toplevelwindow.

        Returns:
            None
        """

        canvas_color = self.canvas_color_dropdown.get().lower()
        selection_color = self.selection_color_dropdown.get().lower()
        highlight_opacity = int(self.highlight_opacity_slider.get())

        self.app.user_settings = {"canvas_color": canvas_color,
                                  "selection_color": selection_color,
                                  "highlight_opacity": highlight_opacity,
                                  }

        self.app.update_user_settings()

        self.destroy()

    def reset_user_settings(self):
        """
        Replaces the user settings.json file with a new file with default values.

        Returns:
            None

        """
        self.app.load_user_settings(reset=True)
        self.destroy()


class RenderMenu(ctk.CTkToplevel):
    """
    Toplevel window that handles the render settings and starting the render.
    """

    def __init__(self, app, batch: bool, *args, **kwargs):
        """

         Args:
             app: main ctk.CTK app
             batch (bool): Mode to render the images, True adds all queued images to render. False renders the current image in view.
             **kwargs:
         """
        super().__init__(*args, **kwargs)

        self.app = app
        self.is_batch = batch

        width = 350
        height = 350
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.screen_width * 0.5625  # clamps window to 16:9 ratio.
        x = (self.screen_width - width) // 2
        y = (self.screen_height - height) // 2

        main_color = "#263142"
        self.title("Render Menu")
        self.configure(fg_color=main_color)  # Darkish blue
        # 200 ms solves the bug with iconbitmap on toplevel windows.
        if sys.platform.startswith('win'):
            self.after(201, lambda: self.iconbitmap(os.path.join("sources", "images", "logo.ico")))
        else:
            self.after(201, lambda: self.iconbitmap(os.path.join("@sources", "images", "logo.xbm")))

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)

        self.columnconfigure(0, weight=1)
        self.rowconfigure((0, 1, 2), weight=1)

        menu_label = ctk.CTkLabel(self, text="Render Settings", font=("Arial Bold", 16))
        menu_label.grid(row=0, column=0, )

        # ========Check Boxes=====================================
        checkbox_border = 1

        self.checkbox_frame = ctk.CTkFrame(self, fg_color=main_color)
        self.checkbox_frame.columnconfigure((0, 1), weight=1)
        self.checkbox_frame.rowconfigure((0, 1, 2, 3), weight=1)
        self.checkbox_frame.grid(row=1, column=0, sticky="news")

        render_overlay_label = ctk.CTkLabel(self.checkbox_frame, text="Render Overlay:", font=("Arial", 16))
        render_overlay_label.grid(row=1, column=0, sticky='e')
        self.render_overlay_checkbox = ctk.CTkCheckBox(self.checkbox_frame, text="", onvalue=1, offvalue=0,
                                                       border_width=checkbox_border,
                                                       command=self.render_overlay_checkbox_handler)
        if self.app.render_overlay:
            self.render_overlay_checkbox.select()
        self.render_overlay_checkbox.grid(row=1, column=1, sticky='w', padx=(25, 0))

        self.overlay_trim_label = ctk.CTkLabel(self.checkbox_frame, text="Trim:", font=("Arial", 16))
        self.overlay_trim_label.place(in_=self.render_overlay_checkbox, relx=0.5, rely=0, anchor="nw",
                                      bordermode="outside")
        self.overlay_trim_label.configure(text_color="grey")

        self.trim_overlay_checkbox = ctk.CTkCheckBox(self.checkbox_frame, text="", onvalue=1, offvalue=0,
                                                     border_width=checkbox_border, width=0,
                                                     command=self.overlay_trim_checkbox_handler)

        self.trim_overlay_checkbox.place(in_=self.overlay_trim_label, relx=1.2, rely=0, anchor="nw",
                                         bordermode="outside", )
        self.trim_overlay_checkbox.configure(state="disabled", fg_color="grey")

        if self.app.render_overlay:  # Populating with values.
            self.overlay_trim_label.configure(text_color="#DADADA")
            self.trim_overlay_checkbox.configure(state="normal", fg_color="#1F6AA5")
            if self.app.trim_overlay:
                self.trim_overlay_checkbox.select()

        sequence_code_label = ctk.CTkLabel(self.checkbox_frame, text="Sequence Code:", font=("Arial", 16), width=0)
        sequence_code_label.grid(row=2, column=0, sticky='e')
        self.sequence_code_checkbox = ctk.CTkCheckBox(self.checkbox_frame, text="", onvalue=1, offvalue=0, width=0,
                                                      border_width=checkbox_border,
                                                      command=self.sequence_code_checkbox_handler)
        if self.app.render_sequence_code:
            self.sequence_code_checkbox.select()
        self.sequence_code_checkbox.grid(row=2, column=1, sticky='w', padx=(25, 0))

        self.sequence_code_position_dropdown = ctk.CTkOptionMenu(self.checkbox_frame,
                                                                 values=["Top-Left", "Top-Right", "Bottom-Left",
                                                                         "Bottom-Right"],
                                                                 width=20,
                                                                 command=self.sequence_code_position_dropdown_handler,
                                                                 height=25)
        self.sequence_code_position_dropdown.place(in_=self.sequence_code_checkbox, relx=2.7, rely=0.5, anchor="center",
                                                   bordermode="outside", )

        if self.app.render_sequence_code:
            current_position = self.app.sequence_code_render_position
            if current_position == "ne":
                self.sequence_code_position_dropdown.set("Top-Right")
            if current_position == "sw":
                self.sequence_code_position_dropdown.set("Bottom-Left")
            if current_position == "se":
                self.sequence_code_position_dropdown.set("Bottom-Left")
            else:
                self.sequence_code_position_dropdown.set("Top-Left")
        else:
            self.sequence_code_position_dropdown.configure(state="disabled")

        anti_alias_label = ctk.CTkLabel(self.checkbox_frame, text="Enable Anti-alias:", font=("Arial", 16))
        anti_alias_label.grid(row=3, column=0, sticky='e')
        self.anti_alias_checkbox = ctk.CTkCheckBox(self.checkbox_frame, text="", onvalue=1, offvalue=0,
                                                   border_width=checkbox_border,
                                                   command=self.anti_alias_checkbox_handler)
        if self.app.anti_alias_output:
            self.anti_alias_checkbox.select()
        self.anti_alias_checkbox.grid(row=3, column=1, sticky='w', padx=(25, 0))

        if self.is_batch:
            include_blank_label = ctk.CTkLabel(self.checkbox_frame, text="Include Blanks:", font=("Arial", 16))
            include_blank_label.grid(row=4, column=0, sticky='e')
            self.include_blanks_checkbox = ctk.CTkCheckBox(self.checkbox_frame, text="", onvalue=1, offvalue=0,
                                                           border_width=checkbox_border,
                                                           command=self.include_blanks_checkbox_handler)
            if self.app.include_blanks:
                self.include_blanks_checkbox.select()
            self.include_blanks_checkbox.grid(row=4, column=1, sticky='w', padx=(25, 0))

        jpeg_quality_label = ctk.CTkLabel(self.checkbox_frame, text="JPEG Quality:", font=("Arial", 16))
        jpeg_quality_label.grid(row=5, column=0, sticky='e')

        self.jpeg_quality_slider = ctk.CTkSlider(self.checkbox_frame, from_=0, to=100, width=int(width * 0.4),
                                                 command=self.jpeg_quality_slider_event_handler,
                                                 number_of_steps=100, )
        self.jpeg_quality_slider.grid(row=5, column=1, sticky='w')

        self.jpeg_quality_slider_value_label = ctk.CTkLabel(self.checkbox_frame, text=self.app.jpeg_quality,
                                                            font=("Arial Bold", 12))
        self.jpeg_quality_slider_value_label.place(in_=self.jpeg_quality_slider, relx=1.1, rely=0.5, anchor="center",
                                                   bordermode="outside")
        self.jpeg_quality_slider.set(self.app.jpeg_quality)
        self.jpeg_quality_slider_event_handler(value=self.app.jpeg_quality)

        png_compression_label = ctk.CTkLabel(self.checkbox_frame, text="PNG Compression:", font=("Arial", 16))
        png_compression_label.grid(row=6, column=0, sticky='e')

        self.png_compression_slider = ctk.CTkSlider(self.checkbox_frame, from_=0, to=9, width=int(width * 0.4),
                                                    command=self.png_compression_slider_event_handler,
                                                    number_of_steps=9, )
        self.png_compression_slider.grid(row=6, column=1, sticky='w')
        self.png_compression_slider.set(self.app.png_compression)

        self.png_compression_slider_value_label = ctk.CTkLabel(self.checkbox_frame, text=self.app.png_compression,
                                                               font=("Arial Bold", 12))
        self.png_compression_slider_value_label.place(in_=self.png_compression_slider, relx=1.1, rely=0.5,
                                                      anchor="center",
                                                      bordermode="outside")
        self.png_compression_slider_event_handler(value=self.app.png_compression)

        # ================Output ==================================
        self.output_frame = ctk.CTkFrame(self, fg_color=main_color)
        self.output_frame.columnconfigure((0, 1), weight=1)
        self.output_frame.rowconfigure((0, 1, 2, 3), weight=1)
        self.output_frame.grid(row=2, column=0, sticky="news", pady=(10, 0))

        output_path_label = ctk.CTkLabel(self.output_frame, text="Output Path:", font=("Arial", 14))
        output_path_label.grid(row=0, column=0, sticky="e")

        self.output_path_btn = ctk.CTkButton(self.output_frame, text="Pick Path", command=self.pick_path,
                                             state="normal",
                                             width=80, height=15, font=("Arial", 15),
                                             fg_color="#d2190d", hover_color="#6a0c06", corner_radius=5)
        self.output_path_btn.grid(row=0, column=1, padx=(0, 40))

        self.output_path_textbox = ctk.CTkTextbox(master=self.output_frame, width=200, height=4, corner_radius=5,
                                                  fg_color="#D9D9D9", wrap="none", font=('Arial', 15),
                                                  text_color="black", )

        self.output_path_textbox.grid(column=0, row=1, columnspan=2)
        self.output_path_textbox.insert("0.0", self.app.output_path)
        if os.path.exists(self.app.output_path):
            self.output_path_textbox.configure(fg_color="#b7ffb0")  # A shade of green if file output path exists.

        self.render_progressbar = ctk.CTkProgressBar(self.output_frame, orientation="horizontal", fg_color=main_color,
                                                     progress_color=main_color)
        self.render_progressbar.set(0)
        self.render_progressbar.grid(column=0, row=2, columnspan=2)

        self.render_images_btn = ctk.CTkButton(self.output_frame, text="Render Images", command=self.start_render,
                                               width=150, height=35, font=("Arial bold", 17),
                                               fg_color="#3568B5", hover_color="#213D67", text_color="white")

        self.render_images_btn.grid(column=0, row=3, columnspan=2, pady=(5, 10))

        if not self.is_batch:  # If not batch configure the render button to batch False.
            self.render_images_btn.configure(text="Render Image")
            self.render_images_btn.configure(command=lambda: self.start_render(batch=False))

        self.protocol("WM_DELETE_WINDOW", self.kill_window)

    def render_overlay_checkbox_handler(self):
        """
        Called on toggling the render_overlay_checkbox.
        Returns:
            None

        """
        if self.render_overlay_checkbox.get() == 1:
            self.app.render_overlay = True
            self.overlay_trim_label.configure(text_color="#DADADA")
            self.trim_overlay_checkbox.configure(state="normal", fg_color="#1F6AA5")
        else:
            self.app.render_overlay = False
            self.overlay_trim_label.configure(text_color="grey")
            self.trim_overlay_checkbox.configure(state="disabled", fg_color="grey")

    def overlay_trim_checkbox_handler(self):
        """
        Called on toggling the trim_overlay_checkbox.

        Returns:
            None
        """
        if self.trim_overlay_checkbox.get() == 1:
            self.app.trim_overlay = True
        else:
            self.app.trim_overlay = False

    def sequence_code_checkbox_handler(self):

        if self.sequence_code_checkbox.get() == 1:
            self.app.render_sequence_code = True
            self.sequence_code_position_dropdown.configure(state="normal")
        else:
            self.app.render_sequence_code = False
            self.sequence_code_position_dropdown.configure(state="disabled")

    def sequence_code_position_dropdown_handler(self, choice):
        choice = choice.lower()
        if choice == "top-right":
            self.app.sequence_code_render_position = "ne"
        elif choice == "bottom-left":
            self.app.sequence_code_render_position = "sw"
        elif choice == "bottom-right":
            self.app.sequence_code_render_position = "se"
        else:
            self.app.sequence_code_render_position = "nw"

    def anti_alias_checkbox_handler(self):
        if self.anti_alias_checkbox.get() == 1:
            self.app.anti_alias_output = True
        else:
            self.app.anti_alias_output = False

    def include_blanks_checkbox_handler(self):
        if self.include_blanks_checkbox.get() == 1:
            self.app.include_blanks = True
        else:
            self.app.include_blanks = False

    def jpeg_quality_slider_event_handler(self, value):
        """
        Called on updating the jpeg_quality_slider.

        Returns:
            None
        """

        value = int(value)
        self.app.jpeg_quality = value

        if value == 75:
            text_color = "white"
        elif 75 < value <= 85:
            text_color = "#BCFFD7"
        elif value > 85:
            text_color = "#9BFF99"
        elif 75 > value >= 50:
            text_color = "#FFE5B1"
        elif 50 > value > 0:
            text_color = "#FF8D4E"
        elif value == 0:
            text_color = "red"
        else:
            text_color = "white"

        self.jpeg_quality_slider_value_label.configure(text=int(value), text_color=text_color)

    def png_compression_slider_event_handler(self, value):
        value = int(value)

        self.app.png_compression = value
        if value <= 3:
            text_color = "white"
        elif 3 < value <= 6:
            text_color = "orange"
        elif value > 6:
            text_color = "red"
        else:
            text_color = "white"
        self.png_compression_slider_value_label.configure(text_color=text_color, text=value)

    def pick_path(self):
        """
        Opens a filedialog.askdirectory window for the user to set a folder path for the output images.

        Returns:
            None
        """

        self.output_path_btn.configure(state="disabled")

        self.app.output_path = filedialog.askdirectory(parent=self)
        # self.deiconify()
        if not self.app.output_path:
            self.app.output_path = "images"

        # Clears the path_textbox and inserts the chosen filepath.
        self.output_path_textbox.delete("0.0", "end")
        self.output_path_textbox.insert("0.0", self.app.output_path)
        self.output_path_btn.configure(state="normal")

    def start_render(self, batch: bool = True):
        """
        Starts the render process by calling the render_images method from ImageProcessor.

        Args:
            batch(bool):True sets the mode to batch and adds all images in queue to render.False renders the current image in view. Default True

        Returns:
            None

        """

        self.app.output_path = self.output_path_textbox.get(0.0, "end").strip()

        if os.path.exists(self.app.output_path):
            self.output_path_textbox.configure(fg_color="#b7ffb0", )
            self.render_progressbar.configure(progress_color="#008F39", fg_color="#6D7684")  # dark green

            # Using threading for rendering images to prevent GUI freeze during the processing.
            threading.Thread(target=self.app.image_processor.render_images, kwargs={'batch': batch},
                             daemon=True).start()

        else:
            # On invalid folder path, change path_textbox to red.
            self.output_path_textbox.configure(fg_color="#ff7575")

    def update_progress_bar(self, progress: float, status: bool):
        """
        Updates the render_progressbar widget on the RenderMenu window based on the files processed.

        Args:
            progress (float):A value between 0-1.
            status (bool): True indicates a success transfer, False indicates a failed render.

        Returns:
            None
        """

        if status == 1:
            self.render_progressbar.configure(progress_color="#008F39")
            self.render_progressbar.set(progress)

            if progress == 1:
                # on completion setting the progress bar to a bright green.
                self.render_progressbar.configure(progress_color="#00FE66")

        else:
            self.render_progressbar.set(1)
            self.render_progressbar.configure(progress_color="#E20000")  # red

        self.update_idletasks()

    def kill_window(self):
        """
        Kills the RenderMenu toplevel window.

        Returns:
            None
        """
        # If window was killed during render, display a render interrupted message.
        if self.render_progressbar.get() not in (0, 1):
            self.app.error_prompt.display_error_prompt(error_msg="Render Interrupted!", priority=1)

        self.destroy()


class ExitPrompt(ctk.CTkToplevel):
    """
    Toplevel window that handles the exit prompt.
    """

    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)

        width = 200
        height = 200
        self.app = app
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.screen_width * 0.5625
        x = (self.screen_width - width) // 2
        y = (self.screen_height - height) // 2
        self.title("Quit?")
        if sys.platform.startswith('win'):
            self.after(201, lambda: self.iconbitmap(os.path.join("sources", "images", "logo.ico")))
        else:
            self.after(201, lambda: self.iconbitmap(os.path.join("@sources", "images", "logo.xbm")))

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)

        btn_pady = 10
        btn_width = 120

        self.save_exit_btn = ctk.CTkButton(self, text="Save & Exit", command=self.save_and_exit,
                                           state="normal",
                                           width=btn_width, height=45, font=("Arial bold", 17),
                                           fg_color="#3568B5", hover_color="#213D67")

        self.save_exit_btn.pack(pady=(20, btn_pady))

        # Calls the function that calls a function in the main window that kills the window.
        self.exit_btn = ctk.CTkButton(self, text="Exit", command=self.exit_main_app, state="normal",
                                      width=btn_width, height=45, font=("Arial bold", 17),
                                      fg_color="#d2190d", hover_color="#6a0c06")
        self.exit_btn.pack(pady=btn_pady)

        # Destroys the exit prompt window.
        self.cancel_btn = ctk.CTkButton(self, text="Cancel", command=self.destroy, state="normal",
                                        width=btn_width, height=45, font=("Arial bold", 17),
                                        fg_color="#7e7d82", hover_color="#58575a")

        self.cancel_btn.pack(pady=btn_pady)

    def save_and_exit(self):
        """
          Calls the save_data method on the App class and kills the program on valid save.

          Returns:
              None

          """

        # Returns True on valid save.
        saved = self.app.save_data(from_exit_prompt=True)
        if saved:
            self.after(200)
            self.app.kill_app()
        elif saved == False:
            self.app.error_prompt.display_error_prompt(error_msg="Project Failed to save", priority=1)

    def exit_main_app(self):
        """
        Kills the main App.

        Returns:
                None
        """
        self.app.kill_app()


# ------------Pop Up Widget------------------#
class ErrorPrompt(ctk.CTkButton):
    """
    A ctk button repurposed to be an Error Popup within the image frame.
    """

    def __init__(self, master, *args, **kwargs):
        super().__init__(master=master, *args, **kwargs)
        self.parent = master
        self.error_prompt_in_display = False
        # Hides the pop-up on mouse hover.
        self.bind("<Enter>", self.hide_error_prompt)

    def display_error_prompt(self, error_msg: str, priority=2):
        """
        Displays the error prompt window with the error message.

        Args:
            error_msg (str): The error message to display.
            priority (int): Integer values of 1,2,3 representing the priority of the error. 1=red,3=green. Default 2=Orange.

        Returns:
            None

        """
        if priority == 1:
            prompt_col = "red"
        elif priority == 2:
            prompt_col = "#D46702"  # orange
        else:
            prompt_col = "#007822"  # dark green
        height = self.parent.winfo_height() * 0.05

        rely_value = -height / self.parent.winfo_height()

        self.y_pos = rely_value

        self.configure(text=error_msg,
                       width=self.parent.winfo_width(), height=height,
                       fg_color=prompt_col, font=("Arial Bold", 16), bg_color=prompt_col,
                       corner_radius=0, hover=False, )

        self.animate_error_prompt()

    def animate_error_prompt(self):
        """
        Method that slightly animates the error prompt entering and leaving the image_frame.

        Returns:
            None

        """

        self.place(relx=0, rely=self.y_pos)
        self.y_pos += 0.01

        if self.y_pos <= 0:
            self.after(20, self.animate_error_prompt)
        else:
            self.y_pos = 0
            self.place(relx=0, rely=0)
            self.error_prompt_in_display = True

    def hide_error_prompt(self, event=None, animate: bool = True):
        """
        Hides the error prompt popup.

        Args:
            event (optional): Tkinter mouse hover event.
            animate (bool): True hides the popup with an animation, False instantly hides the popup. Default True.

        Returns:
                None
        """

        if animate:
            self.y_pos += -0.01
            self.place(relx=0, rely=self.y_pos)

            if self.y_pos >= -0.05:
                self.after(20, self.hide_error_prompt)
            else:
                self.place_forget()
                self.error_prompt_in_display = False
        else:
            self.place_forget()
            self.error_prompt_in_display = False


# ====----Main app Window-------=======-#

class App(ctk.CTk):
    """
    Master window of the program.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # dark mode
        ctk.set_appearance_mode("dark")

        self.image_data = {}
        self.project_data = {}
        self.settings_data = {}
        self.graphics_data = {}
        self.proxy_data = {}
        self.loaded_graphics_data = {}  # Used for loading project.
        self.user_settings = None
        self.user_settings_window = None

        # ----------Render Output Options---------
        self.render_menu = None
        self.render_overlay = True
        self.trim_overlay = True
        self.render_sequence_code = False
        self.sequence_code_render_position = "nw"
        self.anti_alias_output = True
        self.include_blanks = False
        self.jpeg_quality = 75
        self.png_compression = 3
        self.output_path = "images"
        # --------------------------------------
        self.images = []  # List of image filepaths
        self.image_index = 0  # 0 important for loading files
        self.available_index = 0
        self.previous_image_index = -1
        self.last_viewed_image_index = 0
        self.current_hovered_btn_index = -1

        # -----------Widget Colors-------------
        self.default_col = "#242424"
        self.index_queue_col = "#1F57AB"
        self.index_queue_txt_col = "#EBEBEB"
        self.index_removed_col = "#585A5B"
        self.index_removed_txt_col = "#A1A1A1"

        self.index_queue_comment_col = "#279258"
        self.index_queue_comment_txt_col = "white"
        self.index_queue_comment_remove_col = "#496F5A"

        self.index_selected_col = "#1696F2"
        self.index_selected_txt_col = "white"

        self.queue_switch_enabled_col = "#27EE16"
        self.queue_switch_disabled_col = "#D5D9DE"

        self.TOP_BUTTON_FG = "#39473F"
        self.TOP_BUTTON_FG_ACTIVE = "#3C8231"
        # =======================================================

        self.pid = os.getpid()
        self.overlay_canvas = None
        self.overlay_canvas_visible = False

        self.outliner = None
        self.tools_panel = None

        self.scale_factor = 1
        self.maximized_frame_size = 0
        self.windowed_frame_size = 0
        self.maximized_canvas_size = 0
        self.windowed_canvas_size = 0
        self.maximized_mode = None
        self.display_mode = None

        self.viewport_resample = Image.NEAREST
        self.zoomed_ld_img = None
        self.previous_display_mode = None
        self.lock_zoom = False

        ####################################################################################
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.screen_width * 0.5625  # reciprocal of the aspect ratio 16:9
        # Initial window size will be /1.5  of the screen display size.
        width = int(self.screen_width // 1.5)
        height = int(self.screen_height // 1.5)

        x = int(self.screen_width - width) // 2
        y = int(self.screen_height - height) // 2

        self.title("R-View Tool")

        if sys.platform.startswith('win'):
            self.iconbitmap(os.path.join("sources", "images", "logo.ico"))
        else:
            self.iconbitmap(os.path.join("@sources", "images", "logo.xbm"))

        # To center the initial window.
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(width, height)
        # self.maxsize(width,height)
        self.initial_size = (width, height)

        self.file_load_window = None
        self.exit_prompt = None
        # Calls the Exit Prompt window on closing(x) the window.
        self.protocol("WM_DELETE_WINDOW", self.close_all)
        self.withdraw()  # Hides the main window on startup.

        self.open_file_window()

    def load_user_settings(self, reset: bool = False):
        """
        Loads the user settings from the settings.json file.

        Args:
            reset (bool): If True, replaces the settings.json with a new file with default user settings.

        Returns:
            None

        """
        file_path = "settings.json"

        def create_new_user_settings_file():
            """
            Creates a new settings.json file with default values.
            Returns:
                None

            """
            default_settings = {"canvas_color": "default",
                                "selection_color": "cyan",
                                "highlight_opacity": 30}

            with open(file_path, 'w') as file:
                json.dump(default_settings, file, indent=2)

        try:
            if not reset:
                with open(file_path, 'r') as file:
                    json_file = json.load(file)
                    # Validating the user settings file.
                    if FileHandler.validate_user_settings_file(json_data=json_file):
                        self.user_settings = json_file
                    else:
                        raise
            else:
                raise

        except:  # In case of error create a new settings.json.
            create_new_user_settings_file()
            self.load_user_settings()
        else:
            self.update_user_settings()

    def update_user_settings(self):
        """
        Converts values from the user settings json file into variables.

        Returns:
            None

        """

        canvas_color = (self.user_settings["canvas_color"]).lower()
        if canvas_color == "default":
            canvas_color = "#242424"  # dark slate
        self.image_canvas.configure(background=canvas_color)

        selection_color = (self.user_settings["selection_color"]).lower()
        # Assigning a bright color.
        if selection_color == "blue":
            selection_color = "#00BFFF"
        elif selection_color == "pink":
            selection_color = "#FF1B88"
        elif selection_color == "green":
            selection_color = "#1BFF24"

        self.selection_color = selection_color

        file_path = "settings.json"
        with open(file_path, 'w') as file:  # writing the new settings to disc
            json.dump(self.user_settings, file, indent=2)

        # Updates the canvas to reflect the changes made.
        self.update_image_canvas()

    def main_layout(self):
        """
        Creating the UI for the App.

        Returns:
            None
        """

        self.current_state = "x"  # Windowed mode
        self.old_state = "m"  # Maximized window

        #### Color switch to visualize the frame layouts. Only for debug purpose.###################
        if 1 == 2:
            self.red_col = "red"
            self.blue_col = "blue"
            self.green_col = "green"
            self.yellow_col = "yellow"
            self.orange_col = "orange"
            self.purple_col = "purple"
            self.pink_col = "pink"
            self.brown_col = "brown"
            self.white_col = "white"
            self.black_col = "black"
            self.gray_col = "gray"
            self.light_gray_col = "light gray"
            self.dark_gray_col = "dark gray"
            self.lavender_col = "lavender"
            self.violet_col = "violet"
            self.indigo_col = "indigo"
            self.maroon_col = "maroon"
            self.olive_col = "olive"
            self.navy_col = "navy"
            self.teal_col = "teal"
            self.aquamarine_col = "aquamarine"
            self.turquoise_col = "turquoise"
            self.gold_col = "gold"
            self.silver_col = "silver"
            self.khaki_col = "khaki"
            self.coral_col = "coral"
        else:
            self.red_col = self.default_col
            self.blue_col = self.default_col
            self.green_col = self.default_col
            self.yellow_col = self.default_col
            self.orange_col = self.default_col
            self.purple_col = self.default_col
            self.pink_col = self.default_col
            self.brown_col = self.default_col
            self.white_col = self.default_col
            self.black_col = self.default_col
            self.gray_col = self.default_col
            self.light_gray_col = self.default_col
            self.dark_gray_col = self.default_col
            self.lavender_col = self.default_col
            self.violet_col = self.default_col
            self.indigo_col = self.default_col
            self.maroon_col = self.default_col
            self.olive_col = self.default_col
            self.navy_col = self.default_col
            self.teal_col = self.default_col
            self.aquamarine_col = self.default_col
            self.turquoise_col = self.default_col
            self.gold_col = self.default_col
            self.silver_col = self.default_col
            self.khaki_col = self.default_col
            self.coral_col = self.default_col

        self.default_col_dark = "#171616"
        self.columnconfigure(0, weight=1)
        self.rowconfigure((0, 2), weight=1)
        self.rowconfigure(1, weight=2)

        self.top_frame_main = ctk.CTkFrame(master=self, fg_color=self.silver_col, height=40)
        # self.top_frame_main.pack_propagate(False)
        self.top_frame_main.columnconfigure(0, weight=1)
        self.top_frame_main.columnconfigure(1, weight=1)
        self.top_frame_main.rowconfigure(0, weight=1)
        self.top_frame_main.grid(column=0, row=0, sticky="nsew", pady=(5, 0))

        self.top_frame_left = ctk.CTkFrame(master=self.top_frame_main, fg_color=self.blue_col, height=40)
        self.top_frame_left.pack(side="left", fill="both", expand=True)
        self.top_frame_right = ctk.CTkFrame(master=self.top_frame_main, fg_color=self.green_col, height=40)
        self.top_frame_right.pack_propagate(False)
        self.top_frame_right.pack(side="left", fill="y")

        title_image = ctk.CTkImage(light_image=Image.open(os.path.join("sources", "images", "rview_title.png")),
                                   size=(330, 35))
        image_label = ctk.CTkLabel(self.top_frame_left, image=title_image, text="")
        image_label.pack(side="left", padx=(10, 0))

        settings_btn_ld_img = ctk.CTkImage(light_image=Image.open(os.path.join("sources", "images", "settings.png")))

        self.user_settings_btn = ctk.CTkButton(master=self.top_frame_left, image=settings_btn_ld_img,
                                               text="", fg_color="#253A59", command=self.open_user_settings_window,
                                               height=30, width=30)
        self.user_settings_btn.pack(side="left", padx=(10, 0))

        self.cel_slider_frame = ctk.CTkFrame(self.top_frame_left, fg_color=self.brown_col, height=2, width=120)
        self.cel_slider_frame.pack(side="right", padx=(10), pady=(5, 5), anchor="s", fill="y")
        self.cel_slider_frame.grid_propagate(False)
        self.cel_slider_frame.rowconfigure((0, 1), weight=1)
        self.cel_slider_frame.columnconfigure(0, weight=1)

        self.cel_opacity_slider_text = ctk.CTkLabel(self.cel_slider_frame, text="Cel Opacity:",
                                                    font=("Arial Bold", 12), text_color="white")

        self.cel_opacity_slider_text.place(in_=self.cel_slider_frame, relx=0.4, rely=0.33, anchor="center")

        self.cel_opacity_slider_value_label = ctk.CTkLabel(self.cel_slider_frame, text="50",
                                                           font=("Arial Bold", 12), text_color="white")

        self.cel_opacity_slider_value_label.place(in_=self.cel_slider_frame, relx=0.8, rely=0.33, anchor="center")

        self.cel_opacity_slider = ctk.CTkSlider(self.cel_slider_frame, from_=0, to=100,
                                                command=self.cel_opacity_slider_event_handler,
                                                number_of_steps=100)
        self.cel_opacity_slider.grid(column=0, row=1, sticky="s")

        self.hide_annotations_btn = ctk.CTkButton(self.top_frame_left, text="Annotations: ON", font=("Arial Bold", 14),
                                                  command=self.handle_hide_annotations_btn,
                                                  fg_color=self.TOP_BUTTON_FG_ACTIVE,
                                                  border_width=2, height=35, width=140, hover=False)
        self.hide_annotations_btn.pack(side="right", padx=(10), pady=(0, 5), anchor="s")

        self.hq_view_btn = ctk.CTkButton(self.top_frame_left, text="HQ View: OFF", font=("Arial Bold", 14),
                                         command=self.handle_hq_view_btn, height=35, width=120, hover=False,
                                         fg_color=self.TOP_BUTTON_FG,
                                         border_width=2)
        self.hq_view_btn.pack(side="right", padx=10, pady=(0, 5), anchor="s")

        self.actual_scale_btn = ctk.CTkButton(self.top_frame_left, text="Actual Scale: OFF", font=("Arial Bold", 14),
                                              height=35, width=150, fg_color=self.TOP_BUTTON_FG, hover=False,
                                              border_width=2, command=self.handle_actual_scale_btn,
                                              hover_color="#6A6A6A")
        self.actual_scale_btn.pack(side="right", padx=10, pady=(0, 5), anchor="s")

        self.lock_ld_img = ctk.CTkImage(light_image=Image.open(os.path.join("sources", "images", "padlock_locked.png")))
        self.unlock_ld_img = ctk.CTkImage(
            light_image=Image.open(os.path.join("sources", "images", "padlock_unlocked.png")))

        self.lock_zoom_btn = ctk.CTkButton(self.top_frame_left, text="Zoom:", font=("Arial Bold", 14),
                                           height=35, width=100, fg_color=self.TOP_BUTTON_FG, hover=False,
                                           border_width=2, command=self.handle_lock_zoom_btn, hover_color="#6A6A6A",
                                           image=self.unlock_ld_img, compound="right", border_spacing=0)
        self.lock_zoom_btn.pack(side="right", anchor="s", padx=10, pady=(0, 5))

        self.globe_active_ld_img = ctk.CTkImage(
            light_image=Image.open(os.path.join("sources", "images", "globe_icon.png")))
        self.globe_disabled_ld_img = ctk.CTkImage(
            light_image=Image.open(os.path.join("sources", "images", "globe_icon_disabled.png")))

        self.overlay_canvas_btn = ctk.CTkButton(self.top_frame_right, text="Overlay", font=("Arial Bold", 20),
                                                height=55, width=50, fg_color="#3e6160", hover=True,
                                                text_color="#BFBFBF",
                                                border_width=0, command=self.toggle_overlay_canvas,
                                                hover_color="#2F4D9C",
                                                image=self.globe_disabled_ld_img, compound="left")

        self.overlay_canvas_btn.pack(side="bottom", anchor="s", pady=5, padx=0)

        self.mid_frame_main = ctk.CTkFrame(master=self, fg_color=self.orange_col)
        self.mid_frame_main.grid_propagate(False)
        self.mid_frame_main.columnconfigure((0, 2), weight=1)
        self.mid_frame_main.columnconfigure(1, weight=0)
        self.mid_frame_main.rowconfigure(0, weight=1)
        self.mid_frame_main.grid(row=1, column=0, sticky="news")

        # outliner panel
        self.mid_frame1 = ctk.CTkFrame(master=self.mid_frame_main, fg_color=self.pink_col)  # yellow
        self.mid_frame1.grid_propagate(False)
        self.mid_frame1.pack_propagate(False)
        self.mid_frame1.rowconfigure(0, weight=1)
        self.mid_frame1.columnconfigure(0, weight=1)
        self.mid_frame1.grid(row=0, column=0, sticky="ew", )

        # Image Frame
        self.mid_frame2 = ctk.CTkFrame(master=self.mid_frame_main, fg_color=self.purple_col)
        # self.mid_frame2.grid_propagate(True)
        self.mid_frame2.columnconfigure(0, weight=0)
        self.mid_frame2.rowconfigure(0, weight=1)
        self.mid_frame2.grid(row=0, column=1, sticky="ew", padx=5)

        self.mid_frame3 = ctk.CTkFrame(master=self.mid_frame_main, fg_color=self.indigo_col)
        self.mid_frame3.pack_propagate(False)
        self.mid_frame3.grid(row=0, column=2, sticky="ew")

        self.image_frame = ctk.CTkFrame(master=self.mid_frame2, bg_color=self.lavender_col, width=976, height=549,
                                        corner_radius=0)
        self.image_frame.pack_propagate(False)
        self.image_frame.rowconfigure(0, weight=1)
        self.image_frame.columnconfigure(0, weight=1)
        self.image_frame.grid(column=0, row=0)

        self.image_frame_width = 976
        self.image_frame_height = 549

        self.image_frame_width_maxed = self.get_rel_width(.767)
        self.image_frame_height_maxed = self.get_rel_height(.767)

        self.image_frame_width_windowed = self.get_rel_width(.5083)
        self.image_frame_height_windowed = self.get_rel_height(.5083)

        # Grabs the current image from the list of loaded images.
        self.current_image = ctk.CTkImage(light_image=Image.open(self.images[self.image_index]))
        self.image_label = ctk.CTkLabel(master=self.image_frame, text="", fg_color="#404040")

        self.bottom_frame_main = ctk.CTkFrame(master=self, fg_color=self.green_col,
                                              height=int(self.screen_height * .10))

        self.bottom_frame_main.grid(row=2, column=0, sticky="news")
        self.bottom_frame_main.rowconfigure(0, weight=1)
        self.bottom_frame_main.columnconfigure((0, 2), weight=1)
        self.bottom_frame_main.columnconfigure(1, weight=0)
        self.bottom_frame_main.grid_propagate(False)

        self.bottom_sub_frame1 = ctk.CTkFrame(master=self.bottom_frame_main,
                                              fg_color=self.brown_col,
                                              height=self.get_rel_height(0.101))  # ,height=110,width=312)
        self.bottom_sub_frame1.grid_propagate(False)
        self.bottom_sub_frame1.rowconfigure((0, 1, 2), weight=1)
        self.bottom_sub_frame1.columnconfigure(0, weight=1)
        self.bottom_sub_frame1.columnconfigure(1, weight=0)
        self.bottom_sub_frame1.grid(column=0, row=0, sticky="we")

        self.bottom_sub_frame2 = ctk.CTkFrame(master=self.bottom_frame_main,
                                              fg_color=self.default_col_dark,
                                              height=self.get_rel_height(0.101),
                                              width=620, )  # height=110,width=654 ) # Yellow

        self.bottom_sub_frame2.rowconfigure(0, weight=1)
        self.bottom_sub_frame2.rowconfigure(1, weight=1)
        self.bottom_sub_frame2.columnconfigure(0, weight=1)
        self.bottom_sub_frame2.grid_propagate(False)
        self.bottom_sub_frame2.pack_propagate(False)
        self.bottom_sub_frame2.grid(column=1, row=0, sticky="news")

        # -------------Image Tools Frame-----------------------------
        self.image_tools_frame = ctk.CTkFrame(master=self.bottom_sub_frame2,
                                              fg_color=self.default_col_dark,
                                              height=self.get_rel_height(
                                                  0.0540), width=620, )  # .0556  height=60,width=654)

        self.image_tools_frame.rowconfigure((0), weight=1)
        self.image_tools_frame.columnconfigure((0, 4), weight=0)
        self.image_tools_frame.columnconfigure((1, 2, 3), weight=1)

        self.image_tools_frame.pack_propagate(True)
        self.image_tools_frame.grid_propagate(False)
        self.image_tools_frame.pack(side='bottom')

        # ------------Tools and buttons-----------------------------

        self.bottom_sub_frame2_1 = ctk.CTkFrame(master=self.bottom_sub_frame2,
                                                fg_color=self.blue_col, width=620)  # ,width=654)
        self.bottom_sub_frame2_1.pack(side="top")
        self.bottom_sub_frame2_1.grid_propagate(False)
        self.bottom_sub_frame2_1.columnconfigure((0, 2), weight=1)
        self.bottom_sub_frame2_1.columnconfigure(1, weight=2)
        self.bottom_sub_frame2_1.rowconfigure(0, weight=1)

        self.export_current_btn_frame = ctk.CTkFrame(master=self.bottom_sub_frame2_1,
                                                     fg_color=self.yellow_col,
                                                     width=150)  # ,width=654)
        self.export_current_btn_frame.grid_propagate(False)
        self.export_current_btn_frame.rowconfigure(0, weight=1)
        self.export_current_btn_frame.columnconfigure(0, weight=1)
        self.export_current_btn_frame.grid(column=0, row=0, sticky="w")

        self.export_current_btn = ctk.CTkButton(self.export_current_btn_frame, fg_color="#4086EF",
                                                hover_color="#656565",
                                                font=("Arial", 15), text_color="#FFFFFF", border_spacing=0,
                                                width=20, height=30, text="Render Current",
                                                command=lambda: self.create_render_menu(batch=False))
        self.export_current_btn.grid(row=0, column=0, sticky="w", padx=5)

        # ------Media navigation buttons-----------
        self.media_buttons_frame = ctk.CTkFrame(master=self.bottom_sub_frame2_1,
                                                fg_color=self.indigo_col,
                                                )  # ,width=654)
        self.media_buttons_frame.grid_propagate(False)
        self.media_buttons_frame.rowconfigure(0, weight=1)
        self.media_buttons_frame.columnconfigure((0, 1, 2, 3, 4), weight=1)
        self.media_buttons_frame.grid(column=1, row=0, sticky="we")

        BUTTON_HEIGHT = 35
        self.first_btn = ctk.CTkButton(self.media_buttons_frame, fg_color="#D9D9D9", hover_color="#656565",
                                       font=("Arial bold", 15), text_color="#474747", border_spacing=0,
                                       width=40, height=BUTTON_HEIGHT, text="<<", command=self.show_first_img)
        self.first_btn.grid(column=0, row=0, sticky="e", padx=(0, 0))

        self.prev_btn = ctk.CTkButton(self.media_buttons_frame, fg_color="#D9D9D9", hover_color="#656565",
                                      font=("Arial bold", 20), text_color="#474747", border_spacing=0,
                                      width=40, height=BUTTON_HEIGHT, text="<",
                                      command=self.show_previous_img)
        self.prev_btn.grid(column=1, row=0, sticky="e")

        self.current_frame_label = ctk.CTkLabel(self.media_buttons_frame, width=44,
                                                text=f"{self.image_index + 1}", font=("Arial bold", 20),
                                                fg_color="transparent")
        self.current_frame_label.grid(column=2, row=0)

        self.next_btn = ctk.CTkButton(self.media_buttons_frame, fg_color="#D9D9D9", hover_color="#656565",
                                      font=("Arial bold", 20), text_color="#474747", border_spacing=0,
                                      width=40, height=BUTTON_HEIGHT, text=">", command=self.show_next_img)
        self.next_btn.grid(column=3, row=0, sticky="w")

        self.last_btn = ctk.CTkButton(self.media_buttons_frame, fg_color="#D9D9D9", hover_color="#656565",
                                      font=("Arial bold", 15), text_color="#474747", border_spacing=0,
                                      width=40, height=BUTTON_HEIGHT, text=">>", command=self.show_last_img)
        self.last_btn.grid(column=4, row=0, sticky="w", padx=(0, 0))

        self.queue_switch_frame = ctk.CTkFrame(master=self.bottom_sub_frame2_1, width=150,
                                               fg_color=self.violet_col)  # ,width=654)
        self.queue_switch_frame.grid_propagate(False)
        self.queue_switch_frame.columnconfigure((0, 1), weight=1)
        self.queue_switch_frame.rowconfigure(0, weight=1)
        self.queue_switch_frame.grid(column=6, row=0, sticky="e")

        self.queue_switch_label = ctk.CTkLabel(self.queue_switch_frame, text="In-queue:",
                                               font=("Arial Bold", 15))
        self.queue_switch_label.grid(column=0, row=0, sticky="nse", padx=(20, 5))

        self.queue_switch = ctk.CTkSwitch(self.queue_switch_frame, text="", command=self.handle_queue,
                                          width=0, fg_color="#5F6162", progress_color="#1A7313", onvalue=1,
                                          offvalue=0, switch_width=50, switch_height=25, button_length=0)
        self.update_queue_switch()
        self.queue_switch.grid(column=1, row=0, sticky="nse")

        # --------Export buttons--------------

        self.bottom_sub_frame3 = ctk.CTkFrame(master=self.bottom_frame_main,
                                              fg_color=self.aquamarine_col)  # height=110, width=312)

        self.bottom_sub_frame3.grid_propagate(False)
        self.bottom_sub_frame3.pack_propagate(False)
        self.bottom_sub_frame3.grid(column=2, row=0, sticky="we")

        self.file_name_textbox = ctk.CTkTextbox(self.bottom_sub_frame1, fg_color="transparent",
                                                activate_scrollbars=False,
                                                border_color="grey",
                                                wrap="none", height=10, exportselection=False,
                                                font=("Arial Bold", 12), border_spacing=0)
        self.file_name_textbox.grid(column=0, row=0, sticky="nwe", padx=(5, 0))
        self.file_name_textbox.configure(state="disabled")

        save_project_ld_img = ctk.CTkImage(
            light_image=Image.open(os.path.join("sources", "images", "tool_icons", "save.png")),
            size=(30, 30))

        self.save_project_btn = ctk.CTkButton(self.bottom_sub_frame3, text="", image=save_project_ld_img,
                                              font=("Arial Semibold", 16),
                                              fg_color="#254E9F", width=40, height=40,
                                              border_spacing=0, command=self.save_data)

        self.save_project_btn.pack(side="left", anchor="s", padx=(30, 0), pady=8)

        self.render_images_btn = ctk.CTkButton(self.bottom_sub_frame3, text="Render Images", font=("Arial Bold", 15),
                                               fg_color="#195DC2", width=100, height=40, corner_radius=8,
                                               text_color="#EFEFEF",
                                               border_spacing=0, command=self.create_render_menu)
        self.render_images_btn.pack(side="left", anchor="s", padx=10, pady=8)

        # ------Creating Canvas, Overlay Canvasm  and Tools Panel---------
        self.create_outliner()

        self.create_canvas()
        # Handles creating and displaying graphic items on the base canavas.
        self.canvas_gm = GraphicsManager(self, canvas=self.image_canvas)

        self.create_overlay_canvas()
        # Handles creating and displaying graphic items on the Overlay canavas.
        self.overlay_gm = OverlayGraphicsManager(self, canvas=self.overlay_canvas, is_overlay=True)

        self.error_prompt = ErrorPrompt(master=self.image_frame)

        self.image_processor = ImageProcessor(self, canvas_gm=self.canvas_gm, overlay_gm=self.overlay_gm)
        self.tools_panel = self.create_tools()

        self.keybinds = KeyBinds(self)
        self.canvas_keybinds = CanvasKeybinds(self, canvas=self.image_canvas, graphics_manager=self.canvas_gm)
        self.overlay_keybinds = OverlayKeyBinds(self, canvas=self.overlay_canvas, graphics_manager=self.overlay_gm)

        # self.on_resize(state="x") #Calls the window resize with initial state.
        self.bind("<Configure>", self.window_resize)  # Calls when window is moved or resized.

        self.load_user_settings()  # Load the user settings.

        if sys.platform.startswith('win'):  # Windows only feature
            self.wm_state("zoomed")  # Setting the window to be maximized on startup.
        else:
            # self.attributes('-fullscreen', True)
            self.wm_attributes("-zoomed", True)

    def open_user_settings_window(self):
        """
        Creates and displays the UserSettingWindow.

        Returns:
            None

        """
        if self.user_settings_window:
            self.user_settings_window.destroy()
        self.user_settings_window = UserSettingsWindow(app=self)
        self.user_settings_window.attributes('-topmost', True)
        self.user_settings_window.wait_visibility()
        self.user_settings_window.grab_set()

    # ------------------------------------------------------------

    def create_image_tools_panel(self):
        """
        Creats the bottom tools panel for Image and Scale Controls.

        Returns:
            None

        """

        TOOL_BUTTON_WIDTH = 50
        TOOL_BUTTON_FG = "#4A4A4A"
        TEXT_COL = "#D4D4D4"
        tool_button_hover = "#656565"
        TOOLS_FRAME_COL = self.default_col
        TOOL_HOVER = False
        TOOL_ICON_SIZE = (25, 25)
        IMAGE_BUTTON_SIZE = (30, 30)

        self.image_import_ld_img = ctk.CTkImage(
            light_image=Image.open(os.path.join("sources", "images", "tool_icons", "image_import.png")),
            size=(IMAGE_BUTTON_SIZE))
        self.image_import_disabled_ld_img = ctk.CTkImage(
            light_image=Image.open(os.path.join("sources", "images", "tool_icons", "image_import_disabled.png")),
            size=(IMAGE_BUTTON_SIZE))

        self.image_import_btn = ctk.CTkButton(self.image_tools_frame,
                                              fg_color=TOOL_BUTTON_FG,
                                              hover_color=tool_button_hover,
                                              font=("Arial bold", 15),
                                              text_color=TEXT_COL,
                                              hover=True,
                                              width=TOOL_BUTTON_WIDTH,
                                              height=TOOL_BUTTON_WIDTH,
                                              text="", command=self.import_overlay_image,
                                              image=self.image_import_ld_img)

        self.image_import_btn.grid(row=0, column=0, padx=5, sticky="ew")

        self.scale_slider_frame = ctk.CTkFrame(self.image_tools_frame, fg_color=self.default_col_dark)
        self.scale_slider_frame.grid_columnconfigure(0, weight=1)
        self.scale_slider_frame.grid_rowconfigure((0, 1), weight=1)
        self.scale_slider_frame.grid(row=0, column=1, sticky="ns", padx=2)

        self.scale_slider_top_frame = ctk.CTkFrame(self.scale_slider_frame, fg_color=self.default_col_dark)
        self.scale_slider_top_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self.scale_slider_top_frame.grid(row=0, column=0, sticky="new")

        self.scale_minus_btn = ctk.CTkButton(self.scale_slider_top_frame, text="-", fg_color="#454545",
                                             text_color=TEXT_COL,
                                             font=("Arial Bold", 15), width=20, corner_radius=3,
                                             command=lambda: self.scale_slider_event_handler(increment="-"))
        self.scale_minus_btn.grid(row=0, column=0, sticky="w")

        self.scale_plus_btn = ctk.CTkButton(self.scale_slider_top_frame, text="+", fg_color="#454545",
                                            text_color=TEXT_COL,
                                            font=("Arial Bold", 15), width=20, corner_radius=3,
                                            command=lambda: self.scale_slider_event_handler(increment="+"))
        self.scale_plus_btn.grid(row=0, column=3, sticky="e")

        self.scale_slider_value_text = ctk.CTkLabel(self.scale_slider_top_frame, text="Scale:",
                                                    font=("Arial Bold", 15), text_color=TEXT_COL)
        self.scale_slider_value_text.grid(row=0, column=1)

        self.scale_slider_value_label = ctk.CTkLabel(self.scale_slider_top_frame, text="1.0",
                                                     font=("Arial Bold", 15), text_color=TEXT_COL)
        self.scale_slider_value_label.place(relx=0.60, rely=0.005)

        self.scale_slider = ctk.CTkSlider(self.scale_slider_frame, from_=0, to=2,
                                          command=self.scale_slider_event_handler,
                                          number_of_steps=2000, progress_color="transparent")
        self.scale_slider.grid(row=1, column=0, pady=(0, 8), sticky="s")

        self.rotation_slider_frame = ctk.CTkFrame(self.image_tools_frame, fg_color=self.default_col_dark)
        self.rotation_slider_frame.grid_columnconfigure(0, weight=1)
        self.rotation_slider_frame.grid_rowconfigure((0, 1), weight=1)
        self.rotation_slider_frame.grid(row=0, column=2, sticky="ns", padx=2)

        self.rotation_slider_top_frame = ctk.CTkFrame(self.rotation_slider_frame, fg_color=self.default_col_dark)
        self.rotation_slider_top_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self.rotation_slider_top_frame.grid(row=0, column=0, sticky="new")

        self.rotation_minus_btn = ctk.CTkButton(self.rotation_slider_top_frame, text="-", fg_color="#454545",
                                                text_color=TEXT_COL,
                                                font=("Arial Bold", 15), width=20, corner_radius=3,
                                                command=lambda: self.rotation_slider_event_handler(increment="-"))
        self.rotation_minus_btn.grid(row=0, column=0, sticky="w")

        self.rotation_plus_btn = ctk.CTkButton(self.rotation_slider_top_frame, text="+", fg_color="#454545",
                                               text_color=TEXT_COL,
                                               font=("Arial Bold", 15), width=20, corner_radius=3,
                                               command=lambda: self.rotation_slider_event_handler(increment="+"))
        self.rotation_plus_btn.grid(row=0, column=3, sticky="e")

        self.rotation_slider_value_text = ctk.CTkLabel(self.rotation_slider_top_frame, text="Rotation:",
                                                       font=("Arial Bold", 15), text_color=TEXT_COL)
        self.rotation_slider_value_text.grid(row=0, column=1, sticky="w", padx=(5, 0))

        self.rotation_slider_value_label = ctk.CTkLabel(self.rotation_slider_top_frame, text="0",
                                                        font=("Arial Bold", 15), text_color=TEXT_COL)
        self.rotation_slider_value_label.place(relx=0.65, rely=0.05)

        self.rotation_slider = ctk.CTkSlider(self.rotation_slider_frame, from_=0, to=360, number_of_steps=361,
                                             command=self.rotation_slider_event_handler)
        self.rotation_slider.grid(row=1, column=0, pady=(0, 5))
        self.rotation_slider.set(0)

        self.opacity_slider_frame = ctk.CTkFrame(self.image_tools_frame, fg_color=self.default_col_dark)
        self.opacity_slider_frame.grid_columnconfigure(0, weight=1)
        self.opacity_slider_frame.grid_rowconfigure((0, 1), weight=1)
        self.opacity_slider_frame.grid(row=0, column=3, sticky="ns", padx=2)

        self.opacity_slider_value_text = ctk.CTkLabel(self.opacity_slider_frame, text="Image Opacity:",
                                                      font=("Arial Bold", 15), text_color=TEXT_COL)
        self.opacity_slider_value_text.place(relx=0.08, rely=0.005)

        self.opacity_slider_value_label = ctk.CTkLabel(self.opacity_slider_frame, text="100",
                                                       font=("Arial Bold", 15), text_color=TEXT_COL)
        self.opacity_slider_value_label.place(relx=0.78, rely=0.005)

        self.opacity_slider = ctk.CTkSlider(self.opacity_slider_frame, from_=0, to=100,
                                            command=self.opacity_slider_event_handler,
                                            number_of_steps=100, )
        self.opacity_slider.grid(row=1, column=0, pady=(0, 8), sticky="s")

        self.image_reset_ld_img = ctk.CTkImage(
            light_image=Image.open(os.path.join("sources", "images", "tool_icons", "image_reset.png")),
            size=(IMAGE_BUTTON_SIZE))
        self.image_reset_disabled_ld_img = ctk.CTkImage(
            light_image=Image.open(os.path.join("sources", "images", "tool_icons", "image_reset_disabled.png")),
            size=(IMAGE_BUTTON_SIZE))

        self.image_reset_btn = ctk.CTkButton(self.image_tools_frame,
                                             fg_color=TOOL_BUTTON_FG,
                                             hover_color=tool_button_hover,
                                             font=("Arial bold", 15),
                                             text_color=TEXT_COL, border_spacing=0,
                                             hover=True,
                                             width=TOOL_BUTTON_WIDTH,
                                             height=TOOL_BUTTON_WIDTH,
                                             text="", command=self.overlay_gm.reset_selected_image,
                                             image=self.image_reset_ld_img)
        self.image_reset_btn.grid(row=0, column=4, padx=5, sticky="we")

        self.toggle_image_tools_buttons(0)
        self.toggle_image_tools_sliders(0)

    def cel_opacity_slider_event_handler(self, value):
        """
        Called on value update from the opacity_slider, Changes the opacity of the cel.

        Args:
            value: Range from 0 to 1.

        Returns:
            None

        """

        value = round(value)
        self.cel_opacity_slider_value_label.configure(text=f"{value}")

        opacity_value = int((float(value) / 100) * 255)

        self.overlay_cel_ld_image = Image.new("RGBA", (self.image_frame_width_maxed, self.image_frame_height_maxed),
                                              (255, 255, 255, opacity_value))
        self.overlay_cel_tk = ImageTk.PhotoImage(self.overlay_cel_ld_image)

        self.overlay_canvas.itemconfig(self.overlay_canvas_cel_image, image=self.overlay_cel_tk)
        # self.toggle_overlay_canvas(override=True,BG_ALPHA=value)

    def rotation_slider_event_handler(self, value=None, increment=None):
        """
        Rotates the selected overlay image based on the slider value.

        Args:
            value: Range 0 to 360.
            increment: + or - that increments the current rotation by +1 or -1.

        Returns:
            None

        """

        if value != None:
            current_value = int(value)
        if increment == "+":
            current_value = int(self.rotation_slider_value_label.cget("text"))
            current_value += 1
            current_value = min(current_value, 360)
            self.rotation_slider.set(current_value)
        elif increment == "-":
            current_value = int(self.rotation_slider_value_label.cget("text"))
            current_value -= 1
            current_value = max(0, current_value)
            self.rotation_slider.set(current_value)

        self.rotation_slider_value_label.configure(text=int(current_value))
        self.overlay_gm.rotate_overlay_image(current_value)

    def set_rotation_slider(self, value):
        """
        Sets the rotation slider to the value provided.

        Args:
            value (int): Range 0 to 360

        Returns:

        """
        self.rotation_slider.set(value)
        self.rotation_slider_value_label.configure(text=value)

    def scale_slider_event_handler(self, value=None, increment: str = None):
        """
        Scales the selected text item or selected overlay image.

        Args:
            value: A multiplier value that scales the image/text times the current image/text size.
            increment (str): "+" or "-" that increments or decrements the item scale by 1.

        Returns:
            None

        """
        if value:
            value = round(value, 2)
            self.scale_slider_value_label.configure(text=f"{value}")
            self.canvas_gm.update_text_item_scale(value)
            self.overlay_gm.update_text_item_scale(value)
            self.overlay_gm.scale_overlay_image(factor=value, increment=increment)
        else:  # Increment.
            self.canvas_gm.update_text_item_scale(increment=increment)
            self.overlay_gm.update_text_item_scale(increment=increment)
            self.overlay_gm.scale_overlay_image(factor=value, increment=increment)

    def opacity_slider_event_handler(self, value):
        """
        Sets the opacity of the selected overlay image.

        Args:
            value: Range 0 to 100

        Returns:
            None

        """

        value = round(value)
        self.overlay_gm.change_overlay_image_opacity(opacity=value / 100)
        self.opacity_slider_value_label.configure(text=f"{value}")

    def set_opacity_slider(self, value):
        """
        Sets the opacity slider to the provided value.

        Args:
            value: Value from range 0 to 1

        Returns:
            None

        """
        self.opacity_slider.set(value)
        self.opacity_slider_value_label.configure(text=value)

    def reset_scale_slider(self, event):
        """
        Resets the scale slider to middle position on mouse release.

        Args:
            event: Mouse click release event.

        Returns:
            None

        """
        self.overlay_gm.is_image_scaling = False
        self.overlay_gm.is_text_scaling = False
        self.canvas_gm.is_text_scaling = False

        self.scale_slider.set(1.0)
        self.scale_slider_value_label.configure(text="1.0")
        self.overlay_gm.reveal_overlay_image_selection_border()

    def toggle_image_tools_buttons(self, toggle, only_reset=False):
        """
        Toggles the state of image tools button.

        Args:
            toggle (int):  1 sets the state to normal , 0 sets state to disabled.
            only_reset (bool):  Toggles the state of only the image_reset_btn. Default False.

        Returns:
            None

        """

        if only_reset:
            if toggle == 1:
                self.image_reset_btn.configure(state="normal", image=self.image_reset_ld_img)
            elif toggle == 0:
                self.image_reset_btn.configure(state="disabled", image=self.image_reset_disabled_ld_img)
            return

        if toggle == 0:
            TEXT_COL = "#888888"
            self.image_import_btn.configure(state="disabled", image=self.image_import_disabled_ld_img)
            self.image_reset_btn.configure(state="disabled", image=self.image_reset_disabled_ld_img)
            self.cel_opacity_slider.configure(state="disabled")
        else:
            TEXT_COL = "#D4D4D4"
            self.image_import_btn.configure(state="normal", image=self.image_import_ld_img)
            self.image_reset_btn.configure(state="normal", image=self.image_reset_ld_img)
            self.cel_opacity_slider.configure(state="normal")

        self.cel_opacity_slider_text.configure(text_color=TEXT_COL)
        self.cel_opacity_slider_value_label.configure(text_color=TEXT_COL)

    def toggle_image_tools_sliders(self, toggle, only_scale=False):
        """
        Toggles the state of the image tools sliders.

        Args:
            toggle (int):  1 sets the state to normal , 0 sets state to disabled.
            only_scale (bool): Toggles the state of only the scale_slider. Default False.

        Returns:
            None

        """

        if only_scale and toggle == 1:
            TEXT_COL = "#D4D4D4"
            self.scale_slider_value_label.configure(text_color=TEXT_COL)
            self.scale_slider_value_text.configure(text_color=TEXT_COL)
            self.scale_minus_btn.configure(state="normal")
            self.scale_plus_btn.configure(state="normal")
            self.scale_slider.configure(state="normal")
            return

        if toggle == 0:
            TEXT_COL = "#949494"
            self.rotation_plus_btn.configure(state="disabled")
            self.rotation_minus_btn.configure(state="disabled")
            self.rotation_slider.configure(state="disabled")

            self.scale_plus_btn.configure(state="disabled")
            self.scale_minus_btn.configure(state="disabled")
            self.scale_slider.configure(state="disabled")

            self.opacity_slider.configure(state="disabled")

        else:
            TEXT_COL = "#D4D4D4"
            self.rotation_plus_btn.configure(state="normal")
            self.rotation_minus_btn.configure(state="normal")
            self.rotation_slider.configure(state="normal")

            self.scale_minus_btn.configure(state="normal")
            self.scale_plus_btn.configure(state="normal")
            self.scale_slider.configure(state="normal")

            self.opacity_slider.configure(state="normal")

        self.rotation_slider_value_text.configure(text_color=TEXT_COL)
        self.rotation_slider_value_label.configure(text_color=TEXT_COL)

        self.scale_slider_value_label.configure(text_color=TEXT_COL)
        self.scale_slider_value_text.configure(text_color=TEXT_COL)

        self.opacity_slider_value_text.configure(text_color=TEXT_COL)
        self.opacity_slider_value_label.configure(text_color=TEXT_COL)

    def import_overlay_image(self):
        """
        Imports an image into the overlay canvas.
        Returns:
            None

        """
        file_path = filedialog.askopenfilename(title="Select Image",
                                               filetypes=[("Image Files",
                                                           ".bmp .BMP .gif .GIF .icns .ICNS .ico .ICO .im .IM .jpeg .JPEG .jpg .JPG .jfif .JFIF .jpeg2000 .JPEG2000 .png .PNG .ppm .PPM .tga .TGA .tif .TIF .tiff .TIFF .webp .WEBP"),
                                                          ("All Files", "*.*")])

        if file_path:
            if FileHandler.validate_image(file_path):
                self.tools.cursor_tool()
                self.overlay_gm.add_image_to_overlay_canvas(image_path=file_path)
            else:
                # If image fails to load display an error message.
                self.error_prompt.display_error_prompt(error_msg="Image Failed to load", priority=2)

    # ------------------------------------------------------------

    def create_canvas(self):  # creates the canvas object
        """
        Creates the image canvas that displays the images.

        Returns:
            None

        """
        self.ld_img = Image.open((self.images[self.image_index]))
        aspect_ratio = self.ld_img.width / self.ld_img.height

        self.aspect_width = min(self.image_frame_width, int(self.image_frame_height * aspect_ratio))
        self.aspect_height = min(self.image_frame_height, int(self.image_frame_width / aspect_ratio))

        self.image_canvas = ctk.CTkCanvas(master=self.image_frame, width=self.aspect_width, height=self.aspect_height,
                                          background=self.default_col, highlightthickness=0)
        self.pack_propagate(False)

        self.image_canvas.pack(expand=True)

        self.resized_ld_img = self.ld_img.resize((self.aspect_width, self.aspect_height), Image.NEAREST)
        self.current_imagetk = ImageTk.PhotoImage(self.resized_ld_img)

        center_x = self.resized_ld_img.width // 2
        center_y = self.resized_ld_img.height // 2
        self.display_image = self.image_canvas.create_image(center_x, center_y, image=self.current_imagetk, tags="img",
                                                            anchor="center")

        self.canvas_scrollbar_y = ctk.CTkScrollbar(self.image_frame, command=self.image_canvas.yview)
        # self.canvas_scrollbar_y.place(x=25, y=203)

        self.canvas_scrollbar_x = ctk.CTkScrollbar(self.image_frame, command=self.image_canvas.xview,
                                                   orientation="horizontal")
        # self.canvas_scrollbar_x.place(x=12, y=123)
        self.image_canvas.configure(xscrollcommand=self.canvas_scrollbar_x.set,
                                    yscrollcommand=self.canvas_scrollbar_y.set)
        self.image_canvas.configure(xscrollincrement=1, yscrollincrement=1)

        self.update_filename()  # Updates the current image filename on the bottm left corner.

    def create_overlay_canvas(self):
        """
        Creates the overlay_canvas.

        Returns:
            None

        """

        self.overlay_canvas = ctk.CTkCanvas(master=self.image_frame, width=self.image_frame_width,
                                            height=self.image_frame_height,
                                            background="white", highlightthickness=0, )
        self.overlay_canvas_bg_image = self.overlay_canvas.create_image(0, 0, tags="bg", anchor="nw")

        self.overlay_cel_ld_image = Image.new("RGBA", (self.image_frame_width_maxed, self.image_frame_height_maxed),
                                              (255, 255, 255, 128))
        self.overlay_cel_tk = ImageTk.PhotoImage(self.overlay_cel_ld_image)
        self.overlay_canvas_cel_image = self.overlay_canvas.create_image(0, 0, tags="cel",
                                                                         anchor="nw",
                                                                         image=self.overlay_cel_tk)

    def toggle_overlay_canvas(self, override=False, rescaled=False):
        """
        Toggles the display of the overlay_canvas.

        Args:
            override(bool): If True display the overlay_canvas irrespective of current state.Default False
            rescaled(bool):If False reset the Base Canvas to default state. Default False.

        Returns:
            None

        """

        # Resets Zoom and Actual size before
        if not rescaled:
            self.update_image_canvas()

        # Clear all item selections.
        self.canvas_gm.remove_text_item_selection()
        self.overlay_gm.remove_text_item_selection()
        self.overlay_gm.remove_overlay_image_selection()

        if self.overlay_canvas_visible == False or override:
            # if not self.overlay_canvas:
            self.overlay_canvas.place(in_=self.image_frame, anchor="nw")
            self.overlay_canvas_visible = True
            self.overlay_canvas_ld_img = self.resized_ld_img
            # self.overlay_canvas_ld_img.putalpha(BG_ALPHA)

            self.current_backdrop_tk = ImageTk.PhotoImage(self.overlay_canvas_ld_img)

            center_x = (self.image_frame_width - self.overlay_canvas_ld_img.width) // 2
            center_y = (self.image_frame_height - self.overlay_canvas_ld_img.height) // 2

            self.overlay_canvas.itemconfig(self.overlay_canvas_bg_image,
                                           image=self.current_backdrop_tk,
                                           tags="bg", anchor="nw")
            self.overlay_canvas.coords(self.overlay_canvas_bg_image, center_x, center_y)
            # moves the image to lower stack so the drawing on top is visible
            self.overlay_canvas.tag_lower("cel")
            self.overlay_canvas.tag_lower("bg")
            self.toggle_image_control_buttons(toggle=0)
            self.toggle_image_tools_buttons(toggle=1)
            self.toggle_image_tools_buttons(toggle=0, only_reset=True)

            self.overlay_canvas_btn.configure(fg_color="#0095ff", text_color="white",
                                              image=self.globe_active_ld_img)

            # Don't rest to cursor tool while scrolling through the images with overlay enabled.
            if not override:
                self.tools.cursor_tool()


        elif self.overlay_canvas_visible:  # If canvas already visible hide it.
            self.overlay_canvas.place_forget()
            self.overlay_canvas_visible = False
            self.toggle_image_control_buttons(toggle=1)
            self.toggle_image_tools_buttons(toggle=0)

            self.overlay_canvas_btn.configure(fg_color="#3e6160", text_color="#BFBFBF",
                                              image=self.globe_disabled_ld_img)
            self.tools.cursor_tool()
        #

    def create_outliner(self):
        """
        Creates an Outliner object with the current loaded files.
        Returns:
            None

        """
        self.outliner = Outliner(master=self.mid_frame1, parent_app=self, fg_color="#232323")
        self.outliner.grid(column=0, row=0, sticky="news")

        # Shift + hover shows full filename.
        self.outliner_hover_btn = ctk.CTkButton(self, text_color="white", fg_color="#0A283E",
                                                hover=False, font=("Arial Bold", 13))

        # Highlights the first button.
        self.update_outliner_selection()

    def create_tools(self):
        """
        Creates the Tools Object and the TextInsertWindow widget.

        Returns:
            None

        """

        self.tools = Tools(self, canvas=self.image_canvas, graphics_manager=self.canvas_gm)
        self.canvas_text_insert = TextInsertWindow(self, master=self.image_frame, )
        self.canvas_text_insert.hide_text_insert_window()

        def create_color_selector_panel():
            self.color_tools_frame = ctk.CTkFrame(master=self.mid_frame3, fg_color=self.brown_col)
            self.color_tools_frame.grid_propagate(False)
            self.color_tools_frame.rowconfigure((0, 1, 2), weight=1)
            self.color_tools_frame.columnconfigure(0, weight=1)
            self.color_tools_frame.pack(side="top", expand=False)

            self.rgb_picker_frame = ctk.CTkFrame(master=self.color_tools_frame, fg_color=self.yellow_col)
            self.rgb_picker_frame.grid_propagate(False)
            self.rgb_picker_frame.rowconfigure((0, 1), weight=1)
            self.rgb_picker_frame.columnconfigure(0, weight=1)
            self.rgb_picker_frame.pack(side="top")

            self.rgb_picker_canvas = ctk.CTkCanvas(master=self.rgb_picker_frame,
                                                   highlightthickness=0, borderwidth=0, cursor="dotbox")
            # self.rgb_picker_canvas.pack_propagate(True)
            self.rgb_picker_canvas.pack(side="top", )

            self.rgb_img = Image.open(os.path.join("sources", "images", "RGB_picker.png"))
            self.resized_rgb_img = self.rgb_img.resize((200, 200), Image.NEAREST)
            self.current_rgb_img = ImageTk.PhotoImage(self.resized_rgb_img)

            center_x = self.resized_rgb_img.width // 2
            center_y = self.resized_rgb_img.height // 2
            self.rgb_picker_image = self.rgb_picker_canvas.create_image(0, 0, image=self.current_rgb_img,
                                                                        tags="img")

            self.rgb_slider_frame = ctk.CTkFrame(master=self.color_tools_frame, fg_color=self.orange_col)
            self.rgb_slider_frame.rowconfigure((0, 1, 2, 3), weight=1)
            self.rgb_slider_frame.columnconfigure(0, weight=1)
            self.rgb_slider_frame.columnconfigure(1, weight=1)
            self.rgb_slider_frame.pack(expand=False, )

            self.validate_numeric_255 = self.register(self.validate_rgb_input_values)
            self.red_slider_value_entry = ctk.CTkEntry(self.rgb_slider_frame, text_color="white",
                                                       font=("Arial Bold", 12),
                                                       border_width=0, placeholder_text="0", width=35, height=10,
                                                       validate="key",
                                                       validatecommand=(self.validate_numeric_255, "%P"))
            self.red_slider_value_entry.grid(row=1, column=1, sticky="e", padx=(0, 5), pady=2)

            self.red_slider = ctk.CTkSlider(self.rgb_slider_frame, fg_color="#B78383", button_color="red",
                                            button_hover_color="darkred",
                                            from_=0, to=255, number_of_steps=255, command=self.red_slider_event)
            self.red_slider.grid(row=1, column=0, sticky="w")
            self.red_slider.set(255)
            self.red_slider_value_entry.insert(0, 255)

            self.green_slider_value_entry = ctk.CTkEntry(self.rgb_slider_frame, text_color="white",
                                                         font=("Arial Bold", 12),
                                                         border_width=0, placeholder_text="0", width=35, height=10,
                                                         validate="key",
                                                         validatecommand=(self.validate_numeric_255, "%P"))
            self.green_slider_value_entry.grid(row=2, column=1, sticky="e", padx=(0, 5), pady=2)

            self.green_slider = ctk.CTkSlider(self.rgb_slider_frame, fg_color="#7E837F", button_color="green",
                                              button_hover_color="darkgreen", from_=0, to=255, number_of_steps=255,
                                              command=self.green_slider_event)
            self.green_slider.grid(row=2, column=0, sticky="w")
            self.green_slider.set(0)
            self.green_slider_value_entry.insert(0, 0)

            self.blue_slider_value_entry = ctk.CTkEntry(self.rgb_slider_frame, text_color="white",
                                                        font=("Arial Bold", 12),
                                                        border_width=0, placeholder_text="0", width=35, height=10,
                                                        validate="key",
                                                        validatecommand=(self.validate_numeric_255, "%P"))
            self.blue_slider_value_entry.grid(row=3, column=1, sticky="e", padx=(0, 5), pady=2)

            self.blue_slider = ctk.CTkSlider(self.rgb_slider_frame, fg_color="#7E7EAC", button_color="blue",
                                             button_hover_color="darkblue",
                                             from_=0, to=255, number_of_steps=255, command=self.blue_slider_event)
            self.blue_slider.grid(row=3, column=0, sticky="w")
            self.blue_slider.set(0)
            self.blue_slider_value_entry.insert(0, 0)

        def create_color_list_panel():
            COLOR_BTN_WIDTH = 30
            COLOR_BTN_BORDER_COL = "#DDDDDD"
            COLOR_BTN_BORDER_WIDTH = 2
            self.active_color = "#FF0000"
            self.previous_active_color = "#FF0000"
            self.first_color = "green"
            self.second_color = "blue"

            self.color_list_frame = ctk.CTkFrame(master=self.mid_frame3, fg_color=self.brown_col)
            self.color_list_frame.columnconfigure(0, weight=2)
            self.color_list_frame.columnconfigure((1, 2, 3, 4, 5), weight=1)
            self.color_list_frame.rowconfigure((0, 1), weight=1)
            self.color_list_frame.pack(side="top", expand=False, )

            self.active_color_btn = ctk.CTkButton(self.color_list_frame, fg_color="#FF0000",
                                                  hover=False, width=COLOR_BTN_WIDTH + 10,
                                                  height=COLOR_BTN_WIDTH + 10, text="",
                                                  border_width=COLOR_BTN_BORDER_WIDTH,
                                                  border_color=COLOR_BTN_BORDER_COL,
                                                  command=lambda color="#FF0000": self.set_active_color(color))
            self.active_color_btn.grid(row=1, column=0, rowspan=2, padx=(0, 5))

            self.first_color_btn = ctk.CTkButton(self.color_list_frame, fg_color="#00FF00",
                                                 hover=False,
                                                 width=COLOR_BTN_WIDTH,
                                                 height=COLOR_BTN_WIDTH, text="",
                                                 border_width=COLOR_BTN_BORDER_WIDTH,
                                                 border_color=COLOR_BTN_BORDER_COL,
                                                 command=lambda color="#00FF00": self.set_active_color(color))
            self.first_color_btn.grid(row=1, column=1, rowspan=1, padx=(0, 3))

            self.second_color_btn = ctk.CTkButton(self.color_list_frame, fg_color="#0000FF",
                                                  hover=False,
                                                  width=COLOR_BTN_WIDTH,
                                                  height=COLOR_BTN_WIDTH, text="",
                                                  border_width=COLOR_BTN_BORDER_WIDTH,
                                                  border_color=COLOR_BTN_BORDER_COL,
                                                  command=lambda color="#0000FF": self.set_active_color(color))
            self.second_color_btn.grid(row=1, column=2, rowspan=1, padx=3)

            # Color Picker button in create_tool_buttons()

        def create_tool_buttons():
            TOOL_BUTTON_WIDTH = 40
            TOOL_BUTTON_FG = "#4A4A4A"
            tool_button_hover = "#656565"
            TOOLS_FRAME_COL = self.default_col
            TOOL_HOVER = False
            TOOL_ICON_SIZE = (25, 25)

            color_picker_ld_img = ctk.CTkImage(
                light_image=Image.open(os.path.join("sources", "images", "tool_icons", "color_picker.png")),
                size=(18, 18))

            cursor_ld_img = ctk.CTkImage(
                light_image=Image.open(os.path.join("sources", "images", "tool_icons", "cursor.png")),
                size=(TOOL_ICON_SIZE))
            brush_ld_img = ctk.CTkImage(
                light_image=Image.open(os.path.join("sources", "images", "tool_icons", "brush.png")),
                size=(TOOL_ICON_SIZE))
            eraser_ld_img = ctk.CTkImage(
                light_image=Image.open(os.path.join("sources", "images", "tool_icons", "eraser.png")),
                size=(TOOL_ICON_SIZE))
            line_ld_img = ctk.CTkImage(
                light_image=Image.open(os.path.join("sources", "images", "tool_icons", "line.png")),
                size=(TOOL_ICON_SIZE))
            square_ld_img = ctk.CTkImage(
                light_image=Image.open(os.path.join("sources", "images", "tool_icons", "square.png")),
                size=(TOOL_ICON_SIZE))
            oval_ld_img = ctk.CTkImage(
                light_image=Image.open(os.path.join("sources", "images", "tool_icons", "circle.png")),
                size=(TOOL_ICON_SIZE))

            self.pan_ld_img = ctk.CTkImage(
                light_image=Image.open(os.path.join("sources", "images", "tool_icons", "pan.png")),
                size=(TOOL_ICON_SIZE))

            self.text_ld_img = ctk.CTkImage(
                light_image=Image.open(os.path.join("sources", "images", "tool_icons", "text.png")),
                size=TOOL_ICON_SIZE)

            self.text_disabled_ld_img = ctk.CTkImage(
                light_image=Image.open(os.path.join("sources", "images", "tool_icons", "text_disabled.png")),
                size=(TOOL_ICON_SIZE))

            self.text_color_ld_img = ctk.CTkImage(
                light_image=Image.open(os.path.join("sources", "images", "tool_icons", "text_color.png")),
                size=(TOOL_ICON_SIZE))

            self.text_color_disabled_ld_img = ctk.CTkImage(light_image=Image.open(
                os.path.join("sources", "images", "tool_icons", "text_color_disabled.png")),
                size=(TOOL_ICON_SIZE))

            self.color_picker_btn = ctk.CTkButton(self.color_list_frame, fg_color=TOOL_BUTTON_FG,
                                                  hover_color=tool_button_hover,
                                                  font=("Arial bold", 15), text_color="#474747",
                                                  border_spacing=0, hover=TOOL_HOVER,
                                                  width=TOOL_BUTTON_WIDTH - 10, height=TOOL_BUTTON_WIDTH - 10,
                                                  text="", image=color_picker_ld_img,
                                                  command=self.tools.color_picker_tool)

            self.color_picker_btn.grid(row=1, column=3, rowspan=1, padx=(3, 1))

            self.tools_frame = ctk.CTkFrame(master=self.mid_frame3, fg_color=self.violet_col)
            # self.tools_frame.grid_propagate(False)
            self.tools_frame.rowconfigure((0, 1), weight=1)
            self.tools_frame.columnconfigure(0, weight=1)
            self.tools_frame.pack(side="top", expand=False)

            self.tools_items_frame = ctk.CTkFrame(master=self.tools_frame,
                                                  fg_color=TOOLS_FRAME_COL)  # height=1
            self.tools_items_frame.grid_propagate(True)
            self.tools_items_frame.rowconfigure((0, 1, 2), weight=1)
            self.tools_items_frame.columnconfigure((0, 1, 2), weight=1)
            self.tools_items_frame.pack(side="top", expand=False, fill="x", pady=(10, 5))

            self.cursor_btn = ctk.CTkButton(self.tools_items_frame, fg_color=TOOL_BUTTON_FG,
                                            hover_color=tool_button_hover,
                                            font=("Arial bold", 15), text_color="#474747", border_spacing=0,
                                            hover=TOOL_HOVER,
                                            width=TOOL_BUTTON_WIDTH, height=TOOL_BUTTON_WIDTH, image=cursor_ld_img,
                                            text="", command=self.tools.cursor_tool)
            self.cursor_btn.grid(row=0, column=0, sticky="e", padx=(0, 3), pady=6)

            self.brush_btn = ctk.CTkButton(self.tools_items_frame, fg_color=TOOL_BUTTON_FG,
                                           hover_color=tool_button_hover,
                                           font=("Arial bold", 15), text_color="#474747", border_spacing=0,
                                           hover=TOOL_HOVER,
                                           width=TOOL_BUTTON_WIDTH, height=TOOL_BUTTON_WIDTH, image=brush_ld_img,
                                           text="", command=self.tools.brush_tool)
            self.brush_btn.grid(row=0, column=1, padx=3, pady=6)

            self.eraser_btn = ctk.CTkButton(self.tools_items_frame, fg_color=TOOL_BUTTON_FG,
                                            hover_color=tool_button_hover,
                                            font=("Arial bold", 15), text_color="#474747", border_spacing=0,
                                            hover=TOOL_HOVER,
                                            width=TOOL_BUTTON_WIDTH, height=TOOL_BUTTON_WIDTH, image=eraser_ld_img,
                                            text="", command=self.tools.eraser_tool)
            self.eraser_btn.grid(row=0, column=2, sticky="w", padx=(3, 0), pady=6)

            self.line_btn = ctk.CTkButton(self.tools_items_frame, fg_color=TOOL_BUTTON_FG,
                                          hover_color=tool_button_hover,
                                          font=("Arial bold", 15), text_color="#474747", border_spacing=0,
                                          hover=TOOL_HOVER,
                                          width=TOOL_BUTTON_WIDTH, height=TOOL_BUTTON_WIDTH, image=line_ld_img, text="",
                                          command=self.tools.line_tool)
            self.line_btn.grid(row=1, column=0, sticky="e", padx=(0, 3), pady=6)

            self.rectangle_btn = ctk.CTkButton(self.tools_items_frame, fg_color=TOOL_BUTTON_FG,
                                               hover_color=tool_button_hover,
                                               font=("Arial bold", 15), text_color="#474747", border_spacing=0,
                                               hover=TOOL_HOVER,
                                               width=TOOL_BUTTON_WIDTH, height=TOOL_BUTTON_WIDTH, image=square_ld_img,
                                               text="", command=self.tools.rectangle_tool)
            self.rectangle_btn.grid(row=1, column=1, padx=3, pady=6)

            self.oval_btn = ctk.CTkButton(self.tools_items_frame, fg_color=TOOL_BUTTON_FG,
                                          hover_color=tool_button_hover,
                                          font=("Arial bold", 15), text_color="#474747", border_spacing=0,
                                          hover=TOOL_HOVER,
                                          width=TOOL_BUTTON_WIDTH, height=TOOL_BUTTON_WIDTH, image=oval_ld_img, text="",
                                          command=self.tools.oval_tool)
            self.oval_btn.grid(row=1, column=2, sticky="w", padx=(3, 0), pady=6)

            self.pan_btn = ctk.CTkButton(self.tools_items_frame, fg_color=TOOL_BUTTON_FG,
                                         hover_color=tool_button_hover,
                                         font=("Arial bold", 15), text_color="#474747", border_spacing=0,
                                         hover=TOOL_HOVER,
                                         width=TOOL_BUTTON_WIDTH, height=TOOL_BUTTON_WIDTH, text="",
                                         image=self.pan_ld_img, command=self.tools.pan_tool)
            self.pan_btn.grid(row=2, column=0, sticky="e", padx=(0, 3), pady=6)

            self.text_btn = ctk.CTkButton(self.tools_items_frame, fg_color=TOOL_BUTTON_FG,
                                          hover_color=tool_button_hover,
                                          font=("Arial bold", 15), text_color="#474747", border_spacing=0,
                                          hover=TOOL_HOVER,
                                          width=TOOL_BUTTON_WIDTH, height=TOOL_BUTTON_WIDTH, text="",
                                          image=self.text_ld_img, command=self.tools.text_tool)
            self.text_btn.grid(row=2, column=1, padx=3, pady=6)

            self.text_color_btn = ctk.CTkButton(self.tools_items_frame, fg_color=TOOL_BUTTON_FG,
                                                hover_color=tool_button_hover, image=self.text_color_ld_img,
                                                font=("Arial bold", 15), text_color="#474747", border_spacing=0,
                                                hover=TOOL_HOVER,
                                                width=TOOL_BUTTON_WIDTH, height=TOOL_BUTTON_WIDTH, text="",
                                                command=self.tools.text_color_tool)
            self.text_color_btn.grid(row=2, column=2, sticky="w", padx=(3, 0), pady=6)

            self.tools_slider_frame = ctk.CTkFrame(master=self.tools_frame, fg_color=TOOLS_FRAME_COL,
                                                   corner_radius=5)  # height=1
            self.tools_slider_frame.rowconfigure((0, 1, 2, 3), weight=1)
            self.tools_slider_frame.columnconfigure((0, 1), weight=1)
            self.tools_slider_frame.pack(side="top", expand=True, pady=(0, 1))

            width_slider_label = ctk.CTkLabel(self.tools_slider_frame, text="Width:", font=("Arial ", 15))
            width_slider_label.grid(row=0, column=0, sticky="w", ipadx=10)

            self.width_slider_value_label = ctk.CTkLabel(self.tools_slider_frame, text=Tools.stroke_width,
                                                         font=("Arial Bold", 15), text_color="white")
            self.width_slider_value_label.grid(row=0, column=1, sticky="e", ipadx=10)

            self.width_slider = ctk.CTkSlider(self.tools_slider_frame, from_=1, to=50, command=self.width_slider_event,
                                              number_of_steps=49, )
            self.width_slider.grid(row=1, column=0, columnspan=2)
            self.width_slider.set(Tools.stroke_width)

            decimate_slider_label = ctk.CTkLabel(self.tools_slider_frame, text="Decimate:", font=("Arial ", 15))
            decimate_slider_label.grid(row=2, column=0, sticky="w", ipadx=10)

            self.decimate_slider_value_label = ctk.CTkLabel(self.tools_slider_frame,
                                                            text=int(Tools.decimate_factor * 10),
                                                            font=("Arial Bold", 15), text_color="white")
            self.decimate_slider_value_label.grid(row=2, column=1, sticky="e", ipadx=10)

            self.decimate_slider = ctk.CTkSlider(self.tools_slider_frame, from_=0, to=50,
                                                 command=self.decimate_slider_event,
                                                 number_of_steps=50)
            self.decimate_slider.grid(row=3, column=0, columnspan=2)
            self.decimate_slider.set(Tools.decimate_factor * 10)

        def create_modifier_tool_buttons():
            MODIFIER_BUTTON_WIDTH = 23
            MODIFIER_BUTTON_BORDER = 3
            MODIFIER_BUTTON_FONT = 14

            self.modifiers_frame = ctk.CTkFrame(master=self.mid_frame3, fg_color=self.brown_col)
            self.modifiers_frame.grid_propagate(True)
            self.modifiers_frame.rowconfigure((0, 1), weight=1)
            self.modifiers_frame.columnconfigure((0, 1, 2, 3), weight=1)
            self.modifiers_frame.pack(side="top", )

            uniform = ctk.CTkLabel(self.modifiers_frame, text="Uniform:", font=("Arial ", MODIFIER_BUTTON_FONT))
            uniform.grid(row=0, column=0, sticky="w", )
            self.uniform_checkbox = ctk.CTkCheckBox(self.modifiers_frame, text="", checkbox_width=MODIFIER_BUTTON_WIDTH,
                                                    checkbox_height=MODIFIER_BUTTON_WIDTH, width=0,
                                                    border_width=MODIFIER_BUTTON_BORDER,
                                                    command=self.tools.uniform_shape_checkbox_handler)
            self.uniform_checkbox.grid(row=0, column=1, sticky="w", )

            fill_color_label = ctk.CTkLabel(self.modifiers_frame, text="Fill:", font=("Arial ", MODIFIER_BUTTON_FONT))
            fill_color_label.grid(row=0, column=2, sticky="e")
            self.fill_color_checkbox = ctk.CTkCheckBox(self.modifiers_frame, text="",
                                                       checkbox_width=MODIFIER_BUTTON_WIDTH,
                                                       checkbox_height=MODIFIER_BUTTON_WIDTH, width=0,
                                                       border_width=MODIFIER_BUTTON_BORDER,
                                                       command=self.tools.fill_color_checkbox_handler, )
            self.fill_color_checkbox.grid(row=0, column=3, sticky="e", )

            self.flat_cap_label = ctk.CTkLabel(self.modifiers_frame, text="Flat Cap:",
                                               font=("Arial ", MODIFIER_BUTTON_FONT - 3))
            self.flat_cap_label.grid(row=1, column=0, sticky="w", )
            self.flat_cap_checkbox = ctk.CTkCheckBox(self.modifiers_frame, text="",
                                                     checkbox_width=MODIFIER_BUTTON_WIDTH,
                                                     checkbox_height=MODIFIER_BUTTON_WIDTH, width=0,
                                                     border_width=MODIFIER_BUTTON_BORDER,
                                                     command=self.tools.flat_cap_checkbox_handler)
            self.flat_cap_checkbox.grid(row=1, column=1, sticky="w")

            self.highlight_label = ctk.CTkLabel(self.modifiers_frame, text="Highlight:",
                                                font=("Arial ", MODIFIER_BUTTON_FONT - 3))
            self.highlight_label.grid(row=1, column=2, sticky="e")
            self.highlight_checkbox = ctk.CTkCheckBox(self.modifiers_frame, text="",
                                                      checkbox_width=MODIFIER_BUTTON_WIDTH,
                                                      checkbox_height=MODIFIER_BUTTON_WIDTH, width=0,
                                                      border_width=MODIFIER_BUTTON_BORDER,
                                                      command=self.tools.highlight_checkbox_handler)
            self.highlight_checkbox.grid(row=1, column=3, sticky="e")

        create_color_selector_panel()
        create_color_list_panel()
        create_tool_buttons()
        create_modifier_tool_buttons()

        self.create_image_tools_panel()
        # Makes a dictionary with the buttons.
        self.tools.create_tool_button_dict()
        # set first tool as cursor
        self.tools.cursor_tool()

    def rescale_tools_panel(self):
        """
        Rescales the tools panel to adapt to the new window size.

        Returns:
            None

        """

        tool_panel_width = int(self.image_frame_width * .130)

        self.resized_rgb_img = self.rgb_img.resize((tool_panel_width, tool_panel_width), Image.NEAREST)
        self.current_rgb_img = ImageTk.PhotoImage(self.resized_rgb_img)
        center_x = self.resized_rgb_img.width // 2
        center_y = self.resized_rgb_img.height // 2
        self.rgb_picker_frame.configure(width=tool_panel_width, height=tool_panel_width)
        self.rgb_picker_canvas.configure(width=tool_panel_width, height=tool_panel_width)
        self.rgb_picker_canvas.itemconfig(self.rgb_picker_image, image=self.current_rgb_img)
        self.rgb_picker_canvas.coords(self.rgb_picker_image, center_x, center_y)

        self.red_slider.configure(width=tool_panel_width - 30)
        self.green_slider.configure(width=tool_panel_width - 30)
        self.blue_slider.configure(width=tool_panel_width - 30)

        self.modifiers_frame.configure(width=tool_panel_width)

    def update_filename(self):
        """
        Updates the filename on the left lowerside with the name of the current displayed image.

        Returns:
            None

        """
        current_filename = os.path.basename(self.image_data[self.image_index]['file'])
        self.file_name_textbox.configure(state="normal")
        self.file_name_textbox.delete("0.0", "end")
        self.file_name_textbox.insert("0.0", current_filename)
        self.file_name_textbox.configure(state="disabled")

    def toggle_media_buttons(self, toggle: int):
        """
        Toggles the state of the media buttons.

        Args:
            toggle (int): 0 to disable ,1 to set state to normal.

        Returns:
            None

        """
        if toggle == 0:
            state = "disabled"
        else:
            state = "normal"
        self.first_btn.configure(state=state)
        self.last_btn.configure(state=state)
        self.prev_btn.configure(state=state)
        self.next_btn.configure(state=state)

    def toggle_image_control_buttons(self, toggle):
        """
        Toggles the state of the Display Image Control buttons (top).

        Args:
            toggle (int): 0 to disable ,1 to set state to normal.

        Returns:

        """

        if toggle == 0:
            self.lock_zoom_btn.configure(state="disabled")
            self.hq_view_btn.configure(state="disabled")
            self.actual_scale_btn.configure(state="disabled")
            self.hide_annotations_btn.configure(state="disabled")
        else:
            self.lock_zoom_btn.configure(state="normal")
            self.hq_view_btn.configure(state="normal")
            self.actual_scale_btn.configure(state="normal")
            self.hide_annotations_btn.configure(state="normal")

    # ====---Window Resize Call-----------------------------
    def window_resize(self, event=None, state=None):
        """
        Called on change in window size.

        Args:
            event (tkinter.Event): Event object
            state (str): "x" represents the initial state, "m" for maximzied and "w" for windowed.

        Returns:
            None

        """

        if state == "x":  # initial call.
            new_state = "x"

        if sys.platform.startswith('win'):  # Set state to maximized window
            if self.wm_state() == "zoomed":  # For Windows
                new_state = "m"
            else:
                new_state = "w"
        else:
            if self.wm_attributes("-zoomed") == 1:  # For linux
                new_state = "m"
            else:
                new_state = "w"

        if new_state != self.current_state:  # Only execute if state has changed

            if sys.platform.startswith('win'):
                if self.wm_state() == "zoomed":  # For Windows
                    self.current_state = 'm'
                else:
                    self.current_state = 'w'
            else:
                if self.wm_attributes("-zoomed") == 1:  # For linux
                    self.current_state = 'm'
                else:
                    self.current_state = 'w'

            if self.current_state == "m":  # Maximized
                self.screen_width = self.winfo_screenwidth()
                self.maximized_mode = True
                self.image_frame_width = self.image_frame_width_maxed
                self.image_frame_height = self.image_frame_height_maxed
                self.outliner_height = self.image_frame_height
                self.top_frame_right.configure(width=self.get_rel_width(.115))
                MODIFIERS_FONT_SIZE = 14
                SLIDER_FRAME_PADY = (0, 10)
                self.maximized_frame_size = (self.image_frame_width, self.image_frame_height)

                # Scaling the coordinates for the quick text insert.
                if TextInsertWindow.stored_text_position:
                    x = TextInsertWindow.stored_text_position.x
                    y = TextInsertWindow.stored_text_position.y
                    upscaled_coords = self.canvas_gm.scale_coordinates(coordinate_list=(x, y),
                                                                       scale_mode="+",
                                                                       scale_item="text")
                    TextInsertWindow.stored_text_position.x = upscaled_coords[0]
                    TextInsertWindow.stored_text_position.y = upscaled_coords[1]


            else:  # windowed mode
                self.maximized_mode = False
                self.screen_width = self.winfo_screenwidth()
                self.image_frame_width = self.image_frame_width_windowed
                self.image_frame_height = self.image_frame_height_windowed
                self.outliner_height = self.image_frame_height
                self.top_frame_right.configure(width=self.get_rel_width(.075))
                MODIFIERS_FONT_SIZE = 11
                SLIDER_FRAME_PADY = (0, 0)
                self.windowed_frame_size = (self.image_frame_width, self.image_frame_height)

                # Scaling the coordinates for the quick text insert.
                if TextInsertWindow.stored_text_position:
                    x = TextInsertWindow.stored_text_position.x
                    y = TextInsertWindow.stored_text_position.y

                    upscaled_coords = self.canvas_gm.scale_coordinates(coordinate_list=(x, y),
                                                                       scale_mode="-",
                                                                       scale_item="text")
                    TextInsertWindow.stored_text_position.x = upscaled_coords[0]
                    TextInsertWindow.stored_text_position.y = upscaled_coords[1]

            # Updating the widgets with new values based on the current window size.
            self.mid_frame_main.configure(height=self.image_frame_height)
            self.mid_frame1.configure(height=self.image_frame_height, )  # outliner panel
            self.mid_frame2.configure(height=self.image_frame_height, width=self.image_frame_width)
            self.mid_frame3.configure(height=self.image_frame_height, )  # side  panel
            self.image_frame.configure(width=self.image_frame_width, height=self.image_frame_height)

            self.mid_frame1.configure(width=self.image_frame_width // 4)
            self.mid_frame3.configure(width=self.image_frame_width // 4)

            self.overlay_canvas.configure(width=self.image_frame_width, height=self.image_frame_height)

            if self.maximized_mode:
                # Hides all proxy annotations.
                self.canvas_gm.hide_proxy_annotations(hide_current=True)
            else:
                self.canvas_gm.hide_parent_annotations(hide_current=True)

            # Updates the canvas frame
            self.update_image_canvas()

            self.outliner.configure(height=self.image_frame_height)

            self.rescale_tools_panel()
            self.flat_cap_label.configure(font=("Arial", MODIFIERS_FONT_SIZE))
            self.highlight_label.configure(font=("Arial", MODIFIERS_FONT_SIZE))

            self.tools_slider_frame.pack(pady=SLIDER_FRAME_PADY)

            # ----Removing item selection------------
            self.overlay_gm.rescale_overlay_images_to_view()
            self.overlay_gm.remove_text_item_selection()
            self.canvas_gm.remove_text_item_selection()

            self.canvas_text_insert.hide_text_insert_window()

            # Reset to cursor tool on window resize
            self.tools.cursor_tool()
            self.old_state = self.current_state

    # ---Color Fetch Decorator------------------
    def update_colors(func):
        """
        Decorator that updates the current color on the app.

        """

        @wraps(func)
        def wrapper_function(self, *args, **kwargs):
            main_func = func(self, *args, **kwargs)

            if kwargs.get('color_value') is not None:
                self.set_active_color()
                return main_func

            else:
                self.fetch_slider_color()
                self.set_active_color()
                return main_func

        return wrapper_function

    # ---Color Decorator Methods------------------
    def fetch_slider_color(self, event=None):
        """
        Fetches the RGB colors from the color slider and sets as active color.

        Args:
            event (tkinter.Event):

        Returns:
            None

        """
        red = int(self.red_slider.get())
        green = int(self.green_slider.get())
        blue = int(self.blue_slider.get())

        self.active_color = f"#{red:02x}{green:02x}{blue:02x}"  # RGB To Hex.

    def set_active_color(self, color=None):
        """
        Sets active color from other means like color picker.

        Args:
            color(str, optional): Hex color code to set as active color.

        Returns:

        """
        if color:
            self.active_color = color

        self.active_color_btn.configure(fg_color=self.active_color)
        Tools.fill_color = self.active_color

    # ----Decorated-------

    @update_colors
    def red_slider_event(self, event=None, color_value=None):
        """
        Called on red_slider value update.

        Args:
            event (tkinter.Event):
            color_value (str,optional): RGB color value of range 0 to 255

        Returns:
            None

        """
        if not color_value:
            slider_val = self.red_slider.get()
        else:
            slider_val = color_value

        if slider_val:
            self.red_slider_value_entry.delete(0, "end")
            self.red_slider_value_entry.insert(0, int(slider_val))
        else:
            self.red_slider_value_entry.delete(0, "end")
            self.red_slider_value_entry.insert(0, 0)

    @update_colors
    def red_entry_event(self, event):
        """
        Called on updating the red_slider_value_entry.

        Args:
            event (tkinter.Event):

        Returns:
            None

        """
        value = self.red_slider_value_entry.get()
        if value:
            self.red_slider.set(int(value))
        else:
            self.red_slider.set(0)

    @update_colors
    def green_slider_event(self, event=None, color_value=None):
        """
          Called on green_slider value update.

          Args:
              event (tkinter.Event):
              color_value (str,optional): RGB color value of range 0 to 255

          Returns:
              None

          """
        if not color_value:
            slider_val = self.green_slider.get()
        else:
            slider_val = color_value

        if slider_val:
            self.green_slider_value_entry.delete(0, "end")
            self.green_slider_value_entry.insert(0, int(slider_val))
        else:
            self.green_slider_value_entry.delete(0, "end")
            self.green_slider_value_entry.insert(0, 0)

    @update_colors
    def green_entry_event(self, event):
        """
         Called on updating the green_slider_value_entry.

         Args:
             event (tkinter.Event):

         Returns:
             None

         """
        value = self.green_slider_value_entry.get()
        if value:
            self.green_slider.set(int(value))
        else:
            self.green_slider.set(0)

    @update_colors
    def blue_slider_event(self, event=None, color_value=None):
        """
          Called on blue_slider value update.

          Args:
              event (tkinter.Event):
              color_value (str,optional): RGB color value of range 0 to 255

          Returns:
              None
        """

        if not color_value:
            slider_val = self.blue_slider.get()
        else:
            slider_val = color_value

        if slider_val:
            self.blue_slider_value_entry.delete(0, "end")
            self.blue_slider_value_entry.insert(0, int(slider_val))
        else:
            self.blue_slider_value_entry.delete(0, "end")
            self.blue_slider_value_entry.insert(0, 0)

    @update_colors
    def blue_entry_event(self, event):
        """
         Called on updating the blue_slider_value_entry.

         Args:
             event (tkinter.Event):

         Returns:
             None

         """
        value = self.blue_slider_value_entry.get()
        if value:
            self.blue_slider.set(int(value))
        else:
            self.blue_slider.set(0)

    @update_colors
    def pick_color(self, event=None, color=None, canvas: ctk.CTkCanvas = None):
        """
        Picks a color value(pixel) from the canvas.

        Args:
            event (tkinter.Event): Mouse cordiantes for the picked pixel.
            color (str, optional): Hex Color Code
            canvas (ctk.CTkCanvas, optional): If no canvas is provided, picker will pick colors from the rgb_picker_canvas.

        Returns:
            None

        """

        if not color:
            if not canvas:
                canvas_to_pick = self.rgb_picker_canvas
                image_to_pick = self.resized_rgb_img
            else:
                canvas_to_pick = canvas
                if self.display_mode == "actual":
                    image_to_pick = self.ld_img
                elif self.display_mode == "zoomed":
                    image_to_pick = self.zoomed_ld_img
                else:
                    image_to_pick = self.resized_ld_img

            x, y = canvas_to_pick.canvasx(event.x), canvas_to_pick.canvasy(event.y)

            rgb_picker_bbox = canvas_to_pick.bbox("img")

            if rgb_picker_bbox[0] <= x <= rgb_picker_bbox[2] - 1 and rgb_picker_bbox[1] <= y <= rgb_picker_bbox[3] - 1:
                canvas_to_pick.configure(cursor="dotbox")
                # x, y = event.x, event.y
                pixel = image_to_pick.getpixel((x, y))
                red = pixel[0]
                green = pixel[1]
                blue = pixel[2]

                self.red_slider.set(red)
                self.red_slider_event(color_value=red)
                self.green_slider.set(green)
                self.green_slider_event(color_value=green)
                self.blue_slider.set(blue)
                self.blue_slider_event(color_value=blue)
            else:
                canvas_to_pick.configure(cursor="arrow")
        else:
            rgb_values = self.winfo_rgb(color)
            rgb = tuple(int(value / 256) for value in rgb_values)
            red = rgb[0]
            green = rgb[1]
            blue = rgb[2]
            self.red_slider.set(red)
            self.red_slider_event(color_value=red)
            self.green_slider.set(green)
            self.green_slider_event(color_value=green)
            self.blue_slider.set(blue)
            self.blue_slider_event(color_value=blue)

    # -------------------------------------------------------------------
    def modify_previous_color_list(self, event):
        """
        Updates the previous colors.

       Args:
            event (tkinter.Event):

        Returns:
            None

        """
        if self.active_color != self.previous_active_color:
            old_a = self.first_color
            old_b = self.second_color

            self.first_color = self.previous_active_color
            self.second_color = old_a

            self.first_color_btn.configure(fg_color=self.first_color,
                                           command=lambda color=self.first_color: self.set_active_color(color))
            self.second_color_btn.configure(fg_color=self.second_color,
                                            command=lambda color=self.second_color: self.set_active_color(color))

            self.previous_active_color = self.active_color

    def validate_rgb_input_values(self, P):
        """
        Validates the manual value input on the color sliders.

        Args:
            P : Should be an int of range 0 to 255

        Returns:
            False if conditions not met.

        """
        if P == "":
            return True
        elif P == "0":
            return True
        elif P[0] == "0":  # Input must not start with 0
            return False
        elif P.isdigit() and len(P) <= 3:
            number = int(P)
            return 0 <= number <= 255
        return False

    def width_slider_event(self, event):
        """
        Called on updating the width_slider.

        Args:
            event (tkinter.Event):

        Returns:
            None

        """
        if event >= 1 and event < 41:  # Displaying color values based on the width range.
            color = "white"
        elif event == 50:
            color = "red"
            if Tools.current_tool == 3:  # Eraser
                self.error_prompt.display_error_prompt(error_msg="Eraser set to 'Wipe Current'(50).", priority=2)
        else:
            color = "orange"

        Tools.stroke_width = int(event)
        self.width_slider_value_label.configure(text=int(event), text_color=color)

    def decimate_slider_event(self, event):
        """
         Called on updating the decimate_slider.

         Args:
             event (tkinter.Event):

         Returns:
             None

         """

        if event == 0:
            color = "red"
        elif event >= 1 and event < 11:
            color = "orange"
        elif event >= 10 and event < 26:
            color = "white"
        else:
            color = "orange"

        self.decimate_slider_value_label.configure(text=int(event), text_color=color)
        Tools.decimate_factor = event / 10

    def change_stroke_width(self, event):
        """
        Uses the mouse scroll wheel to update the width_slider.

        Args:
            event (tkinter.Event):Mouse scroll event.

        Returns:
            None

        """

        if event.delta > 0:
            Tools.stroke_width += 1
        else:
            Tools.stroke_width -= 1
        width = Tools.stroke_width

        if width <= 0:
            Tools.stroke_width = 1
        elif width > 50:
            Tools.stroke_width = 50

        self.width_slider.set(Tools.stroke_width)
        if Tools.stroke_width >= 1 and Tools.stroke_width < 41:
            color = "white"
        else:
            color = "orange"
        self.width_slider_value_label.configure(text=int(Tools.stroke_width), text_color=color)

    # ----------------------------------------------------------------

    def update_image_canvas(self):  # Rescales the canvas image of window size change.
        """
        Updates the image canvas and the current image.

        Returns:
            None

        """
        self.ld_img = Image.open(self.images[self.image_index])  # Load the image based on the index.

        if self.display_mode == "actual":
            self.previous_display_mode = "actual"
            self.canvas_gm.reset_actual_size()

        elif self.display_mode == "zoomed" and self.lock_zoom:
            self.canvas_gm.reset_zoomed_size()

        elif self.display_mode == "zoomed":
            self.canvas_gm.reset_zoomed_size()

        self.scale_factor = 1
        self.display_mode = "default"
        self.previous_display_mode = "default"

        # Clearing the stored zoomed image from memmory.
        if self.zoomed_ld_img:
            self.zoomed_ld_img = None
        # Also responsible for removing the text selection border on clicking next.
        self.call_display_mode_func()

        aspect_ratio = self.ld_img.width / self.ld_img.height
        # aspect_width
        self.aspect_width_maxed = min(self.image_frame_width_maxed, int(self.image_frame_height_maxed * aspect_ratio))
        self.aspect_height_maxed = min(self.image_frame_height_maxed, int(self.image_frame_width_maxed / aspect_ratio))
        self.maximized_canvas_size = self.aspect_width_maxed, self.aspect_height_maxed

        self.aspect_width_windowed = min(self.image_frame_width_windowed,
                                         int(self.image_frame_height_windowed * aspect_ratio))
        self.aspect_height_windowed = min(self.image_frame_height_windowed,
                                          int(self.image_frame_width_windowed / aspect_ratio))
        self.windowed_canvas_size = self.aspect_width_windowed, self.aspect_height_windowed

        if self.current_state == "m":
            self.resized_ld_img = self.ld_img.resize((self.aspect_width_maxed, self.aspect_height_maxed),
                                                     resample=self.viewport_resample)
            self.image_canvas.configure(width=self.aspect_width_maxed, height=self.aspect_height_maxed)

        elif self.current_state == "w":
            self.resized_ld_img = self.ld_img.resize((self.aspect_width_windowed, self.aspect_height_windowed),
                                                     resample=self.viewport_resample)
            self.image_canvas.configure(width=self.aspect_width_windowed, height=self.aspect_height_windowed)

        self.current_imagetk = ImageTk.PhotoImage(self.resized_ld_img)
        center_x = self.resized_ld_img.width // 2
        center_y = self.resized_ld_img.height // 2

        self.image_canvas.itemconfig(self.display_image, image=self.current_imagetk)
        self.image_canvas.coords(self.display_image, center_x, center_y)
        # moves the image to lower stack so the drawing on top is visible
        self.image_canvas.tag_lower("img")
        self.image_canvas.configure(scrollregion=self.image_canvas.bbox(self.display_image))

        # self.canvas_gm.hide_proxy_annotations()
        # self.canvas_gm.hide_parent_annotations()

        self.overlay_gm.hide_parent_overlay_annotations()
        self.overlay_gm.hide_proxy_overlay_annotations()
        if self.current_state == "w":
            # Hides proxy annotation of the last viewed image index.
            self.canvas_gm.hide_proxy_annotations()
            self.canvas_gm.reveal_proxy_annotations()
            self.overlay_gm.reveal_proxy_overlay_annotations()

        else:
            # Hides parent annotation of the last viewed image index.
            self.canvas_gm.hide_parent_annotations()
            self.canvas_gm.reveal_parent_annotations()
            self.overlay_gm.reveal_parent_overlay_annotations()

        if self.overlay_canvas_visible:  # If overlay canvas was visible before update, re-enable it
            self.toggle_overlay_canvas(override=True, rescaled=True)

    def zoom_image(self, event=0, lock_zoom: bool = False):
        """
        Zooms the current image with the mouse cursor as anchor.

        Args:
            event(tkinter.Event): Mouse Position to anchor the zoom.
            lock_zoom (bool):If True,stores zoom value and scroll position and applies it to the next displayed image.

        Returns:
            None

        """

        if not lock_zoom:
            if event.delta < 0 and self.display_mode == "default":
                return

            if self.display_mode == "actual":
                return

            mouse_canvasx = self.image_canvas.canvasx(event.x)
            mouse_canvasy = self.image_canvas.canvasy(event.y)

            if event.delta > 0:
                self.scale_factor *= 1.5  # Zoom in
            else:
                self.scale_factor *= 1 / 1.5  # Zoom out
            self.scale_factor = max(1, self.scale_factor)

        self.display_mode = "zoomed"
        if self.previous_display_mode != "zoomed":
            self.call_display_mode_func()

        self.previous_display_mode = "zoomed"

        self.previous_display_mode = self.display_mode

        self.zoomed_ld_img = self.ld_img.resize((int(self.resized_ld_img.width * self.scale_factor),
                                                 int(self.resized_ld_img.height * self.scale_factor)),
                                                resample=self.viewport_resample)

        self.current_imagetk = ImageTk.PhotoImage(self.zoomed_ld_img)

        center_x = self.zoomed_ld_img.width // 2
        center_y = self.zoomed_ld_img.height // 2

        self.image_canvas.configure(width=self.zoomed_ld_img.width, height=self.zoomed_ld_img.height)
        self.image_canvas.itemconfig(self.display_image, image=self.current_imagetk)
        self.image_canvas.coords(self.display_image, center_x, center_y)
        self.image_canvas.tag_lower("img")
        self.image_canvas.configure(scrollregion=self.image_canvas.bbox(self.display_image))

        if not lock_zoom:
            if event.delta > 0:  # Zoom in
                new_mouse_x = mouse_canvasx * 1.5
                new_mouse_y = mouse_canvasy * 1.5
                zoomin_x = new_mouse_x - self.image_canvas.canvasx(event.x)
                zoomin_y = new_mouse_y - self.image_canvas.canvasy(event.y)
                self.image_canvas.xview('scroll', int(zoomin_x), 'units')
                self.image_canvas.yview('scroll', int(zoomin_y), 'units')
                self.canvas_gm.scale_to_zoomed_size(mode="+")
            else:  # Zoom out
                znew_mouse_x = mouse_canvasx / 1.5
                znew_mouse_y = mouse_canvasy / 1.5
                zoomout_x = int(znew_mouse_x - self.image_canvas.canvasx(event.x))
                zoomout_y = int(znew_mouse_y - self.image_canvas.canvasy(event.y))
                self.image_canvas.xview('scroll', zoomout_x, 'units')
                self.image_canvas.yview('scroll', zoomout_y, 'units')
                self.canvas_gm.scale_to_zoomed_size(mode="-")

        else:
            self.canvas_gm.scale_to_zoomed_size(mode="+", lock_zoom=True)

        if self.scale_factor == 1:
            self.update_image_canvas()
            self.call_display_mode_func()

            # self.display_mode="default"

    def show_actual_scale(self):
        """
        Displays the current image in its actual size, 1:1 ratio.

        Returns:
            None

        """
        # Directly load the image as it is.
        if self.display_mode == "actual":
            # Prevents from setting the actual size twice.
            self.canvas_gm.reset_actual_size()
            self.update_image_canvas()
            return

        elif self.display_mode == "zoomed":
            self.canvas_gm.reset_zoomed_size()
            self.update_image_canvas()
            self.display_mode = "default"
            self.show_actual_scale()
            return

        self.current_imagetk = ImageTk.PhotoImage(self.ld_img)

        center_x = self.ld_img.width // 2
        center_y = self.ld_img.height // 2

        self.image_canvas.itemconfig(self.display_image, image=self.current_imagetk)
        self.image_canvas.coords(self.display_image, center_x, center_y)
        self.image_canvas.tag_lower("img")

        self.image_canvas.configure(width=self.ld_img.width, height=self.ld_img.height,
                                    scrollregion=self.image_canvas.bbox(self.display_image))

        canvas_width = self.ld_img.width
        canvas_height = self.ld_img.height
        if self.maximized_mode:
            frame_center_x = self.maximized_frame_size[0] / 2
            frame_center_y = self.maximized_frame_size[1] / 2
        else:
            frame_center_x = self.windowed_frame_size[0] / 2
            frame_center_y = self.windowed_frame_size[1] / 2

        dx = (canvas_width / 2) - frame_center_x
        dy = (canvas_height / 2) - frame_center_y

        self.image_canvas.xview_scroll(int(dx), "units")
        self.image_canvas.yview_scroll(int(dy), "units")

        self.canvas_gm.scale_to_actual_size()
        self.display_mode = "actual"
        self.actual_scale_btn.configure(text="Actual Scale: ON", fg_color=self.TOP_BUTTON_FG_ACTIVE)
        self.call_display_mode_func()

    def handle_hq_view_btn(self):
        """
        Sets the resampling algorithm to Image.LANCZOS resulting in a higher quality image.

        Returns:
            None

        """
        if self.viewport_resample != 1:  # 3 is returned if it's bicubic.
            self.hq_view_btn.configure(text="HQ View: ON", fg_color=self.TOP_BUTTON_FG_ACTIVE)
            self.viewport_resample = Image.LANCZOS
        else:
            self.hq_view_btn.configure(text="HQ View: OFF", fg_color=self.TOP_BUTTON_FG)
            self.viewport_resample = Image.NEAREST
        self.update_image_canvas()

    def handle_hide_annotations_btn(self, enable: bool = None):
        """
        Method called on toggling the hide_annotations_btn

        Args:
            enable (bool,optional):If True sets the button to active.

        Returns:
            None

        """

        self.canvas_gm.remove_text_item_selection()
        if not self.canvas_gm.annotation_visibility or enable:
            self.hide_annotations_btn.configure(text="Annotations: ON", fg_color=self.TOP_BUTTON_FG_ACTIVE)
            self.canvas_gm.annotation_visibility = True
            if self.maximized_mode:
                self.canvas_gm.reveal_parent_annotations()
            else:
                self.canvas_gm.reveal_proxy_annotations()

            if self.display_mode != "default":
                self.canvas_gm.hide_current_text_items()

        else:
            self.canvas_gm.hide_proxy_annotations(hide_current=True)
            self.canvas_gm.hide_parent_annotations(hide_current=True)
            self.canvas_gm.annotation_visibility = False
            # Set current tool to cursor.
            self.hide_annotations_btn.configure(text="Annotations: OFF", fg_color=self.TOP_BUTTON_FG)

            self.tools.cursor_tool()

    def handle_actual_scale_btn(self):
        """
        Method called on toggling the actual_scale_btn

        Returns:
            None

        """

        if self.display_mode == "actual":
            # self.actual_scale_btn.configure(text="Actual Scale: OFF",fg_color=self.TOP_BUTTON_FG)
            self.previous_display_mode = "actual"
            self.update_image_canvas()
        elif self.display_mode == "default" or "zoomed":
            self.show_actual_scale()
            # self.actual_scale_btn.configure(text="Actual Scale: ON",fg_color=self.TOP_BUTTON_FG_ACTIVE)

    def handle_lock_zoom_btn(self):
        """
           Method called on toggling the lock_zoom_btn

           Returns:
               None

           """
        if self.lock_zoom:
            self.lock_zoom = False
            self.lock_zoom_btn.configure(text="Zoom:", fg_color=self.TOP_BUTTON_FG, image=self.unlock_ld_img,
                                         compound="right")
        else:
            self.lock_zoom = True
            self.lock_zoom_btn.configure(text="Zoom:", fg_color=self.TOP_BUTTON_FG_ACTIVE, image=self.lock_ld_img,
                                         compound="right")

    def call_display_mode_func(self):
        """
        Called whenever the display_mode changes.

        Returns:
            None.

        """
        try:
            if self.display_mode == "default":
                self.text_btn.configure(state="normal", image=self.text_ld_img)
                self.text_color_btn.configure(state="normal", image=self.text_color_ld_img)
            else:
                if self.tools.current_tool in (8, 9):
                    self.tools.cursor_tool()

                self.text_btn.configure(state="disabled", image=self.text_disabled_ld_img)
                self.text_color_btn.configure(state="disabled", image=self.text_color_disabled_ld_img)

            self.canvas_gm.remove_text_item_selection()

        except AttributeError:
            pass

    def handle_queue(self):
        """
        Adds or removes the image from the render queue based on the value from queue_switch button.

        Returns:
            None
        """
        switch_value = self.queue_switch.get()
        if switch_value == 1:  # switch is on
            self.update_queue_switch(is_queued=True)
            self.add_to_queue()
        else:
            self.update_queue_switch(is_queued=False)
            self.remove_from_queue()

    def add_to_queue(self, index=None):
        """
        Adds an image to the Render queue.

        Args:
            index(int, optional):Index of the image to add to the Render queue, Default is the index of the currently displayed image.

        Returns:
            None
        """
        index = index if index is not None else self.image_index
        self.image_data[index]["in_queue"] = True

    def remove_from_queue(self, index=None):
        """
         Removes an image from the Render queue.

         Args:
             index(int, optional):Index of the image to add to the Render queue, Default is the index of the currently displayed image.

         Returns:
             None
         """

        index = index if index is not None else self.image_index
        self.image_data[index]["in_queue"] = False

    # ------Canvas Panning----------------------
    def set_drag(self, event):
        """
        Sets the starting drag point on the canvas for panning.

        Args:
            event (tkinter.Event): Mouse click position.

        Returns:
            None

        """
        # self.image_canvas.scan_mark(event.x, event.y)
        self.set_x = event.x
        self.set_y = event.y

    def drag_canvas(self, event):
        """
        Pans the canvas.

        Args:
            event (tkinter.Event): Mouse Drag event.

        Returns:
            None

        """
        dx = event.x - self.set_x
        dy = event.y - self.set_y
        self.image_canvas.xview('scroll', -dx, 'units')
        self.image_canvas.yview('scroll', -dy, 'units')
        self.set_x = event.x
        self.set_y = event.y

    # -----Decorator----------------------------------
    def edit_data(func):
        """
        Decorator responsible for updating the text and settings to the project dictionary as well as
            updating the UI elements before and after displaying a different image.

        """

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            """
            Wrapper function for the edit_data decorator.

            Args:
                self:
                *args:
                **kwargs:

            Returns:
                The decorated method.

            """
            if self.available_index <= 0:  # Do nothing if the app has only one image loaded.
                return

            self.prev_image_index = self.image_index
            # Checks if the current comment box has any text and saves to dictionary, returns True if Text exists.
            has_annotation = self.has_annotation()
            is_queued = self.get_queue_status()
            # --------------------------------------------------
            # is the current image the first one?
            if self.image_index != 0 and self.image_index != self.available_index:
                if self.previous_image_index == -1:  # coming from 1st or last?
                    prev_index = self.image_index
                else:
                    self.previous_image_index = -1
                    prev_index = self.image_index
            else:
                prev_index = -1
            # reset the graphics and image to default from actual image ratio.
            if self.display_mode == "actual":
                self.canvas_gm.reset_actual_size()


            elif self.display_mode == "zoomed":
                self.x_scroll = self.canvas_scrollbar_x.get()
                self.y_scroll = self.canvas_scrollbar_y.get()
                self.canvas_gm.reset_zoomed_size()

            self.prev_display_mode = self.display_mode
            self.display_mode = "default"
            # Calls the decorated method.
            self.last_viewed_image_index = self.image_index
            self.prev_scale_factor = self.scale_factor

            self.error_prompt.hide_error_prompt(animate=False)
            main_func = func(self, *args, **kwargs)

            # ------After index change------------
            # after function execution and image index is updated. New image loads.
            self.previous_image_index = prev_index
            self.current_frame_label.configure(text=f"{self.image_index + 1}")
            self.update_outliner_selection(has_annotation=has_annotation, is_queued=is_queued)
            is_current_index = self.get_queue_status()
            self.update_queue_switch(is_queued=is_current_index)

            self.update_image_canvas()
            if self.prev_display_mode == "actual":
                self.display_mode = "default"
                self.show_actual_scale()

            elif self.prev_display_mode == "zoomed" and self.lock_zoom:
                # Scale factor gets reset to 1 in the rescale_canvas_frame
                self.scale_factor = self.prev_scale_factor
                self.zoom_image(lock_zoom=True)
                self.image_canvas.xview_moveto(self.x_scroll[0])
                self.image_canvas.yview_moveto(self.y_scroll[0])

            # Scrolls the outliner to the current image index.
            self.scroll_to_view()
            self.configure_button_functionality()
            self.update_filename()

            if self.overlay_canvas_visible:
                self.toggle_overlay_canvas(override=True)

            memory_info = psutil.Process(self.pid).memory_info()
            # print(f"Memory used: {memory_info.rss / (1024 * 1024)} MB")
            return main_func

        return wrapper

    # ----Decorator Methods--------------------------------------

    def has_annotation(self, index: int = None):
        """
        Checks if the Image in the provided index has any annotations.

        Args:
            index (int,optional): Index of the image to check for annotation, Default is the current viewed image.

        Returns:
            bool: True if the index has annotations, else False.

        """
        index = index if index is not None else self.image_index

        if self.graphics_data[index]:
            return True
        else:
            return False

    def get_queue_status(self, index: int = None):
        """
        Get the queue status of the index.

        Args:
            index (int,optional):Index to check for queue status. Default is the current index.

        Returns:
                bool: True if index is queued, False if not queued.
        """

        index = index if index is not None else self.image_index
        if self.image_data[index]["in_queue"]:
            return True
        else:
            return False

    def update_outliner_selection(self, has_annotation=False, is_queued=True):
        """
        Updates the color of the outliner index selection based on the status of the index.

        Args:
            has_annotation= True if the index has annotation. Default is False.
            is_queued (bool):True if the index is in queue. Default is True

        Returns:
                None

        """

        if has_annotation:
            index_color = self.index_queue_comment_col
            index_text_color = self.index_queue_comment_txt_col
        else:
            index_color = self.index_queue_col
            index_text_color = self.index_queue_txt_col

        if has_annotation and not is_queued:
            index_color = self.index_queue_comment_remove_col
            index_text_color = self.index_removed_txt_col
        elif not is_queued:
            index_color = self.index_removed_col
            index_text_color = self.index_removed_txt_col

        # Assigns colors to the previous index,
        self.outliner.file_index_list[self.last_viewed_image_index].configure(state="normal", fg_color=index_color,
                                                                              text_color=index_text_color)

        # Assign selection color and disables the current Index.

        current_index_button: ctk.CTkButton = self.outliner.file_index_list[self.image_index]
        current_index_button.configure(state="disabled", fg_color=self.index_selected_col,
                                       text_color_disabled=self.index_selected_txt_col)

    def update_outliner_color(self, index=None, has_annotation=None, is_queued=True):
        """
        Updates the color of the Outliner index based on the status of the index.

         Args:
            has_annotation= True if the index has annotation. Default is False.
            is_queued (bool):True if the index is in queue. Default is True

        Returns:
                None

        """

        index = index if index is not None else self.image_index
        if has_annotation:
            index_color = self.index_queue_comment_col
            index_text_color = self.index_queue_comment_txt_col
        else:
            index_color = self.index_queue_col
            index_text_color = self.index_queue_txt_col

        if has_annotation and not is_queued:
            index_color = self.index_queue_comment_remove_col
            index_text_color = self.index_removed_txt_col
        elif not is_queued:
            index_color = self.index_removed_col
            index_text_color = self.index_removed_txt_col

        self.outliner.file_index_list[index].configure(state="normal", fg_color=index_color,
                                                       text_color=index_text_color)

    def update_queue_switch(self, is_queued=True):
        """
        Updates the state of the queue switch without calling the command.

        Args:
            is_queued (bool):Default is True

        Returns:
                None
        """

        if is_queued:
            self.queue_switch.select()
            self.queue_switch.configure(button_color=self.queue_switch_enabled_col)
        elif not is_queued:
            self.queue_switch.deselect()
            self.queue_switch.configure(button_color=self.queue_switch_disabled_col)

    def configure_button_functionality(self):
        """
        Disables the functionality of the Media buttons if the index has reached the limit.

        Returns:
                None
        """

        if self.image_index == self.available_index:
            self.last_btn.configure(command=lambda: None)
            self.next_btn.configure(command=lambda: None)
        else:
            self.last_btn.configure(command=self.show_last_img)
            self.next_btn.configure(command=self.show_next_img)

        if self.image_index == 0:
            self.first_btn.configure(command=lambda: None)
            self.prev_btn.configure(command=lambda: None)
        else:
            self.first_btn.configure(command=self.show_first_img)
            self.prev_btn.configure(command=self.show_previous_img)

    def scroll_to_view(self):
        """
        Scrolls the Outliner till the current filename/sequence becomes visible in the outliner.

        Returns:
                None
        """
        canvas_ypos = abs(self.outliner.file_index_frame.winfo_y())
        current_button = self.outliner.file_index_list[self.image_index]
        outliner_label_height = 30

        # Getting on the bottom points of the button.
        index_ypos = current_button.winfo_y() + current_button.winfo_reqheight()

        distance_to_button = index_ypos - canvas_ypos
        # 30 is the height of the outliner heading.
        scroll_upside_limit = 0
        scroll_downside_limit = self.outliner.winfo_reqheight() - outliner_label_height

        if distance_to_button > scroll_downside_limit:
            increment_value = distance_to_button - scroll_downside_limit
            self.outliner.file_index_frame._parent_canvas.yview_scroll(increment_value, "units")

        elif distance_to_button < scroll_upside_limit:
            increment_value = distance_to_button - scroll_upside_limit - outliner_label_height
            self.outliner.file_index_frame._parent_canvas.yview_scroll(increment_value, "units")

    # -----------Outliner mouse interactions--------------------

    def on_right_click(self, *args, index: int):
        """
        Toggles the queue status of the index based on the index right-clicked on the outliner.

        Args:
            index (int): Index is hardcoded to each Index elements in the outliner at the time of Outliner creation.

        Returns:
            None
        """
        if index == self.image_index:
            # self.update_outliner_selection()
            self.queue_switch.toggle()
        else:
            image_index_to_toggle = index
            is_queued = self.get_queue_status(image_index_to_toggle)
            # has_text = self.has_text(index=image_index_to_toggle)
            has_annotation = self.has_annotation(index=image_index_to_toggle)
            if is_queued:
                self.remove_from_queue(image_index_to_toggle)
                is_queued = False
            else:
                self.add_to_queue(image_index_to_toggle)
                is_queued = True
            self.update_outliner_color(has_annotation=has_annotation, is_queued=is_queued, index=image_index_to_toggle)

    def on_mouse_enter(self, index, event=None):
        """
        Called on hovering the mouse over the outliner. If shift key pressed during the hover, display full file name in the outliner.

        Args:
            index (int): Index value of the outliner index hovered over.
            event (tkinter.Event): Mouse position.

        Returns:
            None

        """
        if self.current_hovered_btn_index != index:
            # Checks if shift key is pressed.
            if event.state & 0x1:
                current_btn = self.outliner.file_index_list[index]
                button_ypos = current_btn.winfo_rooty()

                self.outliner_hover_btn.configure(text=os.path.basename(self.image_data[index]['file']),
                                                  command=current_btn.invoke)
                self.outliner_hover_btn.place(relx=0, rely=1, anchor='sw', in_=current_btn, )

                self.current_hovered_btn_index = index

    def on_mouse_leave(self, event=None, index: int = None, override: bool = False):
        """
         Called when cursor leaves the outliner. Removes the full filename element from the outliner.

        Args:
            index (int): Index value of the outliner index hovered over.
            event (tkinter.Event): Mouse position.
            override (bool): True removes the full filename element bypassing any conditions. Default False

        Returns:
            None

        """

        if self.current_hovered_btn_index != index or override:
            self.outliner_hover_btn.place_forget()

    # -----------------------------
    # make a dictionary with index and sequence if possible files_dict= {1:{}}

    # -------Image Cycling----------------------------

    @edit_data
    def show_next_img(self, event=None):
        """
        Shows the next image.

        Args:
            event (tkinter.Event):Button click event.

        Returns:
                None
        """

        if self.image_index < self.available_index:
            self.image_index += 1

    @edit_data
    def show_previous_img(self, event=None):
        """
        Shows the previous image.

        Args:
             event (tkinter.Event):Button click event.

        Returns:
                None
        """
        if self.image_index <= self.available_index and self.image_index != 0:
            self.image_index -= 1

    @edit_data
    def show_last_img(self, event=None):
        """
          Shows the last image.

          Args:
               event (tkinter.Event):Button click event.

          Returns:
                  None
        """

        if self.image_index != self.available_index:
            if self.previous_image_index == -1:
                self.image_index = self.available_index
            else:
                self.image_index = self.previous_image_index

    @edit_data
    def show_first_img(self, force_first=False, event=None):
        """
          Shows the first image.

          Args:
               event (tkinter.Event):Button click event.

          Returns:
                  None
        """
        if force_first:  # forcing seek to the first image.
            self.image_index = 0
            return

        if self.image_index != 0:
            if self.previous_image_index == -1:
                self.image_index = 0
            else:
                self.image_index = self.previous_image_index

    @edit_data
    def fetch_from_outline(self, index: int, event=None, ):
        """
        Display the image according to the index(button) selected on the outliner.

        Args:
            index (int): Index of the image to set as current image_index.
            event (tkinter.Event):Mouse click event.


        Returns:
               None
        """
        self.image_index = index

    # ------File Processing------------------

    def open_file_window(self):
        """
        Creates and Opens the FileLoad window.

        Returns:
                None
        """

        self.file_load_window = FileLoadWindow(app=self)
        # self.file_load_window.wait_visibility()
        self.file_load_window.grab_set()

    def create_render_menu(self, batch: bool = True):
        """
        Creates a RenderMenu toplevel window and displays the Render Menu window.

        Args:
            batch (bool): True adds all images in queue to render. False renders the current image. Default True.

        Returns:
                None
        """
        if self.render_menu:
            self.render_menu.destroy()
        self.render_menu = RenderMenu(app=self, batch=batch)
        # self.render_menu.withdraw()  # hide the window
        # self.render_menu.after(200, self.render_menu.deiconify)
        self.render_menu.attributes('-topmost', True)
        # self.render_menu.wait_visibility()
        self.render_menu.grab_set()

    def load_images(self):
        """
        Gets the images from the file load window.

        Returns:
                None
        """
        self.protocol = "images"
        self.images = self.file_load_window.file_list
        self.available_index = len(self.images) - 1

        self.cache_data(protocol="images")
        self.main_layout()
        self.file_load_window.update_file_window_progressbar(1, progress_color="#0FDC54")  # darkgreen

        # Makes the main app window visible.
        self.after(200, self.deiconify)
        self.after(350, self.image_canvas.focus_set)  # set focus to the canvas.

    def generate_placeholder_image(self, image_save_folder, image_filename, image_size):
        blank_image = Image.new("RGB", (image_size), "#D71EA3")  # Pink for missing images.

        place_holder_image_savepath = os.path.join(image_save_folder, image_filename)
        blank_image.save(place_holder_image_savepath, quality=3, compress_level=3)

    def load_project(self, project_path: str, images_folder_override_path=None, ignore_missing_images: bool = False):
        """
        Gets the Project file from the file load window.

        Args:
            project_path(str): Path to the project file.
            images_folder_override_path(str|None,optional): Path containing the images used in the saved project.
            ignore_missing_images(bool): True generates blank placeholder images for missing images. False raises error if images not found. Default False.

        Returns:
             None
        """
        self.protocol = "project"
        self.project_path = project_path
        self.cache_data(protocol="project")
        self.images = []  # Clearing the old images from the list.

        for index in self.image_data:
            current_filepath = self.image_data[index]["file"]
            if os.path.exists(current_filepath):  # If path exists then ignore rest.
                self.images.append(current_filepath)

            else:
                if images_folder_override_path:
                    # Replace the folder path of all files.
                    directory, image_filename = os.path.split(current_filepath)
                    overridden_filepath = os.path.join(images_folder_override_path, image_filename)

                    if os.path.exists(images_folder_override_path):
                        if os.path.exists(overridden_filepath):
                            # Rewriting the filepath.
                            self.images.append(overridden_filepath)
                            self.image_data[index]["file"] = overridden_filepath

                        else:
                            if ignore_missing_images:
                                self.generate_placeholder_image(image_filename=image_filename,
                                                                image_save_folder=images_folder_override_path,
                                                                image_size=self.image_data[index]["image_size"])

                                # Updating.
                                self.images.append(overridden_filepath)
                                self.image_data[index]["file"] = overridden_filepath

                            else:
                                raise FileNotFoundError
                    else:
                        raise FileNotFoundError
                else:
                    raise FileNotFoundError

        self.available_index = len(self.images) - 1
        self.create_graphics_data_dict()  # creating graphics_data and proxy_data
        self.main_layout()

        self.file_load_window.grab_set()

        self.canvas_gm.draw_graphic_elements_from_project_file()
        # Drawing the overlay canvas items.
        if self.loaded_graphics_data[-1] or self.loaded_graphics_data[-2]:  # -1 for overlay annotations -2 for images.
            self.overlay_gm.draw_graphic_elements_from_project_file()

        self.file_load_window.update_file_window_progressbar(0.9)  # No reason. :p
        self.file_load_window.update_file_window_progressbar(1, progress_color="#0FDC54")  # darkgreen

        del self.loaded_graphics_data  # Clearing from memory.
        self.tools.cursor_tool()  # Reset to cursor tool
        self.tools.reset_tool_variables()  # Reset the tool values like width to default.

        self.deiconify()
        # Scrolls the outliner to the top.
        self.outliner.file_index_frame._parent_canvas.yview_moveto(0.0)
        self.image_canvas.focus_set()  # set focus to the canvas.

    def cache_data(self, protocol):
        """
        Generates a dictionary from the loaded data.

        Args:
            protocol (str): "images" or "project"

        Returns:
                None
        """

        def create_data_dict(image_size, file, sequence_code=None, in_queue=True):
            """
            Creates a key with 'filename', 'sequence_code' and their 'queue' status of the image.

            Args:
                file (str):file path of the image.
                sequence_code : Sequence code extracted from the filename.
                in_queue (bool): Default True.

            Returns:
                dict: A dictionary.
            """

            entry_dict = {
                "file": file,
                "sequence_code": sequence_code,
                "image_size": image_size,
                "in_queue": in_queue
            }
            return entry_dict

        # Getting the sequence search mode from the fileload window.
        sequence_search = self.file_load_window.sequence_search_mode

        if protocol == "images":
            for image_index in range(0, self.available_index + 1):
                current_image_sequence_code = FileHandler.get_sequence_code(filename=self.images[image_index],
                                                                            sequence_search=sequence_search)

                image_filepath = self.images[image_index]

                # Storing the size to generate placeholder images incase if image is removed.
                try:
                    with Image.open(image_filepath) as img:
                        image_size = img.size
                except Exception:
                    raise

                self.image_data[image_index] = create_data_dict(file=image_filepath,
                                                                sequence_code=current_image_sequence_code,
                                                                image_size=image_size)

            self.create_settings_dict()
            self.create_graphics_data_dict()

        elif protocol == "project":
            loaded_data = FileHandler.load_project_file(self.project_path)
            if loaded_data:  # Fetching the values and assigning them to variables.
                self.image_data = loaded_data["image_data"]
                self.settings_data = loaded_data["settings"]
                self.loaded_graphics_data = loaded_data["graphics_data"]
                # self.graphics_data=loaded_data["graphics_data"]
                self.project_data = {"settings": self.settings_data, "image_data": self.image_data,
                                     "graphics_data": self.graphics_data}

    def create_settings_dict(self):
        """
        Creating a dictionary with the settings values used in the RenderMenu and assigns to self.settings_data.

        Returns:
            None

        """
        settings_dict = {
            "render_overlay": self.render_overlay,
            "trim_overlay": self.trim_overlay,
            "render_sequence_code": self.render_sequence_code,
            "sequence_code_render_position": self.sequence_code_render_position,
            "anti_alias": self.anti_alias_output,
            "include_blanks": self.include_blanks,
            "jpeg_quality": self.jpeg_quality,
            "png_compression": self.png_compression,
            "output_path": self.output_path
        }
        self.settings_data = settings_dict

    def create_graphics_data_dict(self, ):
        """
        Creates the graphics_data and proxy_data dictionary with keys starting from index -2 to number of total images and empty dictionary as values.

        Returns:
            None

        """
        # -2 because, -2 and -1 are needed for overlay elements..

        self.graphics_data = {i: {} for i in range(-2, self.available_index + 1)}
        self.proxy_data = copy.deepcopy(self.graphics_data)

    def save_data(self, from_exit_prompt: bool = False):
        """
        Saves the current project_data dictionary as a .rvp (pickle) file.

        Args:
            from_exit_prompt (bool):Whether the method is being called from the exit_prompt. (to set parent for the asksaveasfilename).Default False.

        Returns:
            bool|None: True if saved, False if failed. None, if operation cancelled.
        """
        # Updates the settings dictionary
        self.create_settings_dict()

        # Making a copy because graphics data has image_objects which will result in high file saving,
        # The image_objects are needed for image transformations within the current session.but not for saving.
        self.save_graphics_data = copy.deepcopy(self.graphics_data)

        # clearing Irrelevant image_object PIL files.
        self.flush_image_objects_from_overlaycache()

        # updated the project_data
        self.project_data = {"settings": self.settings_data,
                             "image_data": self.image_data,
                             "graphics_data": self.save_graphics_data}

        if from_exit_prompt:  # Parent is the exit_prompt toplevel window.
            project_save_path = filedialog.asksaveasfilename(parent=self.exit_prompt, defaultextension=".rvp",
                                                             filetypes=[("RView", "*.rvp")])
        else:  # parent is the main app
            project_save_path = filedialog.asksaveasfilename(parent=self, defaultextension=".rvp",
                                                             filetypes=[("RView", "*.rvp")])

        if project_save_path:
            project_saved = FileHandler.save_project_file(project_data=self.project_data,
                                                          output_path=project_save_path)
            if project_saved:
                return True

            else:  # Display an error prompt if project failed to save.
                self.error_prompt.display_error_prompt(error_msg="Project failed to save.", priority=1)

        return None

    def flush_image_objects_from_overlaycache(self):
        """
        Removes the PIL.IMAGE objects from the overlaycache dictionary.

        Returns:
            None

        """

        OVERLAY_IMAGES_INDEX = -2
        # Image Objects are not needed for loading and saving, so removing them to reduce the save file size.
        for item_id, image_element in self.save_graphics_data[OVERLAY_IMAGES_INDEX].items():
            del image_element.image_object

    def close_all(self):
        """
        Opens the exit prompt window.

        Returns:
                None
        """

        if self.exit_prompt:
            self.exit_prompt.destroy()

        self.exit_prompt = ExitPrompt(app=self)
        # self.exit_prompt.withdraw()
        # self.after(100,self.exit_prompt.deiconify)
        self.exit_prompt.attributes("-topmost", True)
        self.exit_prompt.wait_visibility()
        self.exit_prompt.grab_set()

    def kill_app(self):
        """
        Kills the main app

        Returns:
                None
        """
        self.destroy()

    # ----Relative Maths---------------
    def get_rel_height(self, times):
        """
        Gets the relative height value proportional to the screen height.

        Args:
            times(float): A float value that multiplies the screen height.

        Returns:
            int: The relative height as an integer.
        """
        height = math.ceil((self.winfo_screenwidth() * 0.5625) * times)
        # self.screen_height = self.screen_width * 0.5625
        return height

    def get_rel_width(self, times):
        """
         Gets the relative width value proportional to the screen width.

         Args:
             times(float): A float value that multiplies the screen width.

         Returns:
            int: The relative width as an integer.

         """
        width = math.ceil(self.winfo_screenwidth() * times)
        return width


# --------UI tweaks-----------------

try:  # Setting the DPI settings.
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    pass

ctk.deactivate_automatic_dpi_awareness()


# --------RUN-----------------
def main():
    """
    main
    Returns:
        None

    """
    app = App(className="R-View Tool")
    app.mainloop()


if __name__ == "__main__":
    main()
