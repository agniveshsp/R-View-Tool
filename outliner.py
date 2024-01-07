import customtkinter as ctk
import sys
import os


class Outliner(ctk.CTkFrame):
    """Custom class that generates an outliner with clickable index buttons that navigates to the linked image."""

    def __init__(self, *args, master,
                 width: int = 100,
                 height: int = 30,
                 fg_color="#383838",
                 corner_radius=0,
                 parent_app,
                 **kwargs):
        super().__init__(*args, master=master, width=width,
                         height=height, fg_color=fg_color,
                         corner_radius=corner_radius, **kwargs)

        self.app = parent_app
        self.image_data = self.app.image_data
        self.list_is_sequence = True

        self.outliner_font = ctk.CTkFont(family="Arial", size=13, weight="bold")

        self.pack_propagate(False)
        self.outliner_label_frame = ctk.CTkFrame(master=self, fg_color="#153463",
                                                 height=height)
        self.outliner_label_frame.columnconfigure((0, 1, 2), weight=1)
        self.outliner_label_frame.rowconfigure(0, weight=1)
        self.outliner_label_frame.pack(fill="x", side="top")

        self.sequence_switch = ctk.CTkSwitch(self.outliner_label_frame, text="", width=0,
                                             button_color="#199133",
                                             command=self.toggle_sequence_naming, switch_height=15, )

        self.sequence_switch.grid(column=0, row=0)

        self.outliner_label = ctk.CTkLabel(master=self.outliner_label_frame, text="Outliner",
                                           text_color="#D6D5D5", font=self.outliner_font)

        self.outliner_label.grid(column=1, row=0)

        self.file_index_frame = ctk.CTkScrollableFrame(master=self, fg_color="#383838",
                                                       corner_radius=0)

        if sys.platform.startswith('linux'):
            self.file_index_frame.bind("<Button-4>", self.outline_scroll_handler, "+")
            self.file_index_frame.bind("<Button-5>", self.outline_scroll_handler, "+")
            self.file_index_frame._scrollbar.bind("<Button-4>", self.outline_scroll_handler, "+")
            self.file_index_frame._scrollbar.bind("<Button-5>", self.outline_scroll_handler, "+")

        # bind("<Button-5>", self.mouse_scroll_handler, "+"

        self.file_index_frame.pack(expand=True, fill="both", side="top")
        self.file_index_list = []
        self.create_file_index()

        # Setting the increment to 1, (didn't have to if it was just windows. :/ )
        self.file_index_frame._parent_canvas.configure(yscrollincrement=1)

    def create_file_index(self):
        """
        Loops through the loaded images, creates and assigns an outliner button element for each image and hardcodes the command with the index as parameter.

        Returns:
             None
        """
        files_indexed = 0
        self.index_queue_col = "#1F57AB"
        self.index_queue_txt_col = "#EBEBEB"

        self.index_removed_col = "#585A5B"
        self.index_removed_txt_col = "#A1A1A1"

        self.index_queue_comment_col = "#279258"
        self.index_queue_comment_txt_col = "white"
        self.index_queue_comment_remove_col = "#496F5A"

        # Change the fg color of the file_load progress bar to make it visible.
        self.app.file_load_window.file_load_progressbar.configure(fg_color="#3D3D3D")  # dark grey

        for index in self.image_data:
            # button_text = f"{index + 1}#  {self.image_data[index]['sequence_code']}"
            # Start with actual filenames.
            button_text = os.path.basename(self.image_data[index]['file'])

            button = ctk.CTkButton(master=self.file_index_frame, corner_radius=0, anchor="w", border_spacing=3,
                                   text=button_text, height=27, width=600, text_color_disabled="#A1A1A1")

            files_indexed += 1

            if self.app.protocol == "project":
                has_graphic_elements = self.app.loaded_graphics_data[index]
                # No graphical elements but queued.
                if not has_graphic_elements and self.image_data[index]["in_queue"]:
                    index_color = self.index_queue_col
                    text_color = self.index_queue_txt_col

                # No graphical elements but not queued.
                elif not has_graphic_elements and not self.image_data[index]["in_queue"]:
                    index_color = self.index_removed_col
                    text_color = self.index_removed_txt_col

                # Has graphical elements and is queued.
                elif has_graphic_elements and self.image_data[index]["in_queue"]:
                    index_color = self.index_queue_comment_col
                    text_color = self.index_queue_comment_txt_col

                # Has graphical elements but not queued.
                elif has_graphic_elements and not self.image_data[index]["in_queue"]:
                    index_color = self.index_queue_comment_remove_col
                    text_color = self.index_removed_txt_col
                # 0 to 0.5 range here, because other .5 reserved for the progress of redrawing the graphic elements.
                progress = files_indexed / (len(self.image_data) * 2)
                self.app.file_load_window.update_file_window_progressbar(progress)

            else:
                index_color = self.index_queue_col
                text_color = self.index_queue_txt_col
                progress = files_indexed / len(self.image_data)  # 0 to 1 range
                self.app.file_load_window.update_file_window_progressbar(progress)

            button.configure(text_color=text_color, fg_color=index_color, font=self.outliner_font)

            # binding call functions as parameters for each instance  of the index button.
            button.configure(command=lambda id=index,: self.app.fetch_from_outline(index=id))
            button.bind("<Button-3>", command=lambda event, id=index: self.app.on_right_click(index=id))
            button.bind("<Enter>", command=lambda event, id=index: self.app.on_mouse_enter(event=event, index=id))
            button.bind("<Leave>", command=lambda event, id=index: self.app.on_mouse_leave(event=event, index=id))
            if sys.platform.startswith('linux'):
                button.bind("<Button-4>", self.outline_scroll_handler, "+")
                button.bind("<Button-5>", self.outline_scroll_handler, "+")

            button.grid(row=index, sticky="we", pady=2)
            # Stores the created index buttons to a list.
            self.file_index_list.append(button)

    def toggle_sequence_naming(self):
        """
        When Called, the outliner changes the text of the indexes from file name to sequence codes.

        Returns:
            False

        """
        self.image_data = self.image_data

        if self.sequence_switch.get() == 1:
            self.sequence_switch.configure(button_color="#19CC40")

            for index, button in enumerate(self.file_index_list):
                button.configure(text=f"{index + 1}#  {self.image_data[index]['sequence_code']}")
        else:
            self.sequence_switch.configure(button_color="#199133")
            for index, button in enumerate(self.file_index_list):
                button.configure(text=os.path.basename(self.image_data[index]['file']))

    def outline_scroll_handler(self, event):
        """
        Scrolls the outliner.(Method for in Linux)

        Args:
            event: Mouse Wheel event

        Returns:
            None

        """
        if event.num == 4:
            event.delta = 120
        elif event.num == 5:
            event.delta = -120

        self.file_index_frame._parent_canvas.yview("scroll", -int(event.delta / 6), "units")
