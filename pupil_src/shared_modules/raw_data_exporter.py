"""
(*)~---------------------------------------------------------------------------
Pupil - eye tracking platform
Copyright (C) Pupil Labs

Distributed under the terms of the GNU
Lesser General Public License (LGPL v3.0).
See COPYING and COPYING.LESSER for license details.
---------------------------------------------------------------------------~(*)
"""
import abc
import csv
import logging
import os
import typing

import csv_utils
import player_methods as pm
from plugin import Plugin
from pyglui import ui
from rich.progress import track

# logging
logger = logging.getLogger(__name__)


class Raw_Data_Exporter(Plugin):
    """
    gaze_positions.csv
    keys:
        timestamp - timestamp of the source image frame
        index - associated_frame: closest world video frame
        norm_pos_x - x position in the world image frame in normalized coordinates
        norm_pos_y - y position in the world image frame in normalized coordinates
    """

    icon_chr = chr(0xE873)
    icon_font = "pupil_icons"

    def __init__(
        self,
        g_pool,
        should_export_field_info=True,
        should_export_gaze_positions=True,
    ):
        super().__init__(g_pool)

        self.should_export_field_info = should_export_field_info
        self.should_export_gaze_positions = should_export_gaze_positions

    def get_init_dict(self):
        return {
            "should_export_field_info": self.should_export_field_info,
            "should_export_gaze_positions": self.should_export_gaze_positions,
        }

    def init_ui(self):
        self.add_menu()
        self.menu.label = "Raw Data Exporter"
        self.menu.append(ui.Info_Text("Export Raw Neon data into .csv files."))
        self.menu.append(
            ui.Info_Text(
                "Select your export frame range using the trim marks in the seek bar. This will affect all exporting plugins."
            )
        )

        self.menu.append(
            ui.Switch(
                "should_export_field_info",
                self,
                label="Export Pupil Gaze Positions Info",
            )
        )
        self.menu.append(
            ui.Switch(
                "should_export_gaze_positions", self, label="Export Gaze Positions"
            )
        )
        self.menu.append(
            ui.Info_Text("Press the export button or type 'e' to start the export.")
        )

    def deinit_ui(self):
        self.remove_menu()

    def on_notify(self, notification):
        if notification["subject"] == "should_export":
            self.export_data(notification["ts_window"], notification["export_dir"])

    def export_data(self, export_window, export_dir):
        if self.should_export_gaze_positions:
            gaze_positions_exporter = Gaze_Positions_Exporter()
            gaze_positions_exporter.csv_export_write(
                positions_bisector=self.g_pool.gaze_positions,
                timestamps=self.g_pool.timestamps,
                export_window=export_window,
                export_dir=export_dir,
            )

        if self.should_export_field_info:
            field_info_name = "pupil_gaze_positions_info.txt"
            field_info_path = os.path.join(export_dir, field_info_name)
            with open(field_info_path, "w", encoding="utf-8", newline="") as info_file:
                info_file.write(self.__doc__)


class _Base_Positions_Exporter(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def csv_export_filename(cls) -> str:
        pass

    @classmethod
    @abc.abstractmethod
    def csv_export_labels(cls) -> typing.Tuple[csv_utils.CSV_EXPORT_LABEL_TYPE, ...]:
        pass

    @classmethod
    @abc.abstractmethod
    def dict_export(
        cls, raw_value: csv_utils.CSV_EXPORT_RAW_TYPE, world_index: int
    ) -> dict:
        pass

    def csv_export_write(
        self,
        positions_bisector,
        timestamps,
        export_window,
        export_dir,
    ):
        export_file = type(self).csv_export_filename()
        export_path = os.path.join(export_dir, export_file)

        export_section = positions_bisector.init_dict_for_window(export_window)
        export_world_idc = pm.find_closest(timestamps, export_section["data_ts"])

        with open(export_path, "w", encoding="utf-8", newline="") as csvfile:
            csv_header = type(self).csv_export_labels()
            dict_writer = csv.DictWriter(csvfile, fieldnames=csv_header)
            dict_writer.writeheader()

            for g, idx in track(
                zip(export_section["data"], export_world_idc),
                description=f"Exporting {export_file}",
                total=len(export_world_idc),
            ):
                dict_row = type(self).dict_export(raw_value=g, world_index=idx)
                dict_writer.writerow(dict_row)

        logger.info(f"Created '{export_file}' file.")


class Gaze_Positions_Exporter(_Base_Positions_Exporter):
    @classmethod
    def csv_export_filename(cls) -> str:
        return "gaze_positions.csv"

    @classmethod
    def csv_export_labels(cls) -> typing.Tuple[csv_utils.CSV_EXPORT_LABEL_TYPE, ...]:
        return (
            "gaze_timestamp",
            "world_index",
            "norm_pos_x",
            "norm_pos_y"
        )

    @classmethod
    def dict_export(
        cls, raw_value: csv_utils.CSV_EXPORT_RAW_TYPE, world_index: int
    ) -> dict:
        gaze_timestamp = str(raw_value["timestamp"])
        norm_pos = raw_value["norm_pos"]

        return {
            "gaze_timestamp": gaze_timestamp,
            "world_index": world_index,
            "norm_pos_x": norm_pos[0],
            "norm_pos_y": norm_pos[1],
        }
