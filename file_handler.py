from PIL import Image
import re
import pickle
import json


class FileHandler:
    """
    Class container for static methods responsible for file load and validate operations.
    """

    @staticmethod
    def validate_image(image: str):
        """
       Checks if the image files are supported.

       Args:
          image (str): Path to the image file.

       Returns:
               bool: True on file validation. Else False.
       """
        try:
            with Image.open(image) as img:
                return True
        except Exception:
            return False

    @staticmethod
    def validate_project_file(project_file_path):
        """
        Checks if the project json file matches the format of the app.

        Args:
            project_file_path (str): Path to the project file.

        Returns:
                bool: True on file validation.Else False.
        """

        try:
            with open(project_file_path, 'rb') as file:
                loaded_object = pickle.load(file)
        except Exception as e:

            return False
        else:
            return True

    @staticmethod
    def get_sequence_code(filename, sequence_search):
        """
        Extract the sequence code from the filename.

        Args:
            filename (str): File name.
            sequence_search(str): Which sequence to look for. Default is "auto".

        Returns:
                str|None: Sequence if available. Else None.
        """

        def is_normal_sequence(filename):
            pattern = re.compile(r'\D(0*\d+)(?=\D*$)')
            matches = pattern.search(filename)
            #
            if matches:
                return (matches.group(1))
            else:
                return None

        def is_potplayer_screenshot(filename):
            # Define a regular expression pattern to match the timestamp for any extension
            pot_player_pattern = re.compile(r'_(\d{6})\.(\d{3})\..+')
            match = pot_player_pattern.search(filename)
            if match:
                milliseconds, microseconds = match.groups()
                elapsed_time = f"{int(milliseconds[:2]):02d}:{int(milliseconds[2:4]):02d}:{int(milliseconds[4:]):02d}"
                return elapsed_time
            else:
                return

        def is_vlc_screenshot(filename):
            vlc_pattern = re.compile(r'-(\d{2})_(\d{2})_(\d{2})')
            # Use the pattern to extract the timestamp components
            match = vlc_pattern.search(filename)

            if match:
                hours, minutes, seconds = match.groups()
                elapsed_time = f"{hours}:{minutes}:{seconds}"
                return elapsed_time
            else:
                return

        if sequence_search == "auto":
            result_vlc = is_vlc_screenshot(filename)
            if result_vlc is not None:
                # print(result_vlc)
                return result_vlc

            result_potplayer = is_potplayer_screenshot(filename)
            if result_potplayer is not None:
                # print(result_potplayer)
                return result_potplayer

            result_normal = is_normal_sequence(filename)
            if result_normal is not None:
                # print(result_normal)
                return result_normal

            return None

        elif sequence_search == "normal":
            result_normal = is_normal_sequence(filename)
            if result_normal is not None:
                return result_normal
            else:
                return None

        elif sequence_search == "pot":  # if the image file was screen capped using potplayer.
            result_potplayer = is_potplayer_screenshot(filename)
            if result_potplayer is not None:
                return result_potplayer
            else:
                return None

        elif sequence_search == "vlc":  # if the image file was screen capped using VLC.
            result_vlc = is_vlc_screenshot(filename)
            if result_vlc is not None:
                return result_vlc
            else:
                return None

    @staticmethod
    def load_project_file(file_path):
        """
        Loads the project rvp file.

        Args:
            file_path (str): File path to the rvp project file.

        Returns:
                dict|bool: Returns the Dictionary from the project file on loading the rvp File.Else False.
        """
        try:
            with open(file_path, 'rb') as file:
                data: dict = pickle.load(file)
                return data
        except:
            return False

    @staticmethod
    def save_project_file(project_data: dict, output_path: str):
        """
        Saves the project dictionary as a .rvp (pickle) file.
        Args:
            project_data (dict): Dictionary containing the project data.
            output_path (str): Output path to save the project file.

        Returns:
            True if saved successfully, else False.

        """
        try:
            with open(output_path, 'wb') as file:
                pickle.dump(project_data, file)
        except:
            return False
        else:
            return True

    @staticmethod
    def validate_user_settings_file(json_data):
        """
        Validates the user settings json file by checking keys and value types.
        Args:
            json_data: Json file containing the user settings.

        Returns:
            bool: True on Validation, False on fail.

        """
        try:
            parsed_data = json_data

            # Check if it has the expected structure
            if isinstance(parsed_data, dict) and \
                    "canvas_color" in parsed_data and \
                    "selection_color" in parsed_data and \
                    "highlight_opacity" in parsed_data:

                # Checking value types.
                if isinstance(parsed_data["canvas_color"], str) and \
                        isinstance(parsed_data["selection_color"], str) and \
                        isinstance(parsed_data["highlight_opacity"], (int, float)):
                    return True
                else:
                    return False
            else:
                return False

        except json.JSONDecodeError:
            return False
