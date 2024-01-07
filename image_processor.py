from PIL import Image, ImageDraw, ImageFont
from tkinter.font import Font
import math
import os


class ImageProcessor:
    """
    Handles the Image rendering and save operations.
    """

    def __init__(self, app, canvas_gm, overlay_gm):
        """
        Initializer for the ImageProcessor
        Args:
            app: Main app
            canvas_gm: Base Canvas GraphicsProcessor
            overlay_gm: Overlay Canvas GraphicProcessor
        """
        self.app = app
        self.canvas_gm = canvas_gm
        self.overlay_gm = overlay_gm

        self.current_image = None
        self.canvas_image = None
        self.overlay_layer = None
        self.current_image_size = None
        self.prev_image_size = None
        try:
            self.font = ImageFont.truetype(font=os.path.join("fonts", "RobotoMono-Medium.ttf"), size=30)
        except:
            self.font = ImageFont.load_default()

    def render_images(self, batch: bool):
        """
        Renders the graphic annotations onto the images and saves the images in the specified folder.
        Args:
            batch (bool): True renders every image in queue, False renders the current image on display.

        Returns:
            bool: True on successful render of all images. Else False.

        """

        # OverlayCanvas is the tkinter.Canvas object for the global overlay elements.

        self.HIGHLIGHT_OPACITY = self.app.user_settings["highlight_opacity"]
        self.OVERLAY_IMAGE_INDEX = -2
        self.OVERLAY_GRAPHICS_INDEX = -1
        self.FONT_PATH = "fonts"
        self.data_dict = self.app.image_data
        self.graphics_data = self.app.graphics_data
        self.current_image_size = None
        self.prev_image_size = None

        include_blanks = self.app.include_blanks
        overlay_enabled = self.app.render_overlay
        trim_overlay = self.app.trim_overlay
        render_sequence_code = self.app.render_sequence_code
        sequence_code_position = self.app.sequence_code_render_position
        self.anti_alias = self.app.anti_alias_output
        jpeg_quality = self.app.jpeg_quality
        png_compression = self.app.png_compression
        output_path = self.app.output_path

        first_image_processed = False

        if self.anti_alias:
            self.FILM_RESIZE = 2
        else:
            self.FILM_RESIZE = 1

        if self.graphics_data[self.OVERLAY_GRAPHICS_INDEX]:  # Overlay 2d drawings index.
            has_2d_overlay = True
        else:
            has_2d_overlay = False

        if self.graphics_data[self.OVERLAY_IMAGE_INDEX]:  # Overlay image index
            has_image_overlay = True
        else:
            has_image_overlay = False

        # If nothing in the overlay canvas, set overlay to False.
        if not has_2d_overlay and not has_image_overlay:
            overlay_enabled = False

        if batch:  # If export mode is batch.

            indices_with_queue = []

            # Get the total images in queue
            for index, data in self.data_dict.items():
                if data.get("in_queue") == True:
                    indices_with_queue.append(index)  # saving the indexes of the images in queue
            total_images_in_queue = len(indices_with_queue)

            # total_images_in_queue = sum(1 for index,data in self.data_dict.items() if data.get("in_queue") is True)
            if not include_blanks:
                total_blanks = 0
                for key in indices_with_queue:
                    if not self.graphics_data[key]:
                        total_blanks += 1
                total_images_in_queue = total_images_in_queue - total_blanks

            total_range = (0, self.app.available_index + 1)

            if total_images_in_queue == 0:
                self.app.render_menu.update_progress_bar(progress=1, status=False)
                return False

        else:  # Render only the current image.
            total_images_in_queue = 1
            total_range = (self.app.image_index, self.app.image_index + 1)

        files_saved = 0  # For progress bar update.

        # Iterating through each of the images and redrawing the graphic elements.
        for image_index in range(*total_range):
            try:
                # If the image is queued or single image export.
                if self.data_dict[image_index]["in_queue"] or not batch:
                    # If no 2d drawings, but include blanks is checked.
                    if not self.graphics_data[image_index] and (include_blanks or not batch):
                        self.final_base_image = Image.open(self.app.images[image_index]).convert(mode="RGBA")

                    elif self.graphics_data[image_index]:  # if the current image has 2d drawings.
                        self.current_image = Image.open(self.app.images[image_index]).convert(mode="RGBA")

                        self.base_graphics_layer = Image.new("RGBA", (self.current_image.width * self.FILM_RESIZE,
                                                                      self.current_image.height * self.FILM_RESIZE),
                                                             (0, 0, 0, 0))

                        self.canvas_draw = ImageDraw.Draw(self.base_graphics_layer)

                        # ================Render Base Canvas==========================

                        # The graphic elements are drawn on a transparent blank film layer before finally pasting over the base image.

                        for id, cache in self.app.graphics_data[image_index].items():
                            # cache is the single graphic object.
                            self.current_cache = cache
                            # Draws the 2d elements on the image.
                            self.plot_graphic_element(layer="base")

                        # Resize the enlarged image to Normal size.
                        if self.anti_alias:
                            self.resized_base_graphics_layer = self.base_graphics_layer.resize(self.current_image.size,
                                                                                               resample=Image.LANCZOS)
                        else:  # not wasting time with useless resize
                            self.resized_base_graphics_layer = self.base_graphics_layer

                        # Final Annotated Base image
                        self.final_base_image = Image.alpha_composite(self.current_image,
                                                                      self.resized_base_graphics_layer)

                    else:
                        continue  # Skip the image.

                    self.current_image_size = self.final_base_image.size

                    # ================Render Overlay Canvas==========================
                    if overlay_enabled:
                        # if the previous image had the same resolution, reuse the currently made overlay.
                        if self.prev_image_size != self.current_image_size:
                            self.prepare_overlay_layer()

                            # Makes the transparent layer.
                            # Enlarge the image if anti_alias enabled.
                            if self.anti_alias:
                                self.overlay_layer = self.overlay_layer.resize(
                                    (self.overlay_layer.width * self.FILM_RESIZE,
                                     self.overlay_layer.height * self.FILM_RESIZE))
                                self.overlay_draw = ImageDraw.Draw(self.overlay_layer)

                            for id, cache in self.graphics_data[self.OVERLAY_GRAPHICS_INDEX].items():
                                # cache is the single graphic object.
                                self.current_cache = cache
                                # Draw overlay 2d items one by one.
                                self.plot_graphic_element(layer="overlay")

                            # Rescale overlay to image size.
                            if self.anti_alias:
                                self.overlay_layer = self.overlay_layer.resize(
                                    (self.overlay_layer.width // self.FILM_RESIZE,
                                     self.overlay_layer.height // self.FILM_RESIZE),
                                    resample=Image.LANCZOS)

                            # Images are pasted in after all the drawings has been made on the overlay layer.
                            if has_image_overlay:  # if current overlay canvas has image elements.
                                for id, image_cache in self.graphics_data[self.OVERLAY_IMAGE_INDEX].items():
                                    self.current_cache = image_cache
                                    # Draw overlay image items one by one.
                                    self.insert_overlay_image_element()
                        else:

                            pass

                        self.background_layer = Image.new("RGBA", (self.overlay_layer.width,
                                                                   self.overlay_layer.height), "white")

                        paste_position = ((self.overlay_layer.width - self.final_base_image.width) // 2,
                                          (self.overlay_layer.height - self.final_base_image.height) // 2)

                        # pasting the base image on a 16:9 backdrop
                        self.background_layer.paste(self.final_base_image, paste_position)
                        self.final_image = Image.alpha_composite(self.background_layer, self.overlay_layer)

                        # -----------Trim the Final Image to the original image size------------------
                        if trim_overlay:
                            original_width, original_height = self.final_image.size
                            target_width, target_height = self.final_base_image.size

                            # Calculate the coordinates for cropping from the center
                            left = (original_width - target_width) // 2
                            upper = (original_height - target_height) // 2
                            right = left + target_width
                            lower = upper + target_height
                            # crop the image
                            self.final_image = self.final_image.crop((left, upper, right, lower))

                    else:  # if no overlay save the base image.
                        self.final_image = self.final_base_image

                    # ============Imprint the Sequence code on the image=================
                    if render_sequence_code:
                        sequence_code = self.data_dict[image_index]['sequence_code']
                        if sequence_code:
                            sequence_code_image = self.generate_sequence_code_image(sequence_code=sequence_code)

                            if sequence_code_position == "ne":  # top right
                                paste_anchor = (self.final_image.width - sequence_code_image.width, 0)

                            elif sequence_code_position == "sw":  # bottom left
                                paste_anchor = (0, self.final_image.height - sequence_code_image.height)

                            elif sequence_code_position == "se":  # bottom right
                                paste_anchor = (self.final_image.width - sequence_code_image.width,
                                                self.final_image.height - sequence_code_image.height)
                            else:  # nw top corner
                                paste_anchor = (0, 0)

                            self.final_image.paste(sequence_code_image, paste_anchor)

                    # ================Save the rendered image==========================
                    filename = os.path.basename(self.data_dict[image_index]['file'])
                    output_location = f"{output_path}/{filename}"

                    try:
                        self.final_image.save(output_location, quality=jpeg_quality, compress_level=png_compression)
                    except OSError:  # incase image fails to save with alphas
                        self.final_image = self.final_image.convert("RGB")
                        self.final_image.save(output_location, quality=jpeg_quality, compress_level=png_compression)
                    finally:
                        files_saved += 1
                        progress = files_saved / total_images_in_queue  # 0 to 1 range
                        self.prev_image_size = self.current_image_size
                    try:
                        self.app.render_menu.update_progress_bar(progress=progress, status=True)
                    except:
                        return False

            except Exception:  # If any one of the image fails to save.
                return False

        return True

    def plot_graphic_element(self, layer: str):
        """
        Adjusts the values and calls the specified method to plot the graphic element to an image.
        Args:
            layer (str): If the overlay elements are being drawn then,"overlay". Else "base"

        Returns:

        """
        cache = self.current_cache

        if layer != "overlay":
            canvas = self.canvas_draw
            if cache.tool == 8:
                self.adjusted_coordinates = self.get_resized_coordinates(item="text")
                self.adjusted_font_size = abs(cache.font_size * self.FILM_RESIZE)
            else:
                self.adjusted_coordinates = self.get_resized_coordinates()
                self.adjusted_stroke_width = (round(cache.width) * self.FILM_RESIZE)

        else:
            canvas = self.overlay_draw
            if cache.tool == 8:
                self.adjusted_coordinates = self.get_values_for_overlay_layer_from_overlaycache(item="text")
                self.adjusted_font_size = abs(self.get_values_for_overlay_layer_from_overlaycache(item="font"))
            else:
                self.adjusted_coordinates = self.get_values_for_overlay_layer_from_overlaycache()
                self.adjusted_stroke_width = (round(self.get_values_for_overlay_layer_from_overlaycache(item="width")))

        if cache.tool == 2:  # Brush tool
            self.plot_brush_stroke(canvas)

        elif cache.tool == 4:  # Line tool
            self.plot_line(canvas)

        elif cache.tool == 5:  # rectangle tool
            self.plot_rectangle(canvas)

        elif cache.tool == 6:  # rectangle tool
            self.plot_oval(canvas)

        elif cache.tool == 8:  # Insert Text
            self.insert_text(canvas)

    def prepare_overlay_layer(self):
        """
        Prepares a transparent image in the 16:9 ratio for the graphic elements to be drawn onto.
        Returns:
            None

        """
        annotated_img_width, annotated_img_height = self.final_base_image.size

        canvas_width = 16 * annotated_img_height // 9
        canvas_height = annotated_img_height

        if canvas_width < annotated_img_width:
            canvas_width = annotated_img_width
            canvas_height = 9 * annotated_img_width // 16

        base_width = canvas_width  # *self.OVERLAY_RESIZE
        base_height = canvas_height  # *self.OVERLAY_RESIZE

        # Makes a new transparent image .
        self.overlay_layer = Image.new("RGBA", (base_width, base_height), (0, 0, 0, 0))
        self.overlay_draw = ImageDraw.Draw(self.overlay_layer)

    def insert_overlay_image_element(self):
        """
        Renders the overlay image element to the overlay cel layer.

        Returns:
            None

        """

        transparent_layer = Image.new("RGBA", (self.overlay_layer.width, self.overlay_layer.height), (0, 0, 0, 0))
        # self.overlay_draw = ImageDraw.Draw(transparent_layer)

        image_to_paste = self.current_cache.image_object.convert("RGBA")
        x, y = self.get_values_for_overlay_layer_from_overlaycache(item="image")
        # Converting from overlay canvas size to true image size.
        new_width, new_height = self.get_values_for_overlay_layer_from_overlaycache(coordinates=self.current_cache.size,
                                                                                    item="image")
        resized_image = image_to_paste.resize((round(new_width), round(new_height)))

        if (rotation_angle := self.current_cache.angle) not in (0, 360):
            resized_image = resized_image.rotate(rotation_angle, expand=True, resample=Image.BICUBIC)

        # Center anchoring the image.
        x_offset = x - (resized_image.width // 2)
        y_offset = y - (resized_image.height // 2)

        # Uses the alpha from the imported image as a mask.
        transparent_layer.paste(resized_image, (round(x_offset), round(y_offset)), )
        self.overlay_layer = Image.alpha_composite(self.overlay_layer, transparent_layer)

    def plot_brush_stroke(self, canvas):
        """
        Renders graphic elements plotted using the Brush tool onto the given canvas draw object.
        Args:
            canvas: PIL draw object.

        Returns:
            None

        """
        if self.current_cache.stipple:  # if Current line is a highlight, add transparency.
            fill_color = self.get_highlight_color()
        else:
            fill_color = self.current_cache.fill_color

        self.round_cap(fill_color=fill_color, canvas=canvas)
        canvas.line(self.adjusted_coordinates, fill=fill_color, width=int(self.adjusted_stroke_width), joint="curve")

    def plot_line(self, canvas):
        """
        Renders graphic elements plotted using the Line tool onto the given canvas draw object.
        Args:
            canvas: PIL draw object.

        Returns:
            None

        """
        if self.current_cache.stipple:  # Current line is a highlight
            fill_color = self.get_highlight_color()
        else:
            fill_color = self.current_cache.fill_color

        if self.current_cache.capstyle == "round":
            # Caps the ends
            self.round_cap(fill_color=fill_color, canvas=canvas)

        canvas.line(self.adjusted_coordinates, fill=fill_color, width=self.adjusted_stroke_width)

    def plot_rectangle(self, canvas):
        """
        Renders graphic elements plotted using the Rectangle tool onto the given canvas draw object.
        Args:
            canvas: PIL draw object.

        Returns:
            None

        """
        fill_color = self.current_cache.fill_color
        x1, y1 = self.adjusted_coordinates[0]
        x2, y2 = self.adjusted_coordinates[1]

        # making coordinates Pillow compatible
        if x1 > x2:
            x = x1
            x1 = x2
            x2 = x
        if y1 > y2:
            y = y1
            y1 = y2
            y2 = y

        if self.current_cache.interior_fill_color:  # rectangle is solid filled.
            width = 0
            if self.current_cache.stipple:  # Current line is a highlight
                fill_color = self.get_highlight_color()
            canvas.rectangle((x1, y1, x2, y2), fill=fill_color)
        else:  # rectangle has only outline.
            width = self.adjusted_stroke_width
            # Outline in pillow works differently so pushing it to the center
            canvas.rectangle((x1 - width / 2, y1 - width / 2, x2 + width / 2, y2 + width / 2), width=width,
                             outline=fill_color)

    def plot_oval(self, canvas):
        """
        Renders graphic elements plotted using the Oval tool onto the given canvas draw object.
        Args:
            canvas: PIL draw object.

        Returns:
            None

        """
        fill_color = self.current_cache.fill_color
        x1, y1 = self.adjusted_coordinates[0]
        x2, y2 = self.adjusted_coordinates[1]
        # making coordinates Pillow compatible
        if x1 > x2:
            x = x1
            x1 = x2
            x2 = x
        if y1 > y2:
            y = y1
            y1 = y2
            y2 = y

        if self.current_cache.interior_fill_color:  # rectangle is solid filled.
            width = 0
            if self.current_cache.stipple:  # Current line is a highlight
                fill_color = self.get_highlight_color()
            canvas.ellipse((x1, y1, x2, y2), fill=fill_color)
        else:  # rectangle has only outline.
            width = self.adjusted_stroke_width
            # Outline in pillow works differently so pushing it inside
            canvas.ellipse((x1 - width / 2, y1 - width / 2, x2 + width / 2, y2 + width / 2), width=width,
                           outline=fill_color)

    def insert_text(self, canvas):
        """
        Renders graphic elements plotted using the Text tool onto the given canvas draw object.
        Args:
            canvas: PIL draw object.

        Returns:
             None

        """

        if self.current_cache.stipple:  # Current line is a highlight
            fill_color = self.get_highlight_color()
        else:
            fill_color = self.current_cache.fill_color

        font_path = os.path.join(self.FONT_PATH, self.current_cache.font_file)
        font = ImageFont.truetype(font_path, int(self.adjusted_font_size))

        # Pillow does not use the same anchor,as tkinter and if using left descender("ld") ("sw") some fonts are misaligned.
        # So finding the descent value to get the baseline value of the font. then using that baseline value as an anchor fixes the issue.
        try:
            tk_font = Font(family=self.current_cache.font_name,
                           size=-int(self.adjusted_font_size))  # -ve to match tkinter.
            tk_font_info = tk_font.metrics()
            descent = tk_font_info["descent"]
        except Exception as e:
            self.app.error_prompt.display_error_prompt(error_msg=f'failed to render,"{self.current_cache.text}"')
            return

        # Subtracting the descent value to get the baseline value.
        canvas.text((self.adjusted_coordinates[0], self.adjusted_coordinates[1] - descent), self.current_cache.text,
                    font=font,
                    fill=fill_color, anchor="ls")  # Left Baseline,

    def round_cap(self, fill_color, canvas):
        """
        Uses the start and end coordinate of a segment to draw two circles to generate round tips.
        Args:
            fill_color: Hex color code.
            canvas: PIL draw object.

        Returns:

        """

        start_point = self.adjusted_coordinates[0]
        end_point = self.adjusted_coordinates[-1]
        circle_radius = (math.ceil(self.adjusted_stroke_width / 2)) - 1
        canvas.ellipse([start_point[0] - circle_radius, start_point[1] - circle_radius,
                        start_point[0] + circle_radius, start_point[1] + circle_radius], fill=fill_color)

        canvas.ellipse([end_point[0] - circle_radius, end_point[1] - circle_radius,
                        end_point[0] + circle_radius, end_point[1] + circle_radius], fill=fill_color)

    def get_highlight_color(self):
        """
        Adds 50% transparency to the current fill_color to emulate highlight color
        Returns:
            str: Hex color

        """
        color_rgb = tuple(int(self.current_cache.fill_color[i:i + 2], 16) for i in (1, 3, 5))
        opacity_value = int((self.HIGHLIGHT_OPACITY / 100) * 255)
        fill_color = color_rgb + (opacity_value,)
        return fill_color

    def get_resized_coordinates(self, item=None):
        """
        Scales the coordinates to match the size of the transparent film layer in which the images are being drawn on.
        Args:
            item (str,optional): "text" in the item is text.

        Returns:
            (list|tuple): Scaled coordinates matching the enlarged film layer size.

        """

        if item == "text":
            try:
                x, y = (coordinate * self.FILM_RESIZE for coordinate in self.current_cache.coordinates)
            except ValueError:
                x, y = (coordinate * self.FILM_RESIZE for coordinate in self.current_cache.coordinates[0])
            return (x, y)

        scaled_coordinates = [((x * self.FILM_RESIZE), (y * self.FILM_RESIZE)) for x, y in
                              self.current_cache.coordinates]
        return scaled_coordinates

    def get_values_for_overlay_layer_from_overlaycache(self, coordinates=None, item=None):
        """
        Resize element values to whatever size the current overlay film layer is at.(including scaled up for antialiasing)
        Args:
            coordinates (list|tuple): Coordinates to be scaled to match the current overlay size.
            item (str,optional) : "font", "image", "text", "width"

        Returns:
            Scaled coordinates matching the current overlay film size.

        """

        if coordinates == None:
            coordinates = self.current_cache.coordinates
        else:
            coordinates = coordinates
        # convert cords from 1920 to image size

        # xlarge image since antialias
        new_width, new_height = self.overlay_layer.width, self.overlay_layer.height
        old_width, old_height = self.overlay_gm.OVERLAY_WIDTH, self.overlay_gm.OVERLAY_HEIGHT

        scale_x = new_width / old_width
        scale_y = new_height / old_height

        scale_factor = max(scale_x, scale_y)

        if item == "text" or item == "image":
            try:
                x, y = (coordinate * scale_factor for coordinate in coordinates)
            except ValueError:
                x, y = (coordinate * scale_factor for coordinate in coordinates[0])

            return (x, y)

        elif item == "font":
            new_font_size = self.current_cache.font_size * scale_factor
            return int(new_font_size)

        elif item == "width":
            new_width = self.current_cache.width * scale_factor
            return new_width

        scaled_coordinates = [((x * scale_factor), (y * scale_factor))
                              for x, y in coordinates]

        return scaled_coordinates

    def generate_sequence_code_image(self, sequence_code):
        """
        Generates an image from the sequence code.

        Returns:
            An RGB Image with the sequence code

        """
        final_image_width, final_image_height = self.final_image.size
        backdrop_width = int((10 / 100) * final_image_width)
        backdrop_height = int((35 / 100) * backdrop_width)

        sequence_code_img = Image.new("RGB", (backdrop_width, backdrop_height), color="black")
        drawobj = ImageDraw.Draw(sequence_code_img)

        font_size = int(backdrop_height / 2)

        self.font = ImageFont.truetype(font=os.path.join("fonts", "RobotoMono-Medium.ttf"), size=font_size)

        text_width = drawobj.textlength(sequence_code, font=self.font)
        text_height = font_size
        text_position = (int(backdrop_width - text_width) / 2), (int(backdrop_height - text_height) / 2.3)

        drawobj.text((text_position), sequence_code, fill=(255, 255, 255), font=self.font)

        return sequence_code_img
