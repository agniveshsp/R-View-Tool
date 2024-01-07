from tools import Tools, TextInsertWindow
import sys


class KeyBinds:
    """
    Keybinds Class that handles the user inputs while the widgets of the main app window is focused.

    """

    def __init__(self, app):
        """
        Calls all method during creation.

        Args:
            app: Tkinter main app.
        """

        self.app = app

        # activating the keybinds.
        self.rgb_picker_canvas_binds()
        self.rgb_color_input_binds()
        self.main_app_binds()
        self.image_control_slider_binds()

    def main_app_binds(self):
        """
        Keybind inputs handler while the main app window is in focus.

        Returns:
            None

        """
        self.app.bind("<Escape>", self.app_escape_pressed)
        self.app.bind("<KeyRelease>", self.app_key_released)

        # To avoid bugs,
        # self.app.bind("<ButtonRelease-2>",self.app.reset_scale_slider)
        # self.app.bind("<ButtonRelease-3>", self.app.reset_scale_slider)

    def image_control_slider_binds(self):
        """
        Handles the Click Release event after updating the scale slider.
        Returns:
            None

        """
        self.app.scale_slider.bind("<ButtonRelease-1>", self.app.reset_scale_slider)

    # ---------------------------------------------------------------

    def rgb_picker_canvas_binds(self):
        """
        Handles the mouse events of the mouse on the rgb_picker_canvas.

        Returns:
            None

        """
        self.app.rgb_picker_canvas.bind("<ButtonPress-1>", self.app.pick_color, "+")
        self.app.rgb_picker_canvas.bind("<B1-Motion>", self.app.pick_color, "+")

    def rgb_color_input_binds(self):
        """
        Handles the keypress  on the entry boxes of the RGB inputs.

        Returns:
            None

        """

        self.app.red_slider_value_entry.bind("<KeyRelease>", self.app.red_entry_event)
        self.app.red_slider_value_entry.bind("<FocusOut>", self.app.red_slider_event)

        self.app.green_slider_value_entry.bind("<KeyRelease>", self.app.green_entry_event)
        self.app.green_slider_value_entry.bind("<FocusOut>", self.app.green_slider_event)

        self.app.blue_slider_value_entry.bind("<KeyRelease>", self.app.blue_entry_event)
        self.app.blue_slider_value_entry.bind("<FocusOut>", self.app.blue_slider_event)

    def app_escape_pressed(self, event):
        """
        Handles the event of 'Escape' key being pressed while the main app is in focus.

        Args:
            event (tkinter.Event): Keypress event.

        Returns:
            None

        """
        # Hides the text_insert_text_window.
        self.app.canvas_text_insert.hide_text_insert_window()

    def app_key_released(self, event):
        """
        Handles all key release events while the main app is in focus.

        Args:
            event (tkinter.Event): Key Release event.

        Returns:
            None

        """
        # If shift key is pressed and mouse hovered over the outliner, display the full filename.
        if event.keysym == "Shift_R" or event.keysym == "Shift_L":
            self.app.current_hovered_btn_index = -1
            self.app.on_mouse_leave(override=True)


class CanvasKeybinds:
    """
    Handles all user inputs while the Canvas widget is in focus.
    """

    def __init__(self, app, graphics_manager, canvas):
        """
        Initializer

        Args:
            app: Tkinter main app
            graphics_manager :GraphicsManager or OverlayGraphicsManager object
            canvas: Tkinter Canvas item.
        """

        self.app = app
        self.gm = graphics_manager
        self.active_canvas = canvas

        self.canvas_keybinds()

    def canvas_keybinds(self):
        """
        Activating the keybinds that are used while Canvas is in focus.
        Returns:
            None

        """
        self.app.image_frame.bind("<ButtonPress-1>", lambda event: self.active_canvas.focus_set(), "+")
        self.app.image_canvas.bind("<ButtonPress-1>", lambda event: self.active_canvas.focus_set(), "+")

        self.active_canvas.bind('<Shift-Return>', self.text_insert_window_hotkey)
        self.active_canvas.bind('Return>', self.text_insert_window_hotkey)

        self.active_canvas.bind("<KeyPress>", self.key_press_handler, "+")

        self.active_canvas.bind("<ButtonPress-1>", self.mouse_button1_pressed_handler, "+")
        self.active_canvas.bind("<B1-Motion>", self.mouse_button1_motion_handler, "+")
        self.active_canvas.bind("<B1-Motion>", self.gm.draw_graphics, "+")
        self.active_canvas.bind("<ButtonRelease-1>", self.mouse_button1_release_handler, "+")

        self.active_canvas.bind("<ButtonPress-3>", self.gm.erase_graphic, "+")
        self.active_canvas.bind("<B3-Motion>", self.gm.erase_graphic, "+")

        self.active_canvas.bind("<Right>", self.app.show_next_img, "+")
        self.active_canvas.bind("<Left>", self.app.show_previous_img, "+")
        self.active_canvas.bind("<Control-Right>", self.app.show_last_img, "+")
        self.active_canvas.bind("<Control-Left>", self.app.show_first_img, "+")

        # --Image zoom-------------------------------
        self.active_canvas.bind("<MouseWheel>", self.mouse_scroll_handler, "+")

        # For linux, Button-4 Scrollup. Button-5 Scrolldown
        if sys.platform.startswith('linux'):
            self.active_canvas.bind("<Button-4>", self.mouse_scroll_handler, "+")
            self.active_canvas.bind("<Button-5>", self.mouse_scroll_handler, "+")

        self.active_canvas.bind("<KeyPress-plus>", self.mouse_scroll_handler, "+")
        self.active_canvas.bind("=", self.mouse_scroll_handler, "+")  # pressing shift and + is confusing.
        self.active_canvas.bind("<KeyPress-minus>", self.mouse_scroll_handler, "+")

        # --Canvas Drag----------------------------
        self.active_canvas.bind("<KeyPress-space>", self.on_space_pressed, "+")
        self.active_canvas.bind("<KeyRelease-space>", self.on_space_released, "+")

        self.active_canvas.bind("<ButtonPress-2>", self.mouse_button2_pressed_handler, "+")
        self.active_canvas.bind("<B2-Motion>", self.mouse_button2_motion_handler, "+")
        self.active_canvas.bind("<ButtonRelease-2>", self.mouse_button2_release_handler, "+")

        # Removing the text item or image item from the canvas.
        self.active_canvas.bind('<Delete>', self.gm.delete_item)
        self.active_canvas.bind('<BackSpace>', self.gm.delete_item)

    def text_insert_window_hotkey(self, event=None):
        """
        Handles the display of the text_insert_window and the text insertions.

        Args:
            event (tkinter.Event,Optional): Mouse Click event.

        Returns:
            None

        """

        if self.app.display_mode == "default":
            self.app.tools.text_tool()
            if not TextInsertWindow.stored_text_position:
                center_x = self.app.resized_ld_img.width / 2
                center_y = self.app.resized_ld_img.height / 2
                # if text tool wasn't used manually,Initial text via hotkeys is added to center of the image.
                event.x = center_x
                event.y = center_y
                TextInsertWindow.stored_text_position = event

            self.gm.initial_canvas_click(TextInsertWindow.stored_text_position)

    def key_press_handler(self, event):
        """
        Handles all key press event while the canvas is in focus.

        Args:
           event (tkinter.Event): Keypress event.

        Returns:
            None

        """
        # Hotkey that activates the assigned tool.
        num = event.keysym
        if num == "0":
            self.app.tools.color_picker_tool()

        elif num == "1":
            self.app.tools.cursor_tool()

        elif num == "2":
            self.app.tools.brush_tool()

        elif num == "3":
            self.app.tools.eraser_tool()

        elif num == "4":
            self.app.tools.line_tool()

        elif num == "5":
            self.app.tools.rectangle_tool()

        elif num == "6":
            self.app.tools.oval_tool()

        elif num == "7":
            self.app.tools.pan_tool()

        elif num == "8" and self.app.display_mode == "default":
            self.app.tools.text_tool()

        elif num == "9" and self.app.display_mode == "default":
            self.app.tools.text_color_tool()

    def mouse_button1_pressed_handler(self, event):
        """
        Handles Mouse Left button press events.

        Args:
            event (tkinter.Event): Mouse Click event.

        Returns:
            None

        """
        # Pan tool acts as a text reposition tool when the display mode is 'default'.
        if Tools.current_tool == 0:
            self.app.pick_color(event, canvas=self.active_canvas)

        elif self.app.display_mode == "default":
            if Tools.current_tool == 1:
                self.gm.select_canvas_item(event)

            elif Tools.current_tool == 7:
                pass

            elif Tools.current_tool == 9:
                # Returns true if the click was on a text and has been colored.
                text_colored = self.gm.update_text_color(event)
                if text_colored:
                    self.app.modify_previous_color_list(event)

            else:  # Not default
                self.gm.initial_canvas_click(event)
                self.app.modify_previous_color_list(event)

        else:
            if Tools.current_tool == 7:
                self.app.set_drag(event)

            else:
                self.gm.initial_canvas_click(event)
                self.app.modify_previous_color_list(event)

    def mouse_button1_motion_handler(self, event):
        """
        Handles the Mouse Drag even while left button pressed.

         Args:
            event (tkinter.Event): Mouse Click event.

        Returns:
            None

        """

        if self.app.display_mode != "default":
            if event.state & 0x1:
                constraint = True

        if Tools.current_tool == 0:
            self.app.pick_color(event, canvas=self.active_canvas)

        # While shift key pressed down, constraint the transformations to a single axis.
        elif Tools.current_tool == 1:
            if event.state & 0x1:
                constraint = True
            else:
                constraint = False
            if self.gm.selected_text_item:
                self.gm.reposition_text_item(event, constraint=constraint)

        elif Tools.current_tool == 7 and not self.app.display_mode == "default":
            self.app.drag_canvas(event)

    def mouse_button1_release_handler(self, event):
        """
        Handles the Left Mouse button Release events.

        Args:
            event (tkinter.Event): Mouse click release event.

        Returns:
            None

        """
        self.app.reset_scale_slider(event)
        if Tools.current_tool == 1:
            self.gm.reveal_text_item_selection_border()

        elif Tools.current_tool not in (1, 7):
            self.gm.draw_release(event)
        else:
            pass
        self.gm.flush_mouse_events()

    def mouse_button2_pressed_handler(self, event):
        """
        Handles the Middle Mouse button click event.

        Args:
            event (tkinter.Event): Mouse click event.

        Returns:
            None

        """
        if self.app.display_mode != "default":
            self.app.set_drag(event)

    def mouse_button2_motion_handler(self, event):
        """
        Handles the Middle Mouse button drag event.

        Args:
            event (tkinter.Event): Mouse drag event.

        Returns:
            None

        """
        if self.app.display_mode != "default":
            self.app.drag_canvas(event)

    def mouse_button2_release_handler(self, event):
        """
        Handles the Middle Mouse button release event.

        Args:
            event (tkinter.Event): Mouse click release event.

        Returns:
            None

        """
        self.gm.flush_mouse_events()

    def mouse_scroll_handler(self, event):
        """
        Handles the Mouse wheel scroll events.

        Args:
            event (tkinter.Event): Mouse wheel scroll event.

        Returns:
            None

        """
        if sys.platform.startswith('linux'):
            # num=4 is scroll up and .num=5 is scrolldown.
            if event.num == 4:
                event.delta = 120
            elif event.num == 5:
                event.delta = -120

        # Checking if Ctrl or Cmd key(rich people) is pressed
        if event.state & (1 << 2) or event.state & (1 << 6):
            self.app.zoom_image(event)
        elif event.keysym == "plus" or event.keysym == "equal":
            event.delta = 120
            self.app.zoom_image(event)
        elif event.keysym == "minus":
            event.delta = -120
            self.app.zoom_image(event)
        else:  # If no key pressed change the stroke width.
            self.app.change_stroke_width(event)

    def on_space_pressed(self, event):
        """
        Checks if the Spacebar key is pressed.

        Args:
            event (tkinter.Event): Key pressed event.

        Returns:
            None

        """
        # Switch to pan tool if Spacebar held down.
        if not Tools.current_tool == 7:
            self.app.tools.pan_tool()

    def on_space_released(self, event):
        # Press the button of the previous tool.(ik its dirty)
        self.app.tools.tool_buttons[Tools.previous_tool].invoke()


class OverlayKeyBinds(CanvasKeybinds):
    """
    Handles the user inputs while the OverlayCanvas is in focus.
    """

    def __init__(self, app, graphics_manager, canvas):
        """
        Initializer

        Args:
            app: Tkinter main app
            graphics_manager :GraphicsManager or OverlayGraphicsManager object
            canvas: Tkinter Canvas item.
        """

        super().__init__(app, graphics_manager, canvas)

    def text_insert_window_hotkey(self, event=None):
        """
        Handles the display of the text_insert_window and the text insertions.

        Args:
            event (tkinter.Event,Optional): Mouse Click event.

        Returns:
            None

        """

        self.app.tools.text_tool()
        if TextInsertWindow.stored_text_position:
            self.gm.initial_canvas_click(TextInsertWindow.stored_text_position)

        else:
            self.app.error_prompt.display_error_prompt(error_msg="Quick Insert requires a set text position.",
                                                       priority=2)

    def mouse_scroll_handler(self, event):
        """
        Handles the Mouse wheel scroll events.

        Args:
            event (tkinter.Event): Mouse wheel scroll event.

        Returns:
               None

        """
        self.app.change_stroke_width(event)

    def mouse_button1_motion_handler(self, event):
        """
         Handles the Mouse Drag even while left button pressed.

        Args:
            event (tkinter.Event): Mouse Click event.

        Returns:
            None

        """

        if Tools.current_tool == 1:  # If shift key pressed constraint the transform to a single axis.
            if event.state & 0x1:
                constraint = True
            else:
                constraint = False

            if self.gm.selected_overlay_image:
                self.gm.reposition_overlay_image(event, constraint=constraint)
            else:
                super().mouse_button1_motion_handler(event)

    def mouse_button1_release_handler(self, event):
        """
        Handles the Left Mouse button Release events.

        Args:
           event (tkinter.Event): Mouse click release event.

        Returns:
           None

        """

        self.gm.reveal_overlay_image_selection_border()
        super().mouse_button1_release_handler(event)  # Calls the parent method.
