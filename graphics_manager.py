from dataclasses import dataclass, field
from functools import wraps
from PIL import Image, ImageTk

from tools import Tools
from tools import TextInsertWindow


class GraphicsManager:
    """
    GraphicsManager Class manages the drawing and display of annotations(graphics) that gets drawn onto the images.
    """

    def __init__(self, app, canvas, is_overlay=False):
        """
        Initialising the Class with a given canvas.

        Args:
            app: Tkinter main app
            canvas: Tkinter Canvas
            is_overlay (bool): True if the canvas is the overlay canvas. Default False.
        """
        super().__init__()
        self.app = app
        self.active_canvas = canvas  # image_canvas for base and overlay_canvas for the overlay elements.

        self.coords_list = []
        self.initial = 0
        self.last_x = 0
        self.last_y = 0

        self.x_axis_constraint = None
        self.stored_axis_value = None
        self.selection_click_position = None

        self.is_text_repositioning: bool = False
        self.is_text_scaling: bool = False

        self.selected_text_item = -1
        # Offset so that the text objects anchor point does not snap to the mouse cursor.
        self.text_offset_x = 0
        self.text_offset_y = 0

        self.ready_to_draw = False

        self.interior_fill_color = ""
        self.outline_fill_color = ""

        self.scribble = None
        self.scribble_list = []
        self.temp_stroke = []
        self.scale_to_reset = ""
        self.zoom_to_reset = ""
        self.annotation_visibility = True

        self.insert_text_window = None
        self.is_overlay = is_overlay
        self.index = None
        self.OVERLAY_GRAPHICS_INDEX = -1  # dictionary index of the overlay canvas.
        self.OVERLAY_IMAGES_INDEX = -2  # dictionary index where the images.

        self.create_text_selection_border()

    def draw_graphic_elements_from_project_file(self, is_overlay=False):
        """
        Unpacks the loaded_graphics_data_dict and based on the tool used, mimics the events that happens during the normal drawing.

        Args:
            is_overlay: If True, the graphic elements from OVERLAY_GRAPHICS_INDEX([-1])gets drawn on the overlay_canvas. Default False.

        Returns:
            None

        """
        # Basically feeding in all values to the action that happens when the mouse click is released.
        total_images_to_redraw = len(self.app.graphics_data) - 2  # excluding the overlay indexes
        graphics_redrawn = 0  # the 0.5 progress from the file indexing.

        for image_index, graphic_dict in self.app.loaded_graphics_data.items():

            # excluding overlay items. unless specified (overlay elements).
            if (image_index >= 0 and graphic_dict) or (image_index == -1 and is_overlay):
                for item_id, graphic_object in graphic_dict.items():
                    self.ready_to_draw = True
                    Tools.stroke_width = self.convert_width_to_max_size(graphic_object.width)
                    self.scribble_width = Tools.stroke_width

                    Tools.current_tool = graphic_object.tool
                    Tools.stipple = graphic_object.stipple
                    Tools.endcap = graphic_object.capstyle
                    Tools.fill_color = graphic_object.fill_color
                    Tools.shape_fill = graphic_object.shape_fill

                    TextInsertWindow.selected_font = graphic_object.font_name
                    TextInsertWindow.selected_font_file = graphic_object.font_file
                    TextInsertWindow.selected_font_size = self.convert_width_to_max_size(
                        stroke_width=graphic_object.font_size, item="font")

                    if Tools.shape_fill:
                        self.interior_fill_color = Tools.fill_color
                        self.outline_fill_color = ""
                        self.offset = 0
                    else:  # only outline
                        self.interior_fill_color = ""
                        self.outline_fill_color = Tools.fill_color
                        self.offset = self.scribble_width / 2

                    if Tools.current_tool == 8:  # if it's a text item.
                        # Text is saved as tuple in the graphic_object, but as a list when entered.
                        # so using [] on the graphic_object.coordinates to make it a list.
                        self.coords_list = self.image_coordinates_to_max_size([graphic_object.coordinates])
                        self.draw_release(project_override=True, text=graphic_object.text,
                                          image_sized_coordinates=graphic_object.coordinates)
                    else:
                        self.coords_list = self.image_coordinates_to_max_size(graphic_object.coordinates)
                        self.draw_release(project_override=True, image_sized_coordinates=graphic_object.coordinates)

                # Break if the redraw happens in overlay canvas, break after iterating -1 index in the dict.
                if is_overlay:
                    return

            if image_index >= 0:
                graphics_redrawn += 1
                # Progress bar fill value.
                # 0.5+0.3= 0.8 , remaining .2 is reserved for the progress of overlay items.
                progress = graphics_redrawn / total_images_to_redraw * 0.3

                # the 0.5 progress from the file indexing.
                self.app.file_load_window.update_file_window_progressbar(progress=0.5 + progress)
                self.app.show_next_img()  # Scrolling through the images to get values based on the loaded image.

        self.force_hide_all_canvas_annotations()
        # seek to the first image.
        self.app.show_first_img(force_first=True)
        if self.app.maximized_mode:
            self.reveal_parent_annotations()
        else:
            self.reveal_proxy_annotations()

    def peucker_algorithm(self, points, tolerance):
        """
        An algorithm that decimates a curve composed of line segments to a similar curve with fewer points.

        Args:
            points (tuple|list): Points to decimate.
            tolerance (float): A float number to control the decimation.

        Returns:
            list: A list of simplified coordinates.

        """

        def perpendicular_distance(point, line_start, line_end):
            x, y = point
            x1, y1 = line_start
            x2, y2 = line_end

            numerator = abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1)
            denominator = ((y2 - y1) ** 2 + (x2 - x1) ** 2) ** 0.5
            try:
                return numerator / denominator
            except ZeroDivisionError:
                return 1

        if len(points) <= 2:
            return points

        # Find the point with the maximum distance
        max_distance = 0
        max_index = 0

        for i in range(1, len(points) - 1):
            distance = perpendicular_distance(points[i], points[0], points[-1])
            if distance > max_distance:
                max_distance = distance
                max_index = i

        # If the maximum distance is greater than the tolerance, recursively simplify
        if max_distance > tolerance:
            left_part = self.peucker_algorithm(points[:max_index + 1], tolerance)
            right_part = self.peucker_algorithm(points[max_index:], tolerance)

            return left_part[:-1] + right_part
        else:
            return [points[0], points[-1]]

    def create_text_selection_border(self):
        """
        Creates four line segments on the canvas to act as a selection border.

        Returns:
            None

        """
        SCALE_BOX_SIZE = 10
        self.text_selection_border = self.active_canvas.create_line(0, 0, 0, 0, 0, 0, 0, 0, fill="#ff66ff", width=2,
                                                                    tags="gui")

        # hides the border.
        self.active_canvas.itemconfig(self.text_selection_border, state="hidden")

    def select_canvas_item(self, event, item_id=None):
        """
        Fetches the clicked item on the canvas. If the item is a text, draw the surrounding border.

        Args:
            event(tkinter.Event): Mouse Click event
            item_id(int):id of the canvas item.

        Returns:
            None

        """

        # Removes any existing selections.
        self.remove_text_item_selection()

        if not item_id:  # if no item_id is provided, fetch the item id closest to the mouse click.
            item_id = event.widget.find_closest(event.x, event.y)[0]

        item_tags = self.active_canvas.gettags(item_id)

        if "text" in item_tags:  # all text items have the "text" tag.
            self.select_text_item(text_id=item_id)  # Selects the text item.
            self.set_text_drag_offset(event)  # So that the text items anchor does not snap to the mouse position.

    def select_text_item(self, text_id=None, enable_scale_slider=True):
        """
        Assigns the text item  as the selected_text_item and draws the selection border around it.

        Args:
            text_id (int): id of the text item on the canvas.
            enable_scale_slider: True enables the scale slider that controls the scale of the text. Default True.

        Returns:
            None

        """
        text_bounds = self.active_canvas.bbox(text_id)
        x1, y1, x2, y2 = text_bounds
        border_coordinates = x1, y1, x2, y1, x2, y2, x1, y2, x1, y1
        self.active_canvas.coords(self.text_selection_border, border_coordinates)
        self.active_canvas.tag_raise("gui")  # Pushing the border to the top.
        self.active_canvas.itemconfig(self.text_selection_border, state="normal", fill=self.app.selection_color)
        self.selected_text_item = text_id

        if enable_scale_slider:
            self.app.toggle_image_tools_sliders(only_scale=True, toggle=1)

    def remove_text_item_selection(self):
        """
        Removes the current text item as the selected_text_item.
        Returns:
            None

        """
        self.selected_text_item = None
        self.active_canvas.itemconfig(self.text_selection_border, state="hidden")
        self.app.toggle_image_tools_sliders(toggle=0)

    def hide_text_item_selection_border(self):
        """
        Hides the selection border around the selected text item.

        Returns:
            None

        """
        self.active_canvas.itemconfig(self.text_selection_border, state="hidden")

    def reveal_text_item_selection_border(self):
        """
        Shows the selection border around the selected text item.

        Returns:
            None

        """
        if self.selected_text_item:
            self.select_text_item(text_id=self.selected_text_item)

            self.is_image_scaling = False
            self.is_text_repositioning = False
            self.is_image_repositioning = False
            self.x_axis_constraint = None

    def annotation_visibility_checker(func):
        """
        Checks if annotations are allowed to be displayed on the screen.

        """

        # Saves time skipping annotation calculations if annotation display is turned off.
        # If annotation visibility is disabled, skip the method.
        @wraps(func)
        def wrapper_function(self, *args, **kwargs):
            if self.annotation_visibility:
                main_result = func(self, *args, **kwargs)
                return main_result
            else:
                return None

        return wrapper_function

    def check_if_overlay(func):
        """
        Checks if current operations are being done on the overlay canvas.

        """

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.is_overlay:
                self.index = self.app.image_index
            else:  # If Overlay set index to the Overlay graphics index.
                self.index = self.OVERLAY_GRAPHICS_INDEX
            result = func(self, *args, **kwargs)
            # Pushing the images to the top. Since images will be added last due to antialiasing process.
            self.active_canvas.tag_raise("overlay_img")
            self.active_canvas.tag_raise("gui")
            return result

        return wrapper

    # ====================================================

    def initial_canvas_click(self, event):
        """
        Called on the initial mouse click on the canvas. Stores the mouse coordinates and sets the stroke width based on the display mode.

        Args:
            event (tkinter.Event):Mouse click event.

        Returns:
            None

        """
        self.active_canvas.focus_set()  # Focus set on the active canvas.

        self.flush_mouse_events()  # Clears all previously stored mouse click events.

        if Tools.current_tool == 1:  # If the current tool used to click on the canvas is the cursor tool,
            # set ready_to_draw to false and exit
            self.ready_to_draw = False
            return

        self.ready_to_draw = True

        self.initial_click = self.active_canvas.canvasx(event.x), self.active_canvas.canvasy(event.y)
        self.last_x, self.last_y = self.initial_click
        self.coords_list.append(self.initial_click)

        # Resize the drawing tool to match proxy proportions.
        if self.app.maximized_mode:  # if maximized mode use the width as is.
            self.scribble_width = Tools.stroke_width
        else:
            self.scribble_width = self.get_proxy_stroke_width()  # if windowed mode get the proxy width.

        if self.app.display_mode == "default":  # if text insert.
            if Tools.current_tool == 8:  # Text insert.

                # Stores text postion stores the mouse event for the quick text insert using hotkeys.
                TextInsertWindow.stored_text_position = event
                # -ve means the tkinter will use pixels instead of the font size.(for Pillow)
                if self.app.maximized_mode:
                    TextInsertWindow.selected_font_size = TextInsertWindow.new_font_pixel_size
                else:
                    TextInsertWindow.selected_font_size = TextInsertWindow.new_font_pixel_size

                self.app.canvas_text_insert.reveal_text_insert_window()
                return

        # If the Image is actual sized or zoomed, get the stroke width relative to the zoom. #If the Image is actual sized or zoomed, get the stroke width relative to the zoom.
        elif self.app.display_mode == "actual":
            self.scribble_width = self.get_dynamic_stroke_width(mode="actual")
        elif self.app.display_mode == "zoomed":
            self.scribble_width = self.get_dynamic_stroke_width(mode="zoomed")

        if Tools.shape_fill:  # If the shape_fill check box is enabled. set the fill color as the interior_fill_color.for rectangle and oval.
            self.interior_fill_color = Tools.fill_color
            self.outline_fill_color = ""
            self.offset = 0

        else:  # only outline
            self.interior_fill_color = ""
            self.outline_fill_color = Tools.fill_color
            self.offset = self.scribble_width / 2

    def draw_graphics(self, event):
        """
        Called on Mouse drag event. Plots a temporary shape using the raw mouse coordinates. Erases the item instantly.

        Args:
            event (tkinter.Event):Mouse Drag event.

        Returns:
            None

        """

        if self.ready_to_draw:

            if Tools.current_tool == 2:  # brush , since the coords are raw a simple drawing can have hundreds of coordinates.
                self.scribble = self.active_canvas.create_line(
                    (self.last_x, self.last_y, self.active_canvas.canvasx(event.x),
                     self.active_canvas.canvasy(event.y)), fill=Tools.fill_color,
                    width=self.scribble_width, joinstyle="round", capstyle="round",
                    stipple=Tools.stipple, tags="scribble")
                self.coords_list.append((self.active_canvas.canvasx(event.x), self.active_canvas.canvasy(event.y)))

            elif Tools.current_tool == 3:  # Eraser
                self.erase_graphic(event, radius=Tools.stroke_width)

            elif Tools.current_tool == 4:  # line
                if not self.scribble:
                    self.scribble = self.active_canvas.create_line(self.initial_click[0], self.initial_click[1],
                                                                   self.active_canvas.canvasx(event.x),
                                                                   self.active_canvas.canvasy(event.y),
                                                                   fill=Tools.fill_color, width=self.scribble_width,
                                                                   joinstyle="round", capstyle=Tools.endcap,
                                                                   stipple=Tools.stipple, tags="scribble")
                else:
                    self.active_canvas.coords(self.scribble, self.initial_click[0], self.initial_click[1],
                                              self.active_canvas.canvasx(event.x), self.active_canvas.canvasy(event.y))

                self.coords_list = [(self.initial_click[0], self.initial_click[1]),
                                    (self.active_canvas.canvasx(event.x), self.active_canvas.canvasy(event.y))]

            elif Tools.current_tool == 5:  # rectangle
                final_point_x, final_point_y = self.active_canvas.canvasx(event.x), self.active_canvas.canvasy(event.y)

                # Formula for square.
                if Tools.shape_constraint:
                    side_length = max((final_point_x - self.initial_click[0]), (final_point_y - self.initial_click[1]))
                    final_point_x, final_point_y = self.initial_click[0], self.initial_click[1]
                else:
                    side_length = 0

                if not self.scribble:
                    self.scribble = self.active_canvas.create_rectangle(self.initial_click[0] + self.offset,
                                                                        self.initial_click[1] + self.offset,
                                                                        final_point_x + side_length - self.offset,
                                                                        final_point_y + side_length - self.offset,
                                                                        fill=self.interior_fill_color,
                                                                        outline=self.outline_fill_color,
                                                                        stipple=Tools.stipple,
                                                                        width=self.scribble_width, tags="scribble")
                else:  # modify the rectangle with mouse position.
                    self.active_canvas.coords(self.scribble, self.initial_click[0] + self.offset,
                                              self.initial_click[1] + self.offset,
                                              final_point_x + side_length - self.offset,
                                              final_point_y + side_length - self.offset)

                self.coords_list = [(self.initial_click[0] + self.offset,
                                     self.initial_click[1] + self.offset),
                                    (final_point_x + side_length - self.offset,
                                     final_point_y + side_length - self.offset)]

            elif Tools.current_tool == 6:  # oval
                # self.active_canvas.delete(self.scribble)

                final_point_x, final_point_y = self.active_canvas.canvasx(event.x), self.active_canvas.canvasy(
                    event.y)
                # Formula for circle.
                if Tools.shape_constraint:
                    side_length = max((final_point_x - self.initial_click[0]), (final_point_y - self.initial_click[1]))
                    final_point_x, final_point_y = self.initial_click[0], self.initial_click[1]
                else:
                    side_length = 0

                if not self.scribble:
                    self.scribble = self.active_canvas.create_oval(self.initial_click[0] - side_length,
                                                                   self.initial_click[1] - side_length,
                                                                   final_point_x + side_length,
                                                                   final_point_y + side_length,
                                                                   fill=self.interior_fill_color,
                                                                   outline=self.outline_fill_color,
                                                                   width=self.scribble_width, tags="scribble")
                else:
                    self.active_canvas.coords(self.scribble, self.initial_click[0] - side_length,
                                              self.initial_click[1] - side_length,
                                              final_point_x + side_length,
                                              final_point_y + side_length)

                self.coords_list = [(self.initial_click[0] - side_length, self.initial_click[1] - side_length),
                                    (final_point_x + side_length, final_point_y + side_length)]

            self.scribble_list.append(self.scribble)  # Appends the raw mouse coordinates to the scribble_list.
            self.last_x, self.last_y = self.active_canvas.canvasx(event.x), self.active_canvas.canvasy(event.y)

    @check_if_overlay
    def draw_release(self, event=0, text=None, project_override=False, image_sized_coordinates=None):
        """
        Called on Mouse release. Fetches the raw coordinates, cleans it scales it to the maximized and windowed size and plots the shape.
            The coordinates and width are also scaled to match the actual image before saving the graphics_cache object to the dictionary.

        Args:
            event(tkinter.Event):Mouse click release event.
            text(str,optional): Text, if using the text insert tool.
            project_override (bool): True if the method is being called from a loaded project protocol. Default False.
            image_sized_coordinates (list|tuple,optional):Pre-generated coordinates relative to the actual image size.

        Returns:
            None

        """

        # p49= proxy tag with 49 as the id of its master, linking them to delete both at same time.
        # m1=maximized master tag with image index 1
        # w1=windowed proxy tag with image index 1
        # Graphics items gets drawn in max window size,even if drawn in windowed mode.
        if self.ready_to_draw or Tools.current_tool == 8:  # text tool
            current_tool = Tools.current_tool
            if len(self.coords_list) > 1 or (Tools.current_tool == 8 and text) or project_override:
                item = None
                self.active_canvas.delete("scribble")
                self.scribble = None

                if self.app.maximized_mode or project_override:
                    released_coordinates = self.coords_list
                else:
                    released_coordinates = self.scale_coordinates(scale_mode="+")  # upscale the cords to be maxed

                if self.app.display_mode == "default":
                    pass
                elif self.app.display_mode == "actual":
                    released_coordinates = self.get_dynamic_coordinates(coordinate_list=released_coordinates,
                                                                        mode="actual")

                elif self.app.display_mode == "zoomed":
                    released_coordinates = self.get_dynamic_coordinates(coordinate_list=released_coordinates,
                                                                        mode="zoomed")

                tags = (f"m{self.index}", "master", "2d")

                if current_tool == 2:  # brush
                    if Tools.decimate_factor != 0:
                        released_coordinates = self.peucker_algorithm(released_coordinates, Tools.decimate_factor)

                    current_stroke = self.active_canvas.create_line(released_coordinates, fill=Tools.fill_color,
                                                                    width=Tools.stroke_width,
                                                                    joinstyle="round", capstyle="round",
                                                                    stipple=Tools.stipple, tags=tags)

                elif current_tool == 4:  # line
                    current_stroke = self.active_canvas.create_line(released_coordinates, fill=Tools.fill_color,
                                                                    width=Tools.stroke_width,
                                                                    joinstyle="round", capstyle=Tools.endcap,
                                                                    stipple=Tools.stipple, tags=tags)

                elif current_tool == 5:  # rectangle
                    current_stroke = self.active_canvas.create_rectangle(released_coordinates,
                                                                         fill=self.interior_fill_color,
                                                                         outline=self.outline_fill_color,
                                                                         width=Tools.stroke_width,
                                                                         stipple=Tools.stipple,
                                                                         tags=tags)

                elif current_tool == 6:  # oval
                    current_stroke = self.active_canvas.create_oval(released_coordinates,
                                                                    fill=self.interior_fill_color,
                                                                    outline=self.outline_fill_color,
                                                                    width=Tools.stroke_width,
                                                                    tags=tags)

                elif current_tool == 8:  # text
                    item = "text"
                    selection_color = self.get_selection_color(hex_color=Tools.fill_color)
                    if Tools.stipple:
                        selection_color = "#ecff16"
                    tags = (f"m{self.index}", "master", "text")

                    if isinstance(released_coordinates, list):  # text coordinates are saved as tuples.
                        # Failsafe for slow systems.
                        if released_coordinates:
                            released_coordinates = released_coordinates[0]
                        else:
                            self.app.error_prompt.display_error_prompt(error_msg="Text insertion failed,Try Again.",
                                                                       priority=2)
                            self.flush_mouse_events()
                            return

                    current_stroke = self.active_canvas.create_text(released_coordinates, text=text,
                                                                    fill=Tools.fill_color,
                                                                    activefill=selection_color,
                                                                    font=(TextInsertWindow.selected_font,
                                                                          TextInsertWindow.selected_font_size),
                                                                    tags=tags, anchor="sw")

                # Graphic object gets created here.
                # Save time reusing  image size coords from the project file, if not called from project calculate the coords.
                if not image_sized_coordinates:
                    image_sized_coordinates = self.coordinates_to_image_size(released_coordinates, item=item)

                self.app.graphics_data[self.index][current_stroke] = GraphicsCache(
                    coordinates=image_sized_coordinates,
                    width=self.width_to_image_size(stroke_width=Tools.stroke_width, item="width"),
                    fill_color=Tools.fill_color,
                    shape_fill=Tools.shape_fill,
                    joinstyle="round",
                    capstyle=Tools.endcap,
                    tags=tags,
                    interior_fill_color=self.interior_fill_color,
                    outline_fill_color=self.outline_fill_color,
                    tool=Tools.current_tool,
                    stipple=Tools.stipple,
                    text=text,
                    font_name=TextInsertWindow.selected_font,
                    font_file=TextInsertWindow.selected_font_file,
                    font_size=self.width_to_image_size(TextInsertWindow.selected_font_size, item="font"))

                if current_tool == 8:
                    # p is for parent, p12 means parent stroke id is 12
                    proxy_tags = (f"p{current_stroke}", f"w{self.index}", "text", "proxy")
                else:
                    proxy_tags = (f"p{current_stroke}", f"w{self.index}", "2d", "proxy")

                self.create_proxy_annotation(tags=proxy_tags, text=text, project_override=project_override)

                # hide large size strokes in windowed mode.
                if not self.app.maximized_mode:
                    self.active_canvas.itemconfig(current_stroke, state="hidden")
                else:
                    if self.app.display_mode == "actual":
                        self.scale_item_to_current_scale(item_id=current_stroke, mode="actual")
                    elif self.app.display_mode == "zoomed":
                        self.scale_item_to_current_scale(item_id=current_stroke, mode="zoomed")

        self.flush_mouse_events()

    @check_if_overlay
    def erase_graphic(self, event=None, radius=0, current_item=None):
        """
        Removes an item from the canvas and deletes the object from the dictionaries.

        Args:
            event (tkinter.Event): Mouse event.
            radius (int): Search radius.
            current_item(int,optional): Item id of the element in the canvas to remove.

        Returns:
            None

        """
        # If True delete any given element irrespective of type.Default False.

        if Tools.stroke_width == 50 and Tools.current_tool == 3:  # Maxed out. and eraser tool
            self.wipe_current_annotations()

        delete_mode = False
        OVERLAY_IMAGE_TAG = "overlay_img"
        if not current_item:
            current_item = self.find_item(event, radius)
        else:
            current_item = current_item
            delete_mode = True

        tag = self.active_canvas.gettags(current_item)
        tag_id = tag[0]
        # Deletes the 2d drawing along with all stored data. if delete_mode delete any element irrespective of tags.
        if "2d" in tag or delete_mode:
            if self.app.maximized_mode:
                self.active_canvas.delete(current_item)  # The selected  item.
                del self.app.graphics_data[self.index][current_item]
                proxy_id = self.active_canvas.find_withtag(f"p{current_item}")[0]
                del self.app.proxy_data[self.index][proxy_id]
                self.active_canvas.delete(f"p{current_item}")  # proxy of the parent item.

            else:  # delete the rescaled proxy strokes, and remove parent from graphic dict  as well as delete from screen.
                self.active_canvas.delete(current_item)  # removes the proxy
                self.active_canvas.delete(int(tag_id[1:]))  # eg p101
                del self.app.proxy_data[self.index][current_item]  # deletes proxy item from dict
                del self.app.graphics_data[self.index][int(tag_id[1:])]  # removes the p
        if delete_mode:
            self.remove_text_item_selection()

    def delete_item(self, event=None):
        """
        Calls the erase_graphic method with an item id passed.

        Args:
            event (tkinter.Event): Keypress event.

        Returns:
            None

        """

        if self.selected_text_item:
            self.erase_graphic(current_item=self.selected_text_item)

    def wipe_current_annotations(self):
        """
        Wipes all annotations (including text) drawn on the currently loaded image.
        Returns:

        """
        master_items_to_delete = list(self.app.graphics_data[self.index].keys())
        for item in master_items_to_delete:
            self.active_canvas.delete(item)
            del self.app.graphics_data[self.index][item]  # removes the p

        proxy_items_to_delete = list(self.app.proxy_data[self.index].keys())
        for item in proxy_items_to_delete:  # Clearing proxy annotations
            self.active_canvas.delete(item)
            del self.app.proxy_data[self.index][item]

        self.remove_text_item_selection()

    def flush_mouse_events(self):
        """
        Clears the stored mouse events and temporary coordinates, and sets the state of ready_to_draw to False.
        Returns:
            None

        """
        self.scribble_list = []
        self.coords_list = []
        self.initial_click = None
        self.is_text_repositioning = False
        self.ready_to_draw = False

    def create_proxy_annotation(self, tags, fill_color=None,
                                coordinates=None, width=None,
                                joinstyle="round", stipple=None,
                                capstyle=None, text=None, tool=None, project_override=False):

        """
        Creates a proxy version of the drawing to be displayed on the windowed mode.

        Args:
            tags:
            fill_color:
            coordinates:
            width:
            joinstyle:
            stipple:
            capstyle:
            text:
            tool:
            project_override (bool): True if method being called from load project protocol.

        Returns:
            None

        """

        if not coordinates:
            coordinates = self.coords_list
        if not width:
            width = Tools.stroke_width
        if not capstyle:
            capstyle = Tools.endcap
        if not tool:
            tool = Tools.current_tool
        if not fill_color:
            fill_color = Tools.fill_color
        if not stipple:
            stipple = Tools.stipple

        if self.app.maximized_mode or project_override:
            scaled_coords = self.scale_coordinates(scale_mode="-")
        else:
            scaled_coords = self.coords_list

        if self.app.display_mode == "actual":
            scaled_coords = self.get_dynamic_coordinates(coordinate_list=scaled_coords, mode="actual")
        elif self.app.display_mode == "zoomed":
            scaled_coords = self.get_dynamic_coordinates(coordinate_list=scaled_coords, mode="zoomed")

        if Tools.decimate_factor != 0:
            scaled_coords = self.peucker_algorithm(scaled_coords, Tools.decimate_factor)

        if tool == 2:  # Brush
            proxy_drawing = self.active_canvas.create_line(scaled_coords, fill=fill_color
                                                           , width=self.get_proxy_stroke_width(),
                                                           joinstyle="round", capstyle="round", stipple=stipple,
                                                           tags=tags)
        elif tool == 4:  # line
            proxy_drawing = self.active_canvas.create_line(scaled_coords, fill=fill_color
                                                           , width=self.get_proxy_stroke_width(),
                                                           joinstyle=joinstyle, capstyle=capstyle, stipple=stipple,
                                                           tags=tags)
        elif tool == 5:  # rectangle
            proxy_drawing = self.active_canvas.create_rectangle(scaled_coords, fill=self.interior_fill_color,
                                                                outline=self.outline_fill_color, stipple=stipple,
                                                                width=self.get_proxy_stroke_width(), tags=tags)
        elif tool == 6:  # oval
            proxy_drawing = self.active_canvas.create_oval(scaled_coords, fill=self.interior_fill_color,
                                                           outline=self.outline_fill_color,
                                                           width=self.get_proxy_stroke_width(), tags=tags)
        elif tool == 8:  # Insert text
            selection_color = self.get_selection_color(hex_color=Tools.fill_color)
            if Tools.stipple:
                selection_color = "#ecff16"

            proxy_drawing = self.active_canvas.create_text(scaled_coords[0], text=text, fill=Tools.fill_color,
                                                           activefill=selection_color,
                                                           font=(TextInsertWindow.selected_font,
                                                                 self.get_proxy_stroke_width(
                                                                     TextInsertWindow.selected_font_size,
                                                                     is_font_size=True)),
                                                           tags=tags, anchor="sw")

        self.app.proxy_data[self.index][proxy_drawing] = GraphicsCache(coordinates=scaled_coords,
                                                                       fill_color=Tools.fill_color,
                                                                       width=self.get_proxy_stroke_width(),
                                                                       joinstyle="round",
                                                                       capstyle=Tools.endcap,
                                                                       shape_fill=Tools.shape_fill,
                                                                       tags=tags,
                                                                       interior_fill_color=self.interior_fill_color,
                                                                       outline_fill_color=self.outline_fill_color,
                                                                       tool=Tools.current_tool,
                                                                       stipple=Tools.stipple,
                                                                       text=text,
                                                                       font_name=TextInsertWindow.selected_font,
                                                                       font_file=TextInsertWindow.selected_font_file,
                                                                       font_size=self.get_proxy_stroke_width(
                                                                           TextInsertWindow.selected_font_size,
                                                                           is_font_size=True))

        if self.app.maximized_mode:
            self.active_canvas.itemconfig(proxy_drawing, state="hidden")
        else:  # If the image is zoomed , match the width and coordinates to match the zoomed image.
            if self.app.display_mode == "actual":
                self.scale_item_to_current_scale(item_id=proxy_drawing, mode="actual")
            elif self.app.display_mode == "zoomed":
                self.scale_item_to_current_scale(item_id=proxy_drawing, mode="zoomed")

    def find_item(self, event, radius=0, filter=None):
        """
         Returns the canvas item closest to the Mouse Click event.

        Args:
            event (tkinter.Event): Mouse click event
            radius (int): Radius to search for. Default 0
            filter (str): Specific item to look for. eg- "text"

        Returns:
            int: Id of the canvas item.

        """
        selected_item = self.active_canvas.find_closest(self.active_canvas.canvasx(event.x),
                                                        self.active_canvas.canvasy(event.y),
                                                        halo=radius)[0]
        if not filter:
            # self.selected_text_item = None
            return selected_item

        elif filter == "text":
            tags = self.active_canvas.gettags(selected_item)
            if filter in tags:
                self.selected_text_item = selected_item
                return selected_item
            else:
                self.selected_text_item = None

    def set_text_drag_offset(self, event):
        """
        Sets the initial position of the text item before repositioning.

        Args:
            event(tkinter.Event): Mouse click event.

        Returns:
            None

        """
        if self.app.display_mode == "default":
            self.ready_to_draw = False
            # if text item is clicked get its bounding box.
            if self.find_item(event, filter="text"):
                self.selection_click_position = self.active_canvas.canvasx(event.x), self.active_canvas.canvasy(event.y)
                current_item_bbox = self.active_canvas.bbox(self.selected_text_item)
                # Since the anchor is "sw"  we use x1 and y2
                self.text_offset_x = self.selection_click_position[0] - current_item_bbox[0]  # x1
                self.text_offset_y = self.selection_click_position[1] - current_item_bbox[3]  # y2
            return

    def reposition_text_item(self, event, constraint=False):
        """
        Reposition the text item based on coordinates from the mouse drag event.

        Args:
            event (tkinter.Event): Mouse Drag event.
            constraint (bool): True constraints the text to an axis. False allows free repositioning.

        Returns:
            None

        """
        if self.selected_text_item:
            self.is_text_repositioning = True
            self.hide_text_item_selection_border()
            # Offset so that text anchor won't snap to mouse position.
            current_mousex = self.active_canvas.canvasx(event.x)
            current_mousey = self.active_canvas.canvasx(event.y)

            new_x = current_mousex - self.text_offset_x
            new_y = current_mousey - self.text_offset_y

            if constraint:
                dx = current_mousex - self.selection_click_position[0]
                dy = current_mousey - self.selection_click_position[1]

                if self.x_axis_constraint == None:  # None means no X or Y.
                    if abs(dx) > abs(dy):
                        self.x_axis_constraint = True
                    else:
                        self.x_axis_constraint = False

                if self.x_axis_constraint:
                    new_y = self.selection_click_position[1] - self.text_offset_y
                    self.active_canvas.coords(self.selected_text_item, (new_x, new_y))
                else:
                    new_x = self.selection_click_position[0] - self.text_offset_x
                    self.active_canvas.coords(self.selected_text_item, (new_x, new_y))
            else:
                self.active_canvas.coords(self.selected_text_item, (new_x, new_y))

            event.x = new_x
            event.y = new_y
            TextInsertWindow.stored_text_position = event
            self.update_text_item_coords()

    @check_if_overlay
    def update_text_item_coords(self, ):
        """
        Updates the text item coordinates in the data dictionaries after conversion.

        Args:

        Returns:
            None

        """

        if self.is_text_repositioning and self.app.display_mode == "default":
            # Raw coordinates of current window mode.
            moved_text_bbox = self.active_canvas.bbox(self.selected_text_item)
            new_coords = moved_text_bbox[0], moved_text_bbox[3]  # (x1,y2)
            if self.app.maximized_mode:
                proxy_id = self.active_canvas.find_withtag(f"p{self.selected_text_item}")[0]
                new_proxy_coords = self.scale_coordinates(coordinate_list=new_coords,
                                                          scale_mode="-", scale_item="text")

                self.active_canvas.coords(proxy_id, new_proxy_coords)
                # Converting the max coordinates to image scale.
                image_sized_coords = self.coordinates_to_image_size(coordinate_list=new_coords, item="text")
                self.app.graphics_data[self.index][self.selected_text_item].coordinates = image_sized_coords
                # Updates the proxy with scaled down coordinates from max view.
                self.app.proxy_data[self.index][proxy_id].coordinates = new_proxy_coords

            else:
                tag = self.active_canvas.gettags(self.selected_text_item)[0]
                new_max_coords = self.scale_coordinates(coordinate_list=new_coords,
                                                        scale_mode="+", scale_item="text")

                # Converting the max cords to proxy cords to get near pixel perfect accuracy.
                new_proxy_coords = self.scale_coordinates(coordinate_list=new_max_coords,
                                                          scale_mode="-", scale_item="text")

                self.active_canvas.coords(int(tag[1:]), new_max_coords)
                # update the proxy data as is.
                self.app.proxy_data[self.index][self.selected_text_item].coordinates = new_proxy_coords
                # Converting the max coordinates to image scale.
                image_sized_coords = self.coordinates_to_image_size(coordinate_list=new_max_coords, item="text")
                self.app.graphics_data[self.index][int(tag[1:])].coordinates = image_sized_coords

        # self.select_text_item(text_id=self.selected_text_item)

    @check_if_overlay
    def update_text_item_scale(self, value: float = None, increment: str = None):
        """
        Updates the scale of the selected text item using the provided value.

        Args:
            value (float, optional): A multiplier number.
            increment(str, optional):"+" adds +1 to the current scale, "-" subtracts -1 from the current scale., optional

        Returns:
            None

        """
        MIN_TEXT_SIZE = -10

        if self.selected_text_item:
            if self.app.maximized_mode:
                parent_id = self.selected_text_item
                proxy_id = self.active_canvas.find_withtag(f"p{self.selected_text_item}")[0]
            else:
                proxy_id = self.selected_text_item
                tag = self.active_canvas.gettags(self.selected_text_item)[0]
                parent_id = int(tag[1:])

            current_text_item_object = self.app.graphics_data[self.index][parent_id]
            current_font_family = current_text_item_object.font_name

            current_font_size = current_text_item_object.font_size
            max_font_size = self.convert_width_to_max_size(stroke_width=current_font_size, item="font")

            proxy_font_size = self.get_proxy_stroke_width(stroke_width=max_font_size, is_font_size=True)

            if not self.is_text_scaling:
                TextInsertWindow.stored_text_size = max_font_size
                self.is_text_scaling = True

            if value:
                new_font_size = int(TextInsertWindow.stored_text_size * value)

            elif increment:
                TextInsertWindow.stored_text_size = max_font_size
                # Might be Confusing, the - and + are flipped because tkinter represents fonts in - values(pixel size).
                # so font size of -52 needs to be -53 to be larger.
                if increment == "+":
                    new_font_size = int(TextInsertWindow.stored_text_size - 1)

                elif increment == "-":
                    new_font_size = int(TextInsertWindow.stored_text_size + 1)

            else:
                new_font_size = MIN_TEXT_SIZE

            new_font_size = min(MIN_TEXT_SIZE, new_font_size)
            TextInsertWindow.new_font_pixel_size = new_font_size

            new_proxy_font_size = self.get_proxy_stroke_width(new_font_size, is_font_size=True)

            # 'Arial Unicode MS' # -33 ,negative means pixel size instead of font.
            self.active_canvas.itemconfig(parent_id, font=(current_font_family,
                                                           new_font_size))

            self.active_canvas.itemconfig(proxy_id, font=(current_font_family,
                                                          new_proxy_font_size))

            self.app.graphics_data[self.index][parent_id].font_size = self.width_to_image_size(
                TextInsertWindow.new_font_pixel_size,
                item="font")
            self.app.proxy_data[self.index][proxy_id].font_size = new_proxy_font_size
            # Redraw the bounding
            self.select_text_item(text_id=self.selected_text_item, enable_scale_slider=False)

    @check_if_overlay
    def update_text_color(self, event):
        """
        Updates the color of the clicked text item.

        Args:
            event (tkinter.Event):Mouse click event

        Returns:

        """
        self.find_item(event, filter="text")
        if self.selected_text_item:
            if self.app.maximized_mode:
                parent_id = self.selected_text_item
                proxy_id = self.active_canvas.find_withtag(f"p{self.selected_text_item}")[0]
            else:
                proxy_id = self.selected_text_item
                tag = self.active_canvas.gettags(self.selected_text_item)[0]
                parent_id = int(tag[1:])

            selection_color = self.get_selection_color(hex_color=Tools.fill_color)

            # Updates the text color in all graphic_data and proxy_data.
            self.active_canvas.itemconfig(parent_id, fill=Tools.fill_color, activefill=selection_color)
            self.active_canvas.itemconfig(proxy_id, fill=Tools.fill_color, activefill=selection_color)
            self.app.graphics_data[self.index][parent_id].fill_color = Tools.fill_color
            self.app.proxy_data[self.index][proxy_id].fill_color = Tools.fill_color
            return True

    def force_hide_all_canvas_annotations(self):
        """
        Hides all drawing and text annotations on the image canvas.
        Returns:
            None

        """
        # Hide all canvas items including the image.
        self.app.image_canvas.itemconfig("all", state="hidden")
        # Reveal only the image.
        self.app.image_canvas.itemconfig("img", state="normal")

    @annotation_visibility_checker
    def hide_parent_annotations(self, hide_current: bool = False):  # Hide the graphic objects on screen
        """
        Hides the annotations displayed on the maximized display mode.

        Args:
            hide_current (bool): If True hide the annotations on the currently displayed image index too. Default False.

        Returns:
            None

        """
        if hide_current:
            self.active_canvas.itemconfig(f"m{self.app.last_viewed_image_index}", state="hidden")
            self.active_canvas.itemconfig(f"m{self.app.image_index}", state="hidden")
        else:
            self.active_canvas.itemconfig(f"m{self.app.last_viewed_image_index}", state="hidden")

    @annotation_visibility_checker
    def reveal_parent_annotations(self):
        """
        Displays the annotations of the current image index displayed on the maximized display mode.

        Returns:
            None

        """
        self.active_canvas.itemconfig(f"m{self.app.image_index}", state="normal")

    @annotation_visibility_checker
    def hide_proxy_annotations(self, hide_current=False):
        """
        Hides the annotations displayed on the windowed display mode.

        Args:
            hide_current (bool): If True hide the annotations on the currently displayed image index too. Default False.

        Returns:
            None

        """

        # Hides all objects with the drawing tag. found tcl method is more efficient rather than python loop.
        if hide_current:
            # Make it hide all proxies to avoid any bugs later.
            self.active_canvas.itemconfig(f"w{self.app.last_viewed_image_index}", state="hidden")
            self.active_canvas.itemconfig(f"w{self.app.image_index}", state="hidden")
        else:  # Hide only the previous
            self.active_canvas.itemconfig(f"w{self.app.last_viewed_image_index}", state="hidden")

    @annotation_visibility_checker
    def reveal_proxy_annotations(self):
        """
        Displays the annotations of the current image index displayed on the windowed display mode.

        Returns:
            None

        """

        self.active_canvas.itemconfig(f"w{self.app.image_index}", state="normal")

    # If no coordinates, stroke_width are provided the method uses the attributes of the currently plotted element.

    def get_proxy_stroke_width(self, stroke_width=None, is_font_size=False):
        """
        Calculates the Canvas size difference between maximized and windowed mode and uses that value to adjust the stroke width/font size accordingly.

        Args:
            stroke_width (float, optional): Width of the stroke to be converted to match the proxy window.
            is_font_size (bool): True when the passed coordinates represent the font size.

        Returns:

        """
        if not stroke_width:
            current_stroke_width = Tools.stroke_width
        else:
            current_stroke_width = stroke_width

        new_width, new_height = self.app.windowed_canvas_size
        try:
            old_width, old_height = self.app.maximized_canvas_size
        except:
            # directly calculate the image frame size on maxed mode.
            aspect_ratio = self.app.ld_img.width / self.app.ld_img.height
            width = min(self.app.image_frame_width_maxed, int(self.app.image_frame_height_maxed * aspect_ratio))
            height = min(self.app.image_frame_height_maxed, int(self.app.image_frame_width_maxed / aspect_ratio))
            self.app.maximized_canvas_size = width, height
            old_width, old_height = self.app.maximized_canvas_size

        max_scaling_factor = max(new_width / old_width, new_height / old_height)
        float_stroke_width = current_stroke_width * max_scaling_factor

        if is_font_size:  # If font size, simply round.
            if float_stroke_width > 0:
                float_stroke_width = -float_stroke_width
            return round(float_stroke_width)

        if float_stroke_width <= 1:
            adjusted_stroke_width = 1
        else:
            adjusted_stroke_width = float_stroke_width
            #

        return round(adjusted_stroke_width)

    @annotation_visibility_checker
    def scale_coordinates(self, coordinate_list=None, scale_mode: str = None, scale_item: str = None,
                          round_: bool = False):
        """
        Scale the coordinates of the canvas item to match the specified display mode.

        Args:
            coordinate_list (list|tuple,optional):Coordinates to be scaled.
            scale_mode (str): "+" Scales the coordinates from window size to maximized size. "-" Scales the other way.
            scale_item (str): Item to be scaled, items like "text","images" have only a single x,y coordinate and require different calculations.
            round_ (bool):True rounds the output into an integer. Default False.

        Returns:
            (list|tuple):The scaled coordinates.

        """

        if not coordinate_list:
            coordinate_list = self.coords_list
        if scale_mode == "+":  # scale coordinates in windowed mode to match default Maximized size.
            old_width, old_height = self.app.image_frame_width_windowed, self.app.image_frame_height_windowed
            new_width, new_height = self.app.image_frame_width_maxed, self.app.image_frame_height_maxed
        elif scale_mode == "-":  # scaling default cordinates to proxy windowed mode from maximized mode.
            new_width, new_height = self.app.image_frame_width_windowed, self.app.image_frame_height_windowed
            old_width, old_height = self.app.image_frame_width_maxed, self.app.image_frame_height_maxed

        scale_x = new_width / old_width
        scale_y = new_height / old_height
        coord_scale_factor = max(scale_x, scale_y)

        # Since text only has single tuple (x,y) coordinates.

        if scale_item == "image":
            x, y = (coordinate * coord_scale_factor for coordinate in coordinate_list)
            if round_:
                return (round(x), round(y))
            else:
                return (x, y)

        elif scale_item == "text":
            x, y = (coordinate * coord_scale_factor for coordinate in coordinate_list)
            if round_:
                return (round(x), round(y))
            else:
                return (x, y)

        scaled_coordinates = [((x * coord_scale_factor), (y * coord_scale_factor)) for x, y in coordinate_list]
        return scaled_coordinates

    @annotation_visibility_checker
    def get_dynamic_stroke_width(self, mode: str):
        """
        Returns a stroke width that matches the zoomed image size.

        Args:
            mode (str): Type of zoom, "actual", "zoomed".

        Returns:
            float:Scaled width size that matches the zoomed image size.

        """

        if mode == "actual":
            scale_factor = self.app.ld_img.width / self.app.resized_ld_img.width
        elif mode == "zoomed":
            scale_factor = self.app.scale_factor

        return (self.scribble_width * scale_factor)

    @annotation_visibility_checker
    def get_dynamic_coordinates(self, mode, coordinate_list=None, ):
        """
        Returns the scaled coordinates that matches the  size of the zoomed image.

        Args:
            mode (str): Mode of the displayed image. "actual" or "zoomed".
            coordinate_list (list|tuple, optional):Coordinates to scale.

        Returns:
            Scaled Coordinates that matches the zoomed image size.

        """
        if not coordinate_list:
            coordinate_list = self.coords_list
        if mode == "actual":
            scale_factor = self.app.resized_ld_img.width / self.app.ld_img.width
            scaled_coordinates = [((x * scale_factor), (y * scale_factor)) for x, y in coordinate_list]
        elif mode == "zoomed":  # Compares the difference of the displayed image with the zoomed image size.
            scale_factor = self.app.resized_ld_img.width / self.app.zoomed_ld_img.width
            scaled_coordinates = [((x * scale_factor), (y * scale_factor)) for x, y in coordinate_list]
        return scaled_coordinates

    @annotation_visibility_checker
    def scale_item_to_current_scale(self, item_id: int, mode: str):
        """
        Scale an item in the canvas to match the current zoom level of the image.

        Args:
            item_id (int):id of the canvas item to be scaled to match the zoomed image size.
             mode (str): Mode of the displayed image. "actual" or "zoomed".

        Returns:
            None

        """

        if mode == "actual":
            scale_factor = self.app.ld_img.width / self.app.resized_ld_img.width
        elif mode == "zoomed":
            scale_factor = self.app.scale_factor

        self.active_canvas.scale(item_id, 0, 0, scale_factor, scale_factor)
        if self.app.maximized_mode:
            current_item = self.app.graphics_data[self.app.image_index][item_id]
            self.active_canvas.itemconfig(item_id, width=(self.convert_width_to_max_size() * scale_factor))

        else:
            current_item = self.app.proxy_data[self.app.image_index][item_id]
            self.active_canvas.itemconfig(item_id, width=(current_item.width * scale_factor))

    def coordinates_to_image_size(self, coordinate_list, item: str = None, round_: bool = False):
        """
             Scales the coordinates to match the actual image size. Coordinates are stored in the original image size for file saving and loading purposes.

             Args:
                 coordinate_list (tuple|list ): Coordinates to be converted to the size of the image.
                 item (str, optional): Canvas item type. "text" if the item type is text, else None.
                 round_(bool,optional): Ignored in this method, Used in childclass to round floats to integer.

             Returns:
                  Coordinates that matches the size of the loaded image.

             """

        # Used round_ here to properly override the childclass.

        old_width, old_height = self.app.maximized_canvas_size

        new_width, new_height = self.app.ld_img.size
        scale_factor = new_width / old_width

        if item == "text":
            x, y = (coordinate * scale_factor for coordinate in coordinate_list)
            return (x, y)

        true_coordinates = [((x * scale_factor), (y * scale_factor)) for x, y in coordinate_list]
        return true_coordinates

    def image_coordinates_to_max_size(self, coordinate_list, item: str = None, round_: bool = False):
        """
        Converts the coordinates of the canvas item from the actual image size to maximized window mode. Used with Load and Save.

        Args:
            coordinate_list (tuple|list ): Coordinates to be converted to the size of the image.
            item (str, optional): Canvas item type. "text" if the item type is text, else None.
            round_ (bool):  True rounds the values to the closest integer. Default False.

        Returns:
            Coordinates that matches the image size in the maximized windowed mode.

        """

        old_width, old_height = self.app.ld_img.size
        new_width, new_height = self.app.maximized_canvas_size
        scale_factor = new_width / old_width
        if item == "text":
            x, y = (coordinate * scale_factor for coordinate in coordinate_list)
            return (x, y)

        maximized_coordinates = [((x * scale_factor), (y * scale_factor)) for x, y in coordinate_list]
        return maximized_coordinates

    def width_to_image_size(self, stroke_width=None, item=None):

        """
        Scales the width to match the actual image size. Width is saved in the original image size for file saving and loading purposes.

        Args:
            stroke_width(float|int,optional): Stroke to be converted to match the actual size of the image.
            item (str, optional): Canvas item type. "font" if the item type is text, else None.

        Returns:
             Width or Font size that matches the size of the loaded image.

        """

        if not stroke_width:
            current_stroke_width = Tools.stroke_width
        else:
            current_stroke_width = stroke_width

        new_width, new_height = self.app.ld_img.size
        try:
            old_width, old_height = self.app.maximized_canvas_size
        except:
            aspect_ratio = self.app.ld_img.width / self.app.ld_img.height
            width = min(self.app.image_frame_width_maxed, (self.app.image_frame_height_maxed * aspect_ratio))
            height = min(self.app.image_frame_height_maxed, (self.app.image_frame_width_maxed / aspect_ratio))
            self.app.maximized_canvas_size = width, height
            old_width, old_height = self.app.maximized_canvas_size

        width_scale_factor = new_width / old_width

        float_stroke_width = (current_stroke_width * width_scale_factor)
        if item == "font":
            if float_stroke_width > 0:  # incase bug causes the -ve to +ve
                float_stroke_width = -float_stroke_width
            return round(float_stroke_width)
        if float_stroke_width <= 1:
            adjusted_stroke_width = 1
        else:
            adjusted_stroke_width = (float_stroke_width)
        return adjusted_stroke_width

    def convert_width_to_max_size(self, stroke_width=None, item=None):
        """
        Converts the width of the canvas item from the actual image size to maximized window mode. Used with Load and Save.

        Args:
           stroke_width (float|int,optional ): Width or font size to be converted to the size of the image.
           item (str, optional): Canvas item type. "font" if the item type is text, else None.

        Returns:
           Width that matches the image size in the maximized windowed mode.

        """

        # Since the width is saved to match the actual image in the main cache, resizing here to match the viewport.
        if not stroke_width:
            width_from_image = self.width_to_image_size()
        else:
            width_from_image = stroke_width

        old_width, old_height = self.app.ld_img.size
        try:
            new_width, new_height = self.app.maximized_canvas_size
        except:  # Failsafe incase  no max size found
            aspect_ratio = self.app.ld_img.width / self.app.ld_img.height
            width = min(self.app.image_frame_width_maxed, int(self.app.image_frame_height_maxed * aspect_ratio))
            height = min(self.app.image_frame_height_maxed, int(self.app.image_frame_width_maxed / aspect_ratio))
            self.app.maximized_canvas_size = width, height
            new_width, new_height = self.app.maximized_canvas_size

        width_scale_factor = (new_width / old_width)
        float_stroke_width = (width_from_image * width_scale_factor)

        if item == "font":
            if float_stroke_width > 0:
                float_stroke_width = -float_stroke_width
            return round(float_stroke_width)

        if float_stroke_width <= 1:
            adjusted_stroke_width = 1
        else:
            adjusted_stroke_width = round(float_stroke_width, 4)

        return adjusted_stroke_width

    def scale_to_actual_size(self):
        """
        Scales the visible items on the canvas visually to match the Actual Image size in viewport.

        Returns:
            None

        """

        # finding how much the image has been scaled
        scale_x = self.app.ld_img.width / self.app.resized_ld_img.width
        scale_y = self.app.ld_img.height / self.app.resized_ld_img.height
        scale_factor = max(scale_x, scale_y)

        if self.app.maximized_mode:
            self.active_canvas.scale(f"m{self.app.image_index}", 0, 0, scale_factor, scale_factor)
            for key, item in self.app.graphics_data[self.app.image_index].items():
                if "text" not in item.tags:
                    self.active_canvas.itemconfig(key,
                                                  width=(self.convert_width_to_max_size(item.width) * scale_factor))
                else:
                    self.active_canvas.itemconfig(key, state="hidden")
            self.scale_to_reset = "m"  # maximized

        else:
            self.active_canvas.scale(f"w{self.app.image_index}", 0, 0, scale_factor, scale_factor)
            for key, item in self.app.proxy_data[self.app.image_index].items():
                if "text" not in item.tags:
                    self.active_canvas.itemconfig(key, width=(item.width * scale_factor))
                else:
                    self.active_canvas.itemconfig(key, state="hidden")
            self.scale_to_reset = "w"  # windowed
        #
        self.app.actual_scale_btn.configure(text="Actual Scale: ON", fg_color=self.app.TOP_BUTTON_FG_ACTIVE)

    def reset_actual_size(self):
        """
        Resets the visual scale of items on the canvas from actual scale to the default scale of the image in the viewport.

        Returns:
            None

        """

        scale_factor = self.app.ld_img.width / self.app.resized_ld_img.width

        if self.scale_to_reset == "m":
            self.active_canvas.scale(f"m{self.app.image_index}", 0, 0, 1 / scale_factor, 1 / scale_factor)
            for key, item in self.app.graphics_data[self.app.image_index].items():
                if "text" not in item.tags:
                    self.active_canvas.itemconfig(key, width=self.convert_width_to_max_size(item.width))

        elif self.scale_to_reset == "w":
            self.active_canvas.scale(f"w{self.app.image_index}", 0, 0, 1 / scale_factor, 1 / scale_factor)
            for key, item in self.app.proxy_data[self.app.image_index].items():
                if "text" not in item.tags:
                    self.active_canvas.itemconfig(key, width=item.width)
        self.scale_to_reset = None
        self.app.actual_scale_btn.configure(text="Actual Scale: OFF", fg_color=self.app.TOP_BUTTON_FG)

    def scale_to_zoomed_size(self, mode, lock_zoom=False):
        """
        Scales the visible items on the canvas visually to match the Zoomed image size in viewport.

        Returns:
            None

        """

        if not lock_zoom:
            if mode == "+":
                scale_factor = (1.5)
            else:
                scale_factor = 1 / 1.5
        else:
            scale_factor = self.app.scale_factor

        if self.app.maximized_mode:
            self.active_canvas.scale(f"m{self.app.image_index}", 0, 0, scale_factor, scale_factor)
            for key, item in self.app.graphics_data[self.app.image_index].items():
                if "text" not in item.tags:
                    self.active_canvas.itemconfig(key, width=(
                            self.convert_width_to_max_size(item.width) * self.app.scale_factor))
                else:
                    self.active_canvas.itemconfig(key, state="hidden")
            self.zoom_to_reset = "m"  # maximized

        else:
            self.active_canvas.scale(f"w{self.app.image_index}", 0, 0, scale_factor, scale_factor)
            for key, item in self.app.proxy_data[self.app.image_index].items():
                if "text" not in item.tags:
                    self.active_canvas.itemconfig(key, width=item.width * self.app.scale_factor)
                else:
                    self.active_canvas.itemconfig(key, state="hidden")
            self.zoom_to_reset = "w"  # windowed

    def reset_zoomed_size(self):
        """
        Resets the visual scale of items on the canvas from the zoomed size to the default scale of the image in the viewport.

        Returns:
            None

        """
        # if not zoom_lock:
        scale_factor = 1 / self.app.scale_factor

        if self.zoom_to_reset == "m":
            self.active_canvas.scale(f"m{self.app.image_index}", 0, 0, scale_factor, scale_factor)
            for key, item in self.app.graphics_data[self.app.image_index].items():
                if "text" not in item.tags:
                    self.active_canvas.itemconfig(key, width=int(self.convert_width_to_max_size(item.width)))

        elif self.zoom_to_reset == "w":
            self.active_canvas.scale(f"w{self.app.image_index}", 0, 0, scale_factor, scale_factor)
            for key, item in self.app.proxy_data[self.app.image_index].items():
                if "text" not in item.tags:
                    self.active_canvas.itemconfig(key, width=item.width)

        self.zoom_to_reset = None

    def hide_current_text_items(self):
        """
        Hides the text items on the canvas.
        Returns:
            None

        """

        if self.app.maximized_mode:
            for key, item in self.app.graphics_data[self.app.image_index].items():
                if "text" in item.tags:
                    self.active_canvas.itemconfig(key, state="hidden")
        else:
            for key, item in self.app.proxy_data[self.app.image_index].items():
                if "text" in item.tags:
                    self.active_canvas.itemconfig(key, state="hidden")

    # ------Color Conversion---------------
    def hex_to_rgb(self, hex_color: str):
        """
        Converts a color from Hex to RGB values

        Args:
            hex_color (str): Hex Color code to be converted into RGB values

        Returns:
                tuple:RGB values as a tuple.
        """

        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        return rgb

    def get_selection_color(self, hex_color):
        """
        Checks the given hex value to see if it's on the brighter or darker side, then returns a contrasting color close to the given color range.

       Args:
            hex_color (str): Hex color.

        Returns:
            str: Brighter or Darker tone of the given Hex color.

        """
        OFFSET = 50
        rgb_tuple = self.hex_to_rgb(hex_color)
        max_value = max(rgb_tuple)
        adjusted_color = [
            max(min(value - OFFSET, 255) if max_value > 128 else min(value + OFFSET, 255), 0) for
            value in rgb_tuple]

        r, g, b = adjusted_color
        # RGB to HEX conversion.
        return f'#{r:02x}{g:02x}{b:02x}'


class OverlayGraphicsManager(GraphicsManager):
    """
    Child Class that handles the creation and display of graphic elements and overlay images on the Overlay Canvas.
    """

    def __init__(self, app, canvas, is_overlay=True, *args, **kwargs):
        """
        Initialising the Class with a given canvas.

        Args:
            app: Tkinter main app
            canvas: Overlay Canvas
            is_overlay (bool): True if the canvas is the overlay canvas. Default True.
        """
        super().__init__(app, canvas, is_overlay, *args, **kwargs)

        self.OVERLAY_WIDTH = 1920  # A Ghost image to make sure that the coordinates are saved consistently.
        self.OVERLAY_HEIGHT = 1080
        self.imported_overlay_image_cache = {}
        self.selected_overlay_image = None
        self.is_image_repositioning = False
        self.is_image_scaling = False
        self.stored_image_size = None
        self.selected_overlay_image_cache = None

        self.create_overlay_image_selection_border()

    def draw_graphic_elements_from_project_file(self, is_overlay=True):
        """
        Checks the Overlay image index in the project file for any overlay images and adds the images and applies the saved transformations to it.
        Unpacks the loaded_graphics_data_dict and based on the tool used, mimics the events that happens during the normal drawing.

        Args:
            is_overlay(bool):True, Argument has no use in child method.

        Returns:
            None

        """
        if self.app.loaded_graphics_data[self.OVERLAY_IMAGES_INDEX]:  # checking for images.
            for item_id, image_element in self.app.loaded_graphics_data[self.OVERLAY_IMAGES_INDEX].items():
                coordinates = image_element.coordinates
                max_coordinates = self.get_viewport_size_from_absolute_overlay_size(coordinates, item="image")
                proxy_coordinates = self.scale_coordinates(max_coordinates, scale_mode="-", scale_item="image")

                size = image_element.size
                max_size = self.get_viewport_size_from_absolute_overlay_size(size, item="image", round_=True)
                proxy_size = self.scale_coordinates(max_size, scale_mode="-", scale_item="image", round_=True)

                # add the image to the overlay. Skip if overlay image not found.
                try:
                    self.add_image_to_overlay_canvas(image_path=image_element.image_path)
                except:
                    break
                # Mimicking the image transform operations

                if self.app.maximized_mode:
                    self.scale_overlay_image(size=max_size)
                    self.reposition_overlay_image(position=max_coordinates)
                else:
                    self.scale_overlay_image(size=proxy_size)
                    self.reposition_overlay_image(position=proxy_coordinates)

                self.rotate_overlay_image(value=image_element.angle)
                self.change_overlay_image_opacity(opacity=image_element.opacity)

        if self.app.loaded_graphics_data[self.OVERLAY_GRAPHICS_INDEX]:  # Calls the parent method.
            super().draw_graphic_elements_from_project_file(is_overlay=True)

    def create_overlay_image_selection_border(self):
        """
        Plots a six segmented line segment to act as a selection border while selecting the overlay images.
        Returns:
            None

        """
        self.image_selection_border = self.active_canvas.create_line(0, 0, 0, 0, 0, 0, 0, 0, fill="#20C9FF", width=2,
                                                                     tags="gui")

        self.active_canvas.itemconfig(self.image_selection_border, state="hidden")

    def add_image_to_overlay_canvas(self, image_path: str):
        """
        Places the imported image in the overlay canvas. If the imported image and the currently viewed image size is the same, the imported image is scaled to fit.

        Args:
            image_path (str): File path for the imported image.

        Returns:
            None

        """
        self.imported_overlay_ld_img = Image.open(image_path).convert("RGBA")

        imported_image_width, imported_image_height = self.imported_overlay_ld_img.size

        # If the imported image matches the current image in height or width, placing them without any shrinking.
        if self.app.ld_img.width == imported_image_width:  #
            scale_factor = self.app.resized_ld_img.width / self.app.ld_img.width

        elif self.app.ld_img.height == imported_image_height:  #
            scale_factor = self.app.resized_ld_img.height / self.app.ld_img.height

        # If the Image size does not match the background, shrink it to 1/2 size of the canvas.
        else:
            width_scale_factor = (self.app.resized_ld_img.width / 2) / imported_image_width
            height_scale_factor = (self.app.resized_ld_img.height / 2) / imported_image_height
            scale_factor = min(width_scale_factor, height_scale_factor)

        self.resized_imported_overlay_ld_img = self.imported_overlay_ld_img.resize(
            (int(imported_image_width * scale_factor),
             int(imported_image_height * scale_factor)),
            resample=Image.LANCZOS)

        # self.resized_imported_overlay_ld_img.putalpha(120)
        imported_overlay_image_tk = ImageTk.PhotoImage(self.resized_imported_overlay_ld_img)

        if self.app.maximized_mode:
            center_x = self.app.image_frame_width_maxed // 2
            center_y = self.app.image_frame_height_maxed // 2
        else:
            center_x = self.app.image_frame_width_windowed // 2
            center_y = self.app.image_frame_height_windowed // 2

        tags = ("overlay_img")
        placed_image = self.app.overlay_canvas.create_image(center_x, center_y, anchor="center",
                                                            image=imported_overlay_image_tk,
                                                            tags=tags)

        if self.app.maximized_mode:
            img_max_size = self.resized_imported_overlay_ld_img.size
            img_proxy_size = self.scale_coordinates(self.resized_imported_overlay_ld_img.size, scale_mode="-",
                                                    scale_item="image", round_=True)
            max_coordinates = (center_x, center_y)
            proxy_coordinates = self.scale_coordinates(coordinate_list=max_coordinates, scale_mode="-",
                                                       scale_item="image")
        else:
            img_max_size = self.scale_coordinates(self.resized_imported_overlay_ld_img.size, scale_mode="+",
                                                  scale_item="image", round_=True)
            img_proxy_size = self.resized_imported_overlay_ld_img.size
            proxy_coordinates = (center_x, center_y)
            max_coordinates = self.scale_coordinates(coordinate_list=proxy_coordinates, scale_mode="+",
                                                     scale_item="image")

        # Image size relative to overlay_canvas size.
        img_size = self.rescale_overlay_elements_to_absolute_overlay_size(element=img_max_size, item="image",
                                                                          round_=True)

        coordinates = self.coordinates_to_image_size(coordinate_list=max_coordinates, item="image")

        self.app.graphics_data[self.OVERLAY_IMAGES_INDEX][placed_image] = OverlayImageCache(
            image_object=self.imported_overlay_ld_img,
            image_path=image_path,
            coordinates=(coordinates),
            max_coordinates=max_coordinates,
            proxy_coordinates=proxy_coordinates,
            size=img_size,
            max_size=img_max_size,
            proxy_size=img_proxy_size,
            opacity=1,
            angle=0,
            tags=tags)

        self.imported_overlay_image_cache[placed_image] = imported_overlay_image_tk
        self.select_overlay_image(image_id=placed_image)

    def select_canvas_item(self, event, item_id=None):
        """
        Fetches the clicked item on the canvas. If the item is an image or text, draw the surrounding border.

        Args:
           event(tkinter.Event): Mouse Click event
           item_id(int):id of the canvas item.

        Returns:
           None

        """

        # Remove any existing selected items from selection.
        self.app.overlay_gm.remove_overlay_image_selection()
        self.remove_text_item_selection()

        if not item_id:
            item_id = event.widget.find_closest(event.x, event.y)[0]

        item_tags = self.active_canvas.gettags(item_id)

        if "overlay_img" in item_tags:  # Child methods
            self.app.overlay_gm.select_overlay_image(image_id=item_id)
            self.app.overlay_gm.set_overlay_image_drag_offset(event)

        elif "text" in item_tags:
            self.set_text_drag_offset(event)
            super().select_text_item(text_id=item_id)

    def select_overlay_image(self, image_id=None):
        """
        Assigns the overlay image item as the selected_overlay_image and draws the selection border around it.

        Args:
             image_id (int): id of the text item on the canvas.

        Returns:
             None

        """
        img_bounds = self.active_canvas.bbox(image_id)
        x1, y1, x2, y2 = img_bounds
        border_coordinates = x1, y1, x2, y1, x2, y2, x1, y2, x1, y1, x1, y2, x2, y1, x1, y1, x2, y2
        self.active_canvas.coords(self.image_selection_border, border_coordinates)
        self.active_canvas.tag_raise("gui")
        self.active_canvas.itemconfig(self.image_selection_border, state="normal", fill=self.app.selection_color)
        # Assigning the selected canvas image item as the selected_overlay_image.
        self.selected_overlay_image = image_id
        self.selected_overlay_image_cache = self.app.graphics_data[self.OVERLAY_IMAGES_INDEX][
            self.selected_overlay_image]

        # shows the current opacity of the overlay image.
        self.app.set_opacity_slider(value=int(self.selected_overlay_image_cache.opacity * 100))
        self.app.set_rotation_slider(value=int(self.selected_overlay_image_cache.angle))

        self.app.toggle_image_tools_sliders(1)
        self.app.toggle_image_tools_buttons(only_reset=True, toggle=1)

    def remove_overlay_image_selection(self):
        """
        Removes the selection of the selected overlay image, and resets the image control sliders.

        Returns:
            None

        """
        if self.selected_overlay_image:
            self.active_canvas.itemconfig(self.image_selection_border, state="hidden")
            self.selected_overlay_image = None
            self.selected_overlay_image_cache = None
            self.app.set_opacity_slider(100)
            self.app.set_rotation_slider(0)
            self.app.toggle_image_tools_sliders(0)
            self.app.toggle_image_tools_buttons(only_reset=True, toggle=0)  # disable image reset button.

    def rescale_overlay_images_to_view(self):
        """
        Iterates through the overlay images and scales them to match the current display mode.

        Returns:
            None

        """

        if self.app.maximized_mode:
            window_maxed = True
        else:
            window_maxed = False

        for index, image_cache in self.app.graphics_data[self.OVERLAY_IMAGES_INDEX].items():
            # get current size and multiply by scale factor
            current_image_object: Image = image_cache.image_object
            current_image_size = image_cache.size
            current_image_rotation = image_cache.angle

            if window_maxed:
                current_image_max_size = image_cache.max_size
                current_image_max_coordinates = image_cache.max_coordinates
                resized_imported_overlay_ld_img = current_image_object.resize(current_image_max_size,
                                                                              resample=Image.LANCZOS)
            else:
                current_image_proxy_size = image_cache.proxy_size
                current_image_proxy_coordinates = image_cache.proxy_coordinates
                resized_imported_overlay_ld_img = current_image_object.resize(current_image_proxy_size,
                                                                              resample=Image.LANCZOS)

            if current_image_rotation != 0:
                resized_imported_overlay_ld_img = resized_imported_overlay_ld_img.rotate(current_image_rotation,
                                                                                         expand=True, )

            imported_overlay_image_tk = ImageTk.PhotoImage(resized_imported_overlay_ld_img)
            self.app.overlay_canvas.itemconfig(index, image=imported_overlay_image_tk)

            if window_maxed:
                self.app.overlay_canvas.coords(index, current_image_max_coordinates)
            else:
                self.app.overlay_canvas.coords(index, current_image_proxy_coordinates)

            self.imported_overlay_image_cache[index] = imported_overlay_image_tk

    def delete_item(self, event=None):
        """
        Removes the selected overlay image or text item from the canvas, and deletes the data from the dictionary.

        Args:
            event (tkinter.Event): Keypress event.

        Returns:
            None

        """
        if current_image := self.selected_overlay_image:
            self.active_canvas.delete(current_image)
            del self.app.graphics_data[self.OVERLAY_IMAGES_INDEX][current_image]
            del self.app.overlay_gm.imported_overlay_image_cache[current_image]
            self.active_canvas.itemconfig(self.image_selection_border, state="hidden")
            self.remove_overlay_image_selection()
        else:
            super().delete_item()

    def set_overlay_image_drag_offset(self, event):
        """
        Sets the initial position for overlay image repositioning.

        Args:
            event(tkinter.Event): Mouse click event.

        Returns:
            None

        """
        self.selection_click_position = self.active_canvas.canvasx(event.x), self.active_canvas.canvasy(event.y)
        current_item_bbox = self.active_canvas.bbox(self.selected_overlay_image)
        # Calculate the center coordinates of the text item
        center_x = (current_item_bbox[0] + current_item_bbox[2]) / 2
        center_y = (current_item_bbox[1] + current_item_bbox[3]) / 2

        # Calculate the offset from the center to the initial click, to avoid image snapping to the cursor.
        self.overlay_image_offset_x = self.selection_click_position[0] - round(center_x)
        self.overlay_image_offset_y = self.selection_click_position[1] - round(center_y)

    def reposition_overlay_image(self, event=None, position: tuple = None, constraint: bool = False):
        """
        Repositions the overlay image using the mouse drag cordinates or a set of predefined coordinates.

        Args:
            event (tkinter.Event):Mouse Drag event.
            position (tuple,optional): New Coordinates for the image.
            constraint(bool): True constraints the live positioning to a single axis.Default False.

        Returns:
            None

        """

        if self.selected_overlay_image:
            if not position:
                self.is_image_repositioning = True
                self.hide_overlay_image_selection_border()
                # Offset so that text anchor won't snap to mouse position.
                current_mousex = self.active_canvas.canvasx(event.x)
                current_mousey = self.active_canvas.canvasx(event.y)

                new_x = current_mousex - self.overlay_image_offset_x
                new_y = current_mousey - self.overlay_image_offset_y

                if constraint:
                    dx = current_mousex - self.selection_click_position[0]
                    dy = current_mousey - self.selection_click_position[1]

                    if self.x_axis_constraint == None:

                        if abs(dx) >= abs(dy):
                            self.x_axis_constraint = True
                        else:
                            self.x_axis_constraint = False

                    if self.x_axis_constraint:
                        new_y = self.selection_click_position[1] - self.overlay_image_offset_y
                        self.active_canvas.coords(self.selected_overlay_image, (new_x, new_y))
                    else:
                        new_x = self.selection_click_position[0] - self.overlay_image_offset_x
                        self.active_canvas.coords(self.selected_overlay_image, (new_x, new_y))

                else:
                    self.active_canvas.coords(self.selected_overlay_image, (new_x, new_y))
            else:
                self.active_canvas.coords(self.selected_overlay_image, (position))

            self.update_overlay_image_coordinates()

    def update_overlay_image_coordinates(self):
        """
        Converts the updated overlay image coordinates into multiple display modes and updates them in the dictionary.

        Returns:
            None

        """

        bbox = self.active_canvas.bbox(self.selected_overlay_image)
        x_center = (bbox[0] + bbox[2]) / 2
        y_center = (bbox[1] + bbox[3]) / 2
        new_coords = x_center, y_center  # center coordinates

        if self.app.maximized_mode:
            max_coordinates = new_coords
            proxy_coordinates = self.scale_coordinates(coordinate_list=max_coordinates,
                                                       scale_mode="-",
                                                       scale_item="image")

        else:
            proxy_coordinates = new_coords
            max_coordinates = self.scale_coordinates(coordinate_list=proxy_coordinates,
                                                     scale_mode="+",
                                                     scale_item="image")

        coordinates = self.coordinates_to_image_size(coordinate_list=max_coordinates, item="image")
        # update the coordinates of the image in all screen views.
        self.selected_overlay_image_cache.coordinates = coordinates
        self.selected_overlay_image_cache.max_coordinates = max_coordinates
        self.selected_overlay_image_cache.proxy_coordinates = proxy_coordinates

    def scale_overlay_image(self, factor: float = 1, size: tuple = None, increment: str = None):
        """
        Scales the selected overlay image by a multiplier value.

        Args:
            factor (float):Value that multiplies the scale of the current selected overlay image.
            size (tuple,optional): Predefined size for the selected overlay image.
            increment (str,optional): "+" Increments image scale by +1 and "-" decrements the scale by 1.

        Returns:
            None

        """
        if not self.selected_overlay_image:
            return

        scale_fac = factor
        # Accessing the OverlayImageCache containing the current image.
        selected_image_cache = self.selected_overlay_image_cache
        current_ld_image = selected_image_cache.image_object

        if not self.is_image_scaling:
            # first time during scaling
            if self.app.maximized_mode:  # get the current dimensions based on view.
                current_image_size = selected_image_cache.max_size
            else:
                current_image_size = selected_image_cache.proxy_size

            self.stored_image_size = current_image_size

        else:  # Same initial value will be used unless the click is released.
            current_image_size = self.stored_image_size
            self.hide_overlay_image_selection_border()

        if not increment:
            rescaled_size = (tuple(round(dimension * scale_fac) for dimension in current_image_size))
            self.is_image_scaling = True

        elif increment:
            if increment == "+":
                rescaled_size = (tuple(round(dimension + 1) for dimension in current_image_size))
            elif increment == "-":
                rescaled_size = (tuple(round(dimension - 1) for dimension in current_image_size))
            self.reveal_overlay_image_selection_border()
            self.is_image_scaling = False

        if 0 in rescaled_size:
            return

        if size:  # a defined scale is provided.
            resized_selected_overlay_img = current_ld_image.resize(size, resample=Image.LANCZOS)
        else:

            resized_selected_overlay_img = current_ld_image.resize(rescaled_size, resample=Image.LANCZOS)

        selected_overlay_image_tk = ImageTk.PhotoImage(resized_selected_overlay_img)
        self.app.overlay_canvas.itemconfig(self.selected_overlay_image, image=selected_overlay_image_tk)

        # Saving the reference to prevent garbage collection.
        self.imported_overlay_image_cache[self.selected_overlay_image] = selected_overlay_image_tk

        if self.app.maximized_mode:
            img_max_size = resized_selected_overlay_img.size
            img_proxy_size = self.scale_coordinates(img_max_size, scale_mode="-", scale_item="image", round_=True)

        else:
            img_proxy_size = resized_selected_overlay_img.size
            img_max_size = self.scale_coordinates(img_proxy_size, scale_mode="+", scale_item="image", round_=True)

        img_size = self.rescale_overlay_elements_to_absolute_overlay_size(element=img_max_size, item="image",
                                                                          round_=True)

        # updating the values in the OverlayImageCache
        selected_image_cache.size = img_size
        selected_image_cache.max_size = img_max_size
        selected_image_cache.proxy_size = img_proxy_size
        # Redrawing opacity here, no other way to get a live preview of semitransparent images.
        self.redraw_selected_image(redraw_rotation=True, redraw_opacity=True)

    def rotate_overlay_image(self, value: int):
        """
        Rotates the selected overlay image by the given value.

        Args:
            value (int):Integer of range 0 to 360.

        Returns:
            None

        """
        if self.selected_overlay_image:
            selected_image_cache = self.selected_overlay_image_cache
            current_ld_image = selected_image_cache.image_object
            self.selected_overlay_image_cache.angle = value
            # Redrawing opacity here, no other way to get a live preview of semitransparent images.
            self.redraw_selected_image(redraw_rotation=True, redraw_opacity=True)
            self.reveal_overlay_image_selection_border()

    def change_overlay_image_opacity(self, opacity: float = None):
        """
        Controls the opacity of the selected overlay image.

        Args:
            opacity(float): Float range from 0 to 1.

        Returns:
             None
        """
        if self.selected_overlay_image:
            opacity_value = opacity
            self.selected_overlay_image_cache.opacity = opacity_value
            self.redraw_selected_image(redraw_opacity=True, redraw_rotation=True)

    def redraw_selected_image(self, redraw_opacity: bool = False, redraw_rotation: bool = False):
        """
        Redraws the selected overlay image by loading it from disk and applying the re applying the transformations and opacity.

        Args:
            redraw_opacity (bool): True updates the image opacity using the stored value. False skips the operation. Default False
            redraw_rotation (bool): True updates the image rotation using the stored value. False skips the operation. Default False

        Returns:
            None

        """
        if self.selected_overlay_image:
            image_object_to_redraw = Image.open(self.selected_overlay_image_cache.image_path).convert("RGBA")
            # image_object_to_redraw=self.selected_overlay_image_cache.image_object
            #
            if redraw_opacity:
                # image_object_to_redraw.putalpha(255) #reset to 100
                alpha = image_object_to_redraw.split()[3]
                alpha = alpha.point(lambda p: p * self.selected_overlay_image_cache.opacity)
                image_object_to_redraw.putalpha(alpha)
            # reduced transparent object at full size. this transparent img object will be used for scale and transform.
            self.selected_overlay_image_cache.image_object = image_object_to_redraw

            if self.app.maximized_mode:
                image_scale = self.selected_overlay_image_cache.max_size
                image_position = self.selected_overlay_image_cache.max_coordinates
            else:
                image_scale = self.selected_overlay_image_cache.proxy_size
                image_position = self.selected_overlay_image_cache.proxy_coordinates

            # Scaling the image to match its old scale.

            image_object_to_redraw = image_object_to_redraw.resize(image_scale, resample=Image.LANCZOS)

            if redraw_rotation:
                rotation_value = self.selected_overlay_image_cache.angle
                image_object_to_redraw = image_object_to_redraw.rotate(rotation_value, expand=True, )

            selected_overlay_image_tk = ImageTk.PhotoImage(image_object_to_redraw)

            self.app.overlay_canvas.itemconfig(self.selected_overlay_image, image=selected_overlay_image_tk)
            self.imported_overlay_image_cache[self.selected_overlay_image] = selected_overlay_image_tk

    def reset_selected_image(self):
        """
        Resets the loaded overlay image to the size and position during import by reloading it from disk.

        Returns:
            None

        """
        selected_ld_image_path = self.app.graphics_data[self.OVERLAY_IMAGES_INDEX][
            self.selected_overlay_image].image_path
        self.delete_item()
        self.add_image_to_overlay_canvas(image_path=selected_ld_image_path)

    def wipe_current_annotations(self):
        """
        Wipes all overlay images added to the Overlay canvas.
        Returns:
            None

        """
        image_items_to_delete = list(self.app.graphics_data[self.OVERLAY_IMAGES_INDEX].keys())
        for image in image_items_to_delete:
            self.app.overlay_canvas.delete(image)
            del self.app.graphics_data[self.OVERLAY_IMAGES_INDEX][image]  # removes the p

        self.remove_overlay_image_selection()
        super().wipe_current_annotations()

    def hide_overlay_image_selection_border(self):
        """
        Hides the selection border of the overlay image.

        Returns:
            None

        """
        if self.selected_overlay_image:
            self.active_canvas.itemconfig(self.image_selection_border, state="hidden")

    def reveal_overlay_image_selection_border(self):
        """
        Displays the selection border of the selected overlay image.


        Returns:
            None

        """
        if self.selected_overlay_image:
            image_id = self.selected_overlay_image
            img_bounds = self.active_canvas.bbox(image_id)
            x1, y1, x2, y2 = img_bounds
            border_coordinates = x1, y1, x2, y1, x2, y2, x1, y2, x1, y1, x1, y2, x2, y1, x1, y1, x2, y2

            self.active_canvas.coords(self.image_selection_border, border_coordinates)
            self.active_canvas.tag_raise("gui")
            self.active_canvas.itemconfig(self.image_selection_border, state="normal")

            self.is_image_scaling = False
            self.is_image_repositioning = False
            self.x_axis_constraint = None

    def hide_parent_overlay_annotations(self):  # Hide the graphic objects on screen
        """
        Hides the annotations displayed on maximized display mode.

        Returns:
            None

        """
        self.active_canvas.itemconfig("m-1", state="hidden")

    def reveal_parent_overlay_annotations(self):

        """
        Reveals the annotations displayed on maximized display mode.

        Returns:
            None

        """
        self.active_canvas.itemconfig("m-1", state="normal")

    def hide_proxy_overlay_annotations(self):
        """
        Hides the annotations displayed on windowed display mode.

        Returns:
            None

        """

        self.active_canvas.itemconfig("w-1", state="hidden")

    def reveal_proxy_overlay_annotations(self):
        """
        Reveals the annotations displayed on windowed display mode.

        Returns:
            None

        """
        self.active_canvas.itemconfig("w-1", state="normal")

    def rescale_overlay_elements_to_absolute_overlay_size(self, element, item, round_: bool = False):
        """
        Converts the attributes of the overlay elements to match the size of the overlay ghost image (1920x1080).

        Args:
            element : Coordinates, width , fontsize to rescale to the absolute size of the overlay.
            item (str): Type of item.
            round_ (bool): True rounds the float to an integer. Default False.

        Returns:
            Rescaled element data that matches the size of the Overlay ghost image size.

        """
        # Get rescaled values of elements in the absolute overlay canvas size.
        # old_width, old_height = self.app.image_frame_width_maxed,self.app.image_frame_height_maxed
        # # Converting the image to a 16:9 ratio space since the global canvas coords are stored in 16:9 image.
        # canvas_width = 16 * old_height // 9
        # canvas_height = old_height
        # if canvas_width < old_width:
        #     canvas_width = old_width
        #     canvas_height = 9 * old_width // 16

        old_width, old_height = self.app.image_frame_width_maxed, self.app.image_frame_height_maxed
        new_width, new_height = self.OVERLAY_WIDTH, self.OVERLAY_HEIGHT

        scale_factor = new_width / old_width

        if item == "text":
            x, y = (coordinate * scale_factor for coordinate in element)
            return (x, y)

        elif item == "font":
            new_font_size = element * scale_factor
            if new_font_size > 0:  # incase bug causes the -ve to +ve
                new_font_size = -new_font_size
            return round(new_font_size)

        elif item == "width":
            float_stroke_width = (element * scale_factor)
            if float_stroke_width <= 1:
                adjusted_stroke_width = 1
            else:
                adjusted_stroke_width = (float_stroke_width)
            return adjusted_stroke_width

        elif item == "image":
            x, y = (coordinate * scale_factor for coordinate in element)
            if round_:
                return (round(x), round(y))
            else:
                return (x, y)

        else:  # item=Coords
            true_coordinates = [((x * scale_factor), (y * scale_factor)) for x, y in element]
            return true_coordinates

    def get_viewport_size_from_absolute_overlay_size(self, coordinate_list, item: str = None, round_: bool = False):
        """
        Route method that calls the image_coordinates_to_max_size.

        Args:
            coordinate_list (tuple|list): Coordinates to be scaled from the absolute size to match the maximized display mode.
            item (str): Canvas item.
            round_ (bool): True rounds the float to an integer. Default False.

        Returns:
            Rescaled coordinates that matches the maximized display mode of the overlay canvas.

        """
        return self.image_coordinates_to_max_size(coordinate_list=coordinate_list, item=item, round_=round_)

    def coordinates_to_image_size(self, coordinate_list, item: str = None, round_: bool = False):
        """
        Route method that calls the rescale_overlay_elements_to_absolute_overlay_size.

        Args:
            coordinate_list: Coordinates to be scaled to match the size of the Ghost Overlay image.
            item (str): Item in the canvas.
            round_ (bool): True rounds the float to an integer. Default False.

        Returns:
            Rescaled coordinates that matches the Ghost Image size of the Overlay Canvas (1920x1080).

        """
        return self.rescale_overlay_elements_to_absolute_overlay_size(element=coordinate_list, item=item, round_=round_)

    def width_to_image_size(self, stroke_width=None, item: str = None):
        """
        Scales the width to match the size of the Overlay Ghost Image.

        Args:
            stroke_width: Width to scale.
            item (str): canvas item

        Returns:
            (float|int): Scaled width matching the overlay canvas size.

        """
        if not stroke_width:  # getting -50 here
            current_stroke_width = Tools.stroke_width
        else:
            current_stroke_width = stroke_width

        return self.rescale_overlay_elements_to_absolute_overlay_size(element=stroke_width, item=item)
        # return self.coordinates_to_image_size(coordinate_list=stroke_width, item=item)

    def image_coordinates_to_max_size(self, coordinate_list, item: str = None, round_: bool = False):
        """
        Converts the coordinates from Ghost Overlay Image to match the maximized display mode. Used while loading a project file.

        Args:
            coordinate_list :  Coordinates to rescale.
            item (str):Canvas item.
            round_(bool): True rounds the float to an integer. Default False.

        Returns:
            Coordinates that match the maximzed display mode.

        """

        # to use with save and load
        old_width, old_height = (self.OVERLAY_WIDTH, self.OVERLAY_HEIGHT)
        new_width, new_height = self.app.image_frame_width_maxed, self.app.image_frame_height_maxed
        scale_factor = new_width / old_width

        if item == "text" or item == "image":
            x, y = (coordinate * scale_factor for coordinate in coordinate_list)
            if round_:
                return (round(x), round(y))
            else:
                return (x, y)
        maximized_coordinates = [((x * scale_factor), (y * scale_factor)) for x, y in coordinate_list]
        return maximized_coordinates

    def convert_width_to_max_size(self, stroke_width=None, item=None):
        """
         Converts the width from Ghost Overlay Image to match the maximized display mode. Used while loading a project file.

        Args:
            stroke_width:
            item (str):Canvas item.

         Returns:
                  Width or Fontsize that match the maximzed display mode.
        """

        # Since the width is saved to match the actual image in the main cache, resizing here to match the viewport.

        if not stroke_width:
            width_from_image = self.width_to_image_size()
        else:
            width_from_image = stroke_width

        old_width, old_height = (self.OVERLAY_WIDTH, self.OVERLAY_HEIGHT)

        try:  # Using image_frame here since overlay and image frame is 16:9
            new_width, new_height = self.app.image_frame_width_maxed, self.app.image_frame_height_maxed
        except:  # Failsafe
            aspect_ratio = self.app.ld_img.width / self.app.ld_img.height
            width = min(self.app.image_frame_width_maxed, int(self.app.image_frame_height_maxed * aspect_ratio))
            height = min(self.app.image_frame_height_maxed, int(self.app.image_frame_width_maxed / aspect_ratio))
            self.app.maximized_canvas_size = width, height
            new_width, new_height = self.app.maximized_canvas_size

        width_scale_factor = (new_width / old_width)
        float_stroke_width = (width_from_image * width_scale_factor)

        if item == "font":  # Font size are -ve because tkinter user -ve size as pixel size.
            if float_stroke_width > 0:
                float_stroke_width = -float_stroke_width
            return round(float_stroke_width)

        if float_stroke_width <= 1:
            adjusted_stroke_width = 1
        else:
            adjusted_stroke_width = (float_stroke_width)

        return adjusted_stroke_width


@dataclass(repr=False)
class GraphicsCache:
    """
    Object that stores the coordinates and attributes of the plotted 2d graphic elements.
    """
    # tool:str
    coordinates: list  # coordinates
    width: int  # width
    tags: str | tuple  # tags
    tool: int  # tool id
    fill_color: str = ""  # fill
    shape_fill: bool = False
    interior_fill_color: str = ""
    outline_fill_color: str = ""
    stipple: str = ""
    joinstyle: str = "round"  # joinstyle
    capstyle: str = "round"  # capstyle
    text: str = ""
    font_name: str = ""
    font_file: str = ""
    font_size: int = 0


@dataclass(repr=False)
class OverlayImageCache():
    """
    Object that stores the filepath and transformation values for the imported overlay image elements.
    """
    image_object: Image  # obj from Image.open(image_path)
    image_path: str
    coordinates: list | tuple  # coordinates
    max_coordinates: list | tuple
    proxy_coordinates: list | tuple
    size: tuple
    max_size: tuple
    proxy_size: tuple
    opacity: int
    angle: int
    tags: str | tuple  # tags
