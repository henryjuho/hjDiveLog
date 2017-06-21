#!/usr/bin/env python

import sys
from PyQt4 import QtGui
from PyQt4 import QtCore
import pyqtgraph as pg
import numpy as np


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
        dive_notes = self.notes_box(dive_record['notes'])

        # add everything to main layout
        dw_layout.addLayout(top_boxes)
        dw_layout.addWidget(self.profile_box(dive_record['profile']))
        dw_layout.addWidget(dive_notes)
        self.setLayout(dw_layout)

    def dive_stats_box(self, record):

        labels = ['time_in', 'dive_time', 'time_out', 'max_depth', 'average_depth', 'temp']
        values = [record[x] for x in labels]

        dive_box = self.stats_box(labels, values, 'Dive stats', 3)

        return dive_box

    def gas_stats_box(self, record):

        labels = ['start_pressure', 'end_pressure', 'volume', 'SAC_rate']
        values = [record[x] for x in labels]

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


class SelectWindow(QtGui.QGroupBox):
    def __init__(self, parent=None):
        super(SelectWindow, self).__init__(parent)

        self.setTitle('Dive selection')
        self.setFixedWidth(300)

        sw_layout = QtGui.QVBoxLayout()

        # top buttons
        btn_layout = QtGui.QHBoxLayout()
        add_dive_btn = QtGui.QPushButton('+')
        btn_layout.addWidget(add_dive_btn)
        btn_layout.addStretch()

        selection_pane = QtGui.QListWidget()

        sw_layout.addWidget(selection_pane)
        sw_layout.addLayout(btn_layout)

        self.setLayout(sw_layout)


class Window(QtGui.QMainWindow):

    def __init__(self):
        super(Window, self).__init__()
        self.setGeometry(100, 100, 1050, 700)  # coords start from top left x, y, width, height
        self.setWindowTitle('hjDiveLog')

        # test data
        test_dive_record = {'time_in': '12:00', 'dive_time': '01:22', 'time_out': '13:22',
                            'max_depth': '12', 'average_depth': '8', 'temp': '14C',
                            'start_pressure': '200', 'end_pressure': '60', 'volume': '24',
                            'SAC_rate': '21', 'notes': 'This was a very exciting dive with over 3m vis',
                            'profile': (np.cumsum((0, 2, 72, 3, 3, 3)), (0, -12, -12, -6, -6, 0))}

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
        left_box = SelectWindow()

        # main dive info window
        log_windows = QtGui.QVBoxLayout()

        self.dive_tabs = QtGui.QTabWidget()
        self.dive_tabs.tab1 = DiveWindow(test_dive_record)
        self.dive_tabs.tab2 = QtGui.QWidget()
        self.dive_tabs.tab3 = QtGui.QWidget()

        self.dive_tabs.addTab(self.dive_tabs.tab1, "Tab 1")
        self.dive_tabs.addTab(self.dive_tabs.tab2, "Tab 2")
        self.dive_tabs.addTab(self.dive_tabs.tab3, "Tab 3")

        self.dive_tabs.setTabsClosable(True)

        self.dive_tabs.tabCloseRequested.connect(self.close_tab)
        log_windows.addWidget(self.dive_tabs)

        whole_layout.addWidget(left_box)
        whole_layout.addLayout(log_windows)

        main_widget = QtGui.QWidget()
        main_widget.setLayout(whole_layout)
        self.setCentralWidget(main_widget)
        self.show()

    def close_tab(self, currentIndex):

        current_tab = self.dive_tabs.widget(currentIndex)
        current_tab.deleteLater()
        self.dive_tabs.removeTab(currentIndex)

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
