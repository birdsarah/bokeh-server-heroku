from bokeh.models import ColumnDataSource
from bokeh.properties import Instance
from bokeh.models.widgets import Slider, VBox

# update_active_data and get_frame_for_country are exact copies of
# methods used in client app (under map_data.py)

from numpy import where
WATER_COLOR_RANGE = ["#8c9494", "#8398a2", "#7c9baa", "#73a1b4", "#6aa6bd", "#62abc7", "#5aafd0", "#52b4d9", "#49bae4", "#3fc0f0"]  # nopep8
SANITATION_COLOR_RANGE = ["#d45500", "#da670f", "#eb7e1f", "#eb941f", "#ebb01f", "#f2c83d", "#d3cc4f", "#86c26f", "#4db181", "#15b598"]  # nopep8
GRAY = "#CCCCCC"


def update_active_data(data, active_year, palette_name=None):
    # Default to water
    palette = WATER_COLOR_RANGE
    if palette_name == 'sanitation':
        palette = SANITATION_COLOR_RANGE

    def _get_color(value):
        if value < 0:
            return GRAY
        index = int(value / 10)
        return palette[index]

    data['active_year'] = active_year
    data['active_year_value'] = data[active_year]
    data['color_for_active_year'] = data[active_year].apply(_get_color)
    data['active_year_value'] = where(data['active_year_value'] < 0, '-', data['active_year_value'])  # nopep8
    return data


def get_frame_for_country(frame, country):
    return frame[frame.name == country]


class WashmapApp(VBox):
    year = Instance(Slider)

    wat_source = Instance(ColumnDataSource)
    san_source = Instance(ColumnDataSource)
    wat_source_single = Instance(ColumnDataSource)
    san_source_single = Instance(ColumnDataSource)

    def setup_events(self):
        self.year.on_change('value', self, 'change_year')

    def _get_df_for_country(self, frame, country):
        return frame[frame.name == country]

    def get_dfs(self):
        wat_data = self.wat_source.to_df()
        san_data = self.san_source.to_df()
        return wat_data, san_data

    def get_single_dfs(self, wat_data, san_data, country):
        wat_data_single = get_frame_for_country(wat_data, country)
        san_data_single = get_frame_for_country(san_data, country)
        return wat_data_single, san_data_single

    def change_year(self, obj, attrname, old, new):
        wat_df, san_df = self.get_dfs()
        year = str(self.year.value)
        wat_data = update_active_data(wat_df, year, palette_name='water')
        san_data = update_active_data(san_df, year, palette_name='sanitation')
        self.wat_source.data = ColumnDataSource(wat_data).data
        self.san_source.data = ColumnDataSource(san_data).data
