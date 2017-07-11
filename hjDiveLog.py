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

    # profile
    if d1 >= 6:
        asc_1_time2safety = t_per_m_asc * (d1 - 6)
        d1_bt = t1 - desc_1_time - asc_1_time2safety - safety2surf - stop_t
        x = [0, desc_1_time, d1_bt, asc_1_time2safety, stop_t, safety2surf]
        y = [0, -d1, -d1, -6, -6, 0]
    else:
        asc_1_no_safety = t_per_m_asc_6 * d1
        d1_bt = t1 - desc_1_time - asc_1_no_safety
        x = [0, desc_1_time, d1_bt, asc_1_no_safety]
        y = [0, -d1, -d1, 0]

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


def calc_sac(start_p, end_p, vol, depth, avg_depth, t):
    if not np.isnan(avg_depth):
        usable_depth = avg_depth
    else:
        usable_depth = depth

    t = time_2_min(t)
    vol_gas_used = (start_p - end_p) * vol
    l_per_min_atdepth = vol_gas_used / t
    sac = l_per_min_atdepth / depth2pressure(usable_depth)
    return round(sac, 1)


def update_csv(csv, new_record_dict):
    contents = open(csv).readlines()
    header = contents[0].rstrip().split(',')
    no_dives = len(contents)
    last_dive = contents[-1].split(',')
    last_dive_end = last_dive[4]
    last_dive_date = last_dive[1]
    new_record_dict['time_out'] = min_2_time(time_2_min(new_record_dict['time_in']) +
                                             time_2_min(new_record_dict['duration']))

    if last_dive_date == new_record_dict['date']:
        new_record_dict['surf'] = min_2_time(time_2_min(new_record_dict['time_in']) - time_2_min(last_dive_end))
    else:
        new_record_dict['surf'] = 'NA'

    new_line = ','.join([str(no_dives)] + [str(new_record_dict[z]) for z in header if z != 'num'])
    with open(csv, 'a') as updating_csv:
        updating_csv.write('\n' + new_line)


def make_data_frame():

    csv_data = 'dive_data.csv'
    dd = pd.read_csv(csv_data, index_col='num')
    dd['SAC_rate'] = dd.apply(lambda x: calc_sac(x.start_pres, x.end_pres, x.volume, x.max_depth, x.avg_depth,
                                                 x.duration), axis=1)
    dd['profile'] = dd.apply(lambda x: est_profile(time_2_min(x.duration), x.max_depth), axis=1)
    return dd


class NewDiveWindow(QtGui.QDialog):
    def __init__(self, parent=None):
        super(NewDiveWindow, self).__init__(parent)

        self.setWindowTitle('New dive record')

        # data dict
        columns = ['date', 'time_in', 'duration', 'max_depth', 'avg_depth', 'temp',
                   'start_pres', 'end_pres', 'volume', 'with']

        label_texts = [y.replace('_', ' ') + ':' for y in columns]

        self.new_dive_data = {x: '' for x in columns + ['notes']}

        # start layouts
        d_window_layout = QtGui.QVBoxLayout()
        d_entry_layout = QtGui.QGridLayout()

        # entry objects
        date = QtGui.QLineEdit(self)
        QtGui.QLineEdit.connect(date, QtCore.SIGNAL('textChanged (const QString&)'), self.store_date)
        date.setPlaceholderText('dd_mm_yy')

        t_in = QtGui.QLineEdit(self)
        QtGui.QLineEdit.connect(t_in, QtCore.SIGNAL('textChanged (const QString&)'), self.store_t)
        t_in.setPlaceholderText('hh:mm')

        dur = QtGui.QLineEdit(self)
        QtGui.QLineEdit.connect(dur, QtCore.SIGNAL('textChanged (const QString&)'), self.store_dur)
        dur.setPlaceholderText('hh:mm')

        max_d = QtGui.QLineEdit(self)
        QtGui.QLineEdit.connect(max_d, QtCore.SIGNAL('textChanged (const QString&)'), self.store_max_d)
        max_d.setPlaceholderText('0.0')

        avg_d = QtGui.QLineEdit(self)
        QtGui.QLineEdit.connect(avg_d, QtCore.SIGNAL('textChanged (const QString&)'), self.store_avg_d)
        avg_d.setPlaceholderText('0.0')

        temp = QtGui.QLineEdit(self)
        QtGui.QLineEdit.connect(temp, QtCore.SIGNAL('textChanged (const QString&)'), self.store_temp)
        temp.setPlaceholderText('0')

        pres_1 = QtGui.QComboBox(self)
        for i in range(5, 235, 5):
            pres_1.addItem(str(i))
        QtGui.QComboBox.connect(pres_1, QtCore.SIGNAL('activated(const QString&)'), self.store_p1)

        pres_2 = QtGui.QComboBox(self)
        for i in range(5, 235, 5):
            pres_2.addItem(str(i))
        QtGui.QComboBox.connect(pres_2, QtCore.SIGNAL('activated(const QString&)'), self.store_p2)

        v = QtGui.QComboBox(self)
        for i in [7, 8, 10, 12, 14, 15, 16, 20, 24]:
            v.addItem(str(i))
        QtGui.QComboBox.connect(v, QtCore.SIGNAL('activated(const QString&)'), self.store_v)

        buds = QtGui.QLineEdit(self)
        QtGui.QLineEdit.connect(buds, QtCore.SIGNAL('textChanged (const QString&)'), self.store_buds)
        buds.setPlaceholderText('buddy1,buddy2')

        save_btn = QtGui.QPushButton('Save dive')
        save_btn.clicked.connect(self.save_dive)

        # entry list
        entries = [date, t_in, dur, max_d, avg_d, temp, pres_1, pres_2, v, buds]

        # populate layout
        row, column = 0, 0
        rows_per_box = 4

        for i in range(len(label_texts)):
            lab, val = label_texts[i], entries[i]

            qt_lab = QtGui.QLabel(lab, self)

            d_entry_layout.addWidget(qt_lab, row, column)
            d_entry_layout.addWidget(val, row, column + 1)

            if row == rows_per_box - 1:
                row = 0
                column += 2
            else:
                row += 1

        # notes box
        self.notes_box = QtGui.QTextEdit()
        QtGui.QTextEdit.connect(self.notes_box, QtCore.SIGNAL('textChanged ()'), self.store_notes)
        self.notes_box.setPlainText('notes')

        d_window_layout.addLayout(d_entry_layout)
        d_window_layout.addWidget(self.notes_box)
        d_window_layout.addWidget(save_btn)

        self.setLayout(d_window_layout)

    def store_date(self, text):
        self.new_dive_data['date'] = str(text)

    def store_t(self, text):
        self.new_dive_data['time_in'] = str(text)

    def store_dur(self, text):
        self.new_dive_data['duration'] = str(text)

    def store_max_d(self, text):
        self.new_dive_data['max_depth'] = float(text)

    def store_avg_d(self, text):
        self.new_dive_data['avg_depth'] = float(text)

    def store_temp(self, text):
        self.new_dive_data['temp'] = int(text)

    def store_p1(self, text):
        self.new_dive_data['start_pres'] = int(text)

    def store_p2(self, text):
        self.new_dive_data['end_pres'] = int(text)

    def store_v(self, text):
        self.new_dive_data['volume'] = int(text)

    def store_buds(self, text):
        self.new_dive_data['with'] = str(text)

    def store_notes(self):
        text = self.notes_box.toPlainText()
        self.new_dive_data['notes'] = str(text)

    def save_dive(self):

        missing_data = []
        for x in self.new_dive_data.keys():
            if self.new_dive_data[x] == '':
                missing_data.append(x)

        if len(missing_data) > 0:
            error_fields = ', '.join([y.replace('_', ' ') for y in missing_data])
            QtGui.QMessageBox.warning(self, 'Missing data',
                                      'You have not entered data for: {} please enter data!'.format(error_fields),
                                      QtGui.QMessageBox.Ok)

        else:
            self.accept()

    def get_record(self):
        return self.new_dive_data


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
            self.sum_plot.setLabel('bottom', 'Depth', 'm')
            self.sum_plot.setLabel('left', 'Dive count', '')

        elif text == 'duration':
            self.sum_plot.plotItem.clear()
            vals = [time_2_min(t) for t in self.dive_data_frame.duration.asobject]
            y, x = np.histogram(vals, bins=30)

            # We are required to use stepMode=True so that PlotCurveItem will interpret this data correctly.
            curve = pg.PlotCurveItem(x, y, stepMode=True, fillLevel=0, brush=(0, 0, 255, 150))
            self.sum_plot.addItem(curve)
            self.sum_plot.setLabel('bottom', 'Time', 'mins')
            self.sum_plot.setLabel('left', 'Dive count', '')

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
            self.sum_plot.setLabel('bottom', 'Number of dives', '')
            self.sum_plot.setLabel('left', 'SAC rate', 'l/min')


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
        add_dive_btn.clicked.connect(self.dive_entry)
        btn_layout.addWidget(add_dive_btn)
        btn_layout.addStretch()

        # make and populate list
        self.selection_pane = QtGui.QListWidget()
        for dive in self.dive_data.index:
            label = str(dive) + ' - ' + self.dive_data[dive-1: dive].date.asobject[0]
            dive_entry = QtGui.QListWidgetItem(label)
            self.selection_pane.addItem(dive_entry)

        # self.selection_pane.itemDoubleClicked.connect(self.open_tab)
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
        log_windows.addWidget(self.dive_tabs)

        whole_layout.addWidget(left_box)
        whole_layout.addLayout(log_windows)

        main_widget = QtGui.QWidget()
        main_widget.setLayout(whole_layout)
        self.setCentralWidget(main_widget)
        self.show()

    def dive_entry(self):

        entry_window = NewDiveWindow()

        if entry_window.exec_():
            new_record = entry_window.get_record()

            update_csv('dive_data.csv', new_record)

            # reload data
            self.dive_data = make_data_frame()

            # add latest entry
            dive = self.dive_data.index[-1]
            label = str(dive) + ' - ' + self.dive_data[dive - 1: dive].date.asobject[0]
            dive_entry = QtGui.QListWidgetItem(label)
            self.selection_pane.addItem(dive_entry)

            # todo update history graphs

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
