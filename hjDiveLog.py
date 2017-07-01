#!/usr/bin/env python

import sys
from PyQt4 import QtGui
from PyQt4 import QtCore
import pyqtgraph as pg
import numpy as np
import pandas as pd
import math


def est_profile(t1, d1):
    # calc ascent and descent times
    t_per_m_desc = 1.0 / 30.0  # 30m per min descent rate
    t_per_m_asc = 1.0 / 15.0  # 15m per min to 6m
    t_per_m_asc_6 = 1.0 / 6  # 6m per min above 6m
    safety2surf = 1
    stop_t = 3
    desc_1_time = t_per_m_desc * d1
    asc_1_time2safety = t_per_m_asc * (d1 - 6)
    d1_bt = t1 - desc_1_time - asc_1_time2safety - safety2surf - stop_t

    # profile
    x = [0, desc_1_time, d1_bt, asc_1_time2safety, stop_t, safety2surf]
    y = [0, -d1, -d1, -6, -6, 0]

    x_cum = np.cumsum(x)

    return x_cum, y


def depth2pressure(dep):
    return dep/10.0 + 1


def time_2_min(time):
    hours, mins = [int(x) for x in time.split(':')]
    return float((hours * 60) + mins)


def min_2_time(minutes):
    no_hours = int(minutes) / 60
    mins = minutes - (no_hours * 60)

    time = '{:0>2}:{:0>2}'.format(no_hours, int(mins))

    return time


def calc_sac(start_p, end_p, vol, depth, t):
    t = time_2_min(t)
    vol_gas_used = (start_p - end_p) * vol
    l_per_min_atdepth = vol_gas_used / t
    sac = l_per_min_atdepth / depth2pressure(depth)
    return round(sac, 1)


def make_data_frame():

    csv_data = 'dive_data.csv'
    dd = pd.read_csv(csv_data, index_col='num')
    dd['SAC_rate'] = dd.apply(lambda x: calc_sac(x.start_pres, x.end_pres, x.volume, x.max_depth, x.duration), axis=1)
    dd['profile'] = dd.apply(lambda x: est_profile(time_2_min(x.duration), x.max_depth), axis=1)
    return dd


class HistoryWindow(QtGui.QWidget):
    def __init__(self, dive_data_frame, parent=None):
        super(HistoryWindow, self).__init__(parent)

        # set stats
        self.dive_data_frame = dive_data_frame
        no_dives = str(len(dive_data_frame.index))
        average_len = str(min_2_time(np.average([time_2_min(x) for x in dive_data_frame.duration])))
        total_hours = str(min_2_time(np.sum([time_2_min(x) for x in dive_data_frame.duration])))
        mean_sac = str(round(np.average([x for x in dive_data_frame.SAC_rate if not math.isnan(x)]), 1))

        # Dives to date: Time to date: Average dive time: mean SAC rate:
        labels = ['Dives to date:', 'Average dive length:', 'Hours to date:', 'mean SAC rate:']
        values = [no_dives, average_len, total_hours, mean_sac]

        grid = QtGui.QGridLayout()

        row, column = 0, 0

        for i in range(len(labels)):
            lab, val = labels[i], values[i]

            qt_lab = QtGui.QLabel(lab, self)
            qt_val = QtGui.QLabel(val, self)

            grid.addWidget(qt_lab, row, column)
            grid.addWidget(qt_val, row, column + 1)

            if row == 1:
                row = 0
                column += 2
            else:
                row += 1

        # plot selection
        selection_layout = QtGui.QHBoxLayout()
        sum_lab = QtGui.QLabel('Summarise: ')

        plot_options = QtGui.QComboBox()
        plot_types = ['depth', 'duration', 'SAC_rate']
        for o in plot_types:
            plot_options.addItem(o)

        QtGui.QComboBox.connect(plot_options, QtCore.SIGNAL('activated(const QString&)'), self.change_plot)

        selection_layout.addWidget(sum_lab)
        selection_layout.addWidget(plot_options)
        selection_layout.addStretch()

        # plot
        # invert default background foreground
        pg.setConfigOption('background', 0.89)
        pg.setConfigOption('foreground', 'k')
        self.sum_plot = pg.PlotWidget()
        self.change_plot('depth')

        # add all to layout
        his_layout = QtGui.QVBoxLayout()
        his_layout.addLayout(grid)
        his_layout.addLayout(selection_layout)
        his_layout.addWidget(self.sum_plot)

        self.setLayout(his_layout)

    def change_plot(self, text):
        plot_pen = pg.mkPen('b', width=2)

        if text == 'depth':
            self.sum_plot.plotItem.clear()
            vals = self.dive_data_frame.max_depth.asobject
            y, x = np.histogram(vals, bins=30)

            # We are required to use stepMode=True so that PlotCurveItem will interpret this data correctly.
            curve = pg.PlotCurveItem(x, y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 150))
            self.sum_plot.addItem(curve)

        elif text == 'duration':
            self.sum_plot.plotItem.clear()
            vals = [time_2_min(t) for t in self.dive_data_frame.duration.asobject]
            y, x = np.histogram(vals, bins=30)

            # We are required to use stepMode=True so that PlotCurveItem will interpret this data correctly.
            curve = pg.PlotCurveItem(x, y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 150))
            self.sum_plot.addItem(curve)

        else:
            self.sum_plot.plotItem.clear()
            y = self.dive_data_frame.SAC_rate.asobject
            x = self.dive_data_frame.index

            x_y = [z for z in zip(x, y) if not math.isnan(z[1])]

            clean_x = [c[0] for c in x_y]
            clean_y = [c[1] for c in x_y]

            line = np.polynomial.polynomial.polyfit(clean_x, clean_y, 1)
            ffit = np.polynomial.polynomial.polyval(clean_x, line)
            self.sum_plot.plot(clean_x, ffit, pen=plot_pen)
            self.sum_plot.plot(x, y, pen=None, symbol='t',
                               symbolPen=None, symbolSize=10,
                               symbolBrush=(100, 100, 255, 150))


class DiveWindow(QtGui.QWidget):
    def __init__(self, dive_record, parent=None):

        """
        creates a QTabWidget
        :param dive_record: dict
        :param parent:
        """
        super(DiveWindow, self).__init__(parent)

        dw_layout = QtGui.QVBoxLayout()

        # invert default background foreground
        pg.setConfigOption('background', 0.85)
        pg.setConfigOption('foreground', 'k')

        # top row of stat boxes
        top_boxes = QtGui.QHBoxLayout()
        top_boxes.addWidget(self.dive_stats_box(dive_record))
        top_boxes.addWidget(self.gas_stats_box(dive_record))

        # notes box
        dive_notes = self.notes_box(str(dive_record['notes'].asobject[0]))

        # add everything to main layout
        dw_layout.addLayout(top_boxes)
        dw_layout.addWidget(self.profile_box(dive_record['profile'].asobject[0]))
        dw_layout.addWidget(dive_notes)
        self.setLayout(dw_layout)

    def dive_stats_box(self, record):

        labels = ['time_in', 'duration', 'time_out', 'max_depth', 'avg_depth', 'temp']
        values = [str(record[x].asobject[0]) for x in labels]

        dive_box = self.stats_box(labels, values, 'Dive stats', 3)

        return dive_box

    def gas_stats_box(self, record):

        labels = ['start_pres', 'end_pres', 'volume', 'SAC_rate']
        values = [str(record[x].asobject[0]) for x in labels]

        gas_box = self.stats_box(labels, values, 'Gas stats', 2)

        return gas_box

    def stats_box(self, labels, values, title, no_rows):

        grid = QtGui.QGridLayout()

        row, column = 0, 0
        rows_per_box = no_rows

        for i in range(len(labels)):
            lab, val = labels[i].replace('_', ' ') + ':', values[i]

            qt_lab = QtGui.QLabel(lab, self)
            qt_val = QtGui.QLabel(val, self)

            grid.addWidget(qt_lab, row, column)
            grid.addWidget(qt_val, row, column + 1)

            if row == rows_per_box - 1:
                row = 0
                column += 2
            else:
                row += 1

        stats_box = QtGui.QGroupBox(title)
        stats_box.setLayout(grid)

        return stats_box

    def profile_box(self, profile):

        box = QtGui.QGroupBox('Dive profile')
        prof_layout = QtGui.QVBoxLayout()
        plot_pen = pg.mkPen('b', width=2)
        profile_plot = pg.PlotWidget()
        profile_plot.setLabel('left', 'Depth', 'm')
        profile_plot.setLabel('bottom', 'Time', 'mins')
        profile_plot.plot(profile[0], profile[1], pen=plot_pen)
        prof_layout.addWidget(profile_plot)

        box.setLayout(prof_layout)

        return box

    def notes_box(self, note_text):

        note_layout = QtGui.QVBoxLayout()
        notes = QtGui.QTextEdit()
        notes.setText(note_text)
        notes.setReadOnly(True)
        note_layout.addWidget(notes)

        box = QtGui.QGroupBox('Notes')
        box.setLayout(note_layout)

        return box


class Window(QtGui.QMainWindow):

    def __init__(self):
        super(Window, self).__init__()
        self.setGeometry(100, 100, 1050, 700)  # coords start from top left x, y, width, height
        self.setWindowTitle('hjDiveLog')

        # test data
        self.dive_data = make_data_frame()

        # # set toolbar
        # toolbar = QtGui.QToolBar(self)
        # exit_planner = QtGui.QAction(QtGui.QIcon('images/exit.png'), 'exit', self)
        # exit_planner.setShortcut('Ctrl+Q')
        # QtGui.QAction.connect(exit_planner, QtCore.SIGNAL('triggered()'), self.quit_app)
        # toolbar.addAction(exit_planner)
        # self.addToolBar(QtCore.Qt.TopToolBarArea, toolbar)

        # fonts
        self.header_font = QtGui.QFont('SansSerif', 16)
        self.header_font.setBold(True)
        self.main_font = QtGui.QFont('SansSerif', 16)
        self.options_font = QtGui.QFont('Arial', 14)
        self.param_palette = QtGui.QPalette()
        self.param_palette.setColor(QtGui.QPalette.Foreground, QtCore.Qt.blue)

        # start main layout
        whole_layout = QtGui.QHBoxLayout()

        # left dive add / select column
        left_box = QtGui.QGroupBox('Dive selection')
        left_box.setFixedWidth(300)

        sw_layout = QtGui.QVBoxLayout()

        # bottom buttons
        btn_layout = QtGui.QHBoxLayout()
        add_dive_btn = QtGui.QPushButton('+')
        btn_layout.addWidget(add_dive_btn)
        btn_layout.addStretch()

        # make and populate list
        self.selection_pane = QtGui.QListWidget()
        for dive in self.dive_data.index:
            label = str(dive) + ' - ' + self.dive_data[dive-1: dive].date.asobject[0]
            dive_entry = QtGui.QListWidgetItem(label)
            self.selection_pane.addItem(dive_entry)

        self.selection_pane.itemDoubleClicked.connect(self.open_tab)
        self.selection_pane.currentItemChanged.connect(self.reload_tab)

        sw_layout.addWidget(self.selection_pane)
        sw_layout.addLayout(btn_layout)

        left_box.setLayout(sw_layout)

        # main dive info window
        log_windows = QtGui.QVBoxLayout()

        self.tabs_open = set()
        self.dive_tabs = QtGui.QTabWidget()
        self.dive_tabs.sum_tab = HistoryWindow(self.dive_data)
        self.dive_tabs.addTab(self.dive_tabs.sum_tab, "History")

        # self.dive_tabs.dive_view = QtGui.QWidget()
        # self.dive_tabs.addTab(self.dive_tabs.dive_view, 'Dive view')

        # self.dive_tabs.setTabsClosable(True)

        self.dive_tabs.tabCloseRequested.connect(self.close_tab)
        log_windows.addWidget(self.dive_tabs)

        whole_layout.addWidget(left_box)
        whole_layout.addLayout(log_windows)

        main_widget = QtGui.QWidget()
        main_widget.setLayout(whole_layout)
        self.setCentralWidget(main_widget)
        self.show()

    def open_tab(self, item):
        item_text = str(item.text())
        panda_index = int(item_text.split(' - ')[0])
        record = self.dive_data[panda_index-1:panda_index]

        if item_text not in self.tabs_open:
            self.dive_tabs.tab = DiveWindow(record)
            self.dive_tabs.addTab(self.dive_tabs.tab, item_text)
            self.dive_tabs.setCurrentWidget(self.dive_tabs.tab)
            self.tabs_open |= {item_text}

        else:
            pass

    def close_tab(self, currentIndex):

        item_text = str(self.dive_tabs.tabText(currentIndex))
        current_tab = self.dive_tabs.widget(currentIndex)
        current_tab.deleteLater()
        self.dive_tabs.removeTab(currentIndex)
        self.tabs_open.remove(item_text)

    def reload_tab(self, item):

        item_text = str(item.text())
        panda_index = int(item_text.split(' - ')[0])
        record = self.dive_data[panda_index - 1:panda_index]
        self.dive_tabs.removeTab(1)
        self.dive_tabs.dive_view = DiveWindow(record)
        self.dive_tabs.addTab(self.dive_tabs.dive_view, 'Dive view')
        self.dive_tabs.setCurrentWidget(self.dive_tabs.dive_view)

    def quit_app(self):

        choice = QtGui.QMessageBox.question(self, 'Exit', 'Exit the application?',
                                            QtGui.QMessageBox.No | QtGui.QMessageBox.Yes)

        if choice == QtGui.QMessageBox.Yes:
            sys.exit()

        else:
            pass


def main():
    app = QtGui.QApplication(sys.argv)
    ex = Window()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
