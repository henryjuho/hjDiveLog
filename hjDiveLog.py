#!/usr/bin/env python

import sys
from PyQt4 import QtGui
from PyQt4 import QtCore
import pyqtgraph as pg
import numpy as np
import pandas as pd


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
        pg.setConfigOption('background', 'w')
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

        profile_plot = pg.PlotWidget()
        profile_plot.setLabel('left', 'Depth', 'm')
        profile_plot.setLabel('bottom', 'Time', 'mins')
        profile_plot.plot(profile[0], profile[1])
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

        # set toolbar
        toolbar = QtGui.QToolBar(self)
        exit_planner = QtGui.QAction(QtGui.QIcon('images/exit.png'), 'exit', self)
        exit_planner.setShortcut('Ctrl+Q')
        QtGui.QAction.connect(exit_planner, QtCore.SIGNAL('triggered()'), self.quit_app)
        toolbar.addAction(exit_planner)
        self.addToolBar(QtCore.Qt.TopToolBarArea, toolbar)

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
        selection_pane = QtGui.QListWidget()
        for dive in self.dive_data.index:
            label = str(dive) + ' - ' + self.dive_data[dive-1: dive].date.asobject[0]
            dive_entry = QtGui.QListWidgetItem(label)
            selection_pane.addItem(dive_entry)

        selection_pane.itemDoubleClicked.connect(self.open_tab)

        sw_layout.addWidget(selection_pane)
        sw_layout.addLayout(btn_layout)

        left_box.setLayout(sw_layout)

        # main dive info window
        log_windows = QtGui.QVBoxLayout()

        self.tabs_open = set()
        self.dive_tabs = QtGui.QTabWidget()
        self.dive_tabs.tab2 = QtGui.QWidget()

        self.dive_tabs.addTab(self.dive_tabs.tab2, "Tab 2")

        self.dive_tabs.setTabsClosable(True)

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
