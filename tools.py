import sys

import customtkinter as ctk
import tkinter as tk
from fontTools.ttLib import TTFont
import os
from functools import wraps


class TextInsertWindow(ctk.CTkFrame):
    """
    Custom Widget that handles the insertion of text items into the canvas.
    """
    selected_font = ""
    new_font_pixel_size = -50
    selected_font_index = 0
    selected_font_size = -50
    selected_font_file = ""

    stored_text_size: int = None
    stored_text_position = None

    def __init__(self, app, *args, **kwargs):
        """
        Args:
            app: tkinter Main app
            *args:
            **kwargs:
        """
        super().__init__(*args, **kwargs)
        self.app = app
        width = int(self.app.image_frame_width_maxed * .32)
        height = int(self.app.image_frame_height_maxed * .30)

        self.configure(height=height, width=width, fg_color="#43356B", corner_radius=0)
        self.pack_propagate(False)

        self.top_frame = ctk.CTkFrame(self, fg_color="#43356B", height=25, corner_radius=0)
        self.top_frame.pack(side="top", fill="both")

        self.reset_font_size_btn = ctk.CTkButton(master=self.top_frame, text="Reset Font Size", fg_color="#851936",
                                                 hover_color="#75143b", command=self.reset_font_size)
        self.reset_font_size_btn.pack(side="left")

        self.highlight_warning = ctk.CTkLabel(master=self.top_frame, text_color="#FFF500",
                                              text="",
                                              font=("Arial Bold", 13))
        self.highlight_warning.pack(side="right", padx=20)

        self.main_frame = ctk.CTkFrame(self, fg_color="#43356B", corner_radius=0)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=3)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.pack(side="bottom", fill="both", padx=(0, 5), pady=(0, 5))

        self.text_insert_layout()
        # Binding the Return key to insert the text from the widget onto the canvas.
        self.insert_textbox.bind('<Return>', self.handle_insert_text_btn)

    def reset_font_size(self):
        TextInsertWindow.selected_font_size = -50

    def text_insert_layout(self):
        """
        Creates the text insert widget.
        Returns:
            None

        """

        # Colors to visualize the frame layout. (debug purpose)
        if 1 != 1:
            self.lavender_col = "lavender"
            self.violet_col = "violet"
            self.indigo_col = "indigo"
            self.maroon_col = "maroon"
            self.olive_col = "olive"
            self.navy_col = "navy"
        else:
            TEXT_WINDOW_COL = "#6C59A1"
            self.lavender_col = TEXT_WINDOW_COL
            self.violet_col = TEXT_WINDOW_COL
            self.indigo_col = TEXT_WINDOW_COL
            self.maroon_col = TEXT_WINDOW_COL
            self.olive_col = TEXT_WINDOW_COL
            self.navy_col = TEXT_WINDOW_COL

        self.TEXT_BOX_FONT_SIZE = 20
        # self.configure(bg="#332A50")

        self.left_frame = ctk.CTkFrame(self.main_frame, fg_color="#553C9E", corner_radius=0)
        self.left_frame.columnconfigure(0, weight=1)
        self.left_frame.columnconfigure(1, weight=3)
        self.left_frame.rowconfigure(0, weight=1)
        self.left_frame.rowconfigure(1, weight=2)
        self.left_frame.grid(row=0, column=0, sticky="news", padx=(0, 5))

        self.right_frame = ctk.CTkFrame(self.main_frame, fg_color=self.indigo_col)
        self.right_frame.columnconfigure(0, weight=1)
        self.right_frame.rowconfigure(0, weight=3)
        self.right_frame.rowconfigure(1, weight=1)

        self.right_frame.grid(row=0, column=1, sticky="news", )

        self.font_refresh_btn = ctk.CTkButton(self.left_frame, fg_color="#553C9E",
                                              border_color="#4A338D",
                                              text_color="white", text="Refresh",
                                              hover=False, command=self.populate_listbox,
                                              corner_radius=0)
        self.font_refresh_btn.grid(row=0, column=0, columnspan=2, sticky="news")

        self.font_list_box = tk.Listbox(self.left_frame, background=self.lavender_col,
                                        fg="white", borderwidth=0, selectbackground="#352D4D",
                                        highlightthickness=0,
                                        font=("Arial", 10), exportselection=0)
        self.font_list_box.grid(row=1, column=1, sticky="news")
        self.font_list_box_scrollbar_y = ctk.CTkScrollbar(self.left_frame, command=self.font_list_box.yview,
                                                          bg_color="#43356B", button_color="#E4DEF5")
        self.font_list_box.configure(yscrollcommand=self.font_list_box_scrollbar_y.set)
        self.font_list_box_scrollbar_y.grid(row=1, column=0, sticky="nws")
        self.font_list_box.bind("<<ListboxSelect>>", self.on_listbox_select)

        self.text_top_frame = ctk.CTkFrame(self.right_frame, fg_color=self.maroon_col)
        self.text_top_frame.grid(row=0, column=0, sticky="news")

        self.text_bottom_frame = ctk.CTkFrame(self.right_frame, fg_color=self.olive_col)
        self.text_bottom_frame.columnconfigure((0, 1, 2), weight=1)
        self.text_bottom_frame.rowconfigure((0, 1), weight=1)
        self.text_bottom_frame.grid(row=1, column=0, sticky="news")

        self.insert_textbox = ctk.CTkTextbox(master=self.text_top_frame, corner_radius=5,
                                             fg_color="#E4DEF5", border_color="#352D4D",
                                             border_width=2, text_color="black", wrap="word",
                                             activate_scrollbars=True, exportselection=False,
                                             font=(TextInsertWindow.selected_font, self.TEXT_BOX_FONT_SIZE))

        self.insert_textbox.pack(side="top", fill="both", expand=True)

        self.font_warning_label = ctk.CTkLabel(master=self.text_bottom_frame, text_color="white",
                                               text="Use the Dropdown only if the font update fails.",
                                               font=("Arial", 15))
        self.font_warning_label.grid(row=0, column=0, columnspan=3, pady=5)

        self.cancel_btn = ctk.CTkButton(master=self.text_bottom_frame, text="Cancel", font=("Arial", 20),
                                        fg_color="#A53A4D", hover_color="#C71616", height=50, width=0,
                                        command=self.hide_text_insert_window)
        self.cancel_btn.grid(row=1, column=0, pady=(0, 5))

        self.font_variation_combobox = ctk.CTkComboBox(self.text_bottom_frame, state="readonly", font=("Arial", 15),
                                                       border_width=0, button_color="#5A4499",
                                                       command=self.on_combobox_select,
                                                       fg_color="#BDB1DF", text_color="#2B2528",
                                                       dropdown_fg_color="#504080", dropdown_text_color="#E4E4E4",
                                                       border_color="#504080", dropdown_hover_color="#352D4D")

        self.font_variation_combobox.grid(row=1, column=1, pady=(0, 5))
        self.font_variation_combobox.set(TextInsertWindow.selected_font)

        self.insert_text_btn = ctk.CTkButton(master=self.text_bottom_frame, text="Insert", font=("Arial", 20),
                                             fg_color="#1C54A7", height=50, width=0, hover_color="#213552",
                                             command=self.handle_insert_text_btn)
        self.insert_text_btn.grid(row=1, column=2, pady=(0, 5))
        self.populate_listbox()  # Loads and lists the fonts on the sidebar.

    def populate_listbox(self):
        """
        Loads the fonts from the 'fonts' folder in the program directory and lists the fonts in the widget list box.
        Returns:
            None

        """
        FONT_FOLDER = "fonts"
        self.font_list_box.delete(0, tk.END)
        if os.path.exists(FONT_FOLDER) and os.path.isdir(FONT_FOLDER):
            files = os.listdir(FONT_FOLDER)
            font_files = [file for file in files if file.lower().endswith(('.ttf', '.otf'))]
            for font_file in font_files:
                self.font_list_box.insert(tk.END, font_file)

            self.font_list_box.selection_set(0)
            font_name = font_files[0]
            self.on_listbox_select(file_name=font_name)

        else:
            self.app.error_prompt.display_error_prompt(error_msg="fonts folder not Found", priority=1)
            self.font_list_box.insert(tk.END, "fonts folder not Found!")

    def check_if_overlay(func):
        """
        Decorator that checks if the current active canvas is the base canvas or the overlay canvas.

        """

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # If the overlay canvas is visible, reassigning  the variables accordingly.
            if self.app.overlay_canvas_visible:
                self.gm = self.app.overlay_gm
                self.active_canvas = self.app.overlay_canvas
            else:
                self.gm = self.app.canvas_gm
                self.active_canvas = self.app.image_canvas
            result = func(self, *args, **kwargs)
            return result

        return wrapper

    @check_if_overlay
    def on_listbox_select(self, event=0, file_name=None):
        """
        Called on selecting a font name from the listbox. Assigns the Text font as the selected font.
        Args:
            event(tkinter.Event,optional):Mouse click event.
            file_name (str,optional): Font filename to use.

        Returns:
            None

        """
        if not file_name:
            # Get the selected item in the listbox
            font_file_name = self.font_list_box.get(self.font_list_box.curselection())
        else:
            font_file_name = file_name
        self.font_variation_list = []
        # TextInsertWindow.selected_font = self.font_list_box.get(self.font_list_box.curselection())
        try:
            font = TTFont(os.path.join("fonts", font_file_name))
            for record in font['name'].names:
                # 95% of time The Full font name comes just before the Version.
                if str(record).split()[0] == "Version":
                    break
                else:
                    try:  # Sometimes it won't have 'Version' and will only be the version numbers.
                        float_value = float(str(record))
                    except ValueError:
                        pass
                    else:
                        break
                self.font_variation_list.append(str(record))

            font.close()
            self.font_variation_combobox.configure(state="normal")
            self.font_variation_list = self.font_variation_list[1:]
            self.font_variation_list.reverse()
            self.font_variation_combobox.configure(values=self.font_variation_list)
            # Usually the full font name comes just before version.
            self.font_variation_combobox.set(self.font_variation_list[0])
            self.font_variation_combobox.configure(state="readonly")
            selected_font = self.font_variation_list[0]
            self.insert_textbox.configure(font=(selected_font, self.TEXT_BOX_FONT_SIZE))

        except Exception as e:
            self.app.error_prompt.display_error_prompt(error_msg=e, priority=1)

    @check_if_overlay
    def on_combobox_select(self, choice):
        """
        Called on selecting an option from the dropdown combobox.
        Args:
            choice(str): Name of the font.

        Returns:
            None

        """
        self.font_variation_combobox.configure(state="normal")
        self.font_variation_combobox.set(choice)
        self.font_variation_combobox.configure(state="readonly")
        selected_font = choice
        self.insert_textbox.configure(font=(selected_font, self.TEXT_BOX_FONT_SIZE))

    @check_if_overlay
    def handle_insert_text_btn(self, event=None):
        """
        Inserts the text from the widget onto the canvas.
        Args:
            event (tkinter.Event):

        Returns:
            None

        """
        text = self.insert_textbox.get("0.0", "end").replace("\n", " ")  # remove all linebreaks before text insertion.
        if text and not text.isspace():
            TextInsertWindow.selected_font = self.font_variation_combobox.get()
            TextInsertWindow.selected_font_index = self.font_list_box.curselection()[0]
            TextInsertWindow.selected_font_file = self.font_list_box.get(TextInsertWindow.selected_font_index)
            self.gm.draw_release(text=text)
            self.hide_text_insert_window()
            self.active_canvas.focus_set()

        elif text.isspace():  # If there is no text hide the widget.
            self.hide_text_insert_window()

    @check_if_overlay
    def hide_text_insert_window(self):
        """
        Hides the text_insert_window widget.

        Returns:
            None

        """
        # Clear the initial click Coordinates on closing the main window.
        self.insert_textbox.delete("0.0", "end")
        self.grab_release()
        self.place_forget()
        self.active_canvas.focus_set()

    @check_if_overlay
    def reveal_text_insert_window(self, event=None):
        """
        Displays the text_insert_window widget.
        Args:
            event(tkinter.Event,optional):

        Returns:
            None

        """
        if self.app.highlight_checkbox.get() == 1:  # If highlight box is checked.
            self.highlight_warning.configure(text="Highlight Mode ENABLED")
        else:
            self.highlight_warning.configure(text="")
        self.place(in_=self.app.image_frame, relx=0.5, rely=0.5, anchor="center")

        self.wait_visibility()
        self.grab_set()
        self.insert_textbox.delete("0.0", "end")
        self.after(150, self.insert_textbox.focus_set)


class Tools:
    """
    Class that handles the different tools in the main app.
    """
    current_tool = 1
    previous_tool = 0
    stroke_width = 10
    fill_color = "#FF0000"
    decimate_factor = 1.5
    shape_fill = False
    stipple = ""
    shape_constraint = False
    endcap = "round"

    def __init__(self, app, canvas, graphics_manager):
        """
        Initializer for the tool class.
        Args:
            app: Main app
            canvas: Canvas the tool is being used in.
            graphics_manager: GraphicManager or OverlayGraphicsManager.
        """
        self.app: ctk = app
        self.active_canvas = canvas
        self.gm = graphics_manager
        self.default_tool_button_col = "#4A4A4A"
        self.active_tool_button_col = "black"

        self.enabled_checkbox_col = "#1F6AA5"
        self.disabled_checkbox_col = "grey"

    # -------Decorator------------------
    def select_tool_button(func):
        """
        Decorator that handles the switch to a new tool.

        """

        @wraps(func)
        def wrapper_function(self, *args, **kwargs):
            # "Before executing wrapped function"
            if self.app.overlay_canvas_visible:
                self.active_canvas = self.app.overlay_canvas
            else:
                self.active_canvas = self.app.image_canvas

            self.tool_buttons[Tools.current_tool].configure(fg_color=self.default_tool_button_col, border_width=0)
            Tools.previous_tool = Tools.current_tool
            if self.app.error_prompt.error_prompt_in_display:
                self.app.error_prompt.hide_error_prompt(animate=False)

            main_func = func(self, *args, **kwargs)

            self.active_canvas.focus_set()
            self.tool_buttons[Tools.current_tool].configure(fg_color=self.active_tool_button_col, border_width=2,
                                                            border_color="#B2B2B2")

            # Removes all item selections if any.
            self.app.canvas_gm.remove_text_item_selection()
            self.app.overlay_gm.remove_text_item_selection()
            self.app.overlay_gm.remove_overlay_image_selection()

            if Tools.current_tool not in [1] and not self.gm.annotation_visibility:
                if Tools.current_tool == 7:
                    if self.app.display_mode == "default":
                        self.app.handle_hide_annotations_btn(enable=True)
                else:
                    self.app.handle_hide_annotations_btn(enable=True)

            return main_func

        return wrapper_function

    # ------------------------------------
    @select_tool_button
    def color_picker_tool(self):
        """
        Activates the Color Picker tool.
        Returns:
            None

        """
        Tools.current_tool = 0
        self.active_canvas.configure(cursor="dotbox")
        self.disable_all_modifiers()

    @select_tool_button
    def cursor_tool(self):  # 1
        """
        Activates the Cursor tool.

        Returns:
            None

        """
        Tools.current_tool = 1  # 1 for cursor
        self.active_canvas.configure(cursor="arrow")
        self.app.canvas_text_insert.hide_text_insert_window()
        self.disable_all_modifiers()

    @select_tool_button
    def brush_tool(self):  # 2
        """
        Activates the brush tool.

        Returns:
              None
        """

        Tools.current_tool = 2  # 2 for brush
        self.active_canvas.configure(cursor="dot")
        self.disable_all_modifiers()
        self.app.highlight_checkbox.configure(state="normal", fg_color=self.enabled_checkbox_col)

    @select_tool_button
    def eraser_tool(self):
        """
      Activates the Eraser tool.

      Returns:
          None

        """
        Tools.current_tool = 3  # 3 for eraser
        try:
            self.active_canvas.configure(cursor="x_cursor")
        except:  # For Linux.
            self.active_canvas.configure(cursor="star")

        if Tools.stroke_width == 50:
            self.app.error_prompt.display_error_prompt(error_msg="Eraser set to 'Wipe Current'(50).", priority=2)

        self.disable_all_modifiers()

    @select_tool_button
    def line_tool(self):
        """
          Activates the Line tool.

          Returns:
              None

          """
        Tools.current_tool = 4  # 4 for line
        self.active_canvas.configure(cursor="target")
        self.disable_all_modifiers()
        self.app.flat_cap_checkbox.configure(state="normal", fg_color=self.enabled_checkbox_col)
        self.app.highlight_checkbox.configure(state="normal", fg_color=self.enabled_checkbox_col)

    @select_tool_button
    def rectangle_tool(self):  # 5
        """
        Activates the Rectangle tool.

        Returns:
            None

        """
        Tools.current_tool = 5  # 5 for rectangle
        if self.app.highlight_checkbox.get() == 1:
            Tools.shape_fill = True
            self.app.fill_color_checkbox.select()
            self.app.fill_color_checkbox.configure(state="disabled", fg_color=self.enabled_checkbox_col)
        self.disable_all_modifiers()
        if self.app.highlight_checkbox.get() != 1:
            self.app.fill_color_checkbox.configure(state="normal", fg_color=self.enabled_checkbox_col)
        # self.app.fill_color_checkbox.configure(state="normal",fg_color=self.enabled_checkbox_col)
        self.app.uniform_checkbox.configure(state="normal", fg_color=self.enabled_checkbox_col)
        self.app.highlight_checkbox.configure(state="normal", fg_color=self.enabled_checkbox_col)
        self.active_canvas.configure(cursor="sizing")

    @select_tool_button
    def oval_tool(self):  # 5
        """
        Activates the Oval tool.

        Returns:
            None

        """
        Tools.current_tool = 6  # 5 for circle
        self.disable_all_modifiers()
        self.app.uniform_checkbox.configure(state="normal", fg_color=self.enabled_checkbox_col)
        self.app.fill_color_checkbox.configure(state="normal", fg_color=self.enabled_checkbox_col)
        if sys.platform.startswith("win"):
            self.active_canvas.configure(cursor="circle")
        else:
            self.active_canvas.configure(cursor="target")

    @select_tool_button
    def pan_tool(self):
        """
        Activates the Pan tool.

        Returns:
            None

        """

        Tools.current_tool = 7
        self.active_canvas.configure(cursor="fleur")
        self.disable_all_modifiers()

    @select_tool_button
    def text_tool(self):
        """
         Activates the Text tool.

         Returns:
             None

         """
        Tools.current_tool = 8
        self.active_canvas.configure(cursor="cross")
        self.disable_all_modifiers()
        Tools.stipple = ""
        self.app.highlight_checkbox.configure(state="normal", fg_color=self.enabled_checkbox_col)
        self.app.highlight_checkbox.deselect()

    @select_tool_button
    def text_color_tool(self):
        """
         Activates the Text color tool.

         Returns:
             None

         """
        Tools.current_tool = 9
        self.active_canvas.configure(cursor="plus")

    def create_tool_button_dict(self):
        """
        Creates a dictionary consisting of the tool index as keys and the buttons as values. For ease of configuring the buttons.
        Returns:
            None

        """
        self.tool_buttons = {0: self.app.color_picker_btn,
                             1: self.app.cursor_btn,
                             2: self.app.brush_btn,
                             3: self.app.eraser_btn,
                             4: self.app.line_btn,
                             5: self.app.rectangle_btn,
                             6: self.app.oval_btn,
                             7: self.app.pan_btn,
                             8: self.app.text_btn,
                             9: self.app.text_color_btn}

    def enable_all_tool_buttons(self):
        """
        Sets the state of all tool buttons to normal.
        Returns:
            None

        """
        for key, button in self.tool_buttons:
            button.configure(state="normal")

    def disable_all_tool_buttons(self):
        """
        Sets the state of all tool buttons to 'disabled'.

        Returns:
            None

        """
        for key, button in self.tool_buttons:
            button.configure(state="disabled")

    # -----Modifier checkboxes--------------------------
    def uniform_shape_checkbox_handler(self):
        """
        Gets the state of the uniform checkbox and sets the shape_constraint variable accordingly.

        Returns:
            None

        """
        if self.app.uniform_checkbox.get() == 1:  # If checked.
            Tools.shape_constraint = True
        else:
            Tools.shape_constraint = False

    def fill_color_checkbox_handler(self):
        """
        Gets the state of the fill checkbox and sets the shape_fill variable accordingly.

        Returns:
                 None

        """
        if self.app.fill_color_checkbox.get() == 1:  # if checked.
            Tools.shape_fill = True
        else:
            Tools.shape_fill = False

    def flat_cap_checkbox_handler(self):
        """
        Gets the state of the flatcap checkbox and sets the endcap variable accordingly.

        Returns:
                 None

        """
        if self.app.flat_cap_checkbox.get() == 1:  # If enabled the ends of the line segments are flat.
            Tools.endcap = "butt"
        else:
            Tools.endcap = "round"

    def highlight_checkbox_handler(self):
        """
           Gets the state of the highlight checkbox and sets the stipple variable accordingly.

           Returns:
                    None

           """

        # For better Ux sets the fill color to a highlight color when highight box is enabled.
        if self.app.highlight_checkbox.get() == 1:
            Tools.stipple = "gray25"
            # Set fill color to yellow.
            self.app.pick_color(color="#FFFF00")
            if Tools.current_tool == 4 and self.app.flat_cap_checkbox.get() == 0:  # If line set endcap to flat
                self.app.flat_cap_checkbox.toggle()

            elif Tools.current_tool == 5:
                Tools.shape_fill = True
                self.app.fill_color_checkbox.select()
                self.app.fill_color_checkbox.configure(state="disabled", fg_color=self.disabled_checkbox_col)

        else:
            Tools.stipple = ""
            if Tools.current_tool == 5 or Tools.current_tool == 6:
                self.app.fill_color_checkbox.configure(state="normal", fg_color=self.enabled_checkbox_col)

    def disable_all_modifiers(self):
        """
        Sets the state of all modifier checkbox to 'disabled'.

        Returns:
            None

        """
        self.app.uniform_checkbox.configure(state="disabled", fg_color=self.disabled_checkbox_col)
        self.app.fill_color_checkbox.configure(state="disabled", fg_color=self.disabled_checkbox_col)
        self.app.flat_cap_checkbox.configure(state="disabled", fg_color=self.disabled_checkbox_col)
        self.app.highlight_checkbox.configure(state="disabled", fg_color=self.disabled_checkbox_col)

    # ----------------------------------------------
    def reset_tool_variables(self):
        """
        Resets all tool variables like width, fill, constraint to the default state.
        Returns:

        """
        Tools.current_tool = 1
        Tools.previous_tool = 0
        Tools.stroke_width = 10
        Tools.fill_color = "#FF0000"
        Tools.decimate_factor = 1.5
        Tools.shape_fill = False
        Tools.stipple = ""
        Tools.shape_constraint = False
        Tools.endcap = "round"
